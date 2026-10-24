import struct

import pytest

from layout_evidence import (
    deadline_summary, gds_polygons, gds_real8, load_layout, matched_tt_comparison, snapshot_hashes,
    validate_measurements,
)


def test_layout_counts_do_not_relabel_two_ns_as_original_pass():
    data = load_layout()
    summary = deadline_summary(data).set_index(["mode", "deadline_ns"])
    assert summary.loc[("Distributed RC", 1), "correct"] == 12
    assert summary.loc[("Distributed RC", 1), "unresolved"] == 8
    assert summary.loc[("Distributed RC", 2), "correct"] == 20
    assert summary.loc[("Distributed RC", 2), "sampled_points"] == 20
    assert data["receipt"]["qualification"]["original_five_condition_pilot_qualified"] is False


def test_compared_costs_use_identical_signs_and_step():
    table = matched_tt_comparison(load_layout()).set_index("implementation")
    assert table.loc["Schematic", "mean_core_energy_fj"] == pytest.approx(244.0520989948)
    assert table.loc["Previous balanced RC", "mean_core_energy_fj"] == pytest.approx(520.83921576045)
    assert table.loc["Repaired Distributed RC", "mean_core_energy_fj"] == pytest.approx(425.35803388035)
    assert table.loc["Repaired Distributed RC", "mean_delay_ns"] == pytest.approx(0.645110288486)
    assert table.matched_signed_points.eq(2).all()


def test_fixed_scope_missing_and_duplicate_observations_fail():
    data = load_layout()
    with pytest.raises(ValueError, match="80-point"):
        validate_measurements(data["frame"].iloc[:-1], data["receipt"])
    changed = data["frame"].copy()
    changed.iloc[1] = changed.iloc[0]
    with pytest.raises(ValueError, match="80-point"):
        validate_measurements(changed, data["receipt"])


def test_invalid_unknown_values_or_relaxed_conditions_fail():
    data = load_layout()
    for field, value in (("trim_code", 1), ("max_step_ps", 10), ("reset_ok", False),
                         ("core_energy_fj", float("nan")), ("outcome_at_3_5ns", "correct")):
        changed = data["frame"].copy()
        changed.loc[0, field] = value
        with pytest.raises(ValueError):
            validate_measurements(changed, data["receipt"])
    changed = data["frame"].copy()
    unresolved = changed.index[changed.outcome_at_1ns == "unresolved"][0]
    changed.loc[unresolved, "latency_at_1ns_ns"] = 0.0
    with pytest.raises(ValueError, match="invented"):
        validate_measurements(changed, data["receipt"])


def test_snapshot_checksum_records_are_unambiguous():
    value = "a" * 64 + "  data.json\n"
    assert snapshot_hashes(value) == {"data.json": "a" * 64}
    with pytest.raises(ValueError, match="Duplicate"):
        snapshot_hashes(value + value)
    with pytest.raises(ValueError, match="Malformed"):
        snapshot_hashes("not a checksum")


def test_native_renderer_cannot_assume_other_units_or_hidden_hierarchy():
    data = load_layout()
    contents = (data["snapshot"] / "atlas.gds").read_bytes()
    assert len(gds_polygons(contents)[(125, 44)]) == 10
    assert sum(len(values) for values in gds_polygons(contents).values()) == 2867
    with pytest.raises(ValueError, match="Truncated"):
        gds_polygons(contents[:-1])
    with pytest.raises(ValueError, match="hierarchy"):
        gds_polygons(contents + struct.pack(">HBB", 4, 10, 0))


def test_gds_hex_real_decoding_is_explicitly_big_endian():
    assert gds_real8(bytes.fromhex("4110000000000000")) == 1
    assert gds_real8(bytes.fromhex("C110000000000000")) == -1
    assert gds_real8(bytes(8)) == 0
    with pytest.raises(ValueError, match="eight-byte"):
        gds_real8(b"\x00")
