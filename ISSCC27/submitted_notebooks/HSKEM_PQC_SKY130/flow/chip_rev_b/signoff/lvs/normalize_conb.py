from pathlib import Path
import sys

source = Path(sys.argv[1])
target = Path(sys.argv[2])
stats_path = Path(sys.argv[3])

logical = []
for raw in source.read_text(encoding="utf-8").splitlines():
    stripped = raw.strip()
    if stripped.startswith("+") and logical:
        logical[-1] += " " + stripped[1:].strip()
    else:
        logical.append(stripped)

top_name = "trustedge_asic_core"
conb_name = "sky130_fd_sc_hd__conb_1"
parent = {}

def find(name):
    parent.setdefault(name, name)
    while parent[name] != name:
        parent[name] = parent[parent[name]]
        name = parent[name]
    return name

def union(preferred, other):
    a, b = find(preferred), find(other)
    if a != b:
        parent[b] = a

in_top = False
top_before = 0
conb_instances = 0
for line in logical:
    tokens = line.split()
    if len(tokens) >= 2 and tokens[0].lower() == ".subckt":
        in_top = tokens[1].lower() == top_name
        continue
    if in_top and tokens and tokens[0].lower() == ".ends":
        in_top = False
        continue
    if not in_top or not tokens or tokens[0].startswith("*"):
        continue
    if tokens[0].startswith("."):
        continue
    if not tokens[0].lower().startswith("x") or len(tokens) < 3:
        raise SystemExit(f"unexpected top-level element: {line[:160]}")
    top_before += 1
    if tokens[-1].lower() == conb_name:
        if len(tokens) != 8:
            raise SystemExit(f"unexpected CONB arity: {line}")
        # Reference order: VGND VNB VPB VPWR HI LO. Preserve the supply net as
        # representative and merge the constant output into it.
        union(tokens[1], tokens[6])
        union(tokens[4], tokens[5])
        conb_instances += 1

if conb_instances == 0:
    raise SystemExit("no CONB instances found")

out = []
in_top = False
top_after = 0
for line in logical:
    tokens = line.split()
    if len(tokens) >= 2 and tokens[0].lower() == ".subckt":
        in_top = tokens[1].lower() == top_name
        out.append(line)
        continue
    if in_top and tokens and tokens[0].lower() == ".ends":
        in_top = False
        out.append(line)
        continue
    if not in_top or not tokens or tokens[0].startswith("*") or tokens[0].startswith("."):
        out.append(line)
        continue
    if tokens[-1].lower() == conb_name:
        continue
    rewritten = [tokens[0], *(find(net) for net in tokens[1:-1]), tokens[-1]]
    out.append(" ".join(rewritten))
    top_after += 1

if top_after != top_before - conb_instances:
    raise SystemExit("top instance accounting mismatch")
target.write_text("\n".join(out) + "\n", encoding="utf-8")
stats_path.write_text(
    "A3_RUN9_CONB_NORMALIZE=PASS\n"
    f"top_instances_before={top_before}\n"
    f"conb_instances_removed={conb_instances}\n"
    f"top_instances_after={top_after}\n"
    f"net_aliases={sum(1 for k in parent if find(k) != k)}\n",
    encoding="utf-8",
)
print(f"A3_RUN9_CONB_NORMALIZE=PASS|removed={conb_instances}|top_after={top_after}")
