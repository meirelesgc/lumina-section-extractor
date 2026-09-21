import argparse
import time
from pathlib import Path
from lumina_section_extractor.annotate_pdf import process_directory as run_stage_4
from lumina_section_extractor.extract_chunks import process_directory as run_stage_3
from lumina_section_extractor.extract_raw_markdown import process_directory as run_stage_1
from lumina_section_extractor.extract_sections import process_directory as run_stage_2


def run_full_pipeline(
    input_pdf_dir: Path,
    base_data_dir: Path,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
    annotate: bool = False,
) -> None:
    """Executa os 3 estágios do pipeline em sequência de forma integrada."""
    stage_1_dir = base_data_dir / "01_raw_markdown"
    stage_2_dir = base_data_dir / "02_sections_tree"
    stage_3_dir = base_data_dir / "03_chunks"

    print("=" * 70)
    print("🚀 INICIANDO PIPELINE LUMINA: PDF ➔ MARKDOWN ➔ SEÇÕES ➔ CHUNKS")
    print("=" * 70)
    total_start = time.time()

    # Estágio 1
    print("\n▶️ [ESTÁGIO 1] Extração Bruta de PDFs (pymupdf4llm com páginas)")
    run_stage_1(input_pdf_dir, stage_1_dir)

    # Estágio 2
    print("\n▶️ [ESTÁGIO 2] Limpeza Funcional de Cabeçalhos e Árvore de Seções")
    run_stage_2(stage_1_dir, stage_2_dir)

    # Estágio 3
    print("\n▶️ [ESTÁGIO 3] Chunking Intra-seção e Enriquecimento Semântico")
    run_stage_3(stage_2_dir, stage_3_dir, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    if annotate:
        stage_4_dir = base_data_dir / "04_annotated_pdfs"
        print("\n▶️ [ESTÁGIO 4] Localização no PDF (rects) e PDFs anotados")
        run_stage_4(input_pdf_dir, stage_1_dir, stage_2_dir, stage_3_dir, stage_4_dir)

    total_elapsed = time.time() - total_start
    print("\n" + "=" * 70)
    print(f"🏁 PIPELINE FINALIZADO COM SUCESSO EM {total_elapsed:.2f}s!")
    print(f"📁 Resultados disponíveis em:")
    print(f"   - Estágio 1 (Markdown Cru):    {stage_1_dir}")
    print(f"   - Estágio 2 (Árvore de Seções): {stage_2_dir}")
    print(f"   - Estágio 3 (Chunks Prontos):   {stage_3_dir}")
    print("=" * 70)


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    default_input_dir = project_root / "data" / "00_input_pdfs"
    default_base_data_dir = project_root / "data"

    parser = argparse.ArgumentParser(
        description="Executa o pipeline completo do Lumina Section Extractor (Estágios 1 a 3)."
    )
    parser.add_argument(
        "--input-dir",
        "-i",
        type=Path,
        default=default_input_dir,
        help=f"Diretório contendo os PDFs de entrada (padrão: {default_input_dir})",
    )
    parser.add_argument(
        "--data-dir",
        "-d",
        type=Path,
        default=default_base_data_dir,
        help=f"Diretório base de dados (padrão: {default_base_data_dir})",
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
        "--annotate",
        action="store_true",
        help="Executa o Estágio 4: rects no JSON de chunks + PDFs anotados em 04_annotated_pdfs",
    )

    args = parser.parse_args()
    run_full_pipeline(
        args.input_dir,
        args.data_dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        annotate=args.annotate,
    )


if __name__ == "__main__":
    main()
