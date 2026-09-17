import argparse
import json
import time
from pathlib import Path
from typing import Any
from lumina_section_extractor.chunking import (
    create_default_text_splitter,
    documents_to_dict,
    documents_to_markdown_preview,
    run_chunk_pipeline,
    sections_to_documents,
)
from lumina_section_extractor.models import Heading, Section


def dict_to_section_recursive(data: dict[str, Any]) -> Section:
    """Reconstrói um objeto Section a partir do dicionário salvo no estágio 2."""
    heading = Heading(
        line_number=data.get("line_number", 0),
        level=data.get("level", 1),
        title=data.get("title", ""),
        raw=data.get("raw_heading", ""),
        page=data.get("page"),
        level_source=data.get("level_source", "font"),
    )
    section = Section(
        heading=heading,
        breadcrumb=data.get("breadcrumb", [data.get("title", "")]),
        content=data.get("content", ""),
        parent_title=data.get("parent_title"),
    )
    for child_dict in data.get("children", []):
        section.children.append(dict_to_section_recursive(child_dict))
    return section


def flatten_section_objects(sections: list[Section]) -> list[Section]:
    """Retorna lista plana de seções."""
    flat: list[Section] = []

    def walk(s: Section) -> None:
        flat.append(s)
        for child in s.children:
            walk(child)

    for s in sections:
        walk(s)
    return flat


def process_sections_file_to_chunks(
    json_path: Path,
    output_dir: Path,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> dict[str, Any]:
    """Lê as seções salvas em JSON, aplica fatiamento inteligente, pipeline de limpeza e salva chunks."""
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_data = json.loads(json_path.read_text(encoding="utf-8"))

    source_file = raw_data.get("source_file", json_path.stem)
    sections_data = raw_data.get("sections", [])

    start_time = time.time()

    # Reconstrói seções e achata para processamento
    root_sections = [dict_to_section_recursive(s) for s in sections_data]
    flat_sections = flatten_section_objects(root_sections)

    # 1. Cria splitter e gera documents
    splitter = create_default_text_splitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    docs = sections_to_documents(flat_sections, source_name=source_file, splitter=splitter)

    # 2. Executa pipeline funcional de chunks
    cleaned_docs = run_chunk_pipeline(docs)

    elapsed = time.time() - start_time
    doc_stem = json_path.stem.replace("_sections", "")

    # 3. Salva JSON com chunks enriquecidos
    out_json = output_dir / f"{doc_stem}_chunks.json"
    out_json.write_text(
        json.dumps(
            {
                "source_file": source_file,
                "total_chunks": len(cleaned_docs),
                "chunk_size_config": chunk_size,
                "chunk_overlap_config": chunk_overlap,
                "chunks": documents_to_dict(cleaned_docs),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # 4. Salva visualização de inspeção em Markdown
    out_md = output_dir / f"{doc_stem}_chunks.md"
    out_md.write_text(documents_to_markdown_preview(source_file, cleaned_docs), encoding="utf-8")

    print(f"📦 {source_file}:")
    print(
        f"   - {len(flat_sections)} seções convertidas em {len(cleaned_docs)} chunks "
        f"({elapsed:.2f}s)"
    )
    print(f"   - Salvos em: {out_json.name} e {out_md.name}\n")

    return {
        "file": source_file,
        "sections": len(flat_sections),
        "chunks": len(cleaned_docs),
    }


def process_directory(
    input_dir: Path,
    output_dir: Path,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[dict[str, Any]]:
    """Processa todos os arquivos de seções da pasta de entrada para gerar chunks."""
    if not input_dir.exists():
        print(f"⚠️ Diretório de entrada não encontrado: {input_dir}")
        return []

    section_files = sorted(input_dir.glob("*_sections.json"))
    if not section_files:
        print(f"ℹ️ Nenhum arquivo *_sections.json encontrado em: {input_dir}")
        print("💡 Execute a etapa 2 ('poetry run extract-sections') primeiro.")
        return []

    print(f"🔍 Encontrados {len(section_files)} arquivo(s) de seções em '{input_dir}'.")
    print(f"📁 Pasta de destino (Chunks): '{output_dir}'\n")

    results: list[dict[str, Any]] = []
    for sf in section_files:
        res = process_sections_file_to_chunks(
            sf, output_dir, chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        results.append(res)

    print(f"🎉 Estágio 3 concluído! {len(results)} arquivo(s) fatiado(s) em chunks.")
    return results


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    default_input_dir = project_root / "data" / "02_sections_tree"
    default_output_dir = project_root / "data" / "03_chunks"

    parser = argparse.ArgumentParser(
        description="Etapa 03: Chunking intra-seção com RecursiveCharacterTextSplitter e enriquecimento de metadados."
    )
    parser.add_argument(
        "--input-dir",
        "-i",
        type=Path,
        default=default_input_dir,
        help=f"Diretório contendo os arquivos de seções (padrão: {default_input_dir})",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=default_output_dir,
        help=f"Diretório onde os chunks serão salvos (padrão: {default_output_dir})",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Tamanho máximo de caracteres por chunk (padrão: 1000)",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=150,
        help="Sobreposição de caracteres entre chunks (padrão: 150)",
    )
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        default=None,
        help="Arquivo *_sections.json específico para processar (opcional)",
    )

    args = parser.parse_args()

    if args.file:
        process_sections_file_to_chunks(
            args.file,
            args.output_dir,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
    else:
        process_directory(
            args.input_dir,
            args.output_dir,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )


if __name__ == "__main__":
    main()
