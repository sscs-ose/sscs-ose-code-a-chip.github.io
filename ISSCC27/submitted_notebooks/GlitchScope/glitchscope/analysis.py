from .functional import evaluate_stable

def stable_epoch_maps(network, epochs):
    current = dict(network.initial_inputs)
    before, after = {}, {}
    for e in sorted(epochs, key=lambda x: (x.time_fs, x.epoch_id)):
        before[e.epoch_id] = evaluate_stable(network, current)
        current.update(e.updates)
        after[e.epoch_id] = evaluate_stable(network, current)
    return before, after
