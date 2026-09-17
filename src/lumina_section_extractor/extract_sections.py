import argparse
import json
import time
from pathlib import Path
from typing import Any
from lumina_section_extractor.heading_cleaners import run_heading_pipeline
from lumina_section_extractor.section_tree import (
    build_section_tree,
    flatten_sections,
    parse_headings_from_markdown,
    tree_to_dict,
    tree_to_markdown,
)


def load_page_map(pages_file: Path) -> list[dict[str, Any]] | None:
    """Carrega o mapa de páginas se o arquivo JSON existir."""
    if pages_file.exists():
        try:
            data = json.loads(pages_file.read_text(encoding="utf-8"))
            return data.get("pages", [])
        except Exception:
            return None
    return None


def process_markdown_to_sections(
    md_path: Path, output_dir: Path, pages_file: Path | None = None
) -> dict[str, Any]:
    """Processa um arquivo Markdown, executa os cleaners funcionais e salva a árvore de seções."""
    output_dir.mkdir(parents=True, exist_ok=True)
    full_text = md_path.read_text(encoding="utf-8")

    if pages_file is None:
        pages_file = md_path.parent / f"{md_path.stem}_pages.json"

    page_map = load_page_map(pages_file)

    start_time = time.time()

    # 1. Parse de headings brutos
    raw_headings = parse_headings_from_markdown(full_text, page_map)

    # 2. Execução da pipeline funcional de cleaners
    cleaned_headings = run_heading_pipeline(raw_headings, full_text)

    # 3. Construção da árvore hierárquica
    tree = build_section_tree(cleaned_headings, full_text)
    all_sections = flatten_sections(tree)

    elapsed = time.time() - start_time
    base_name = md_path.stem

    # 4. Salva árvore serializada em JSON
    json_path = output_dir / f"{base_name}_sections.json"
    json_path.write_text(
        json.dumps(
            {
                "source_file": md_path.name,
                "total_raw_headings": len(raw_headings),
                "total_cleaned_headings": len(cleaned_headings),
                "total_sections": len(all_sections),
                "sections": tree_to_dict(tree),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # 5. Salva visualização estruturada em Markdown
    md_report_path = output_dir / f"{base_name}_sections.md"
    md_report_path.write_text(tree_to_markdown(md_path.name, tree), encoding="utf-8")

    print(f"🌲 {md_path.name}:")
    print(
        f"   - Headings brutos: {len(raw_headings)} | Limpos: {len(cleaned_headings)} "
        f"({len(raw_headings) - len(cleaned_headings)} removidos pelos cleaners)"
    )
    print(f"   - Seções estruturadas na árvore: {len(all_sections)} ({elapsed:.2f}s)")
    print(f"   - Salvos em: {json_path.name} e {md_report_path.name}\n")

    return {
        "file": md_path.name,
        "raw_headings": len(raw_headings),
        "cleaned_headings": len(cleaned_headings),
        "sections": len(all_sections),
    }


def process_directory(input_dir: Path, output_dir: Path) -> list[dict[str, Any]]:
    """Processa todos os markdowns da pasta de entrada para gerar a árvore de seções."""
    if not input_dir.exists():
        print(f"⚠️ Diretório de entrada não encontrado: {input_dir}")
        return []

    md_files = [f for f in sorted(input_dir.glob("*.md")) if f.name.lower() != "readme.md"]
    if not md_files:
        print(f"ℹ️ Nenhum arquivo Markdown cru encontrado em: {input_dir}")
        print("💡 Execute a etapa 1 ('poetry run extract-raw') primeiro.")
        return []

    print(f"🔍 Encontrados {len(md_files)} arquivo(s) Markdown em '{input_dir}'.")
    print(f"📁 Pasta de destino (Árvore de Seções): '{output_dir}'\n")

    results: list[dict[str, Any]] = []
    for md_file in md_files:
        res = process_markdown_to_sections(md_file, output_dir)
        results.append(res)

    print(f"🎉 Estágio 2 concluído! {len(results)} arquivo(s) processado(s).")
    return results


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    default_input_dir = project_root / "data" / "01_raw_markdown"
    default_output_dir = project_root / "data" / "02_sections_tree"

    parser = argparse.ArgumentParser(
        description="Etapa 02: Limpeza funcional de cabeçalhos e construção da árvore de seções."
    )
    parser.add_argument(
        "--input-dir",
        "-i",
        type=Path,
        default=default_input_dir,
        help=f"Diretório contendo os markdowns crus (padrão: {default_input_dir})",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=default_output_dir,
        help=f"Diretório onde a árvore de seções será salva (padrão: {default_output_dir})",
    )
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        default=None,
        help="Arquivo .md específico para processar (opcional)",
    )

    args = parser.parse_args()

    if args.file:
        process_markdown_to_sections(args.file, args.output_dir)
    else:
        process_directory(args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()
