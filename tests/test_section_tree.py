import unittest
from lumina_section_extractor.models import Heading
from lumina_section_extractor.section_tree import (
    build_section_tree,
    find_page_for_line,
    flatten_sections,
    parse_headings_from_markdown,
    tree_to_dict,
)


class TestSectionTree(unittest.TestCase):
    def test_find_page_for_line(self):
        page_map = [
            {"page": 1, "start_line": 1, "end_line": 10},
            {"page": 2, "start_line": 13, "end_line": 25},
        ]
        self.assertEqual(find_page_for_line(5, page_map), 1)
        self.assertEqual(find_page_for_line(15, page_map), 2)
        self.assertIsNone(find_page_for_line(5, None))

    def test_parse_headings_from_markdown(self):
        content = "# H1 Titulo\nTexto\n## H2 Subtitulo\n"
        headings = parse_headings_from_markdown(content)
        self.assertEqual(len(headings), 2)
        self.assertEqual(headings[0].level, 1)
        self.assertEqual(headings[0].title, "H1 Titulo")
        self.assertEqual(headings[1].level, 2)
        self.assertEqual(headings[1].title, "H2 Subtitulo")

    def test_build_section_tree_and_breadcrumbs(self):
        full_text = """
# 1. Termo de Referência
Conteúdo geral do termo de referência.

## 1.1 Objeto
Descrição detalhada do objeto.

### 1.1.1 Especificações
Itens técnicos do edital.

## 1.2 Justificativa
Razões da contratação.
"""
        headings = [
            Heading(line_number=2, level=1, title="1. Termo de Referência", raw="# 1. Termo de Referência"),
            Heading(line_number=5, level=2, title="1.1 Objeto", raw="## 1.1 Objeto"),
            Heading(line_number=8, level=3, title="1.1.1 Especificações", raw="### 1.1.1 Especificações"),
            Heading(line_number=11, level=2, title="1.2 Justificativa", raw="## 1.2 Justificativa"),
        ]

        tree = build_section_tree(headings, full_text)
        self.assertEqual(len(tree), 1)  # 1 seção raiz: H1

        root = tree[0]
        self.assertEqual(root.heading.title, "1. Termo de Referência")
        self.assertEqual(root.breadcrumb, ["1. Termo de Referência"])
        self.assertEqual(len(root.children), 2)  # H2: 1.1 Objeto e 1.2 Justificativa

        h2_objeto = root.children[0]
        self.assertEqual(h2_objeto.breadcrumb, ["1. Termo de Referência", "1.1 Objeto"])
        self.assertEqual(len(h2_objeto.children), 1)  # H3: 1.1.1 Especificações

        h3_espec = h2_objeto.children[0]
        self.assertEqual(
            h3_espec.breadcrumb,
            ["1. Termo de Referência", "1.1 Objeto", "1.1.1 Especificações"],
        )

        all_flat = flatten_sections(tree)
        self.assertEqual(len(all_flat), 4)

        tree_dict = tree_to_dict(tree)
        self.assertEqual(len(tree_dict), 1)
        self.assertEqual(tree_dict[0]["title"], "1. Termo de Referência")


if __name__ == "__main__":
    unittest.main()
