import argparse
import sys
import time
from pathlib import Path
import pymupdf4llm


def extract_pdf_to_raw_markdown(pdf_path: Path, output_dir: Path) -> Path:
    """Lê um arquivo PDF e salva a versão em Markdown cru (sem pós-tratamento)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{pdf_path.stem}.md"

    print(f"📄 Processando: {pdf_path.name}...")
    start_time = time.time()

    # Conversão direta e crua utilizando pymupdf4llm
    raw_markdown = pymupdf4llm.to_markdown(str(pdf_path))

    output_file.write_text(raw_markdown, encoding="utf-8")
    elapsed = time.time() - start_time

    print(f"✅ Salvo em: {output_file} ({elapsed:.2f}s, {len(raw_markdown)} caracteres)")
    return output_file


def process_directory(input_dir: Path, output_dir: Path) -> list[Path]:
    """Processa todos os PDFs em input_dir e salva os arquivos .md em output_dir."""
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
    # Localiza o diretório raiz do projeto com base na localização deste arquivo
    project_root = Path(__file__).resolve().parents[2]
    default_input_dir = project_root / "data" / "00_input_pdfs"
    default_output_dir = project_root / "data" / "01_raw_markdown"

    parser = argparse.ArgumentParser(
        description="Etapa 01: Extração básica de PDF para Markdown cru (sem tratamento)."
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
        help=f"Diretório onde os arquivos .md serão gravados (padrão: {default_output_dir})",
    )

    args = parser.parse_args()
    process_directory(args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()
