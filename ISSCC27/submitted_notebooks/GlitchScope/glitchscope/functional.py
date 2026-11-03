from .logic import eval_primitive
from .netlist import topo_cells

def evaluate_stable(network, inputs, order=None):
    state = dict(inputs)
    for c in (order if order is not None else topo_cells(network)):
        pins = {pin: state[net] for pin, net in c.inputs.items()}
        state[c.output] = eval_primitive(c.kind, pins)
    return state
