from enum import Enum
from typing import Optional


class SectionRole(str, Enum):
    TITLE_BLOCK = "title_block"
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    METHODOLOGY = "methodology"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    REFERENCES = "references"
    UNKNOWN = "unknown"


class Heading:
    """Representa um cabeçalho Markdown identificado."""

    def __init__(
        self,
        line_number: int,
        level: int,
        title: str,
        raw: str,
        page: Optional[int] = None,
        level_source: str = "font",
    ):
        self.line_number = line_number
        self.level = level
        self.title = title
        self.raw = raw
        self.page = page
        self.level_source = level_source

    def __repr__(self) -> str:
        return (
            f"Heading(line_number={self.line_number}, level={self.level}, "
            f"title='{self.title}', page={self.page}, level_source='{self.level_source}')"
        )


class Section:
    """Representa uma seção delimitada por um cabeçalho e seu conteúdo associado."""

    def __init__(
        self,
        heading: Optional[Heading] = None,
        breadcrumb: Optional[list[str]] = None,
        content: str = "",
        parent_title: Optional[str] = None,
        children: Optional[list["Section"]] = None,
        role: SectionRole = SectionRole.UNKNOWN,
        role_confidence: Optional[str] = None,
        title: Optional[str] = None,
        char_start: Optional[int] = None,
        char_end: Optional[int] = None,
        heading_char_start: Optional[int] = None,
    ):
        if heading is None:
            heading = Heading(
                line_number=1,
                level=1,
                title=title or "Sem título",
                raw=f"# {title or 'Sem título'}",
            )
        elif title is not None:
            heading.title = title

        self.heading = heading
        self.breadcrumb = breadcrumb if breadcrumb is not None else [self.heading.title]
        self.content = content
        self.parent_title = parent_title
        self.children = children if children is not None else []
        self.role = role
        self.role_confidence = role_confidence
        # Offsets absolutos no markdown consolidado: content == markdown[char_start:char_end]
        self.char_start = char_start
        self.char_end = char_end
        self.heading_char_start = heading_char_start

    @property
    def title(self) -> str:
        return self.heading.title

    @title.setter
    def title(self, value: str) -> None:
        self.heading.title = value

    @property
    def level(self) -> int:
        return self.heading.level

    @level.setter
    def level(self, value: int) -> None:
        self.heading.level = value


    def __repr__(self) -> str:
        return (
            f"Section(title='{self.title}', role={self.role.value if hasattr(self.role, 'value') else self.role}, "
            f"role_confidence='{self.role_confidence}', children_count={len(self.children)})"
        )
