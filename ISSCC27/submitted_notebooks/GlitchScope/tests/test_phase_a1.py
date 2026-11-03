from __future__ import annotations
from glitchscope.fixtures import propagated_glitch_fixture, static1_hazard_fixture
from glitchscope.timed import TransportSimulator
from glitchscope.analysis import stable_epoch_maps
from glitchscope.classify import extract_pulses
from glitchscope.lineage import classify_glitch_lineages
from glitchscope.model import ps_to_fs

def analyze(factory):
    net, epochs = factory()
    before, after = stable_epoch_maps(net, epochs)
    trace, final_state = TransportSimulator(net).run(epochs)
    pulses = extract_pulses(trace, before, after)
    lineages, edges = classify_glitch_lineages(trace, pulses)
    return trace, pulses, lineages, edges, final_state

def test_static1_generated_hazard():
    _, _, lineages, _, final_state = analyze(static1_hazard_fixture)
    ys = [g for g in lineages if g.net == "Y"]
    assert len(ys) == 1
    g = ys[0]
    assert g.classification == "GENERATED"
    assert g.polarity == "negative"
    assert g.width_fs == ps_to_fs(40)
    assert final_state["Y"] == 1

def test_propagated_lineage():
    _, _, lineages, edges, final_state = analyze(propagated_glitch_fixture)
    by_net = {g.net:g for g in lineages}
    assert by_net["n_glitch"].classification == "GENERATED"
    assert by_net["n_buf1"].classification == "PROPAGATED"
    assert by_net["Y"].classification == "PROPAGATED"
    root = by_net["n_glitch"].root_ids
    assert len(root) == 1
    assert by_net["n_buf1"].root_ids == root
    assert by_net["Y"].root_ids == root
    assert by_net["n_glitch"].width_fs == ps_to_fs(60)
    assert by_net["n_buf1"].width_fs == ps_to_fs(60)
    assert by_net["Y"].width_fs == ps_to_fs(60)
    assert final_state["Y"] == 0
    assert len(edges) >= 2
