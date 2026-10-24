"""Validate published GDS component arithmetic and provenance, not full PEX."""

from decimal import Decimal
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results" / "study" / "gds_geometry"
SOURCES = ROOT / "layout_compact_repair/evidence/attempt1"


def test_geometry_inputs_are_the_archived_public_layout():
    geometry = json.loads((EVIDENCE / "geometry.json").read_text(encoding="utf-8"))
    assert hashlib.sha256((SOURCES / "atlas.mag").read_bytes()).hexdigest() == \
        geometry["source_mag_sha256"]
    assert hashlib.sha256((SOURCES / "atlas.gds").read_bytes()).hexdigest() == \
        geometry["source_gds_sha256"]
    assert geometry["mag_gds_export_polygons_and_text_match_archived_gds"]
    assert geometry["logical_check"]["mos_count"] == 27
    assert geometry["logical_check"]["net_count"] == 26
    assert len(geometry["logical_check"]["ports"]) == 15
    assert len(geometry["per_net"]) == 26
    assert sum(layer["source_polygons"] for layer in geometry["mask_partition"].values()) == 2508
    assert all(layer["assigned_once"] == layer["source_polygons"]
               for layer in geometry["mask_partition"].values())
    assert geometry["model_status"].endswith("no solved network R/C")


def test_public_coefficients_produce_only_the_claimed_components():
    geometry = json.loads((EVIDENCE / "geometry.json").read_text(encoding="utf-8"))
    sheet = Decimal("0.047")
    for net, length, expected in (
        ("clk", "48.8", "6.745882"),
        ("tail", "123.6", "17.085882"),
        ("xp", "53.6", "7.409412"),
        ("xn", "53.6", "7.409412"),
        ("qp", "50.8", "7.022353"),
        ("qn", "50.8", "7.022353"),
    ):
        assert geometry["per_net"][net]["metal3"]["rect_dims_um"] == [
            [float(length), 0.34, 1]
        ]
        isolated = sheet * Decimal(length) / Decimal("0.34")
        assert abs(isolated - Decimal(expected)) < Decimal("0.000001")
    examples = (
        ("clk-tail", "clk_metal2_vs_tail_metal3_overlap_um2",
         "0.34", "0.0861861", "0.029303274"),
        ("clk-tail", "tail_metal1_vs_clk_metal2_overlap_um2",
         "0.0133", "0.133861", "0.0017803513"),
        ("qp-qn", "qn_metal2_vs_qp_metal3_overlap_um2",
         "0.34", "0.0861861", "0.029303274"),
        ("qp-qn", "qp_metal2_vs_qn_metal3_overlap_um2",
         "0.27", "0.0861861", "0.023270247"),
    )
    for pair, key, area, coefficient, result in examples:
        measured = geometry["opposing_pairs"][pair][key]
        assert Decimal(str(measured)) == Decimal(area)
        assert Decimal(area) * Decimal(coefficient) == Decimal(result)
    assert not any(value for key, value in geometry["opposing_pairs"]["xp-xn"].items()
                   if key.endswith("_overlap_um2"))
