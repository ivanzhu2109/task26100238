"""Place cells on the logical grid and detect overlaps."""

from __future__ import annotations

from .model import Cell, ColGroup, RowGroup, Table
from .parser import TableStructureError


def build_table(table_id: str, groups: list[RowGroup], raw_colgroups: list[int]) -> Table:
    """Assign anchors, apply span rules, fill the occupancy grid.

    Raises TableStructureError when a cell's rectangle overlaps an
    already occupied slot.
    """
    total_rows = 0
    for group in groups:
        group.start_row = total_rows
        total_rows += group.row_count

    grid: list[list[Cell | None]] = [[] for _ in range(total_rows)]

    def slot(row: int, col: int) -> Cell | None:
        row_slots = grid[row]
        return row_slots[col] if col < len(row_slots) else None

    def occupy(cell: Cell, row: int, col: int) -> None:
        row_slots = grid[row]
        if len(row_slots) <= col:
            row_slots.extend([None] * (col + 1 - len(row_slots)))
        row_slots[col] = cell

    col_count = 0
    for group in groups:
        rows_of_group: list[list[Cell]] = [[] for _ in range(group.row_count)]
        for cell in group.cells:
            rows_of_group[cell.row_offset].append(cell)
        for row_offset, row_cells in enumerate(rows_of_group):
            abs_row = group.start_row + row_offset
            cursor = 0
            for cell in row_cells:
                eff_rowspan = _effective_rowspan(cell, group)
                eff_colspan = max(1, cell.colspan)
                col = cursor
                while slot(abs_row, col) is not None:
                    col += 1
                for r in range(abs_row, abs_row + eff_rowspan):
                    for c in range(col, col + eff_colspan):
                        if slot(r, c) is not None:
                            raise TableStructureError(
                                f"cell {cell.id!r} overlaps cell "
                                f"{slot(r, c).id!r} at ({r}, {c})"
                            )
                cell.anchor_row = abs_row
                cell.anchor_col = col
                cell.eff_rowspan = eff_rowspan
                cell.eff_colspan = eff_colspan
                for r in range(abs_row, abs_row + eff_rowspan):
                    for c in range(col, col + eff_colspan):
                        occupy(cell, r, c)
                cursor = col + eff_colspan
                col_count = max(col_count, cursor)

    colgroups = list(raw_colgroups)
    declared = sum(g.span for g in colgroups)
    if declared < col_count:
        colgroups.append(ColGroup(start=declared, span=col_count - declared))

    cells = [cell for group in groups for cell in group.cells]
    return Table(
        id=table_id,
        groups=groups,
        colgroups=colgroups,
        cells=cells,
        by_id={cell.id: cell for cell in cells},
        grid=grid,
        row_count=total_rows,
        col_count=col_count,
    )


def _effective_rowspan(cell: Cell, group: RowGroup) -> int:
    remaining = group.row_count - cell.row_offset
    if cell.rowspan == 0:
        return remaining
    if cell.rowspan < 0:
        return 1
    return min(cell.rowspan, remaining)
