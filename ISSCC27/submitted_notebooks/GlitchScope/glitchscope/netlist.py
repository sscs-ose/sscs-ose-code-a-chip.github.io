from collections import defaultdict, deque

def build_fanout(network):
    fanout = defaultdict(list)
    drivers = {}
    for c in network.cells:
        if c.output in drivers:
            raise ValueError(f"Multiple drivers for net {c.output}")
        drivers[c.output] = c.name
        for _, net in c.inputs.items():
            fanout[net].append(c)
    return fanout, drivers

def topo_cells(network):
    producer = {c.output: c.name for c in network.cells}
    by_name = {c.name: c for c in network.cells}
    indeg = {c.name: 0 for c in network.cells}
    users = defaultdict(list)

    for c in network.cells:
        deps = {producer[n] for n in c.inputs.values() if n in producer}
        indeg[c.name] = len(deps)
        for d in deps:
            users[d].append(c.name)

    q = deque(sorted(n for n, d in indeg.items() if d == 0))
    out = []
    while q:
        n = q.popleft()
        out.append(by_name[n])
        for u in sorted(users[n]):
            indeg[u] -= 1
            if indeg[u] == 0:
                q.append(u)

    if len(out) != len(network.cells):
        raise ValueError("Combinational cycle detected; Phase A0 requires a DAG.")
    return out
