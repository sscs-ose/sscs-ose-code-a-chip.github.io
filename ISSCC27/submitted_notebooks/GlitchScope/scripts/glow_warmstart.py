"""GLOW with a warm start: give Gurobi the exact minimum-register retiming as a MIP start.

In the cold runs of section 7, GLOW found no feasible placement within 1 h on the three largest
designs, although the original and minimum-register retiming are always feasible.  This script
writes the minimum-register lags of a case exported by ``scripts/glow_compare.py`` as
``start_lags.json`` (keyed by GLOW node name), and ``make_glow_warm`` writes ``glow_warm.py``, a
copy of GLOW's ``glow.py`` that accepts ``--start_lags`` and sets them as the start values of its
retiming variables (Gurobi completes the rest of the start).  The results are imported as
``glow_west`` / ``glow_wsim`` by ``scripts/glow_compare.py import``.

    python scripts/glow_warmstart.py lags <liberty> <name> [--factor F]   -> data/glow/<name>@<F>/start_lags.json
    python scripts/glow_warmstart.py patch <GLOW checkout>                -> <GLOW checkout>/glow_warm.py
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PATCH_ARG = ("    parser.add_argument('--time_limit',",
             "    parser.add_argument('--start_lags', type=str, default=None,\n"
             "                        help='JSON {node: lag}: MIP start for the retiming variables')\n"
             "    parser.add_argument('--time_limit',")
PATCH_START = ("    model.setParam('TimeLimit', args.time_limit)\n",
               "    model.setParam('TimeLimit', args.time_limit)\n"
               "    if args.start_lags:                     # warm start (added by glitchscope/scripts/glow_warmstart.py)\n"
               "        import re as _re\n"
               "        _st = json.load(open(args.start_lags))\n"
               "        _n = 0\n"
               "        for _v, _var in var_dicts['r'].items():\n"
               "            _b = _v if _v in _st else _re.sub(r'_(in|out)\\d+$', '', str(_v))\n"
               "            if _b in _st:\n"
               "                _var.Start = _st[_b]\n"
               "                _n += 1\n"
               "        model.update()\n"
               "        print(f\"[INFO] MIP start: {_n} of {len(var_dicts['r'])} retiming variables from {args.start_lags}\")\n")


def make_glow_warm(glow_dir):
    src = Path(glow_dir) / "glow.py"
    s = src.read_text()
    for old, new in (PATCH_ARG, PATCH_START):
        if s.count(old) != 1:
            raise SystemExit(f"glow.py does not have the expected line: {old.strip()}")
        s = s.replace(old, new)
    if "import json" not in s:
        s = "import json\n" + s
    out = src.with_name("glow_warm.py")
    out.write_text(s)
    print(f"wrote {out}")


def write_lags(lib, name, factor):
    from scripts.glow_compare import setting, OUT
    d = OUT / f"{name}@{factor}"
    meta = json.loads((d / "map.json").read_text())
    fx, T, _ = setting(lib, name, factor)
    if abs(T - meta["target_ps"]) > 0.5:
        raise SystemExit(f"target {T} ps differs from the exported {meta['target_ps']} ps")
    c = fx.classic_min_area(T, time_limit=1800.0)
    if c is None:
        raise SystemExit("minimum-register retiming found no solution")
    lags = {meta["names"][i]: int(c.lags[i]) if i < fx.rg.C else 0       # GLOW fixes sources and sinks at 0
            for i in range(len(meta["names"]))}
    (d / "start_lags.json").write_text(json.dumps(lags))
    print(f"{name}@{factor}: min-register {c.n_flops} flip-flops, {c.energy['total']:.1f} fJ; "
          f"wrote {d / 'start_lags.json'} ({len(lags)} nodes)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("lags"); p.add_argument("lib"); p.add_argument("name"); p.add_argument("--factor", type=float, default=1.1)
    p = sub.add_parser("patch"); p.add_argument("glow")
    a = ap.parse_args()
    if a.cmd == "patch":
        make_glow_warm(a.glow)
    else:
        write_lags(a.lib, a.name, a.factor)


if __name__ == "__main__":
    main()
