"""布局：把原始行组摆放到逻辑网格上，并计算列组区间。"""

from __future__ import annotations

from .model import Cell, RawTable, Table, TableConflictError


def layout_table(raw: RawTable) -> Table:
    """按跨度规则摆放单元格，冲突时抛出 TableConflictError。"""
    grid: dict[tuple[int, int], Cell] = {}
    cells: list[Cell] = []
    by_id: dict[str, Cell] = {}
    cell_row_group: dict[str, int] = {}
    row_group_ranges: list[tuple[int, int]] = []

    row_cursor = 0
    for group_index, group in enumerate(raw.row_groups):
        group_start = row_cursor
        group_row_count = len(group.rows)
        for row_in_group, raw_row in enumerate(group.rows):
            row = group_start + row_in_group
            rows_left_in_group = group_row_count - row_in_group
            col_cursor = 0
            for raw_cell in raw_row.cells:
                anchor = col_cursor
                while (row, anchor) in grid:
                    anchor += 1
                if raw_cell.rowspan == 0:
                    rowspan = rows_left_in_group
                else:
                    rowspan = min(raw_cell.rowspan, rows_left_in_group)
                colspan = raw_cell.colspan
                overlap = [
                    (r, c)
                    for r in range(row, row + rowspan)
                    for c in range(anchor, anchor + colspan)
                    if (r, c) in grid
                ]
                if overlap:
                    raise TableConflictError(
                        f"单元格 {raw_cell.cell_id!r} 的占用矩形与已有单元格重叠: {overlap}"
                    )
                cell = Cell(
                    cell_id=raw_cell.cell_id,
                    tag=raw_cell.tag,
                    row=row,
                    col=anchor,
                    rowspan=rowspan,
                    colspan=colspan,
                    row_group_index=group_index,
                    headers_attr=raw_cell.headers_attr,
                    scope=raw_cell.scope,
                    text=raw_cell.text,
                )
                for r in range(row, row + rowspan):
                    for c in range(anchor, anchor + colspan):
                        grid[(r, c)] = cell
                cells.append(cell)
                by_id[cell.cell_id] = cell
                cell_row_group[cell.cell_id] = group_index
                col_cursor = anchor + colspan
        row_cursor = group_start + group_row_count
        row_group_ranges.append((group_start, row_cursor))

    total_cols = max((cell.col_end for cell in cells), default=0)
    col_group_ranges: list[tuple[int, int]] = []
    col_start = 0
    for raw_col_group in raw.col_groups:
        col_group_ranges.append((col_start, col_start + raw_col_group.span))
        col_start += raw_col_group.span
    if col_start < total_cols or not col_group_ranges:
        col_group_ranges.append((col_start, total_cols))

    return Table(
        table_id=raw.table_id,
        cells=cells,
        col_group_ranges=col_group_ranges,
        row_group_ranges=row_group_ranges,
        cell_row_group=cell_row_group,
        grid=grid,
        by_id=by_id,
    )
