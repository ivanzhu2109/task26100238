"""table_context 的自动测试（手写预期结果）。"""

import unittest

from table_context import compile_table, describe, TableConflictError


def header_ids(info):
    return [h.id for h in info.headers]


class RowspanZeroAndNestedTest(unittest.TestCase):
    """rowspan=0、多行组、横纵合并、嵌套表格与边界空洞，逐格验证。"""

    HTML = """
    <table id="t1">
      <colgroup span="2"></colgroup>
      <tr>
        <th id="rh" rowspan="0">RH</th>
        <td id="mm" rowspan="2" colspan="2">M <i>M</i></td>
        <td id="nt">pre
          <table id="nested"><tr><td id="nx">inner</td></tr></table>
        post</td>
      </tr>
      <tr>
        <td id="p1">P1</td>
      </tr>
      <tr>
        <td id="p2" colspan="2">P2</td>
      </tr>
      <tbody>
        <tr>
          <td id="q" rowspan="0">Q</td>
          <td id="r" colspan="2">R</td>
        </tr>
        <tr>
          <td id="s">S</td>
        </tr>
      </tbody>
    </table>
    """

    # 5 行 4 列的期望归属：(id, 左上角行, 左上角列)，None 表示空洞
    EXPECTED = [
        [("rh", 0, 0), ("mm", 0, 1), ("mm", 0, 1), ("nt", 0, 3)],
        [("rh", 0, 0), ("mm", 0, 1), ("mm", 0, 1), ("p1", 1, 3)],
        [("rh", 0, 0), ("p2", 2, 1), ("p2", 2, 1), None],
        [("q", 3, 0), ("r", 3, 1), ("r", 3, 1), None],
        [("q", 3, 0), ("s", 4, 1), None, None],
    ]

    @classmethod
    def setUpClass(cls):
        cls.table = compile_table(cls.HTML, "t1")

    def test_every_coordinate(self):
        for row, expected_row in enumerate(self.EXPECTED):
            for col, expected in enumerate(expected_row):
                info = describe(self.table, row, col)
                if expected is None:
                    self.assertIsNone(info, f"({row},{col}) 应为空洞")
                else:
                    want_id, want_row, want_col = expected
                    self.assertIsNotNone(info, f"({row},{col}) 不应为空洞")
                    self.assertEqual(
                        (info.id, info.row, info.col),
                        (want_id, want_row, want_col),
                        f"({row},{col}) 归属错误",
                    )

    def test_merged_cell_results_identical(self):
        coords = [(0, 1), (0, 2), (1, 1), (1, 2)]
        infos = [describe(self.table, r, c) for r, c in coords]
        for info in infos[1:]:
            self.assertEqual(infos[0], info)

    def test_nested_table_isolated(self):
        self.assertNotIn("nx", self.table.by_id)
        self.assertNotIn("nested", self.table.by_id)
        self.assertEqual(describe(self.table, 0, 3).text, "pre post")

    def test_text_collapsed(self):
        self.assertEqual(describe(self.table, 0, 1).text, "M M")

    def test_implicit_headers(self):
        self.assertEqual(header_ids(describe(self.table, 0, 1)), ["rh"])
        self.assertEqual(header_ids(describe(self.table, 1, 3)), [])
        self.assertEqual(header_ids(describe(self.table, 2, 1)), ["rh"])
        self.assertEqual(header_ids(describe(self.table, 3, 0)), ["rh"])
        self.assertEqual(header_ids(describe(self.table, 3, 1)), [])
        self.assertEqual(header_ids(describe(self.table, 4, 1)), [])

    def test_row_and_col_group_ranges(self):
        self.assertEqual(self.table.row_group_ranges, [(0, 3), (3, 5)])
        self.assertEqual(self.table.col_group_ranges, [(0, 2), (2, 4)])


class ScopeAndRayTest(unittest.TestCase):
    """目标横跨两个列组；行组与多级表头并存；射线被 td 阻断；重复命中去重。"""

    HTML = """
    <table id="t2">
      <colgroup span="2"></colgroup>
      <colgroup span="2"></colgroup>
      <thead>
        <tr>
          <th id="mega" colspan="4">Mega</th>
        </tr>
        <tr>
          <th id="c0" scope="col">C0</th>
          <th id="c1" scope="col">C1</th>
          <th id="c2" scope="col">C2</th>
          <th id="c3" scope="col">C3</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <th id="bg" scope="rowgroup">BG</th>
          <td id="tgt" colspan="2">T</td>
          <td id="tail">X</td>
        </tr>
        <tr>
          <th id="rh3">RH3</th>
          <td id="blk">B</td>
          <td id="tgt2" colspan="2">T2</td>
        </tr>
      </tbody>
    </table>
    """

    @classmethod
    def setUpClass(cls):
        cls.table = compile_table(cls.HTML, "t2")

    def test_target_spanning_two_colgroups(self):
        # tgt 覆盖列 1-2，横跨列组 (0,2) 与 (2,4)
        info = describe(self.table, 2, 1)
        self.assertEqual((info.id, info.row, info.col), ("tgt", 2, 1))
        # mega 被列 1、列 2 两条向上射线重复命中，仅保留一次
        self.assertEqual(header_ids(info), ["mega", "c1", "c2", "bg"])
        self.assertEqual(
            [(h.id, h.text) for h in info.headers],
            [("mega", "Mega"), ("c1", "C1"), ("c2", "C2"), ("bg", "BG")],
        )
        # 同一合并单元格的另一坐标结果完全相同
        self.assertEqual(info, describe(self.table, 2, 2))

    def test_ray_blocked_by_td(self):
        # tgt2 向左被 blk 阻断（rh3 不可见），向上被 tgt/tail 阻断（mega 不可见）
        info = describe(self.table, 3, 2)
        self.assertEqual(info.id, "tgt2")
        self.assertEqual(header_ids(info), ["c2", "c3", "bg"])

    def test_scope_row_not_matched_when_beside(self):
        # rh3 未写 scope，且被 td 阻断，不出现在 tgt2 表头中
        self.assertNotIn("rh3", header_ids(describe(self.table, 3, 2)))


