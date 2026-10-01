"""表头推导：headers 属性覆盖、scope 匹配与射线扫描。"""

from __future__ import annotations

from .model import Cell, HeaderEntry, Table


def _intervals_intersect(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


def _headers_from_attr(table: Table, cell: Cell) -> list[HeaderEntry]:
    entries: list[HeaderEntry] = []
    seen: set[str] = set()
    for token in cell.headers_attr.split():
        if token in seen or token == cell.cell_id:
            continue
        target = table.by_id.get(token)
        if target is None or target.tag != "th":
            continue
        seen.add(token)
        entries.append(HeaderEntry(id=target.cell_id, text=target.text))
    return entries


def _scope_matches(table: Table, target: Cell, th: Cell) -> bool:
    if th.scope == "row":
        return th.col_end <= target.col and _intervals_intersect(
            th.row, th.row_end, target.row, target.row_end
        )
    if th.scope == "col":
        return th.row_end <= target.row and _intervals_intersect(
            th.col, th.col_end, target.col, target.col_end
        )
    if th.scope == "rowgroup":
        return th.row_group_index == target.row_group_index
    if th.scope == "colgroup":
        return any(
            _intervals_intersect(th.col, th.col_end, g_start, g_end)
            and _intervals_intersect(target.col, target.col_end, g_start, g_end)
            for g_start, g_end in table.col_group_ranges
        )
    return False


def _scan_ray(
    table: Table, positions: list[tuple[int, int]], found: dict[str, Cell]
) -> None:
    """沿射线逐格扫描：跳过空洞，遇 td 终止，收集未写 scope 的 th。"""
    for pos in positions:
        cell = table.grid.get(pos)
        if cell is None:
            continue
        if cell.tag == "td":
            return
        if cell.scope is None:
            found[cell.cell_id] = cell


def _implicit_headers(table: Table, target: Cell) -> list[HeaderEntry]:
    found: dict[str, Cell] = {}

    for th in table.cells:
        if th.tag != "th" or th.cell_id == target.cell_id or th.scope is None:
            continue
        if _scope_matches(table, target, th):
            found[th.cell_id] = th

    for row in range(target.row, target.row_end):
        positions = [(row, col) for col in range(target.col - 1, -1, -1)]
        _scan_ray(table, positions, found)
    for col in range(target.col, target.col_end):
        positions = [(row, col) for row in range(target.row - 1, -1, -1)]
        _scan_ray(table, positions, found)

    ordered = sorted(found.values(), key=lambda c: (c.row, c.col))
    return [HeaderEntry(id=c.cell_id, text=c.text) for c in ordered]


def compute_headers(table: Table, cell: Cell) -> list[HeaderEntry]:
    """计算目标单元格的有序表头列表。"""
    if cell.headers_attr is not None:
        return _headers_from_attr(table, cell)
    return _implicit_headers(table, cell)
