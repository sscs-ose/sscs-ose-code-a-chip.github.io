import pytest
import matplotlib.pyplot as plt

from comparator_atlas.designs import circuit_text, get_design
from presentation.circuit_guide import (
    PROFILE, check_topology, connections, device_groups, mos_symbol, schematic_figure,
)
from presentation.figure_style import review_artists


def test_diagram_matches_the_actual_twenty_seven_device_topology():
    devices = connections(circuit_text(get_design("lvt_balanced_4b")))
    check_topology(devices)
    assert len(devices) == 27
    assert devices["Xinp"][:4] == ("xp", "vinp", "tail", "vss")
    assert devices["Xln"][:4] == ("qn", "qp", "xp", "vss")
    assert devices["Xsp3"][:4] == ("sp3", "tp3", "tail", "vss")


@pytest.mark.parametrize("terminal", range(5))
def test_changed_terminal_or_model_invalidates_the_annotated_guide(terminal):
    devices = connections(circuit_text(get_design("lvt_balanced_4b")))
    changed = list(devices["Xinp"])
    changed[terminal] = "incorrect"
    devices["Xinp"] = tuple(changed)
    with pytest.raises(ValueError, match="topology"):
        check_topology(devices)


def test_duplicate_instance_names_are_rejected():
    text = circuit_text(get_design("lvt_balanced_4b"))
    with pytest.raises(ValueError, match="duplicate"):
        connections(text + "\nXinp xp vinp tail vss sky130_fd_pr__nfet_01v8_lvt\n")


def test_symbol_groups_cover_the_twenty_seven_real_instances_without_duplication():
    devices = connections(circuit_text(get_design("lvt_balanced_4b")))
    groups = device_groups(devices)
    names = [name for values in groups.values() for name in values]
    assert len(names) == len(set(names)) == 27
    assert set(names) == set(devices)
    assert groups["Xr[node]"] == ["Xrxp", "Xrxn", "Xrqp", "Xrqn"]
    assert groups["Xtp[k]"] == ["Xtp0", "Xtp1", "Xtp2", "Xtp3"]
    assert groups["Xsn[k]"] == ["Xsn0", "Xsn1", "Xsn2", "Xsn3"]


@pytest.mark.parametrize("side", (-1, 1))
def test_mos_symbol_maintains_polarity_and_terminal_orientation(side):
    figure, axes = plt.subplots()
    try:
        nfet = mos_symbol(axes, 2, 3, kind="n", gate_side=side)
        pfet = mos_symbol(axes, 2, 3, kind="p", gate_side=side)
        assert nfet["D"] == pfet["S"] == (2, 3.35)
        assert nfet["S"] == pfet["D"] == (2, 2.65)
        assert nfet["G"] == pfet["G"] == (2 + side * 0.51, 3)
        assert pfet["gate_inversion_bubble"] and not nfet["gate_inversion_bubble"]
        with pytest.raises(ValueError, match="polarity"):
            mos_symbol(axes, 2, 3, kind="unknown")
    finally:
        plt.close(figure)


def test_schematic_is_readable_at_publication_size_with_the_free_portable_font(monkeypatch):
    monkeypatch.setattr("presentation.figure_style.available_font", lambda: "DejaVu Sans")
    design = get_design("lvt_balanced_4b")
    devices = connections(circuit_text(design))
    figure, symbols, groups = schematic_figure(design, devices)
    try:
        assert set(symbols) == set(groups)
        for name, instances in groups.items():
            expected_kind = "p" if devices[instances[0]][-1].endswith("pfet_01v8") else "n"
            assert symbols[name]["kind"] == expected_kind
        review = review_artists(figure, PROFILE)
        assert review["minimum_font_pt"] == 9
        assert review["maximum_font_pt"] == 9.5
        assert not review["overlapping_text_artists"]
    finally:
        plt.close(figure)
