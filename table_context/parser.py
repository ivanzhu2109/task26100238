"""Parse HTML into row groups, cells and column groups of the target table.

Nested tables are isolated: their rows, cells, ids and text never leak
into the enclosing table.
"""

from __future__ import annotations

from html.parser import HTMLParser

from .model import Cell, ColGroup, RowGroup


class TableNotFoundError(KeyError):
    """Raised when no table with the requested id exists."""


class TableStructureError(ValueError):
    """Raised when the target table violates the layout rules."""


def parse_table(html: str, table_id: str) -> tuple[list[RowGroup], list[ColGroup], list[Cell]]:
    """Extract row groups, column groups and cells of the table with
    the given id. Column group spans are raw (not yet normalized)."""
    parser = _TargetTableParser(table_id)
    parser.feed(html)
    parser.close()
    if not parser.found:
        raise TableNotFoundError(table_id)
    return parser.groups, parser.colgroups, parser.cells


def _parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


class _TargetTableParser(HTMLParser):
    def __init__(self, table_id: str) -> None:
        super().__init__(convert_charrefs=True)
        self.table_id = table_id
        self.found = False
        self.done = False
        self.groups: list[RowGroup] = []
        self.colgroups: list[ColGroup] = []
        self.cells: list[Cell] = []

        self._depth = 0  # table nesting depth, target table = 1
        self._open_group: RowGroup | None = None  # thead/tbody/tfoot accepting rows
        self._implicit_open = False  # last direct child run was implicit trs
        self._cur_cell: Cell | None = None
        self._cur_text: list[str] = []
        self._cell_nested = 0  # nested table depth inside the captured cell

    # -- helpers ---------------------------------------------------------
    def _in_target(self) -> bool:
        return self._depth >= 1

    def _skipping_nested(self) -> bool:
        # Inside a table nested within the target table.
        return self._depth >= 2

    # -- element handlers ------------------------------------------------
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.done:
            return
        attr = {key: (value if value is not None else "") for key, value in attrs}
        if tag == "table":
            if not self._in_target():
                if attr.get("id") == self.table_id:
                    self.found = True
                    self._depth = 1
                # Tables before/around the target are ignored entirely.
            else:
                self._depth += 1
                if self._cur_cell is not None:
                    self._cell_nested += 1
            return
        if not self._in_target() or self._skipping_nested():
            return
        if tag in ("thead", "tbody", "tfoot"):
            group = RowGroup(kind=tag)
            self.groups.append(group)
            self._open_group = group
            self._implicit_open = False
        elif tag == "colgroup":
            span = _parse_int(attr.get("span"), 1)
            start = self.colgroups[-1].start + self.colgroups[-1].span if self.colgroups else 0
            self.colgroups.append(ColGroup(start=start, span=span))
            self._implicit_open = False
        elif tag == "tr":
            if self._open_group is None:
                if not self._implicit_open or not self.groups or self.groups[-1].kind != "implicit":
                    self.groups.append(RowGroup(kind="implicit"))
                self._open_group = self.groups[-1]
                self._implicit_open = True
            self._open_group.row_count += 1
        elif tag in ("th", "td"):
            headers_attr = attr.get("headers")
            cell = Cell(
                id=attr.get("id", ""),
                is_header=(tag == "th"),
                text="",
                headers_attr=None if headers_attr is None else tuple(headers_attr.split()),
                scope=attr.get("scope"),
                group_index=len(self.groups) - 1,
                row_offset=self._open_group.row_count - 1,
                rowspan=_parse_int(attr.get("rowspan"), 1),
                colspan=_parse_int(attr.get("colspan"), 1),
            )
            self._open_group.cells.append(cell)
            self.cells.append(cell)
            self._cur_cell = cell
            self._cur_text = []
            self._cell_nested = 0

    def handle_endtag(self, tag: str) -> None:
        if self.done:
            return
        if tag == "table":
            if self._in_target():
                self._depth -= 1
                if self._cur_cell is not None and self._cell_nested > 0:
                    self._cell_nested -= 1
                if self._depth == 0:
                    self.done = True
            return
        if not self._in_target() or self._skipping_nested():
            return
        if tag in ("thead", "tbody", "tfoot"):
            self._open_group = None
        elif tag == "tr":
            if self._open_group is not None and self._open_group.kind != "implicit":
                pass  # group stays open until its own end tag
            else:
                self._open_group = None
        elif tag in ("th", "td"):
            if self._cur_cell is not None:
                self._cur_cell.text = " ".join("".join(self._cur_text).split())
                self._cur_cell = None
                self._cur_text = []

    def handle_data(self, data: str) -> None:
        if self.done or not self._in_target() or self._skipping_nested():
            return
        if self._cur_cell is not None and self._cell_nested == 0:
            self._cur_text.append(data)
