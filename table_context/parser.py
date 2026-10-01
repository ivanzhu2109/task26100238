"""HTML 解析：从 HTML 文本中抽取指定表格的原始结构。"""

from __future__ import annotations

from html.parser import HTMLParser

from .model import RawCell, RawColGroup, RawRow, RawRowGroup, RawTable

_ROW_GROUP_TAGS = {"thead": "thead", "tbody": "tbody", "tfoot": "tfoot"}


def _parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


class _TableExtractor(HTMLParser):
    """抽取目标表格的结构；嵌套表格的内容一律忽略。"""

    def __init__(self, table_id: str) -> None:
        super().__init__(convert_charrefs=True)
        self._wanted = table_id
        self.result: RawTable | None = None
        self._in_target = False
        self._done = False
        self._nested_depth = 0  # 目标表内部嵌套 table 的深度
        self._current_group: RawRowGroup | None = None
        self._current_row: RawRow | None = None
        self._current_cell: RawCell | None = None
        self._text_parts: list[str] = []

    # -- 内部工具 -----------------------------------------------------

    def _active(self) -> bool:
        """是否正处于目标表的直接内容层级（非嵌套表）。"""
        return self._in_target and not self._done and self._nested_depth == 0

    def _finish_cell(self) -> None:
        if self._current_cell is None:
            return
        text = " ".join("".join(self._text_parts).split())
        self._current_cell.text = text
        self._current_row.cells.append(self._current_cell)
        self._current_cell = None
        self._text_parts = []

    def _finish_row(self) -> None:
        self._finish_cell()
        if self._current_row is None:
            return
        self._current_group.rows.append(self._current_row)
        self._current_row = None

    # -- HTMLParser 回调 ----------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._done:
            return
        attr = dict(attrs)
        if tag == "table":
            if not self._in_target:
                if attr.get("id") == self._wanted:
                    self._in_target = True
                    self.result = RawTable(table_id=self._wanted)
            else:
                self._nested_depth += 1
            return
        if not self._active():
            return
        if tag in _ROW_GROUP_TAGS:
            self._finish_row()
            group = RawRowGroup(kind=_ROW_GROUP_TAGS[tag])
            self.result.row_groups.append(group)
            self._current_group = group
        elif tag == "tr":
            self._finish_row()
            if self._current_group is None:
                group = RawRowGroup(kind="implicit")
                self.result.row_groups.append(group)
                self._current_group = group
            self._current_row = RawRow()
        elif tag in ("th", "td"):
            self._finish_cell()
            rowspan = _parse_int(attr.get("rowspan"), 1)
            if rowspan < 0:
                rowspan = 1
            colspan = _parse_int(attr.get("colspan"), 1)
            if colspan < 1:
                colspan = 1
            headers_attr = attr.get("headers")
            if headers_attr is None and "headers" in attr:
                headers_attr = ""
            self._current_cell = RawCell(
                cell_id=attr.get("id", ""),
                tag=tag,
                rowspan=rowspan,
                colspan=colspan,
                headers_attr=headers_attr,
                scope=(attr.get("scope") or None),
                text="",
                source_index=len(self._current_row.cells),
            )
            self._text_parts = []
        elif tag == "colgroup":
            span = _parse_int(attr.get("span"), 1)
            if span < 1:
                span = 1
            self.result.col_groups.append(RawColGroup(span=span))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag in _ROW_GROUP_TAGS or tag == "tr" or tag in ("th", "td"):
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if self._done:
            return
        if tag == "table":
            if self._nested_depth > 0:
                self._nested_depth -= 1
            elif self._in_target:
                self._finish_row()
                self._done = True
            return
        if not self._active():
            return
        if tag in _ROW_GROUP_TAGS:
            self._finish_row()
            self._current_group = None
        elif tag == "tr":
            self._finish_row()
        elif tag in ("th", "td"):
            self._finish_cell()

    def handle_data(self, data: str) -> None:
        if self._active() and self._current_cell is not None:
            self._text_parts.append(data)


def parse_table(html: str, table_id: str) -> RawTable:
    """解析 html 中 id 为 table_id 的表格，返回原始结构。

    找不到目标表格时抛出 KeyError。
    """
    extractor = _TableExtractor(table_id)
    extractor.feed(html)
    extractor.close()
    if extractor.result is None:
        raise KeyError(f"找不到 id 为 {table_id!r} 的表格")
    return extractor.result
