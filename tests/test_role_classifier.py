import unittest
from lumina_section_extractor.models import Heading, Section, SectionRole
from lumina_section_extractor.role_classifier import (
    AliasRoleClassifier,
    PositionalAbstractFallbackClassifier,
    SectionRolePipeline,
    classify_section_roles,
)


def create_mock_section(title: str, content: str = "Texto da seção.") -> Section:
    heading = Heading(line_number=1, level=1, title=title, raw=f"# {title}")
    return Section(heading=heading, content=content)


class TestRoleClassifier(unittest.TestCase):
    def test_alias_role_classifier_explicit(self):
        sections = [
            create_mock_section("Resumo", "Resumo do trabalho em português."),
            create_mock_section("1. Introdução", "Texto da introdução."),
            create_mock_section("2. Metodologia", "Métodos aplicados."),
            create_mock_section("3. Resultados e Discussão", "Dados obtidos."),
            create_mock_section("4. Conclusão", "Considerações finais."),
            create_mock_section("Referências Bibliográficas", "[1] Artigo A."),
        ]

        classifier = AliasRoleClassifier()
        classified = classifier.classify(sections)

        self.assertEqual(classified[0].role, SectionRole.ABSTRACT)
        self.assertEqual(classified[0].role_confidence, "alias_match")

        self.assertEqual(classified[1].role, SectionRole.INTRODUCTION)
        self.assertEqual(classified[1].role_confidence, "alias_match")

        self.assertEqual(classified[2].role, SectionRole.METHODOLOGY)
        self.assertEqual(classified[3].role, SectionRole.RESULTS)
        self.assertEqual(classified[4].role, SectionRole.CONCLUSION)
        self.assertEqual(classified[5].role, SectionRole.REFERENCES)

    def test_alias_does_not_overwrite_existing_role(self):
        sec = create_mock_section("1. Introdução")
        sec.role = SectionRole.TITLE_BLOCK
        sec.role_confidence = "manual_override"

        classifier = AliasRoleClassifier()
        classified = classifier.classify([sec])

        self.assertEqual(classified[0].role, SectionRole.TITLE_BLOCK)
        self.assertEqual(classified[0].role_confidence, "manual_override")

    def test_positional_abstract_fallback(self):
        # Cenário de artigo sem cabeçalho explícito de Abstract antes de INTRODUCTION
        sections = [
            create_mock_section(
                "Análise de Desempenho em Redes",
                "Autores: Silva et al.\nAbstract: Este artigo apresenta um estudo detalhado...",
            ),
            create_mock_section("1. Introduction", "A área de redes tem crescido..."),
            create_mock_section("2. Methods", "Utilizamos simulação..."),
        ]

        # Camada 1 não detecta Abstract porque o título da seção 0 é o título do artigo
        alias_clf = AliasRoleClassifier()
        alias_clf.classify(sections)
        self.assertEqual(sections[0].role, SectionRole.UNKNOWN)
        self.assertEqual(sections[1].role, SectionRole.INTRODUCTION)

        # Camada 2 aplica o fallback posicional
        fallback_clf = PositionalAbstractFallbackClassifier()
        fallback_clf.classify(sections)

        self.assertEqual(sections[0].role, SectionRole.ABSTRACT)
        self.assertEqual(sections[0].role_confidence, "positional_fallback")
        self.assertEqual(sections[1].role, SectionRole.INTRODUCTION)

    def test_positional_abstract_fallback_with_title_block(self):
        # Cenário com título separado e bloco preliminar sem heading antes da introdução
        sections = [
            create_mock_section("Título do Artigo Científico", "Autores e afiliações"),
            create_mock_section("Texto Preliminar", "Resumo implícito sem título formal"),
            create_mock_section("1. Introdução", "Texto da introdução"),
        ]

        pipeline = SectionRolePipeline()
        classified = pipeline.run(sections)

        self.assertEqual(classified[0].role, SectionRole.TITLE_BLOCK)
        self.assertEqual(classified[0].role_confidence, "positional_header")
        self.assertEqual(classified[1].role, SectionRole.ABSTRACT)
        self.assertEqual(classified[1].role_confidence, "positional_fallback")
        self.assertEqual(classified[2].role, SectionRole.INTRODUCTION)

    def test_positional_fallback_not_triggered_if_abstract_exists(self):
        sections = [
            create_mock_section("Abstract", "Conteúdo do resumo"),
            create_mock_section("1. Introduction", "Texto da introdução"),
        ]
        pipeline = SectionRolePipeline()
        classified = pipeline.run(sections)

        self.assertEqual(classified[0].role, SectionRole.ABSTRACT)
        self.assertEqual(classified[0].role_confidence, "alias_match")
        self.assertEqual(classified[1].role, SectionRole.INTRODUCTION)

    def test_convenience_function(self):
        sections = [create_mock_section("Abstract"), create_mock_section("1. Introdução")]
        result = classify_section_roles(sections)
        self.assertEqual(result[0].role, SectionRole.ABSTRACT)
        self.assertEqual(result[1].role, SectionRole.INTRODUCTION)


if __name__ == "__main__":
    unittest.main()
