"""Data model for compiled tables."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class HeaderRef:
    """One entry of the ordered header list returned by describe()."""

    id: str
    text: str


@dataclass(frozen=True)
class Description:
    """Result of describe(): the cell covering a logical coordinate."""

    id: str
    row: int
    col: int
    text: str
    headers: tuple[HeaderRef, ...]


@dataclass
class Cell:
    """A th/td of the target table (never of a nested table)."""

    id: str
    is_header: bool
    text: str
    headers_attr: tuple[str, ...] | None  # None = attribute absent
    scope: str | None  # None = attribute absent
    group_index: int  # index of the row group owning the cell's row
    row_offset: int  # row index within its row group (source order)
    rowspan: int  # raw attribute value, 0 allowed
    colspan: int
    # Filled during layout:
    anchor_row: int = -1  # absolute row of the top-left corner
    anchor_col: int = -1
    eff_rowspan: int = 0  # after truncation / rowspan=0 expansion
    eff_colspan: int = 0


@dataclass
class RowGroup:
    """thead/tbody/tfoot or an implicit group of direct tr children."""

    kind: str  # "thead" | "tbody" | "tfoot" | "implicit"
    cells: list[Cell] = field(default_factory=list)
    row_count: int = 0  # number of source rows in the group
    start_row: int = 0  # absolute index of the group's first row


@dataclass
class ColGroup:
    """A column group from <colgroup span=N>; an implicit tail group
    covering undeclared columns is appended last."""

    start: int
    span: int


@dataclass
class Table:
    """A compiled table ready for describe()."""

    id: str
    groups: list[RowGroup]
    colgroups: list[ColGroup]
    cells: list[Cell]
    by_id: dict[str, Cell]
    grid: list[list[Cell | None]]  # grid[r][c] -> covering cell or None (hole)
    row_count: int
    col_count: int
