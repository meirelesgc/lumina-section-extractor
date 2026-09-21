import argparse
import json
import time
from pathlib import Path
from typing import Any

import pymupdf

from lumina_section_extractor.positioning import locate_range, page_sizes_from_pages

CHUNK_COLORS = [
    (1.0, 0.85, 0.2),
    (0.5, 0.85, 1.0),
    (0.6, 1.0, 0.6),
    (1.0, 0.65, 0.85),
    (0.85, 0.7, 1.0),
    (1.0, 0.75, 0.5),
]

ROLE_COLORS = {
    "title_block": (0.5, 0.5, 0.5),
    "abstract": (0.1, 0.5, 0.9),
    "introduction": (0.1, 0.7, 0.3),
    "methodology": (0.9, 0.5, 0.0),
    "results": (0.6, 0.2, 0.8),
    "discussion": (0.9, 0.2, 0.5),
    "conclusion": (0.8, 0.1, 0.1),
    "references": (0.4, 0.3, 0.2),
    "unknown": (0.75, 0.75, 0.75),
}


def make_words_provider(pdf: pymupdf.Document):
    """Função com cache: página (1-based) → palavras do PyMuPDF."""
    cache: dict[int, list] = {}

    def provider(page_no: int) -> list:
        if page_no not in cache:
            cache[page_no] = pdf[page_no - 1].get_text("words")
        return cache[page_no]

    return provider


