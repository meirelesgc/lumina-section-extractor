import re
import unicodedata
from abc import ABC, abstractmethod
from typing import Sequence
from lumina_section_extractor.heading_cleaners import strip_markup
from lumina_section_extractor.models import Section, SectionRole

ROLE_ALIASES: dict[SectionRole, list[str]] = {
    SectionRole.ABSTRACT: [
        r"^resumo$",
        r"^abstract$",
        r"^resumo\s*/\s*abstract$",
        r"^resumen$",
        r"^summary$",
        r"^sinopse$",
    ],
    SectionRole.INTRODUCTION: [
        r"^\d*\.?\s*introdu[çc][ãa]o$",
        r"^\d*\.?\s*introduction$",
        r"^1\.?\s*introdu[çc][ãa]o$",
        r"^1\.?\s*introduction$",
    ],
    SectionRole.METHODOLOGY: [
        r"materials?\s+and\s+methods?",
        r"materiais?\s+e\s+m[ée]todos?",
        r"materiais?\s+e\s+procedimentos?",
        r"metodologia",
        r"methodology",
        r"m[ée]todos?",
        r"methods?",
        r"procedimentos?\s+metodol[óo]gicos?",
    ],
    SectionRole.RESULTS: [
        r"^\d*\.?\s*resultados?$",
        r"^\d*\.?\s*results?$",
        r"resultados?\s+e\s+discuss[ãa]o",
        r"results?\s+and\s+discussion",
    ],
    SectionRole.DISCUSSION: [
        r"^\d*\.?\s*discuss[ãa]o$",
        r"^\d*\.?\s*discussion$",
    ],
    SectionRole.CONCLUSION: [
        r"conclus[ãa]o",
        r"conclus[õo]es",
        r"conclusion",
        r"conclusions?",
        r"concluding\s+remarks",
        r"considera[çc][õo]es\s+finais",
    ],
    SectionRole.REFERENCES: [
        r"refer[êe]ncias",
        r"refer[êe]ncias\s+bibliogr[áa]ficas",
        r"references",
        r"bibliography",
    ],
}


def normalize_title_for_alias(title: str) -> str:
    """Remove pontuações, tags e normaliza o título para o casamento com regexes."""
    cleaned = strip_markup(title)
    # Remove numeração inicial de outline (ex: '1. Introdução' -> 'Introdução', '3.1 Resultados' -> 'Resultados')
    cleaned = re.sub(r"^\d+[\.\d*]*\s*[-–:]?\s*", "", cleaned)
    # Remove caracteres de pontuação no final (ex: 'Abstract.' -> 'Abstract', 'Resumo:' -> 'Resumo')
    cleaned = re.sub(r"[:\.\-_]+$", "", cleaned)
    return cleaned.strip().lower()


class RoleClassifier(ABC):
    """Interface base para classificadores determinísticos de papéis de seções."""

    @abstractmethod
    def classify(self, sections: list[Section]) -> list[Section]:
        """Classifica e enriquece a lista de seções com seus respectivos papéis semânticos."""
        pass


class AliasRoleClassifier(RoleClassifier):
    """Camada 1: Classificação determinística baseada em regex de aliases."""

    def __init__(self, aliases: dict[SectionRole, list[str]] | None = None):
        self.aliases = aliases or ROLE_ALIASES

    def classify(self, sections: list[Section]) -> list[Section]:
        for s in sections:
            # Não sobrescreve papéis já preenchidos
            if s.role and s.role != SectionRole.UNKNOWN:
                continue

            normalized_title = normalize_title_for_alias(s.title)

            for role, patterns in self.aliases.items():
                if any(
                    re.search(p, normalized_title, re.IGNORECASE)
                    or re.search(p, s.title.strip().lower(), re.IGNORECASE)
                    for p in patterns
                ):
                    s.role = role
                    s.role_confidence = "alias_match"
                    break

        return sections


class PositionalAbstractFallbackClassifier(RoleClassifier):
    """Camada 2: Fallback posicional para detectar a seção Resumo/Abstract ausente de cabeçalho."""

    def classify(self, sections: list[Section]) -> list[Section]:
        # Se já existir alguma seção classificada como ABSTRACT, não aciona fallback
        has_abstract = any(s.role == SectionRole.ABSTRACT for s in sections)
        if has_abstract:
            return sections

        # Localiza a primeira seção classificada como INTRODUCTION
        for idx, s in enumerate(sections):
            if s.role == SectionRole.INTRODUCTION and idx > 0:
                target = sections[idx - 1]

                # Se a seção anterior não tiver role definido ou for UNKNOWN
                if not target.role or target.role == SectionRole.UNKNOWN:
                    target.role = SectionRole.ABSTRACT
                    target.role_confidence = "positional_fallback"

                    # Se houver uma seção antes do abstract (ex: título do artigo na posição 0)
                    if idx - 1 > 0:
                        prev = sections[idx - 2]
                        if not prev.role or prev.role == SectionRole.UNKNOWN:
                            prev.role = SectionRole.TITLE_BLOCK
                            prev.role_confidence = "positional_header"
                    elif idx == 1 and target.level == 1:
                        # Se for a única seção antes da introdução, o conteúdo geralmente traz título + abstract
                        # Pode ser marcado diretamente como ABSTRACT conforme a especificação
                        pass

                break

        return sections


class SectionRolePipeline:
    """Orquestrador sequencial das camadas de classificação de papéis."""

    def __init__(self, classifiers: Sequence[RoleClassifier] | None = None):
        self.classifiers = list(
            classifiers
            if classifiers is not None
            else [
                AliasRoleClassifier(),
                PositionalAbstractFallbackClassifier(),
            ]
        )

    def run(self, sections: list[Section]) -> list[Section]:
        current_sections = sections
        for classifier in self.classifiers:
            current_sections = classifier.classify(current_sections)
        return current_sections


def classify_section_roles(sections: list[Section]) -> list[Section]:
    """Função de conveniência para executar a pipeline padrão de classificação de roles."""
    pipeline = SectionRolePipeline()
    return pipeline.run(sections)
