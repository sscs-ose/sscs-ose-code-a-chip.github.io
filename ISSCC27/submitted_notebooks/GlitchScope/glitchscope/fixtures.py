from __future__ import annotations
from .model import Network, Cell, StimulusEpoch, ps_to_fs

def inverter_fixture():
    net = Network(
        primary_inputs=["A"],
        primary_outputs=["Y"],
        initial_inputs={"A": 0},
        cells=[
            Cell("U_INV", "INV", {"A":"A"}, "Y", ps_to_fs(50), ps_to_fs(50)),
        ],
    )
    epochs = [StimulusEpoch(ps_to_fs(100), {"A":1}, 1)]
    return net, epochs

def xor_atomic_no_glitch_fixture():
    net = Network(
        primary_inputs=["A","B"],
        primary_outputs=["Y"],
        initial_inputs={"A":0,"B":0},
        cells=[
            Cell("U_XOR", "XOR2", {"A":"A","B":"B"}, "Y", ps_to_fs(20), ps_to_fs(20)),
        ],
    )
    epochs = [StimulusEpoch(ps_to_fs(100), {"A":1,"B":1}, 1)]
    return net, epochs

def xor_reconvergent_fixture():
    net = Network(
        primary_inputs=["A"],
        primary_outputs=["Y"],
        initial_inputs={"A":0},
        cells=[
            Cell("U_FAST", "BUF", {"A":"A"}, "n_fast", ps_to_fs(40), ps_to_fs(40)),
            Cell("U_SLOW", "BUF", {"A":"A"}, "n_slow", ps_to_fs(100), ps_to_fs(100)),
            Cell("U_XOR", "XOR2", {"A":"n_fast","B":"n_slow"}, "Y", ps_to_fs(20), ps_to_fs(20)),
        ],
    )
    epochs = [StimulusEpoch(ps_to_fs(0), {"A":1}, 1)]
    return net, epochs

def propagated_glitch_fixture():
    net = Network(
        primary_inputs=["A"],
        primary_outputs=["Y"],
        initial_inputs={"A":0},
        cells=[
            Cell("U_FAST", "BUF", {"A":"A"}, "n_fast", ps_to_fs(40), ps_to_fs(40)),
            Cell("U_SLOW", "BUF", {"A":"A"}, "n_slow", ps_to_fs(100), ps_to_fs(100)),
            Cell("U_XOR", "XOR2", {"A":"n_fast","B":"n_slow"}, "n_glitch", ps_to_fs(20), ps_to_fs(20)),
            Cell("U_BUF1", "BUF", {"A":"n_glitch"}, "n_buf1", ps_to_fs(30), ps_to_fs(30)),
            Cell("U_BUF2", "BUF", {"A":"n_buf1"}, "Y", ps_to_fs(25), ps_to_fs(25)),
        ],
    )
    epochs = [StimulusEpoch(ps_to_fs(0), {"A":1}, 1)]
    return net, epochs

def static1_hazard_fixture():
    # Y = A*B + (~A)*C, B=C=1.
    # old path deasserts at 40 ps; new path asserts at 80 ps;
    # OR delay adds 20 ps to both boundaries => Y low from 60 to 100 ps.
    net = Network(
        primary_inputs=["A","B","C"],
        primary_outputs=["Y"],
        initial_inputs={"A":0,"B":1,"C":1},
        cells=[
            Cell("U_INV", "INV", {"A":"A"}, "nA", ps_to_fs(20), ps_to_fs(20)),
            Cell("U_AND_OLD", "AND2", {"A":"nA","B":"C"}, "old_term", ps_to_fs(20), ps_to_fs(20)),
            Cell("U_AND_NEW", "AND2", {"A":"A","B":"B"}, "new_term", ps_to_fs(80), ps_to_fs(80)),
            Cell("U_OR", "OR2", {"A":"old_term","B":"new_term"}, "Y", ps_to_fs(20), ps_to_fs(20)),
        ],
    )
    epochs = [StimulusEpoch(ps_to_fs(0), {"A":1}, 1)]
    return net, epochs


def changed_final_state_glitch_fixture():
    net = Network(
        ["A"],["Y"],[
            Cell("U_FAST","BUF",{"A":"A"},"n_fast",ps_to_fs(40),ps_to_fs(40)),
            Cell("U_MID","BUF",{"A":"A"},"n_mid",ps_to_fs(100),ps_to_fs(100)),
            Cell("U_XOR","XOR2",{"A":"n_fast","B":"n_mid"},"n_glitch",ps_to_fs(0),ps_to_fs(0)),
            Cell("U_FUNC","BUF",{"A":"A"},"n_func",ps_to_fs(160),ps_to_fs(160)),
            Cell("U_OR","OR2",{"A":"n_glitch","B":"n_func"},"Y",ps_to_fs(10),ps_to_fs(10)),
        ],{"A":0})
    return net,[StimulusEpoch(ps_to_fs(0),{"A":1},1)]

def two_epoch_glitch_fixture():
    net = Network(
        ["A"],["Y"],[
            Cell("U_FAST","BUF",{"A":"A"},"n_fast",ps_to_fs(40),ps_to_fs(40)),
            Cell("U_SLOW","BUF",{"A":"A"},"n_slow",ps_to_fs(100),ps_to_fs(100)),
            Cell("U_XOR","XOR2",{"A":"n_fast","B":"n_slow"},"Y",ps_to_fs(20),ps_to_fs(20)),
        ],{"A":0})
    return net,[StimulusEpoch(ps_to_fs(0),{"A":1},1),
                StimulusEpoch(ps_to_fs(1000),{"A":0},2)]

def merged_roots_fixture():
    net = Network(
        ["A","B"],["Y"],[
            Cell("A_FAST","BUF",{"A":"A"},"a_fast",ps_to_fs(40),ps_to_fs(40)),
            Cell("A_SLOW","BUF",{"A":"A"},"a_slow",ps_to_fs(100),ps_to_fs(100)),
            Cell("A_XOR","XOR2",{"A":"a_fast","B":"a_slow"},"n_g1",ps_to_fs(20),ps_to_fs(20)),
            Cell("B_FAST","BUF",{"A":"B"},"b_fast",ps_to_fs(60),ps_to_fs(60)),
            Cell("B_SLOW","BUF",{"A":"B"},"b_slow",ps_to_fs(120),ps_to_fs(120)),
            Cell("B_XOR","XOR2",{"A":"b_fast","B":"b_slow"},"n_g2",ps_to_fs(20),ps_to_fs(20)),
            Cell("U_OR","OR2",{"A":"n_g1","B":"n_g2"},"Y",ps_to_fs(10),ps_to_fs(10)),
        ],{"A":0,"B":0})
    return net,[StimulusEpoch(ps_to_fs(0),{"A":1,"B":1},1)]
