"""Unit tests of compare_reports.py on synthetic KLayout report databases.  SPDX-License-Identifier: Apache-2.0"""
import compare_reports as cr


def rdb(path, items):
    body = "".join(f"<item><category>'{c}'</category><values><value>{v}</value></values></item>" for c, v in items)
    path.write_text(f"<report-database><items>{body}</items></report-database>")
    return str(path)


def test_identical_marker_sets_are_equivalent(tmp_path):
    full = rdb(tmp_path / "f.lyrdb", [("m1.1", "edge: (0,0;1,0)"), ("li.3", "edge: (5,5;6,5)")])
    p1 = rdb(tmp_path / "p1.lyrdb", [("m1.1", "edge: (0,0;1,0)")])
    p2 = rdb(tmp_path / "p2.lyrdb", [("li.3", "edge: (5,5;6,5)")])
    assert cr.main(full, p1, p2) == 0


def test_missing_marker_in_a_part_is_a_difference(tmp_path):
    full = rdb(tmp_path / "f.lyrdb", [("m1.1", "a"), ("m1.1", "b")])
    p1 = rdb(tmp_path / "p1.lyrdb", [("m1.1", "a")])
    assert cr.main(full, p1) == 1


def test_same_rule_different_geometry_is_a_difference(tmp_path):
    full = rdb(tmp_path / "f.lyrdb", [("m1.1", "a")])
    p1 = rdb(tmp_path / "p1.lyrdb", [("m1.1", "b")])
    assert cr.main(full, p1) == 1


def test_empty_reports_are_equivalent(tmp_path):
    full = rdb(tmp_path / "f.lyrdb", [])
    assert cr.main(full, rdb(tmp_path / "p.lyrdb", [])) == 0
