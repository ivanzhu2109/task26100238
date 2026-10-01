# task26100238

## table_context — 语音导航用 HTML 表格上下文组件

纯标准库、单线程、内存内处理。把 HTML 表格编译为逻辑网格后，可按从 0
开始的逻辑坐标查询每个位置所属的单元格及其有序表头列表，支持合并单元格、
多级表头、行组（thead/tbody/tfoot/隐式）、列组（colgroup span）与嵌套表格隔离。

### 用法

```python
from table_context import compile_table, describe

table = compile_table(html, "my-table-id")   # 编译指定 id 的表格
desc = describe(table, 2, 1)                 # 查询逻辑坐标 (row=2, col=1)

if desc is None:
    ...            # 空洞或越界
else:
    desc.id        # 所属单元格 id
    desc.row, desc.col   # 单元格左上角坐标
    desc.text      # 正文（源顺序拼接，连续空白折为一个空格并去首尾空白）
    for h in desc.headers:   # 有序表头列表
        h.id, h.text
```

同一合并单元格覆盖的所有坐标返回完全相同的结果。

### 规则要点

- 布局：行按源顺序排列；thead/tbody/tfoot 各为行组，直属 table 的连续 tr
  组成隐式行组。rowspan 缺省 1，正值截断到行组末尾，0 延伸到组末尾；
  colspan 为正数。每行从游标起找首个空格作锚点再按跨度占格；占用矩形与
  已有单元格重叠时 `compile_table` 抛出 `TableStructureError`（空洞允许存在）。
- 表头：单元格带 `headers` 属性（含空值）时完全取代隐式推导，按空白拆分、
  保留首次出现顺序，仅接受本表其他 th 的 id，不递归展开。否则合并 scope
  （row/col/rowgroup/colgroup）匹配与无 scope th 的射线扫描（从目标矩形外
  开始，遇空洞跳过、遇 td 终止、遇 th 继续），按 id 去重后按锚点行、列升序。
- 嵌套表格的行、单元格、id 与文本均不混入外层。

### 测试

```sh
python3 -m unittest discover -s tests -v
```

### 文件结构

- `table_context/model.py` — 数据模型（Cell / RowGroup / ColGroup / Table / Description）
- `table_context/parser.py` — HTML 解析，抽取行组、列组与单元格，隔离嵌套表格
- `table_context/layout.py` — 锚点放置、跨度规则、占用网格与冲突检测
- `table_context/headers.py` — 表头推导（headers 属性 / scope / 射线扫描）
- `table_context/api.py` — `compile_table` 与 `describe`
- `tests/test_table_context.py` — 手写预期结果的自动测试
