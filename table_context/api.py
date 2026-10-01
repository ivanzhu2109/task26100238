"""Public API: compile_table() and describe()."""

from __future__ import annotations

from .headers import resolve_headers
from .layout import build_table
from .model import Description, Table
from .parser import parse_table


def compile_table(html: str, table_id: str) -> Table:
    """Compile the table with the given id found in html."""
    groups, colgroups, _ = parse_table(html, table_id)
    return build_table(table_id, groups, colgroups)


def describe(table: Table, row: int, col: int) -> Description | None:
    """Describe the cell covering logical coordinate (row, col).

    Returns None for holes and out-of-range coordinates.
    """
    if row < 0 or row >= table.row_count or col < 0 or col >= table.col_count:
        return None
    row_slots = table.grid[row]
    cell = row_slots[col] if col < len(row_slots) else None
    if cell is None:
        return None
    return Description(
        id=cell.id,
        row=cell.anchor_row,
        col=cell.anchor_col,
        text=cell.text,
        headers=resolve_headers(table, cell),
    )
