import argparse
import json
import time
from pathlib import Path
from typing import Any
import pymupdf
import pymupdf4llm


def extract_raw_with_pages(pdf_path: Path) -> tuple[str, list[dict[str, Any]]]:
    """Extrai markdown bruto e lista de chunks por página do PDF via pymupdf4llm."""
    page_chunks = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
    with pymupdf.open(str(pdf_path)) as pdf:
        page_sizes = [
            {"width": p.rect.width, "height": p.rect.height, "rotation": p.rotation} for p in pdf
        ]

    page_map: list[dict[str, Any]] = []
    text_parts: list[str] = []
    current_line = 1
    current_char = 0

    for chunk in page_chunks:
        raw_text = chunk.get("text", "")
        metadata = chunk.get("metadata", {})
        page_num = metadata.get("page_number", 1)

        lines = raw_text.splitlines()
        num_lines = len(lines)
        start_line = current_line
        end_line = current_line + max(0, num_lines - 1)

        size = page_sizes[page_num - 1] if 0 < page_num <= len(page_sizes) else {}
        boxes = [
            {"class": b["class"], "bbox": list(b["bbox"]), "pos": list(b["pos"])}
            for b in chunk.get("page_boxes", [])
        ]

        page_map.append(
            {
                "page": page_num,
                "start_line": start_line,
                "end_line": end_line,
                "char_count": len(raw_text),
                "toc_items": chunk.get("toc_items", []),
                # Posição física: 'pos' de cada box são offsets locais ao texto da página;
                # 'char_start' é o offset da página no markdown consolidado.
                "char_start": current_char,
                "width": size.get("width"),
                "height": size.get("height"),
                "rotation": size.get("rotation", 0),
                "boxes": boxes,
            }
        )

        text_parts.append(raw_text)
        # 2 quebras de linha adicionam 2 linhas vazias entre páginas
        current_line = end_line + 3
        # "\n\n".join adiciona 2 caracteres entre páginas
        current_char += len(raw_text) + 2

    full_markdown = "\n\n".join(text_parts)
    return full_markdown, page_map


def extract_pdf_to_raw_markdown(pdf_path: Path, output_dir: Path) -> Path:
    """Lê um PDF e salva o Markdown cru (.md) e o mapeamento de páginas (.pages.json)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{pdf_path.stem}.md"
    pages_file = output_dir / f"{pdf_path.stem}_pages.json"

    print(f"📄 Processando: {pdf_path.name}...")
    start_time = time.time()

    full_markdown, page_map = extract_raw_with_pages(pdf_path)

    output_file.write_text(full_markdown, encoding="utf-8")
    pages_file.write_text(
        json.dumps({"source_file": pdf_path.name, "pages": page_map}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    elapsed = time.time() - start_time
    print(
        f"✅ Salvo em: {output_file.name} e {pages_file.name} "
        f"({elapsed:.2f}s, {len(full_markdown)} chars, {len(page_map)} páginas)"
    )
    return output_file


def process_directory(input_dir: Path, output_dir: Path) -> list[Path]:
    """Processa todos os PDFs em input_dir e salva os arquivos em output_dir."""
    if not input_dir.exists():
        print(f"⚠️ Diretório de entrada não encontrado: {input_dir}")
        return []

    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"ℹ️ Nenhum arquivo PDF encontrado em: {input_dir}")
        print("💡 Coloque arquivos .pdf nessa pasta e execute o script novamente.")
        return []

    print(f"🔍 Encontrados {len(pdf_files)} arquivo(s) PDF em '{input_dir}'.")
    print(f"📁 Pasta de destino (Markdown cru): '{output_dir}'\n")

    saved_files: list[Path] = []
    for pdf_path in pdf_files:
        saved_path = extract_pdf_to_raw_markdown(pdf_path, output_dir)
        saved_files.append(saved_path)

    print(f"\n🎉 Concluído! {len(saved_files)} arquivo(s) processado(s).")
    return saved_files


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    default_input_dir = project_root / "data" / "00_input_pdfs"
    default_output_dir = project_root / "data" / "01_raw_markdown"

    parser = argparse.ArgumentParser(
        description="Etapa 01: Extração básica de PDF para Markdown cru com metadados por página."
    )
    parser.add_argument(
        "--input-dir",
        "-i",
        type=Path,
        default=default_input_dir,
        help=f"Diretório contendo os PDFs de entrada (padrão: {default_input_dir})",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=default_output_dir,
        help=f"Diretório onde os arquivos serão gravados (padrão: {default_output_dir})",
    )

    args = parser.parse_args()
    process_directory(args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()
