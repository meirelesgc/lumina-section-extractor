import unittest
from lumina_section_extractor.heading_cleaners import (
    clean_markup,
    make_orphan_cleaner,
    make_repeated_cleaner,
    run_heading_pipeline,
    strip_markup,
)
from lumina_section_extractor.models import Heading


class TestHeadingCleaners(unittest.TestCase):
    def test_strip_markup(self):
        self.assertEqual(strip_markup("**Título em Negrito**"), "Título em Negrito")
        self.assertEqual(strip_markup("<u>Sublinhado</u>"), "Sublinhado")
        self.assertEqual(strip_markup("<mark>Destaque</mark> com *itálico*"), "Destaque com itálico")

    def test_clean_markup(self):
        headings = [
            Heading(line_number=1, level=1, title="**1. INTRODUÇÃO**", raw="# **1. INTRODUÇÃO**"),
            Heading(line_number=5, level=2, title="<u>1.1 Detalhes</u>", raw="## <u>1.1 Detalhes</u>"),
        ]
        cleaned = clean_markup(headings, "")
        self.assertEqual(cleaned[0].title, "1. INTRODUÇÃO")
        self.assertEqual(cleaned[1].title, "1.1 Detalhes")

    def test_make_repeated_cleaner(self):
        cleaner = make_repeated_cleaner(min_occurrences=3)
        headings = [
            Heading(line_number=1, level=1, title="Secretaria Municipal", raw="# Secretaria Municipal"),
            Heading(line_number=20, level=1, title="Secretaria Municipal", raw="# Secretaria Municipal"),
            Heading(line_number=40, level=1, title="Secretaria Municipal", raw="# Secretaria Municipal"),
            Heading(line_number=10, level=2, title="Objeto do Edital", raw="## Objeto do Edital"),
        ]
        filtered = cleaner(headings, "")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].title, "Objeto do Edital")

    def test_make_orphan_cleaner(self):
        full_text = """
# 1. Título Vazio
# 2. Título com Conteúdo Real
Este é um parágrafo que tem mais de vinte caracteres com certeza absoluta.
# 3. Outro Título
"""
        headings = [
            Heading(line_number=2, level=1, title="1. Título Vazio", raw="# 1. Título Vazio"),
            Heading(line_number=3, level=1, title="2. Título com Conteúdo Real", raw="# 2. Título com Conteúdo Real"),
            Heading(line_number=5, level=1, title="3. Outro Título", raw="# 3. Outro Título"),
        ]
        cleaner = make_orphan_cleaner(min_chars=20)
        filtered = cleaner(headings, full_text)
        titles = [h.title for h in filtered]
        self.assertNotIn("1. Título Vazio", titles)
        self.assertIn("2. Título com Conteúdo Real", titles)

    def test_run_heading_pipeline(self):
        full_text = """
# **Secretaria de Saúde**
# **Secretaria de Saúde**
# **Secretaria de Saúde**
# **1. DISPOSIÇÕES GERAIS**
Texto explicativo com extensão suficiente para não ser órfão de forma alguma.
"""
        headings = [
            Heading(line_number=2, level=1, title="**Secretaria de Saúde**", raw="# **Secretaria de Saúde**"),
            Heading(line_number=3, level=1, title="**Secretaria de Saúde**", raw="# **Secretaria de Saúde**"),
            Heading(line_number=4, level=1, title="**Secretaria de Saúde**", raw="# **Secretaria de Saúde**"),
            Heading(line_number=5, level=1, title="**1. DISPOSIÇÕES GERAIS**", raw="# **1. DISPOSIÇÕES GERAIS**"),
        ]
        result = run_heading_pipeline(headings, full_text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "1. DISPOSIÇÕES GERAIS")


if __name__ == "__main__":
    unittest.main()
