from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Heading:
    """Representa um cabeçalho Markdown identificado."""

    line_number: int
    level: int
    title: str
    raw: str
    page: Optional[int] = None


@dataclass
class Section:
    """Representa uma seção delimitada por um cabeçalho e seu conteúdo associado."""

    heading: Heading
    breadcrumb: list[str]
    content: str
    parent_title: Optional[str] = None
    children: list["Section"] = field(default_factory=list)
