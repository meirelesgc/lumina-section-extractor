"""Localização física (página + retângulos) de intervalos de texto do markdown.

Ponte texto → PDF:
  1. Estágio 1 guarda, por página, os `page_boxes` do pymupdf4llm (bbox + offsets `pos`).
  2. Um intervalo [start, end) do markdown consolidado é convertido nos boxes que ele toca.
  3. Dentro de cada box, os tokens do markdown são alinhados às palavras reais do PDF
     (`page.get_text("words")`) para obter retângulos por linha. Se o alinhamento falhar
     (imagem, tabela rasterizada), cai para o bbox do bloco.

Todas as funções são puras, exceto pela leitura de palavras via um `words_by_page` injetado.
"""

import re
from difflib import SequenceMatcher
from typing import Any, Callable

# Classes de box do pymupdf4llm que não carregam texto de conteúdo
IGNORED_BOX_CLASSES = frozenset({"page-header", "page-footer", "picture"})

# Marcações markdown que não existem no texto do PDF
_MARKUP_RE = re.compile(r"[*_`#|>\\]+")
_SEPARATOR_RE = re.compile(r"^[-:\s]*$")

Rect = tuple[float, float, float, float]
Word = tuple[float, float, float, float, str, int, int, int]
WordsProvider = Callable[[int], list[Word]]


def normalize_token(token: str) -> str:
    return _MARKUP_RE.sub("", token).lower()


def tokenize_with_offsets(text: str, base: int = 0) -> list[tuple[str, int]]:
    """Tokens normalizados (sem markup) com o offset absoluto de cada um."""
    tokens: list[tuple[str, int]] = []
    for match in re.finditer(r"\S+", text):
        raw = match.group()
        if _SEPARATOR_RE.match(raw):
            continue
        norm = normalize_token(raw)
        if norm:
            tokens.append((norm, base + match.start()))
    return tokens


def char_range_to_blocks(
    pages: list[dict[str, Any]], start: int, end: int
) -> list[dict[str, Any]]:
    """Boxes de conteúdo que intersectam [start, end) do markdown consolidado.

    Cada item traz `page`, `bbox`, `class` e o intervalo global [box_start, box_end) do box.
    """
    blocks: list[dict[str, Any]] = []
    for page in pages:
        base = page.get("char_start", 0)
        for box in page.get("boxes", []):
            if box["class"] in IGNORED_BOX_CLASSES:
                continue
            box_start = base + box["pos"][0]
            box_end = base + box["pos"][1]
            if box_start < end and box_end > start:
                blocks.append(
                    {
                        "page": page["page"],
                        "bbox": tuple(box["bbox"]),
                        "class": box["class"],
                        "box_start": box_start,
                        "box_end": box_end,
                    }
                )
    return blocks


def _center_inside(word: Word, bbox: Rect, tol: float = 1.5) -> bool:
    cx = (word[0] + word[2]) / 2
    cy = (word[1] + word[3]) / 2
    return bbox[0] - tol <= cx <= bbox[2] + tol and bbox[1] - tol <= cy <= bbox[3] + tol


def _union(rects: list[Rect]) -> Rect:
    return (
        min(r[0] for r in rects),
        min(r[1] for r in rects),
        max(r[2] for r in rects),
        max(r[3] for r in rects),
    )


def words_to_line_rects(words: list[Word]) -> list[Rect]:
    """Agrupa palavras por (block_no, line_no) e une seus retângulos, como no sistema real.

    Depois funde grupos na mesma linha visual (ex.: marcador "a)" que o PyMuPDF separa
    do texto em outro line_no).
    """
    groups: dict[tuple[int, int], list[Rect]] = {}
    for w in words:
        groups.setdefault((w[5], w[6]), []).append((w[0], w[1], w[2], w[3]))

    merged: list[Rect] = []
    for rect in sorted((_union(rs) for rs in groups.values()), key=lambda r: (r[1], r[0])):
        if merged:
            prev = merged[-1]
            overlap = min(prev[3], rect[3]) - max(prev[1], rect[1])
            if overlap > 0.5 * min(prev[3] - prev[1], rect[3] - rect[1]):
                merged[-1] = _union([prev, rect])
                continue
        merged.append(rect)
    return merged


def refine_block_to_line_rects(
    markdown: str,
    block: dict[str, Any],
    start: int,
    end: int,
    words: list[Word],
    min_match_ratio: float = 0.3,
) -> list[Rect]:
    """Retângulos por linha do trecho [start, end) dentro de um único box.

    Alinha os tokens do markdown do box com as palavras do PDF contidas no bbox
    (difflib) e devolve as linhas das palavras correspondentes ao trecho. Sem
    alinhamento confiável, devolve o bbox do bloco inteiro.
    """
    fallback = [tuple(float(v) for v in block["bbox"])]

    box_words = sorted(
        (w for w in words if _center_inside(w, block["bbox"])),
        key=lambda w: (w[5], w[6], w[7]),
    )
    box_tokens = tokenize_with_offsets(
        markdown[block["box_start"] : block["box_end"]], base=block["box_start"]
    )
    if not box_words or not box_tokens:
        return fallback

    word_tokens = [(i, normalize_token(w[4])) for i, w in enumerate(box_words)]
    word_tokens = [(i, t) for i, t in word_tokens if t]
    if not word_tokens:
        return fallback

    matcher = SequenceMatcher(
        None, [t for t, _ in box_tokens], [t for _, t in word_tokens], autojunk=False
    )
    matched = matcher.get_matching_blocks()
    matched_count = sum(m.size for m in matched)
    if matched_count / len(box_tokens) < min_match_ratio:
        return fallback

    token_to_word: dict[int, int] = {}
    for m in matched:
        for k in range(m.size):
            token_to_word[m.a + k] = word_tokens[m.b + k][0]

    selected = [
        token_to_word[i]
        for i, (_, offset) in enumerate(box_tokens)
        if start <= offset < end and i in token_to_word
    ]
    if not selected:
        return fallback

    lo, hi = min(selected), max(selected)
    return words_to_line_rects(box_words[lo : hi + 1])


def locate_range(
    pages: list[dict[str, Any]],
    markdown: str,
    start: int,
    end: int,
    words_provider: WordsProvider,
) -> list[dict[str, Any]]:
    """Retângulos por linha [{page, x1, y1, x2, y2}] para o intervalo [start, end) do markdown."""
    result: list[dict[str, Any]] = []
    for block in char_range_to_blocks(pages, start, end):
        rects = refine_block_to_line_rects(
            markdown, block, start, end, words_provider(block["page"])
        )
        for r in rects:
            result.append(rect_to_contract(block["page"], r))
    return result


def rect_to_contract(page: int, rect: Rect) -> dict[str, Any]:
    """[x0, y0, x1, y1] → {page, x1, y1, x2, y2} (contrato do frontend, com página no rect)."""
    return {
        "page": page,
        "x1": round(float(rect[0]), 2),
        "y1": round(float(rect[1]), 2),
        "x2": round(float(rect[2]), 2),
        "y2": round(float(rect[3]), 2),
    }


def page_sizes_from_pages(pages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Dimensões (pontos PDF, origem topo-esquerda) e rotação por página, para o frontend escalar."""
    return {
        str(p["page"]): {
            "width": p.get("width"),
            "height": p.get("height"),
            "rotation": p.get("rotation", 0),
        }
        for p in pages
    }
