import tempfile
import unittest
from pathlib import Path
from lumina_section_extractor.extract_titles import (
    extract_titles_from_content,
    format_titles_as_markdown,
    process_markdown_file,
)


class TestExtractTitles(unittest.TestCase):
    def test_extract_titles_from_content(self):
        sample_content = """
# 1. Introdução

Este é o texto inicial.

## 1.1 Contexto Geral
Mais texto aqui.

### Detalhe A
Texto com # dentro da frase (não é título).

#### Nível 4
##### Nível 5
###### Nível 6
"""
        titles = extract_titles_from_content(sample_content)

        self.assertEqual(len(titles), 6)
        self.assertEqual(titles[0]["level"], 1)
        self.assertEqual(titles[0]["title"], "1. Introdução")
        self.assertEqual(titles[0]["line_number"], 2)

        self.assertEqual(titles[1]["level"], 2)
        self.assertEqual(titles[1]["title"], "1.1 Contexto Geral")

        self.assertEqual(titles[2]["level"], 3)
        self.assertEqual(titles[2]["title"], "Detalhe A")

        self.assertEqual(titles[5]["level"], 6)
        self.assertEqual(titles[5]["title"], "Nível 6")

    def test_process_markdown_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_path = Path(tmp_dir_str)
            input_file = tmp_path / "exemplo.md"
            input_file.write_text("# Seção Principal\n\n## Subseção\n", encoding="utf-8")

            out_dir = tmp_path / "saida"
            result = process_markdown_file(input_file, out_dir)

            self.assertEqual(result["count"], 2)

            md_out = out_dir / "exemplo_titles.md"
            json_out = out_dir / "exemplo_titles.json"

            self.assertTrue(md_out.exists())
            self.assertTrue(json_out.exists())

            json_content = json_out.read_text(encoding="utf-8")
            self.assertIn('"title": "Seção Principal"', json_content)
            self.assertIn('"title": "Subseção"', json_content)


if __name__ == "__main__":
    unittest.main()
