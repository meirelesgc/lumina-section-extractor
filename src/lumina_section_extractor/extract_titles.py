import argparse
import json
import re
from pathlib import Path
from typing import Any


def extract_titles_from_content(content: str) -> list[dict[str, Any]]:
    """Extrai todas as linhas de título (iniciadas com '#') do conteúdo Markdown."""
    titles: list[dict[str, Any]] = []
    # Expressão regular para identificar linhas iniciadas com 1 a 6 '#'
    pattern = re.compile(r"^(#{1,6})\s*(.*)$")

    for line_idx, raw_line in enumerate(content.splitlines(), start=1):
        stripped = raw_line.strip()
        match = pattern.match(stripped)
        if match:
            hashes, title_text = match.groups()
            titles.append(
                {
                    "line_number": line_idx,
                    "level": len(hashes),
                    "hashes": hashes,
                    "title": title_text.strip(),
                    "raw": stripped,
                }
            )

    return titles


def format_titles_as_markdown(source_name: str, titles: list[dict[str, Any]]) -> str:
    """Formata os títulos extraídos em um relatório Markdown legível e hierárquico."""
    lines = [
        f"# Títulos Extraídos: {source_name}",
        "",
        f"Total de títulos identificados: **{len(titles)}**",
        "",
        "| Linha | Nível | Título |",
        "|---|---|---|",
    ]

    for item in titles:
        indent = "&nbsp;&nbsp;" * (item["level"] - 1)
        safe_title = item["title"].replace("|", "\\|")
        lines.append(
            f"| {item['line_number']} | H{item['level']} | {indent}**{safe_title}** |"
        )

    lines.append("\n## Estrutura Hierárquica\n")
    for item in titles:
        indent = "  " * (item["level"] - 1)
        lines.append(f"{indent}- **H{item['level']}** (L{item['line_number']}): {item['title']}")

    return "\n".join(lines) + "\n"


def process_markdown_file(md_path: Path, output_dir: Path) -> dict[str, Any]:
    """Processa um arquivo .md individual, extraindo os títulos e salvando os resultados."""
    output_dir.mkdir(parents=True, exist_ok=True)
    content = md_path.read_text(encoding="utf-8")
    titles = extract_titles_from_content(content)

    base_name = md_path.stem

    # Salva relatório em Markdown
    md_output_path = output_dir / f"{base_name}_titles.md"
    md_report = format_titles_as_markdown(md_path.name, titles)
    md_output_path.write_text(md_report, encoding="utf-8")

    # Salva dados estruturados em JSON
    json_output_path = output_dir / f"{base_name}_titles.json"
    json_output_path.write_text(
        json.dumps({"source_file": md_path.name, "total": len(titles), "titles": titles}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\n📑 Arquivo: {md_path.name} -> {len(titles)} título(s) com '#' encontrado(s)")
    for t in titles[:10]:
        print(f"   [Linha {t['line_number']:3d}] {t['hashes']} {t['title']}")
    if len(titles) > 10:
        print(f"   ... e mais {len(titles) - 10} título(s).")

    print(f"   💾 Salvo em:")
    print(f"      - {md_output_path}")
    print(f"      - {json_output_path}")

    return {"file": md_path.name, "count": len(titles)}


def process_directory(input_dir: Path, output_dir: Path) -> list[dict[str, Any]]:
    """Processa todos os arquivos .md da pasta de entrada."""
    if not input_dir.exists():
        print(f"⚠️ Diretório não encontrado: {input_dir}")
        return []

    # Ignora README.md ao processar os arquivos de markdown
    md_files = [f for f in sorted(input_dir.glob("*.md")) if f.name.lower() != "readme.md"]

    if not md_files:
        print(f"ℹ️ Nenhum arquivo Markdown cru encontrado em: {input_dir}")
        print("💡 Execute primeiro a etapa 1 ('poetry run extract-raw') para gerar os markdowns.")
        return []

    print(f"🔍 Encontrados {len(md_files)} arquivo(s) Markdown em '{input_dir}'.")
    print(f"📁 Pasta de destino (Títulos extraídos): '{output_dir}'")

    results = []
    for md_path in md_files:
        res = process_markdown_file(md_path, output_dir)
        results.append(res)

    print(f"\n🎉 Concluído! Títulos extraídos de {len(results)} arquivo(s).")
    return results


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    default_input_dir = project_root / "data" / "01_raw_markdown"
    default_output_dir = project_root / "data" / "02_extracted_titles"

    parser = argparse.ArgumentParser(
        description="Etapa 02: Extração de todos os títulos e seções que contêm '#' no Markdown."
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
        help=f"Diretório onde os títulos extraídos serão salvos (padrão: {default_output_dir})",
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
        process_markdown_file(args.file, args.output_dir)
    else:
        process_directory(args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()