class HeadersAttrTest(unittest.TestCase):
    """headers 属性的覆盖、空值、去重、无效与跨表引用。"""

    HTML = """
    <table id="t3">
      <tr>
        <th id="h1">H1</th>
        <th id="h2">H2</th>
        <th id="h3" headers="h1">H3</th>
        <th id="h4" headers="h4 h1">H4</th>
        <td id="d1">D1</td>
      </tr>
      <tr>
        <td id="e" headers="">E</td>
        <td id="dup" headers="h1 h2 h1 h2">DUP</td>
        <td id="bad" headers="h1 d1 nope h2">BAD</td>
        <td id="rec" headers="h3">REC</td>
        <td id="cross" headers="h1 other-th">X</td>
      </tr>
    </table>
    <table id="other">
      <tr><th id="other-th">O</th></tr>
    </table>
    """

    @classmethod
    def setUpClass(cls):
        cls.table = compile_table(cls.HTML, "t3")

    def headers_of(self, cell_id):
        cell = self.table.by_id[cell_id]
        return header_ids(describe(self.table, cell.row, cell.col))

    def test_empty_headers_overrides_implicit(self):
        self.assertEqual(self.headers_of("e"), [])

    def test_duplicate_refs_keep_first_order(self):
        self.assertEqual(self.headers_of("dup"), ["h1", "h2"])

    def test_invalid_refs_ignored(self):
        # d1 是 td，nope 不存在
        self.assertEqual(self.headers_of("bad"), ["h1", "h2"])

    def test_no_recursive_expansion(self):
        # h3 自身的 headers 指向 h1，但引用 h3 时不展开
        self.assertEqual(self.headers_of("rec"), ["h3"])

    def test_cross_table_ref_ignored(self):
        self.assertEqual(self.headers_of("cross"), ["h1"])

    def test_self_ref_excluded(self):
        self.assertEqual(self.headers_of("h4"), ["h1"])

    def test_headers_attr_on_th_overrides(self):
        # h3 写了 headers，不再隐式推导（否则射线会命中 h1/h2）
        self.assertEqual(self.headers_of("h3"), ["h1"])


class ConflictTest(unittest.TestCase):
    """锚点为空但 colspan 横跨既有 rowspan 占格，必须报冲突。"""

    def test_colspan_overlaps_rowspan(self):
        html = """
        <table id="b">
          <tr><td id="first">1</td><td id="a" rowspan="2">2</td></tr>
          <tr><td id="x" colspan="2">3</td></tr>
        </table>
        """
        with self.assertRaises(TableConflictError):
            compile_table(html, "b")

    def test_missing_table_raises(self):
        with self.assertRaises(KeyError):
            compile_table("<table id='a'></table>", "zzz")


class ScopeRowAndColgroupTest(unittest.TestCase):
    """scope=row 与 scope=colgroup 的匹配与排除。"""

    HTML = """
    <table id="t4">
      <colgroup span="1"></colgroup>
      <tr><th id="sr" scope="row">SR</th><td id="a1">A1</td><td id="a2">A2</td></tr>
      <tr><th id="scg" scope="colgroup">SCG</th><td id="b1">B1</td><td id="b2">B2</td></tr>
      <tr><td id="c0">C0</td><td id="c1">C1</td><td id="c2">C2</td></tr>
    </table>
    """

    @classmethod
    def setUpClass(cls):
        cls.table = compile_table(cls.HTML, "t4")

    def headers_of(self, cell_id):
        cell = self.table.by_id[cell_id]
        return header_ids(describe(self.table, cell.row, cell.col))

    def test_scope_row_matches_same_row_only(self):
        self.assertEqual(self.headers_of("a1"), ["sr"])
        self.assertEqual(self.headers_of("a2"), ["sr"])
        self.assertEqual(self.headers_of("b1"), [])

    def test_scope_colgroup_shares_declared_group(self):
        # c0 与 scg 同处列组 (0,1)；c1/c2 在未声明的剩余列组，与 scg 不共享
        self.assertEqual(self.headers_of("c0"), ["scg"])
        self.assertEqual(self.headers_of("c1"), [])
        self.assertEqual(self.headers_of("b2"), [])


if __name__ == "__main__":
    unittest.main()
