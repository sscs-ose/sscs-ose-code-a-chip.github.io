#!/usr/bin/env python3
"""Keep only the time where top-level `busy`=1 (compute cycles), closing the gaps.
Usage: vcd_window.py in.vcd out.vcd   Prints busy cycles kept (20 ns clock) and total cycles.
Value changes that happen in gaps (weight loads, idle) are emitted as one diff at window entry."""
import sys

src, dst = sys.argv[1], sys.argv[2]
lines = open(src).read().split("\n")
i = next(k for k, l in enumerate(lines) if l.startswith("$enddefinitions")) + 1
head = lines[:i]
busy_id, depth = None, 0
for l in head:
    if l.startswith("$scope"):
        depth += 1
    elif l.startswith("$upscope"):
        depth -= 1
    elif l.startswith("$var"):
        p = l.split()
        if p[4] == __import__("os").environ.get("WIN_SIG", "busy") and busy_id is None:
            busy_id = p[3]
assert busy_id, "no top-level busy"


def split(tok):
    if tok[0] in "bBrR":
        v, ident = tok.split()
        return ident, tok
    return tok[1:], tok


state, emitted, dirty = {}, {}, set()
out = list(head)
acc = 0
t_prev = 0
was = False
import os
EXTRA = int(os.environ.get("WINDOW_EXTRA_PS", "0"))   # keep this long after busy falls (PIPE_MERGE output register)
hold_until = 0
busy_was = False
t_total = 0
in_dump = False
body = lines[i:]
j = 0
pending = []  # changes at current timestamp
cur_t = 0


def flush(t, pending_changes):
    global acc, t_prev, was, hold_until, busy_was
    for tok in pending_changes:
        ident, full = split(tok)
        state[ident] = full
        dirty.add(ident)
    busy_now = state.get(busy_id, "0" + busy_id)[0] == "1"
    if busy_was and not busy_now:
        hold_until = t + EXTRA
    busy_was = busy_now
    now = busy_now or t < hold_until
    if was:
        acc += t - t_prev
    if was or now:
        out.append("#%d" % acc)
        for ident in sorted(dirty):
            if emitted.get(ident) != state[ident]:
                out.append(state[ident])
                emitted[ident] = state[ident]
        dirty.clear()
    t_prev, was = t, now


started = False
for l in body:
    l = l.strip()
    if not l or l.startswith("$dump") or l == "$end" or l.startswith("$comment"):
        continue
    if l[0] == "#":
        if started:
            flush(cur_t, pending)
        cur_t, pending, started = int(l[1:]), [], True
        t_total = cur_t
    else:
        pending.append(l)
flush(cur_t, pending)
out.append("#%d" % acc)
open(dst, "w").write("\n".join(out) + "\n")
print("busy window ns: %.1f (%.1f cycles); full run ns: %.1f" % (acc / 1000.0, acc / float(__import__("os").environ.get("PERIOD_PS", "30000")), t_total / 1000.0))
