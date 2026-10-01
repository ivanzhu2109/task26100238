"""供语音导航使用的 HTML 表格上下文组件。

公开 API：
- compile_table(html, table_id) -> Table
- describe(table, row, col) -> CellInfo | None
"""

from __future__ import annotations

from .headers import compute_headers
from .layout import layout_table
from .model import CellInfo, Table, TableConflictError
from .parser import parse_table

__all__ = ["compile_table", "describe", "Table", "CellInfo", "TableConflictError"]


def compile_table(html: str, table_id: str) -> Table:
    """编译 html 中 id 为 table_id 的表格。"""
    return layout_table(parse_table(html, table_id))


def describe(table: Table, row: int, col: int) -> CellInfo | None:
    """按从 0 开始的逻辑坐标描述所属单元格；空洞返回 None。"""
    cell = table.grid.get((row, col))
    if cell is None:
        return None
    return CellInfo(
        id=cell.cell_id,
        row=cell.row,
        col=cell.col,
        text=cell.text,
        headers=compute_headers(table, cell),
    )
