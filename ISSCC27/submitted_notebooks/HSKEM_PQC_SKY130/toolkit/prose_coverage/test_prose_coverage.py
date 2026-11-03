"""Unit tests of prose_coverage.py on small synthetic notebooks.  SPDX-License-Identifier: Apache-2.0"""
import prose_coverage as pc


def nb(*cells):
    out = []
    for kind, src, *rest in cells:
        c = {"cell_type": kind, "source": [src]}
        if kind == "code":
            c["outputs"] = [{"output_type": "stream", "text": [rest[0]]}] if rest else []
        out.append(c)
    return {"cells": out}


def test_asserted_shown_and_hand_typed():
    r = pc.analyse(nb(("markdown", "# Title\n\nThe block runs at 82.5 MHz, takes 7,170 cycles and needs 42 pins."),
                      ("code", "assert round(fmax, 1) == 82.5", ""),
                      ("code", "print(cycles)", "7170\n")))
    assert (r["total"], r["asserted"], r["shown"], r["neither"]) == (3, 1, 1, 1)
    assert r["neither_by_section"] == {"Title": ["42"]}


def test_rounding_and_percent_forms():
    r = pc.analyse(nb(("markdown", "# R\n\nAbout 27 uJ, and the sponge is busy 99.5 % of the time."),
                      ("code", "assert busy > 0.995", "26.62\n")))
    assert r["neither"] == 0 and r["asserted"] == 1 and r["shown"] == 1


def test_one_significant_digit_does_not_match_by_rounding():
    r = pc.analyse(nb(("markdown", "# R\n\nThree is 3 and thirty is 30."), ("code", "x", "29.4\n")))
    assert r["neither"] == 2


def test_labels_are_not_claims_and_body_ends_at_appendix():
    r = pc.analyse(nb(("markdown", "# 1. Intro\n\nSee Section 4, Appendix B.2, [13] and FIPS 203 in 2024; `N = 60`."),
                      ("markdown", "# Appendices\n\nThe appendix says 123."),))
    assert r["total"] == 0


def test_table_compared_as_a_whole_and_excluded_cell():
    r = pc.analyse(nb(("markdown", "# T\n\n| a | b |\n|:--|:--|\n| x | 6,856 |"),
                      ("code", "assert rows == TABLE", ""),
                      ("code", "print(coverage)  # prose_coverage", "6856\n")),
                   table_assert_marker="assert rows == TABLE", exclude_cell_marker="prose_coverage")
    assert (r["asserted"], r["shown"], r["neither"]) == (1, 0, 0)


def test_unexecuted_notebook_is_flagged():
    r = pc.analyse(nb(("markdown", "# T\n\n5.5 dB"), ("code", "x = 1")))
    assert r["executed_outputs_present"] is False and r["neither"] == 1
