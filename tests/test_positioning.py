import unittest
from lumina_section_extractor.chunking import create_default_text_splitter, sections_to_documents
from lumina_section_extractor.models import Heading, Section
from lumina_section_extractor.positioning import (
    char_range_to_blocks,
    locate_range,
    rect_to_contract,
    words_to_line_rects,
)
from lumina_section_extractor.section_tree import (
    build_section_tree,
    parse_headings_from_markdown,
)

MD = "# Titulo\n\nO fornecedor deve **apresentar** certidao negativa.\n\n## Outro\n\nTexto final aqui."

# palavras PyMuPDF: (x0, y0, x1, y1, texto, block, line, word)
WORDS = [
    (10, 100, 40, 110, "O", 0, 0, 0),
    (42, 100, 90, 110, "fornecedor", 0, 0, 1),
    (92, 100, 120, 110, "deve", 0, 0, 2),
    (10, 112, 80, 122, "apresentar", 0, 1, 0),
    (82, 112, 130, 122, "certidao", 0, 1, 1),
    (132, 112, 170, 122, "negativa.", 0, 1, 2),
]


def make_pages():
    start = MD.index("O fornecedor")
    end = MD.index("negativa.") + len("negativa.")
    return [
        {
            "page": 1,
            "char_start": 0,
            "boxes": [
                {"class": "page-header", "bbox": [0, 0, 10, 10], "pos": [0, 8]},
                {"class": "text", "bbox": [5, 95, 175, 125], "pos": [start, end]},
            ],
        }
    ]


class TestPositioning(unittest.TestCase):
    def test_section_offsets_reproduce_content(self):
        tree = build_section_tree(parse_headings_from_markdown(MD), MD)
        sec = tree[0]
        self.assertEqual(MD[sec.char_start : sec.char_end], sec.content)

    def test_chunk_offsets_reproduce_text_and_unique_ids(self):
        tree = build_section_tree(parse_headings_from_markdown(MD), MD)
        docs = sections_to_documents(
            [tree[0], tree[0].children[0]], "x.md", create_default_text_splitter(20, 5)
        )
        self.assertEqual(len({d.metadata["chunk_id"] for d in docs}), len(docs))
        for d in docs:
            m = d.metadata
            self.assertIn(MD[m["char_start"] : m["char_end"]], d.page_content)

    def test_char_range_ignores_header_and_out_of_range(self):
        blocks = char_range_to_blocks(make_pages(), 0, len(MD))
        self.assertEqual([b["class"] for b in blocks], ["text"])
        self.assertEqual(char_range_to_blocks(make_pages(), 0, 3), [])

    def test_locate_range_line_rects_ignore_markup(self):
        rects = locate_range(make_pages(), MD, MD.index("O fornecedor"), MD.index("negativa.") + 9, lambda p: WORDS)
        self.assertEqual(len(rects), 2)
        self.assertEqual(rects[0], {"page": 1, "x1": 10, "y1": 100, "x2": 120, "y2": 110})

    def test_locate_partial_range_selects_only_matching_lines(self):
        start = MD.index("apresentar") - 2  # dentro do markup '**'
        rects = locate_range(make_pages(), MD, start, MD.index("negativa.") + 9, lambda p: WORDS)
        self.assertEqual(len(rects), 1)
        self.assertEqual(rects[0]["y1"], 112)

    def test_fallback_to_block_bbox_without_words(self):
        rects = locate_range(make_pages(), MD, MD.index("O fornecedor"), MD.index("negativa."), lambda p: [])
        self.assertEqual(rects, [rect_to_contract(1, (5, 95, 175, 125))])

    def test_merges_marker_on_same_visual_line(self):
        words = [(0, 10, 8, 20, "a)", 0, 0, 0), (12, 10.5, 90, 20.5, "texto", 0, 1, 0)]
        self.assertEqual(len(words_to_line_rects(words)), 1)


if __name__ == "__main__":
    unittest.main()
