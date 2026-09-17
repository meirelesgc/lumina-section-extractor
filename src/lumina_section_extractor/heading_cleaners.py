import re
from collections import Counter
from typing import Callable, Sequence
from lumina_section_extractor.models import Heading

# Tipo funcional para um cleaner de cabeçalhos
HeadingCleaner = Callable[[list[Heading], str], list[Heading]]


def strip_markup(text: str) -> str:
    """Remove marcações Markdown e tags HTML simples do título."""
    # Remove marcações Markdown comuns: **, *, __, _, ~~
    cleaned = re.sub(r"(\*\*|__|\*|_|~~)", "", text)
    # Remove tags HTML simples como <u>, <mark>, <b>, etc.
    cleaned = re.sub(r"</?[a-zA-Z0-9_-]+[^>]*>", "", cleaned)
    # Remove múltiplos espaços
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def clean_markup(headings: list[Heading], full_text: str) -> list[Heading]:
    """Limpa marcações tipográficas e formatações dos títulos, preservando o raw."""
    for h in headings:
        h.title = strip_markup(h.title)
    return headings


def normalize_title(title: str) -> str:
    """Normaliza um título para fins de agrupamento e contagem de repetições."""
    # Minúsculas e apenas letras/números
    return re.sub(r"[^\w]+", "", title.lower())


def make_repeated_cleaner(min_occurrences: int = 3) -> HeadingCleaner:
    """Factory de cleaner funcional para descartar cabeçalhos/rodapés repetidos por página."""

    def cleaner(headings: list[Heading], full_text: str) -> list[Heading]:
        counts = Counter(normalize_title(h.title) for h in headings if normalize_title(h.title))
        filtered: list[Heading] = []
        for h in headings:
            norm = normalize_title(h.title)
            if not norm or counts[norm] < min_occurrences:
                filtered.append(h)
        return filtered

    return cleaner


def make_orphan_cleaner(min_chars: int = 20) -> HeadingCleaner:
    """Factory de cleaner funcional para descartar headings cujo conteúdo subsequente é vazio ou insignificante."""

    def cleaner(headings: list[Heading], full_text: str) -> list[Heading]:
        if not headings:
            return []

        lines = full_text.splitlines()
        total_lines = len(lines)
        filtered: list[Heading] = []

        for i, h in enumerate(headings):
            start_line = h.line_number  # linha logo após o heading
            end_line = headings[i + 1].line_number - 1 if i + 1 < len(headings) else total_lines

            # Pega o texto entre este heading e o próximo
            section_lines = lines[start_line:end_line]
            section_text = "\n".join(section_lines).strip()

            # Se for o último heading ou tiver conteúdo >= min_chars, mantém
            if len(section_text) >= min_chars:
                filtered.append(h)
            elif i + 1 < len(headings) and headings[i + 1].level > h.level:
                # Se for um título pai (ex: H1) que antecede um subtítulo (H2), mantém o pai mesmo sem corpo imediato
                filtered.append(h)

        return filtered

    return cleaner


def get_default_heading_cleaners() -> list[HeadingCleaner]:
    """Retorna a lista ordenada padrão de cleaners funcionais de cabeçalho."""
    return [
        clean_markup,
        make_repeated_cleaner(min_occurrences=3),
        make_orphan_cleaner(min_chars=20),
    ]


def run_heading_pipeline(
    headings: list[Heading],
    full_text: str,
    cleaners: Sequence[HeadingCleaner] | None = None,
) -> list[Heading]:
    """Executa sequencialmente os cleaners funcionais na lista de headings."""
    if cleaners is None:
        cleaners = get_default_heading_cleaners()

    current_headings = headings
    for cleaner in cleaners:
        current_headings = cleaner(current_headings, full_text)

    return current_headings
