"""Resolve the ordered header list of a cell."""

from __future__ import annotations

from .model import Cell, HeaderRef, Table


def resolve_headers(table: Table, cell: Cell) -> tuple[HeaderRef, ...]:
    """Compute the ordered header list for a cell of a compiled table."""
    if cell.headers_attr is not None:
        return _from_headers_attr(table, cell)
    found: dict[str, Cell] = {}
    for header in _scope_matches(table, cell):
        found.setdefault(header.id, header)
    for header in _ray_matches(table, cell):
        found.setdefault(header.id, header)
    ordered = sorted(found.values(), key=lambda h: (h.anchor_row, h.anchor_col))
    return tuple(HeaderRef(id=h.id, text=h.text) for h in ordered)


def _from_headers_attr(table: Table, cell: Cell) -> tuple[HeaderRef, ...]:
    refs: list[HeaderRef] = []
    seen: set[str] = set()
    for token in cell.headers_attr:
        if token in seen:
            continue
        seen.add(token)
        target = table.by_id.get(token)
        if target is None or target is cell or not target.is_header:
            continue
        refs.append(HeaderRef(id=target.id, text=target.text))
    return tuple(refs)


def _rows(cell: Cell) -> range:
    return range(cell.anchor_row, cell.anchor_row + cell.eff_rowspan)


def _cols(cell: Cell) -> range:
    return range(cell.anchor_col, cell.anchor_col + cell.eff_colspan)


def _ranges_intersect(a: range, b: range) -> bool:
    return a.start < b.stop and b.start < a.stop


def _scope_matches(table: Table, cell: Cell) -> list[Cell]:
    matches: list[Cell] = []
    cell_rows, cell_cols = _rows(cell), _cols(cell)
    for other in table.cells:
        if other is cell or not other.is_header or other.scope is None:
            continue
        other_rows, other_cols = _rows(other), _cols(other)
        if other.scope == "row":
            if other_cols.stop <= cell_cols.start and _ranges_intersect(other_rows, cell_rows):
                matches.append(other)
        elif other.scope == "col":
            if other_rows.stop <= cell_rows.start and _ranges_intersect(other_cols, cell_cols):
                matches.append(other)
        elif other.scope == "rowgroup":
            if other.group_index == cell.group_index:
                matches.append(other)
        elif other.scope == "colgroup":
            if _share_colgroup(table, cell_cols, other_cols):
                matches.append(other)
    return matches


def _share_colgroup(table: Table, a: range, b: range) -> bool:
    for group in table.colgroups:
        group_range = range(group.start, group.start + group.span)
        if _ranges_intersect(a, group_range) and _ranges_intersect(b, group_range):
            return True
    return False


def _ray_matches(table: Table, cell: Cell) -> list[Cell]:
    matches: list[Cell] = []

    def look(row: int, col: int) -> bool:
        """True to keep scanning, False to terminate the ray."""
        occupant = table.grid[row][col] if col < len(table.grid[row]) else None
        if occupant is None:
            return True
        if not occupant.is_header:
            return False
        if occupant.scope is None and occupant is not cell:
            matches.append(occupant)
        return True

    for row in _rows(cell):
        for col in range(cell.anchor_col - 1, -1, -1):
            if not look(row, col):
                break
    for col in _cols(cell):
        for row in range(cell.anchor_row - 1, -1, -1):
            if not look(row, col):
                break
    return matches
