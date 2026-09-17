import re
from typing import Any, Callable, Sequence
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from lumina_section_extractor.models import Section

# Tipo funcional para cleaners de documentos/chunks
ChunkCleaner = Callable[[list[Document]], list[Document]]


def clean_whitespace(docs: list[Document]) -> list[Document]:
    """Normaliza espaços em branco e múltiplos saltos de linha contínuos nos chunks."""
    for doc in docs:
        doc.page_content = re.sub(r"\n{3,}", "\n\n", doc.page_content).strip()
    return docs


def clean_llm_residual_stub(docs: list[Document]) -> list[Document]:
    """Stub preparado para limpeza residual via LLM leve (mantido inativo inicialmente)."""
    return docs


def get_default_chunk_cleaners() -> list[ChunkCleaner]:
    """Retorna os cleaners funcionais padrão para o pós-chunking."""
    return [
        clean_whitespace,
        clean_llm_residual_stub,
    ]


def run_chunk_pipeline(
    docs: list[Document],
    cleaners: Sequence[ChunkCleaner] | None = None,
) -> list[Document]:
    """Executa a sequência funcional de cleaners sobre a lista de Documents."""
    if cleaners is None:
        cleaners = get_default_chunk_cleaners()

    current_docs = docs
    for cleaner in cleaners:
        current_docs = cleaner(current_docs)

    return current_docs


def create_default_text_splitter(
    chunk_size: int = 1000, chunk_overlap: int = 150
) -> RecursiveCharacterTextSplitter:
    """Cria o fatiador de texto do LangChain configurado para Markdown e português."""
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", "; ", ", ", " ", ""],
    )


def section_to_documents(
    section: Section,
    splitter: RecursiveCharacterTextSplitter,
    source_name: str,
) -> list[Document]:
    """Converte uma Seção em um ou mais Documents do LangChain fatiando apenas seções longas."""
    content = section.content.strip()
    if not content:
        return []

    section_title = section.heading.title
    breadcrumb_str = " > ".join(section.breadcrumb)
    confidence = (
        "numbered" if section.heading.level_source == "numbering_pattern" else "font_derived"
    )

    # Se a seção cabe no tamanho do chunk, não fatiamos
    if len(content) <= splitter._chunk_size:
        sub_texts = [content]
    else:
        sub_texts = splitter.split_text(content)

    docs: list[Document] = []
    total_sub_chunks = len(sub_texts)

    for idx, text in enumerate(sub_texts):
        # Prefixo semântico leve com o título da seção imediata (sem breadcrumbs longos)
        prefixed_content = f"[{section_title}] {text}"
        metadata = {
            "section_title": section_title,
            "section_path": breadcrumb_str,
            "section_level": section.heading.level,
            "level_source": section.heading.level_source,
            "hierarchy_confidence": confidence,
            "chunk_index": idx,
            "total_chunks_in_section": total_sub_chunks,
            "page_number": section.heading.page,
            "source_file": source_name,
            "line_number": section.heading.line_number,
        }
        docs.append(Document(page_content=prefixed_content, metadata=metadata))

    return docs



def sections_to_documents(
    sections: list[Section],
    source_name: str,
    splitter: RecursiveCharacterTextSplitter | None = None,
) -> list[Document]:
    """Converte uma lista plana de seções em uma lista completa de Documents enriquecidos."""
    if splitter is None:
        splitter = create_default_text_splitter()

    all_docs: list[Document] = []
    for sec in sections:
        docs = section_to_documents(sec, splitter, source_name)
        all_docs.extend(docs)

    return all_docs


def documents_to_dict(docs: list[Document]) -> list[dict[str, Any]]:
    """Serializa lista de Documents para dicionários utilizáveis em JSON."""
    return [
        {
            "page_content": doc.page_content,
            "metadata": doc.metadata,
            "char_count": len(doc.page_content),
        }
        for doc in docs
    ]


def documents_to_markdown_preview(source_name: str, docs: list[Document]) -> str:
    """Gera visualização de inspeção rápida em Markdown dos chunks gerados."""
    lines = [
        f"# Chunks Gerados: {source_name}",
        "",
        f"Total de chunks: **{len(docs)}**",
        "",
    ]

    for idx, doc in enumerate(docs, start=1):
        meta = doc.metadata
        page_str = meta.get("page_number", "-")
        lines.append(f"### Chunk {idx} (Pág: {page_str} | Nível: H{meta.get('section_level')})")
        lines.append(f"**Caminho**: `{meta.get('section_path')}`  ")
        lines.append(f"**Tamanho**: {len(doc.page_content)} caracteres")
        lines.append("")
        lines.append("```text")
        lines.append(doc.page_content)
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines) + "\n"
