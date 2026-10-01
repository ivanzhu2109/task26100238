# table_context

供语音导航使用的 HTML 表格上下文组件，支持合并单元格与多级表头。
纯标准库实现，单线程、内存内处理，无第三方依赖。

## API

```python
from table_context import compile_table, describe

table = compile_table(html, "my-table")   # 编译 id 为 my-table 的表格
info = describe(table, 1, 2)              # 按从 0 开始的逻辑坐标查询
```

- `compile_table(html, table_id)`：解析并布局指定表格，返回 `Table`。
  占用矩形重叠时抛出 `TableConflictError`；找不到表格时抛出 `KeyError`。
- `describe(table, row, col)`：返回 `CellInfo`（`id`、左上角 `row`/`col`、
  正文 `text`、有序表头列表 `headers`，每项含 `id` 与 `text`）；
  空洞返回 `None`。同一合并单元格覆盖的所有坐标返回完全相同的结果。

## 规则摘要

- 布局：`thead`/`tbody`/`tfoot` 各自成行组，直属 `tr` 形成隐式行组；
  `rowspan=0` 延伸到行组末尾，正 `rowspan` 截断到行组末尾；锚点为本行
  游标起首个空格，占用矩形与已有单元格重叠即编译失败；允许空洞。
- 列组：仅计 `colgroup` 的正 `span` 属性，剩余列归为一个列组。
- 表头：单元格写了 `headers` 属性（含空值）则完全取代隐式推导，只接受
  本表其他 `th` 的 id，不递归展开；否则按 `scope`（row/col/rowgroup/
  colgroup）匹配，再对未写 `scope` 的 `th` 做向左/向上射线扫描（跳过空洞、
  遇 `td` 终止），合并去重后按锚点行列升序排列。
- 嵌套表格的行、单元格、id 与文本不会混入外层；正文按源顺序拼接，
  连续空白折为一个空格并去首尾空白。

## 测试

```sh
python3 -m unittest discover -s tests -v
```
