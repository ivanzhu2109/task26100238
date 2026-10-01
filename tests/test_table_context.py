"""Hand-written expectation tests for table_context."""

from __future__ import annotations

import unittest

from table_context import (
    HeaderRef,
    TableNotFoundError,
    TableStructureError,
    compile_table,
    describe,
)


def header_ids(desc):
    return [h.id for h in desc.headers]


class MergedCellsAndRowGroupsTest(unittest.TestCase):
    """rowspan=0, multiple row groups, 2-D merges, nested table, holes.

    Grid (h3's rowspan=5 is truncated to the thead's single row):
        row0: h1 h2 h3
        row1: a  b  b      a: rowspan=0 -> extends to tbody end
        row2: a  c  d      d: wraps a nested table
        row3: a  c  e
        row4: f  f  .      (4,2) is a hole
    """

    HTML = """
    <table id="t1">
      <thead>
        <tr><th id="h1">H1</th><th id="h2">H2</th><th id="h3" rowspan="5">H3</th></tr>
      </thead>
      <tbody>
        <tr>
          <td id="a" rowspan="0">A</td>
          <td id="b" colspan="2">B</td>
        </tr>
        <tr>
          <td id="c" rowspan="2">C</td>
          <td id="d">D <span><em>styled</em></span>
            <table><tr><td id="n1">inner</td></tr></table> tail</td>
        </tr>
        <tr><td id="e">E</td></tr>
      </tbody>
      <tfoot>
        <tr><td id="f" colspan="2">F</td></tr>
      </tfoot>
    </table>
    """

    @classmethod
    def setUpClass(cls):
        cls.table = compile_table(cls.HTML, "t1")

    def test_grid_ownership(self):
        expected = [
            ["h1", "h2", "h3"],
            ["a", "b", "b"],
            ["a", "c", "d"],
            ["a", "c", "e"],
            ["f", "f", None],
        ]
        for row, expected_row in enumerate(expected):
            for col, expected_id in enumerate(expected_row):
                with self.subTest(row=row, col=col):
                    desc = describe(self.table, row, col)
                    if expected_id is None:
                        self.assertIsNone(desc)
                    else:
                        self.assertIsNotNone(desc)
                        self.assertEqual(desc.id, expected_id)

    def test_merged_cell_identical_everywhere(self):
        results = {describe(self.table, r, 0) for r in (1, 2, 3)}
        self.assertEqual(len(results), 1)
        desc = results.pop()
        self.assertEqual((desc.id, desc.row, desc.col, desc.text), ("a", 1, 0, "A"))
        b1 = describe(self.table, 1, 1)
        b2 = describe(self.table, 1, 2)
        self.assertEqual(b1, b2)
        self.assertEqual((b1.row, b1.col), (1, 1))

    def test_rowspan_truncated_to_group(self):
        # h3 declared rowspan=5 but thead has a single row.
        self.assertEqual(describe(self.table, 1, 2).id, "b")
        desc = describe(self.table, 0, 2)
        self.assertEqual((desc.id, desc.row, desc.col), ("h3", 0, 2))

    def test_nested_table_isolated(self):
        self.assertNotIn("n1", self.table.by_id)
        self.assertNotIn("inner", describe(self.table, 2, 2).text)
        self.assertEqual(describe(self.table, 2, 2).text, "D styled tail")

    def test_text_whitespace_collapsed(self):
        self.assertEqual(describe(self.table, 0, 0).text, "H1")

    def test_ray_headers(self):
        self.assertEqual(header_ids(describe(self.table, 1, 1)), ["h2", "h3"])
        # e: upward ray hits td d, leftward ray hits td c -> no headers.
        self.assertEqual(header_ids(describe(self.table, 3, 2)), [])

    def test_out_of_range(self):
        self.assertIsNone(describe(self.table, 5, 0))
        self.assertIsNone(describe(self.table, 0, 3))
        self.assertIsNone(describe(self.table, -1, 0))

    def test_missing_table(self):
        with self.assertRaises(TableNotFoundError):
            compile_table(self.HTML, "nope")


