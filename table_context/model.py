"""数据类型定义：表格编译与描述所需的全部结构。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RawCell:
    """解析阶段得到的单元格（尚未布局）。"""

    cell_id: str
    tag: str  # "th" 或 "td"
    rowspan: int
    colspan: int
    headers_attr: Optional[str]  # None 表示未写 headers 属性
    scope: Optional[str]  # None 表示未写 scope
    text: str
    source_index: int  # 在所属行内的出现顺序


@dataclass
class RawRow:
    cells: list[RawCell] = field(default_factory=list)


@dataclass
class RawRowGroup:
    kind: str  # "thead" | "tbody" | "tfoot" | "implicit"
    rows: list[RawRow] = field(default_factory=list)


@dataclass
class RawColGroup:
    span: int


@dataclass
class RawTable:
    table_id: str
    row_groups: list[RawRowGroup] = field(default_factory=list)
    col_groups: list[RawColGroup] = field(default_factory=list)


@dataclass
class Cell:
    """布局完成后的单元格。"""

    cell_id: str
    tag: str
    row: int  # 左上角逻辑行
    col: int  # 左上角逻辑列
    rowspan: int
    colspan: int
    row_group_index: int
    headers_attr: Optional[str]
    scope: Optional[str]
    text: str

    @property
    def row_end(self) -> int:
        return self.row + self.rowspan

    @property
    def col_end(self) -> int:
        return self.col + self.colspan


@dataclass
class HeaderEntry:
    """describe 返回的有序表头项。"""

    id: str
    text: str


@dataclass
class CellInfo:
    """describe 的返回结果。"""

    id: str
    row: int
    col: int
    text: str
    headers: list[HeaderEntry]


@dataclass
class Table:
    """编译完成的表格，describe 的输入。"""

    table_id: str
    cells: list[Cell]
    col_group_ranges: list[tuple[int, int]]  # 每个列组的 [start, end) 列区间
    row_group_ranges: list[tuple[int, int]]  # 每个行组的 [start, end) 行区间
    cell_row_group: dict[str, int]  # cell_id -> 行组下标
    grid: dict[tuple[int, int], Cell] = field(default_factory=dict)
    by_id: dict[str, Cell] = field(default_factory=dict)


class TableConflictError(ValueError):
    """单元格占用矩形互相重叠时抛出。"""
