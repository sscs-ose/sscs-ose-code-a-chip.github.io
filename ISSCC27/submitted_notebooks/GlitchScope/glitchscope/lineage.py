from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class GlitchRecord:
    glitch_id: str
    epoch_id: int
    net: str
    start_event_id: int
    end_event_id: int
    start_fs: int
    end_fs: int
    width_fs: int
    polarity: str
    classification: str
    root_ids: Tuple[str,...]
    source_instance: str

@dataclass(frozen=True)
class LineageEdge:
    root_id: str
    origin_net: str
    descendant_net: str
    descendant_glitch_id: str

def _anc(eid, evmap, memo):
    if eid in memo:
        return memo[eid]
    out=set()
    for p in evmap[eid].parent_event_ids:
        out.add(p)
        if p in evmap:
            out.update(_anc(p,evmap,memo))
    memo[eid]=out
    return out

def classify_glitch_lineages_reference(trace,pulses):
    """
    Build a complete pulse-dependency DAG first, then classify roots.
    This is required for overlapping pulses: a child pulse may start before
    a second parent pulse has ended, so chronological pulse completion is not
    a valid basis for root assignment.
    """
    evmap={e.event_id:e for e in trace}
    pulse_by_id={p.pulse_id:p for p in pulses}
    boundary_owner={}
    for p in pulses:
        boundary_owner[p.start_event_id]=p.pulse_id
        boundary_owner[p.end_event_id]=p.pulse_id

    memo={}
    parents={p.pulse_id:set() for p in pulses}
    for p in pulses:
        ancestors=set()
        for bid in (p.start_event_id,p.end_event_id):
            ancestors.update(_anc(bid,evmap,memo))
        for ae in ancestors:
            owner=boundary_owner.get(ae)
            if owner is not None and owner != p.pulse_id:
                parents[p.pulse_id].add(owner)

    # Root pulses are dependency-free. Allocate IDs in deterministic physical order.
    root_pulses=sorted(
        [p for p in pulses if not parents[p.pulse_id]],
        key=lambda p:(p.epoch_id,p.start_fs,p.end_fs,p.net,p.pulse_id)
    )
    root_id_by_pulse={p.pulse_id:f"GROOT{i:04d}" for i,p in enumerate(root_pulses,1)}
    root_origin={root_id_by_pulse[p.pulse_id]:p.net for p in root_pulses}

    rootmemo={}
    visiting=set()
    def roots_of(pid):
        if pid in rootmemo:
            return rootmemo[pid]
        if pid in visiting:
            raise AssertionError(f"Pulse dependency cycle at {pid}")
        visiting.add(pid)
        if not parents[pid]:
            roots={root_id_by_pulse[pid]}
        else:
            roots=set()
            for pp in sorted(parents[pid]):
                roots.update(roots_of(pp))
        visiting.remove(pid)
        rootmemo[pid]=roots
        return roots

    records=[]
    edges=[]
    for p in sorted(pulses,key=lambda x:(x.epoch_id,x.start_fs,x.end_fs,x.net,x.pulse_id)):
        roots=tuple(sorted(roots_of(p.pulse_id)))
        if not parents[p.pulse_id]:
            cls="GENERATED"
        elif len(roots)==1:
            cls="PROPAGATED"
        else:
            cls="MERGED"
        records.append(GlitchRecord(
            p.pulse_id,p.epoch_id,p.net,p.start_event_id,p.end_event_id,
            p.start_fs,p.end_fs,p.width_fs,p.polarity,cls,roots,
            evmap[p.start_event_id].source_instance
        ))
        if cls != "GENERATED":
            for rid in roots:
                edges.append(LineageEdge(rid,root_origin[rid],p.net,p.pulse_id))
    return records,edges


