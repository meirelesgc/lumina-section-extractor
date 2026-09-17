import unittest
from langchain_core.documents import Document
from lumina_section_extractor.chunking import (
    clean_whitespace,
    create_default_text_splitter,
    run_chunk_pipeline,
    section_to_documents,
    sections_to_documents,
)
from lumina_section_extractor.models import Heading, Section


class TestChunking(unittest.TestCase):
    def test_clean_whitespace(self):
        docs = [
            Document(page_content="Texto linha 1\n\n\n\n\nTexto linha 2   "),
        ]
        cleaned = clean_whitespace(docs)
        self.assertEqual(cleaned[0].page_content, "Texto linha 1\n\nTexto linha 2")

    def test_section_to_documents_short(self):
        splitter = create_default_text_splitter(chunk_size=500, chunk_overlap=50)
        sec = Section(
            heading=Heading(line_number=10, level=2, title="1.1 Objeto", raw="## 1.1 Objeto", page=3),
            breadcrumb=["Termo", "1.1 Objeto"],
            content="Conteúdo curto que cabe em um único chunk com folga.",
        )
        docs = section_to_documents(sec, splitter, "edital.pdf")
        self.assertEqual(len(docs), 1)
        doc = docs[0]
        self.assertTrue(doc.page_content.startswith("[1.1 Objeto]"))
        self.assertEqual(doc.metadata["section_title"], "1.1 Objeto")
        self.assertEqual(doc.metadata["section_path"], "Termo > 1.1 Objeto")
        self.assertEqual(doc.metadata["section_level"], 2)
        self.assertEqual(doc.metadata["page_number"], 3)
        self.assertEqual(doc.metadata["source_file"], "edital.pdf")

    def test_section_to_documents_long(self):
        splitter = create_default_text_splitter(chunk_size=100, chunk_overlap=20)
        long_content = "Palavra " * 50  # ~400 chars
        sec = Section(
            heading=Heading(line_number=5, level=1, title="Disposições", raw="# Disposições", page=1),
            breadcrumb=["Disposições"],
            content=long_content,
        )
        docs = section_to_documents(sec, splitter, "edital.pdf")
        self.assertGreater(len(docs), 1)
        for i, d in enumerate(docs):
            self.assertTrue(d.page_content.startswith("[Disposições]"))
            self.assertEqual(d.metadata["chunk_index"], i)
            self.assertEqual(d.metadata["total_chunks_in_section"], len(docs))

    def test_run_chunk_pipeline(self):
        docs = [
            Document(page_content="Item A\n\n\n\nItem B"),
        ]
        result = run_chunk_pipeline(docs)
        self.assertEqual(result[0].page_content, "Item A\n\nItem B")


if __name__ == "__main__":
    unittest.main()
