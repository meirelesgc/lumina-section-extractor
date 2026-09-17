import re
from collections import Counter
from typing import Callable, Sequence
from lumina_section_extractor.models import Heading

# Tipo funcional para um cleaner de cabeçalhos
HeadingCleaner = Callable[[list[Heading], str], list[Heading]]

# Padrões de numeração e outlines formais de documentos jurídicos/editais brasileiros
NUMBERING_PATTERNS: list[tuple[re.Pattern[str], int]] = [
    # Nível 4: 1.1.1.1
    (re.compile(r"^\d+\.\d+\.\d+\.\d+"), 4),
    # Nível 3: 1.1.1
    (re.compile(r"^\d+\.\d+\.\d+"), 3),
    # Nível 2: 1.1, 2.3, etc. (evitando pegar 1.0 que é nível 1)
    (re.compile(r"^\d+\.[1-9]\d*"), 2),
    # Nível 1: 1.0, 1.0., 1., 2., 10., etc. (ex: '1.0. DO OBJETO:', '2.0 – DOS RECURSOS:')
    (re.compile(r"^\d+(\.0+)?\.?\s*[-–:]?\s+"), 1),
    # Nível 1: CLÁUSULA I, CLÁUSULA 1...
    (re.compile(r"^CL[ÁA]USULA\s+[IVXLCDM\d]+", re.IGNORECASE), 1),
    # Nível 1: ANEXO I, ANEXO 1...
    (re.compile(r"^ANEXO\s+[IVXLCDM\d]+", re.IGNORECASE), 1),
    # Nível 1: Títulos capitulares frequentes
    (re.compile(r"^(TERMO DE REFER[ÊE]NCIA|PRE[ÂA]MBULO|EDITAL)\b", re.IGNORECASE), 1),
]