def classify_glitch_lineages(trace, pulses):
    """Same result as ``classify_glitch_lineages_reference`` (kept for tests), computed
    with integer bitmasks over pulses instead of explicit ancestor-event sets:

    * ``E(e)``: pulses owning a strict ancestor event of ``e``, propagated once in
      trace (firing) order;
    * a pulse's parents are ``E(start) | E(end)`` minus itself;
    * a pulse's roots are the union of its parents' roots (parent-free pulses are
      roots), with a parent skipped when it is already in the transitive closure of
      a parent visited before it (its roots are then already included).
    """
    evmap = {e.event_id: e for e in trace}
    P = len(pulses)
    owner = {}
    for i, p in enumerate(pulses):
        owner[p.start_event_id] = i
        owner[p.end_event_id] = i
    emask = {}
    # ancestor-pulse masks in trace order (parents fire before their children)
    for e in trace:
        m = 0
        for pid in e.parent_event_ids:
            o = owner.get(pid)
            if o is not None:
                m |= 1 << o
            pm = emask.get(pid)
            if pm:
                m |= pm
            elif pm is None and pid in evmap:   # not in firing order: reference algorithm
                return classify_glitch_lineages_reference(trace, pulses)
        emask[e.event_id] = m
    pmask = [0] * P
    for i, p in enumerate(pulses):
        pmask[i] = (emask.get(p.start_event_id, 0) | emask.get(p.end_event_id, 0)) & ~(1 << i)

    root_order = sorted((i for i in range(P) if not pmask[i]),
                        key=lambda i: (pulses[i].epoch_id, pulses[i].start_fs, pulses[i].end_fs, pulses[i].net,
                                       pulses[i].pulse_id))
    root_id = {i: f"GROOT{n:04d}" for n, i in enumerate(root_order, 1)}
    root_origin = {root_id[i]: pulses[i].net for i in root_order}

    roots = [None] * P          # root mask
    clos = [None] * P           # transitive parent closure mask
    visiting = set()

    def bits_desc(m):
        while m:
            b = m.bit_length() - 1
            yield b
            m ^= 1 << b

    def solve(i):
        # iterative post-order DFS; frame = [pulse, parents left, root acc, closure acc]
        stack = [[i, None, 0, 0]]
        while stack:
            fr = stack[-1]
            x = fr[0]
            if fr[1] is None:
                if roots[x] is not None:
                    stack.pop()
                    continue
                if x in visiting:
                    raise AssertionError(f"Pulse dependency cycle at {pulses[x].pulse_id}")
                visiting.add(x)
                fr[1] = pmask[x]
            rem = fr[1] & ~fr[3]
            pushed = False
            while rem:
                y = rem.bit_length() - 1
                if roots[y] is None:
                    if y in visiting:
                        raise AssertionError(f"Pulse dependency cycle at {pulses[y].pulse_id}")
                    stack.append([y, None, 0, 0])
                    pushed = True
                    break
                fr[2] |= roots[y]
                fr[3] |= clos[y] | (1 << y)
                rem &= ~fr[3]
            fr[1] = rem
            if pushed:
                continue
            if pmask[x]:
                roots[x], clos[x] = fr[2], fr[3] | pmask[x]
            else:
                roots[x], clos[x] = 1 << x, 0
            visiting.discard(x)
            stack.pop()

    records, edges = [], []
    order = sorted(range(P), key=lambda i: (pulses[i].epoch_id, pulses[i].start_fs, pulses[i].end_fs,
                                            pulses[i].net, pulses[i].pulse_id))
    for i in order:
        p = pulses[i]
        if roots[i] is None:
            solve(i)
        rs = tuple(sorted(root_id[b] for b in bits_desc(roots[i])))
        if not pmask[i]:
            cls = "GENERATED"
        elif len(rs) == 1:
            cls = "PROPAGATED"
        else:
            cls = "MERGED"
        records.append(GlitchRecord(p.pulse_id, p.epoch_id, p.net, p.start_event_id, p.end_event_id,
                                    p.start_fs, p.end_fs, p.width_fs, p.polarity, cls, rs,
                                    evmap[p.start_event_id].source_instance))
        if cls != "GENERATED":
            for rid in rs:
                edges.append(LineageEdge(rid, root_origin[rid], p.net, p.pulse_id))
    return records, edges
