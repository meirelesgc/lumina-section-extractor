import unittest
from lumina_section_extractor.heading_cleaners import (
    clean_markup,
    make_adjacent_merger,
    make_orphan_cleaner,
    make_repeated_cleaner,
    reclassify_numbering_level,
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

    def test_make_adjacent_merger(self):
        full_text = """
#### 1.0. DO OBJETO:

#### CONTRATAÇÃO DE EMPRESA ESPECIALIZADA EM AQUISIÇÃO DE MATERIAL

Compõem este Edital os seguintes anexos com mais de vinte caracteres.
"""
        headings = [
            Heading(line_number=2, level=4, title="1.0. DO OBJETO:", raw="#### 1.0. DO OBJETO:"),
            Heading(
                line_number=4,
                level=4,
                title="CONTRATAÇÃO DE EMPRESA ESPECIALIZADA EM AQUISIÇÃO DE MATERIAL",
                raw="#### CONTRATAÇÃO DE EMPRESA ESPECIALIZADA EM AQUISIÇÃO DE MATERIAL",
            ),
        ]
        merger = make_adjacent_merger(max_gap_chars=5)
        merged = merger(headings, full_text)
        self.assertEqual(len(merged), 1)
        self.assertEqual(
            merged[0].title,
            "1.0. DO OBJETO: CONTRATAÇÃO DE EMPRESA ESPECIALIZADA EM AQUISIÇÃO DE MATERIAL",
        )
        self.assertEqual(merged[0].line_number, 2)

    def test_reclassify_numbering_level(self):
        headings = [
            Heading(line_number=1, level=4, title="1.0. DO OBJETO:", raw="#### 1.0. DO OBJETO:"),
            Heading(line_number=5, level=4, title="1.1 ESPECIFICAÇÕES", raw="#### 1.1 ESPECIFICAÇÕES"),
            Heading(line_number=10, level=4, title="1.1.1 Detalhe Técnico", raw="#### 1.1.1 Detalhe Técnico"),
            Heading(line_number=15, level=6, title="CLÁUSULA II – DO PREÇO", raw="###### CLÁUSULA II – DO PREÇO"),
            Heading(line_number=20, level=4, title="ANEXO IV - TERMO", raw="#### ANEXO IV - TERMO"),
            Heading(line_number=25, level=2, title="Justificativa Sem Número", raw="## Justificativa Sem Número"),
        ]
        reclassified = reclassify_numbering_level(headings, "")
        self.assertEqual(reclassified[0].level, 1)
        self.assertEqual(reclassified[0].level_source, "numbering_pattern")

        self.assertEqual(reclassified[1].level, 2)
        self.assertEqual(reclassified[1].level_source, "numbering_pattern")

        self.assertEqual(reclassified[2].level, 3)
        self.assertEqual(reclassified[2].level_source, "numbering_pattern")

        self.assertEqual(reclassified[3].level, 1)
        self.assertEqual(reclassified[3].level_source, "numbering_pattern")

        self.assertEqual(reclassified[4].level, 1)
        self.assertEqual(reclassified[4].level_source, "numbering_pattern")

        # Mantém fonte como fallback
        self.assertEqual(reclassified[5].level, 2)
        self.assertEqual(reclassified[5].level_source, "font")

    def test_full_pipeline_preserves_objeto_lines_38_42(self):
        full_text = """
#### **<mark>1.0. DO OBJETO:</mark>**

#### **CONTRATAÇÃO DE EMPRESA ESPECIALIZADA EM AQUISIÇÃO DE MATERIAL DE FISIOTERAPIA**

Compõem este Edital, além das condições específicas, os seguintes documentos com texto substantivo.

#### **<mark>2.0 – DOS RECURSOS ORÇAMENTÁRIOS:</mark>**

2.1. As despesas decorrentes desta contratação estão programadas em dotação própria.
"""
        headings = [
            Heading(line_number=2, level=4, title="**<mark>1.0. DO OBJETO:</mark>**", raw="#### **<mark>1.0. DO OBJETO:</mark>**"),
            Heading(
                line_number=4,
                level=4,
                title="**CONTRATAÇÃO DE EMPRESA ESPECIALIZADA EM AQUISIÇÃO DE MATERIAL DE FISIOTERAPIA**",
                raw="#### **CONTRATAÇÃO DE EMPRESA ESPECIALIZADA EM AQUISIÇÃO DE MATERIAL DE FISIOTERAPIA**",
            ),
            Heading(
                line_number=8,
                level=4,
                title="**<mark>2.0 – DOS RECURSOS ORÇAMENTÁRIOS:</mark>**",
                raw="#### **<mark>2.0 – DOS RECURSOS ORÇAMENTÁRIOS:</mark>**",
            ),
        ]
        result = run_heading_pipeline(headings, full_text)
        self.assertEqual(len(result), 2)
        # Título 1 foi fundido e normalizado
        self.assertTrue(result[0].title.startswith("1.0. DO OBJETO: CONTRATAÇÃO DE EMPRESA ESPECIALIZADA"))
        self.assertEqual(result[0].level, 1)  # 1.0 virou H1
        self.assertEqual(result[0].level_source, "numbering_pattern")

        # Título 2 virou H1
        self.assertTrue(result[1].title.startswith("2.0 – DOS RECURSOS ORÇAMENTÁRIOS:"))
        self.assertEqual(result[1].level, 1)


if __name__ == "__main__":
    unittest.main()