def strip_markup(text: str) -> str:
    """Remove marcações Markdown (**, *, __, _, ~~) e tags HTML (<u>, <mark>, etc.)."""
    cleaned = re.sub(r"(\*\*|__|\*|_|~~)", "", text)
    cleaned = re.sub(r"</?[a-zA-Z0-9_-]+[^>]*>", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def text_between(full_text: str, h1: Heading, h2: Heading) -> str:
    """Retorna o texto delimitado entre a linha de h1 e a linha de h2."""
    lines = full_text.splitlines()
    start_line = h1.line_number
    end_line = h2.line_number - 1
    if start_line > end_line:
        return ""
    return "\n".join(lines[start_line:end_line])


def clean_markup(headings: list[Heading], full_text: str) -> list[Heading]:
    """Passo 1 da Pipeline: Normaliza texto sem side-effects estruturais.

    Pré-condição: Nenhuma.
    Garante que os títulos fiquem livres de asteriscos e tags, preservando o raw.
    """
    for h in headings:
        h.title = strip_markup(h.title)
    return headings


def normalize_title_for_counting(title: str) -> str:
    """Normaliza título para detecção de repetições por página."""
    return re.sub(r"[^\w]+", "", title.lower())


def make_repeated_cleaner(min_occurrences: int = 3) -> HeadingCleaner:
    """Passo 2 da Pipeline: Remove ruído puro de cabeçalho/rodapé repetido.

    Pré-condição: Títulos já normalizados por clean_markup.
    Precisa rodar antes do merge, senão títulos quebrados que foram fundidos
    nunca coincidem para contagem exata de repetição.
    """

    def cleaner(headings: list[Heading], full_text: str) -> list[Heading]:
        counts = Counter(
            normalize_title_for_counting(h.title)
            for h in headings
            if normalize_title_for_counting(h.title)
        )
        filtered: list[Heading] = []
        for h in headings:
            norm = normalize_title_for_counting(h.title)
            if not norm or counts[norm] < min_occurrences:
                filtered.append(h)
        return filtered

    return cleaner


def make_adjacent_merger(max_gap_chars: int = 5) -> HeadingCleaner:
    """Passo 3 da Pipeline: Funde títulos adjacentes quebrados em múltiplas linhas.

    Pré-condição: Texto já normalizado e cabeçalhos repetidos já eliminados.
    Quando dois headings consecutivos têm <= max_gap_chars de texto entre si,
    trata-se quase sempre da mesma linha lógica de título dividida pelo PDF
    (ex: '1.0. DO OBJETO:' + 'CONTRATAÇÃO DE EMPRESA ESPECIALIZADA...').
    """

    def cleaner(headings: list[Heading], full_text: str) -> list[Heading]:
        if not headings:
            return []

        merged: list[Heading] = []
        i = 0
        total = len(headings)

        while i < total:
            current = headings[i]

            # Funde consecutivamente enquanto o próximo estiver colado
            while i + 1 < total:
                nxt = headings[i + 1]
                gap = text_between(full_text, current, nxt)
                if len(gap.strip()) <= max_gap_chars:
                    current.title = f"{current.title} {nxt.title}".strip()
                    current.raw = f"{current.raw} {nxt.raw}".strip()
                    i += 1
                else:
                    break

            merged.append(current)
            i += 1

        return merged

    return cleaner


def reclassify_numbering_level(headings: list[Heading], full_text: str) -> list[Heading]:
    """Passo 4 da Pipeline: Corrige o nível hierárquico com base na numeração explícita do título.

    Pré-condição: Títulos já fundidos e corretos.
    O pymupdf4llm infere o nível de heading (#/##/###) pelo tamanho de fonte, o que é instável.
    A numeração explícita (1.0, 1.1, CLÁUSULA II, ANEXO I) é a fonte de verdade semântica.
    Quando nenhum padrão é encontrado, mantém o nível derivado de fonte como fallback.
    """
    for h in headings:
        matched = False
        clean_title = strip_markup(h.title)
        for pattern, level in NUMBERING_PATTERNS:
            if pattern.search(clean_title):
                h.level = level
                h.level_source = "numbering_pattern"
                matched = True
                break
        if not matched:
            h.level_source = "font"

    return headings


def make_orphan_cleaner(min_chars: int = 20) -> HeadingCleaner:
    """Passo 5 da Pipeline: Remove ruídos residuais genuínos.

    Pré-condição: Títulos fundidos e reclassificados.
    Como os títulos quebrados foram fundidos no Passo 3, qualquer heading que ainda tenha
    conteúdo menor que min_chars é um ruído real, a menos que seja um título pai de uma
    subseção subsequente com nível semântico reconhecido.
    """

    def cleaner(headings: list[Heading], full_text: str) -> list[Heading]:
        if not headings:
            return []

        lines = full_text.splitlines()
        total_lines = len(lines)
        filtered: list[Heading] = []

        for i, h in enumerate(headings):
            start_line = h.line_number
            end_line = headings[i + 1].line_number - 1 if i + 1 < len(headings) else total_lines

            section_lines = lines[start_line:end_line]
            section_text = "\n".join(section_lines).strip()

            # Mantém se tiver texto substancial
            if len(section_text) >= min_chars:
                filtered.append(h)
            # Ou mantém se for um cabeçalho estruturado pai que antecede um subtítulo
            elif i + 1 < len(headings) and headings[i + 1].level > h.level:
                filtered.append(h)
            elif h.level_source == "numbering_pattern" and i + 1 < len(headings):
                # Títulos com numeração explícita (ex: 1.0, Cláusula) nunca são descartados como órfãos se houver seções seguintes
                filtered.append(h)

        return filtered

    return cleaner


def get_default_heading_cleaners() -> list[HeadingCleaner]:
    """Retorna a sequência ordenada padrão de cleaners funcionais de cabeçalho.

    A ordem é estrita e documentada:
    1. clean_markup: normaliza o texto sem efeitos colaterais estruturais.
    2. make_repeated_cleaner: remove ruído puro repetido por página (antes da fusão).
    3. make_adjacent_merger: funde títulos quebrados em linhas adjacentes.
    4. reclassify_numbering_level: reclassifica o nível com base na numeração explícita.
    5. make_orphan_cleaner: elimina ruídos residuais reais com segurança.
    """
    return [
        clean_markup,
        make_repeated_cleaner(min_occurrences=3),
        make_adjacent_merger(max_gap_chars=5),
        reclassify_numbering_level,
        make_orphan_cleaner(min_chars=20),
    ]


def run_heading_pipeline(
    headings: list[Heading],
    full_text: str,
    cleaners: Sequence[HeadingCleaner] | None = None,
) -> list[Heading]:
    """Executa sequencialmente a pipeline ordenada de cleaners funcionais nos headings."""
    if cleaners is None:
        cleaners = get_default_heading_cleaners()

    current_headings = headings
    for cleaner in cleaners:
        current_headings = cleaner(current_headings, full_text)

    return current_headings