class HeaderResolutionTest(unittest.TestCase):
    """Column groups, rowgroup + multi-level headers, ray blocking,
    duplicate ray hits, headers attribute overrides.

    Grid (colgroups: g1 = cols 0-1, g2 = cols 2-3):
        row0: top1 top1 top2 top2     (scope=colgroup)
        row1: c1   mid  mid  c4       (scope=col)
        row2: hh1  wide wide hh4      (no scope)
        row3: rg   pl   pl   z        (rg: scope=rowgroup; pl: no scope)
        row4: r1   t    t    after    (r1: scope=row)
        row5: eh   dup  self cross    (headers attribute cases)
    """

    HTML = """
    <table id="other"><tr><th id="ext">Ext</th></tr></table>
    <table id="t2">
      <colgroup span="2"></colgroup>
      <colgroup span="2"></colgroup>
      <thead>
        <tr>
          <th id="top1" colspan="2" scope="colgroup">TopA</th>
          <th id="top2" colspan="2" scope="colgroup">TopB</th>
        </tr>
        <tr>
          <th id="c1" scope="col">C1</th>
          <th id="mid" colspan="2" scope="col">Mid</th>
          <th id="c4" scope="col">C4</th>
        </tr>
        <tr>
          <th id="hh1">H1</th>
          <th id="wide" colspan="2">Wide</th>
          <th id="hh4">H4</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <th id="rg" scope="rowgroup">RG</th>
          <th id="pl" colspan="2">PL</th>
          <td id="z">z</td>
        </tr>
        <tr>
          <th id="r1" scope="row">R1</th>
          <td id="t" colspan="2">T</td>
          <td id="after">A</td>
        </tr>
        <tr>
          <td id="eh" headers="">e</td>
          <td id="dup" headers="mid mid c1 zz mid">d</td>
          <td id="selfref" headers="selfref c1">s</td>
          <td id="crossref" headers="ext">x</td>
        </tr>
      </tbody>
    </table>
    """

    @classmethod
    def setUpClass(cls):
        cls.table = compile_table(cls.HTML, "t2")

    def test_target_spanning_two_colgroups(self):
        desc = describe(self.table, 4, 1)
        self.assertEqual((desc.id, desc.row, desc.col), ("t", 4, 1))
        # colgroup scope (top1/top2), col scope (mid), rowgroup scope (rg),
        # row scope (r1), ray hits (wide, pl; each hit by two rays, deduped),
        # sorted by anchor (row, col).
        self.assertEqual(
            header_ids(desc),
            ["top1", "top2", "mid", "wide", "rg", "pl", "r1"],
        )
        # Same merged cell, same result from the other covered coordinate.
        self.assertEqual(describe(self.table, 4, 2), desc)

    def test_header_texts(self):
        desc = describe(self.table, 4, 1)
        texts = {h.id: h.text for h in desc.headers}
        self.assertEqual(texts["top1"], "TopA")
        self.assertEqual(texts["wide"], "Wide")
        self.assertEqual(texts["pl"], "PL")

    def test_ray_blocked_by_td(self):
        # after: upward ray stops at td z, leftward ray stops at td t.
        desc = describe(self.table, 4, 3)
        self.assertEqual(header_ids(desc), ["top2", "c4", "rg", "r1"])

    def test_th_target(self):
        # pl is itself a th; its own headers are still derived.
        desc = describe(self.table, 3, 1)
        self.assertEqual(header_ids(desc), ["top1", "top2", "mid", "wide", "rg"])

    def test_empty_headers_attribute(self):
        self.assertEqual(describe(self.table, 5, 0).headers, ())

    def test_headers_attribute_overrides_and_dedupes(self):
        # dup sits under mid/wide/pl yet its explicit list wins entirely;
        # repeated tokens collapse to first occurrence, unknown id dropped.
        desc = describe(self.table, 5, 1)
        self.assertEqual(header_ids(desc), ["mid", "c1"])
        self.assertEqual(
            desc.headers,
            (HeaderRef(id="mid", text="Mid"), HeaderRef(id="c1", text="C1")),
        )

    def test_headers_attribute_ignores_self_and_non_th(self):
        self.assertEqual(header_ids(describe(self.table, 5, 2)), ["c1"])

    def test_headers_attribute_ignores_cross_table_refs(self):
        self.assertEqual(header_ids(describe(self.table, 5, 3)), [])


class OverlapConflictTest(unittest.TestCase):
    def test_colspan_over_rowspan_occupancy_fails(self):
        # b anchors at the empty (1,0) but its colspan crosses a's
        # rowspan occupancy at (1,1): compile must fail, not reflow.
        html = """
        <table id="t">
          <tr><td id="p">p</td><td id="a" rowspan="2">a</td></tr>
          <tr><td id="b" colspan="2">b</td></tr>
        </table>
        """
        with self.assertRaises(TableStructureError):
            compile_table(html, "t")

    def test_holes_are_allowed(self):
        html = """
        <table id="t">
          <tr><td id="a" colspan="2">a</td><td id="b">b</td></tr>
          <tr><td id="c">c</td></tr>
        </table>
        """
        table = compile_table(html, "t")
        self.assertIsNone(describe(table, 1, 1))
        self.assertIsNone(describe(table, 1, 2))
        self.assertEqual(describe(table, 1, 0).id, "c")


if __name__ == "__main__":
    unittest.main()