def flatten_section_dicts(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for s in sections:
        flat.append(s)
        flat.extend(flatten_section_dicts(s.get("children", [])))
    return flat


def enrich_chunks_with_rects(
    chunks_data: dict[str, Any],
    pages: list[dict[str, Any]],
    markdown: str,
    words_provider,
) -> dict[str, Any]:
    """Adiciona `rects`, `pages` a cada chunk (metadata) e `page_sizes` no topo. Idempotente."""
    for chunk in chunks_data["chunks"]:
        meta = chunk["metadata"]
        if "char_start" not in meta:
            meta["rects"], meta["pages"] = [], []
            continue
        rects = locate_range(pages, markdown, meta["char_start"], meta["char_end"], words_provider)
        meta["rects"] = rects
        meta["pages"] = sorted({r["page"] for r in rects})
    chunks_data["page_sizes"] = page_sizes_from_pages(pages)
    return chunks_data


def section_rects(
    sections: list[dict[str, Any]],
    pages: list[dict[str, Any]],
    markdown: str,
    words_provider,
) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
    result = []
    for sec in flatten_section_dicts(sections):
        if sec.get("char_end") is None:
            continue
        start = sec.get("heading_char_start", sec["char_start"])
        result.append((sec, locate_range(pages, markdown, start, sec["char_end"], words_provider)))
    return result


def annotate_pdf(
    pdf: pymupdf.Document,
    chunks_data: dict[str, Any],
    sections_rects: list[tuple[dict[str, Any], list[dict[str, Any]]]],
) -> None:
    # Seções: barra vertical na margem esquerda, colorida por role, com rótulo
    for sec, rects in sections_rects:
        color = ROLE_COLORS.get(sec.get("role", "unknown"), ROLE_COLORS["unknown"])
        by_page: dict[int, list[dict[str, Any]]] = {}
        for r in rects:
            by_page.setdefault(r["page"], []).append(r)
        for page_no, rs in by_page.items():
            page = pdf[page_no - 1]
            y1 = min(r["y1"] for r in rs)
            y2 = max(r["y2"] for r in rs)
            bar = pymupdf.Rect(4, y1, 8, y2)
            page.draw_rect(bar, color=color, fill=color, width=0)
            label = f"{sec.get('role', 'unknown')}: {sec.get('title', '')}"[:40]
            page.insert_text((10, y1 + 5), label, fontsize=4.5, color=color)

    # Chunks: highlight translúcido por linha, com chunk_id no popup da anotação
    for i, chunk in enumerate(chunks_data["chunks"]):
        meta = chunk["metadata"]
        color = CHUNK_COLORS[i % len(CHUNK_COLORS)]
        by_page: dict[int, list[dict[str, Any]]] = {}
        for r in meta.get("rects", []):
            by_page.setdefault(r["page"], []).append(r)
        for page_no, rs in by_page.items():
            page = pdf[page_no - 1]
            quads = [pymupdf.Rect(r["x1"], r["y1"], r["x2"], r["y2"]).quad for r in rs]
            annot = page.add_highlight_annot(quads=quads)
            annot.set_colors(stroke=color)
            annot.set_opacity(0.4)
            annot.set_info(
                title=meta["chunk_id"],
                content=f"{meta['chunk_id']} | {meta.get('section_path', '')}",
            )
            annot.update()
            first = rs[0]
            page.insert_text(
                (first["x1"], max(first["y1"] - 1, 5)),
                meta["chunk_id"].replace("chunk_", "c"),
                fontsize=4,
                color=(0.3, 0.3, 0.3),
            )


def process_document(
    pdf_path: Path,
    md_path: Path,
    sections_path: Path,
    chunks_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    start_time = time.time()

    markdown = md_path.read_text(encoding="utf-8")
    pages = json.loads(md_path.with_name(f"{md_path.stem}_pages.json").read_text("utf-8"))["pages"]
    sections = json.loads(sections_path.read_text("utf-8")).get("sections", [])
    chunks_data = json.loads(chunks_path.read_text("utf-8"))

    with pymupdf.open(str(pdf_path)) as pdf:
        provider = make_words_provider(pdf)
        enrich_chunks_with_rects(chunks_data, pages, markdown, provider)
        sec_rects = section_rects(sections, pages, markdown, provider)
        annotate_pdf(pdf, chunks_data, sec_rects)
        out_pdf = output_dir / f"{pdf_path.stem}_annotated.pdf"
        pdf.save(str(out_pdf), garbage=3, deflate=True)

    chunks_path.write_text(json.dumps(chunks_data, indent=2, ensure_ascii=False), encoding="utf-8")

    total = len(chunks_data["chunks"])
    located = sum(1 for c in chunks_data["chunks"] if c["metadata"].get("rects"))
    print(
        f"🖍️ {pdf_path.name}: {located}/{total} chunks com rects "
        f"({time.time() - start_time:.2f}s) → {out_pdf.name}"
    )
    return {"file": pdf_path.name, "chunks": total, "located": located}


def process_directory(
    pdf_dir: Path, raw_dir: Path, sections_dir: Path, chunks_dir: Path, output_dir: Path
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        stem = pdf_path.stem
        md_path = raw_dir / f"{stem}.md"
        sections_path = sections_dir / f"{stem}_sections.json"
        chunks_path = chunks_dir / f"{stem}_chunks.json"
        if not (md_path.exists() and sections_path.exists() and chunks_path.exists()):
            print(f"⚠️ Pulando {pdf_path.name}: execute os estágios 1-3 antes.")
            continue
        results.append(process_document(pdf_path, md_path, sections_path, chunks_path, output_dir))
    print(f"🎉 Estágio 4 concluído! {len(results)} PDF(s) anotado(s) em '{output_dir}'.")
    return results


def main() -> None:
    root = Path(__file__).resolve().parents[2] / "data"
    parser = argparse.ArgumentParser(
        description="Etapa 04: localiza chunks/seções no PDF (rects) e gera PDFs anotados."
    )
    parser.add_argument("--data-dir", "-d", type=Path, default=root)
    args = parser.parse_args()
    d = args.data_dir
    process_directory(
        d / "00_input_pdfs",
        d / "01_raw_markdown",
        d / "02_sections_tree",
        d / "03_chunks",
        d / "04_annotated_pdfs",
    )


if __name__ == "__main__":
    main()
