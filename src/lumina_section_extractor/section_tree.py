import re
from typing import Any
from lumina_section_extractor.models import Heading, Section

HEADING_PATTERN = re.compile(r"^(#{1,6})\s*(.*)$")


def find_page_for_line(line_number: int, page_map: list[dict[str, Any]] | None) -> int | None:
    """Encontra o número da página correspondente ao número da linha a partir do mapa de páginas."""
    if not page_map:
        return None
    for p in page_map:
        if p["start_line"] <= line_number <= p["end_line"]:
            return p["page"]
    # Se não encontrar no intervalo exato (ex: quebras intermediárias), pega a página mais próxima anterior
    for p in reversed(page_map):
        if line_number >= p["start_line"]:
            return p["page"]
    return page_map[0]["page"] if page_map else None


def parse_headings_from_markdown(
    content: str, page_map: list[dict[str, Any]] | None = None
) -> list[Heading]:
    """Identifica todos os cabeçalhos ('#') no texto com números de linha e página."""
    headings: list[Heading] = []
    lines = content.splitlines()

    for line_idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        match = HEADING_PATTERN.match(stripped)
        if match:
            hashes, title = match.groups()
            page = find_page_for_line(line_idx, page_map)
            headings.append(
                Heading(
                    line_number=line_idx,
                    level=len(hashes),
                    title=title.strip(),
                    raw=stripped,
                    page=page,
                )
            )

    return headings


def slice_sections_content(headings: list[Heading], full_text: str) -> list[tuple[Heading, str]]:
    """Fatia o texto do documento entre cada heading e o heading subsequente."""
    if not headings:
        return []

    lines = full_text.splitlines()
    total_lines = len(lines)
    sliced: list[tuple[Heading, str]] = []

    for i, h in enumerate(headings):
        start_line = h.line_number  # linha logo após o cabeçalho
        end_line = headings[i + 1].line_number - 1 if i + 1 < len(headings) else total_lines

        content_lines = lines[start_line:end_line]
        content_text = "\n".join(content_lines).strip()
        sliced.append((h, content_text))

    return sliced


def build_section_tree(headings: list[Heading], full_text: str) -> list[Section]:
    """Constrói a árvore hierárquica de Seções a partir dos headings e do texto."""
    if not headings:
        return []

    sliced = slice_sections_content(headings, full_text)
    root_sections: list[Section] = []
    # Pilha para rastrear pais: list[tuple[level, Section]]
    stack: list[tuple[int, Section]] = []

    for heading, content in sliced:
        # Desempilha nós de nível maior ou igual (irmãos ou nós de níveis mais profundos)
        while stack and stack[-1][0] >= heading.level:
            stack.pop()

        parent_section = stack[-1][1] if stack else None
        breadcrumb = [p.heading.title for _, p in stack] + [heading.title]

        current_section = Section(
            heading=heading,
            breadcrumb=breadcrumb,
            content=content,
            parent_title=parent_section.heading.title if parent_section else None,
        )

        if parent_section:
            parent_section.children.append(current_section)
        else:
            root_sections.append(current_section)

        stack.append((heading.level, current_section))

    return root_sections


def flatten_sections(sections: list[Section]) -> list[Section]:
    """Retorna todas as seções da árvore em uma lista plana (em ordem de profundidade/leitura)."""
    flat: list[Section] = []

    def walk(sec: Section) -> None:
        flat.append(sec)
        for child in sec.children:
            walk(child)

    for sec in sections:
        walk(sec)

    return flat


def section_to_dict(section: Section) -> dict[str, Any]:
    """Converte uma seção e seus filhos recursivamente em dicionário serializável."""
    confidence = "numbered" if section.heading.level_source == "numbering_pattern" else "font_derived"
    return {
        "title": section.heading.title,
        "level": section.heading.level,
        "level_source": section.heading.level_source,
        "hierarchy_confidence": confidence,
        "line_number": section.heading.line_number,
        "page": section.heading.page,
        "raw_heading": section.heading.raw,
        "breadcrumb": section.breadcrumb,
        "breadcrumb_path": " > ".join(section.breadcrumb),
        "content_length": len(section.content),
        "content": section.content,
        "parent_title": section.parent_title,
        "children": [section_to_dict(child) for child in section.children],
    }



def tree_to_dict(sections: list[Section]) -> list[dict[str, Any]]:
    """Converte a lista de seções raiz em lista de dicionários serializáveis."""
    return [section_to_dict(sec) for sec in sections]


def tree_to_markdown(source_name: str, sections: list[Section]) -> str:
    """Gera visualização em Markdown da árvore de seções com breadcrumbs e contagem de caracteres."""
    all_flat = flatten_sections(sections)

    lines = [
        f"# Árvore de Seções: {source_name}",
        "",
        f"Total de seções estruturadas: **{len(all_flat)}**",
        "",
        "| Linha | Pág. | Nível | Caminho (Breadcrumb) | Caracteres |",
        "|---|---|---|---|---|",
    ]

    for sec in all_flat:
        page_str = str(sec.heading.page) if sec.heading.page is not None else "-"
        path_str = " > ".join(sec.breadcrumb).replace("|", "\\|")
        lines.append(
            f"| {sec.heading.line_number} | {page_str} | H{sec.heading.level} | **{path_str}** | {len(sec.content)} |"
        )

    lines.append("\n## Hierarquia de Seções\n")
    for sec in all_flat:
        indent = "  " * (sec.heading.level - 1)
        lines.append(f"{indent}- **H{sec.heading.level}** `{sec.heading.title}` (L{sec.heading.line_number})")

    return "\n".join(lines) + "\n"
