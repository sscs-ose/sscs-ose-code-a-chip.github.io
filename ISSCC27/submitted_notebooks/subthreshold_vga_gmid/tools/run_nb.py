#!/usr/bin/env python3
"""Run notebook.ipynb headless, so you never have to flip flags or click Run All by hand.

  python tools/run_nb.py                 # tier1 : cache only, ~1 min  (what a judge runs)
  python tools/run_nb.py --mode spice    # re-run every SPICE sim, then a clean tier-1 pass
  python tools/run_nb.py --mode full     # rebuild the tables, re-run the flow and every SPICE sim, then a clean tier-1 pass
  python tools/run_nb.py --mode layout   # rerun the post-layout gate on the committed extraction (ngspice)

Flags are flipped in memory only. For spice/full the saved notebook is always the SECOND, tier-1
pass, so the committed file has all flags False and its printed outputs say so (no mismatch).
On failure the partial notebook is written to executed_failed.ipynb and the error is printed as text.
"""
import argparse, re, sys, time
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from pathlib import Path
import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

FLAGS = {"tier1": [], "spice": ["RERUN_SPICE"], "full": ["REBUILD_LUT", "RERUN_FLOW", "RERUN_SPICE"],
         "layout": ["RUN_LAYOUT"]}
ALL = ["REBUILD_LUT", "RERUN_FLOW", "RERUN_SPICE", "RUN_LAYOUT"]

def set_flags(nb, on):
    hits = 0
    for c in nb.cells:
        if c.cell_type != "code": continue
        for f in ALL:
            c.source, k = re.subn(rf"^({f}\s*=\s*)(True|False)", rf"\g<1>{f in on}", c.source, flags=re.M)
            hits += k
    return hits

def run(nb, cwd, timeout, label):
    t = time.time(); print(f"[{label}] executing {len(nb.cells)} cells ...", flush=True)
    NotebookClient(nb, timeout=timeout, kernel_name="python3",
                   resources={"metadata": {"path": str(cwd)}}).execute()
    print(f"[{label}] OK in {time.time()-t:.0f} s", flush=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nb", default="notebook.ipynb")
    ap.add_argument("--mode", choices=list(FLAGS), default="tier1")
    ap.add_argument("--timeout", type=int, default=3600)
    ap.add_argument("--no-save", action="store_true", help="execute but do not overwrite the notebook")
    a = ap.parse_args()
    path = Path(a.nb).resolve(); cwd = path.parent
    nb = nbformat.read(path, 4)
    if set_flags(nb, []) < len(ALL): sys.exit(f"could not find the {len(ALL)} run-mode flags in the notebook")
    passes = [("tier1", [])] if a.mode == "tier1" else [(a.mode, FLAGS[a.mode]), ("tier1", [])]
    def top_is_current(nb_):
        """The summary at the top is drawn from the registry before the cells that update it run: after a run that
        changed the results, it shows the previous run's summary until the notebook runs once more."""
        import json as _j
        R_ = _j.loads((cwd / "cache" / "results.json").read_text()) if (cwd / "cache" / "results.json").exists() else {}
        top_ = next((c for c in nb_.cells if c.cell_type == "code" and "first_md" in c.source and "display(Markdown" in c.source), None)
        out = "".join("".join(o.get("data", {}).get("text/markdown", "")) for o in (top_.get("outputs", []) if top_ else []))
        norm = lambda t: re.sub(r"\s+", " ", t).strip()
        return not R_.get("first_md") or norm(R_["first_md"]) in norm(out)
    try:
        for i, (label, on) in enumerate(passes):
            nb = nbformat.read(path, 4); set_flags(nb, on)
            run(nb, cwd, a.timeout, f"pass {i+1}/{len(passes)} {label}")
        if not top_is_current(nb):                       # one more tier-1 pass so the top summary is this run's
            nb = nbformat.read(path, 4); set_flags(nb, [])
            run(nb, cwd, a.timeout, "extra tier1 pass (summary at the top was stale)")
    except CellExecutionError as e:
        (cwd / "executed_failed.ipynb").write_text(nbformat.writes(nb))
        msg = re.sub(r"\x1b\[[0-9;]*m", "", str(e))                 # strip colour codes so it pastes cleanly
        print("\n=== NOTEBOOK FAILED ===\n" + msg[-3500:] + "\n(partial notebook: executed_failed.ipynb)")
        sys.exit(1)
    set_flags(nb, [])                                   # source ships with all flags False
    if not a.no_save:
        nbformat.write(nb, path); print(f"saved {path.name} (tier-1 outputs, flags False)")
        from finalize_nb import finalize                  # one-string outputs and embedded images: any viewer renders it
        j, e = finalize(path); print(f"finalize_nb: {j} output fields joined, {e} cells got embedded images")

if __name__ == "__main__":
    main()
