"""RTL-to-GDS wrapper: design config -> LibreLane (sky130A) -> GDS + metrics -> flow_runs.csv.

    python flow_runner.py --D 512 --P 32 --learn 2 --w 4 --k 3 --render   # one run
    python flow_runner.py --batch 30 --jobs 3                            # LHS batch + pairs

LibreLane runs in its pinned Docker image (librelane --dockerized). DRC/LVS/timing problems
do not abort a run: they are recorded as counts in the CSV, so every run yields a row.
"""
import argparse
import csv
import json
import os
import pathlib
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict

import numpy as np

from rtlgen import RTLConfig, generate_chip

ROOT = pathlib.Path(__file__).resolve().parents[1]
FLOW_DIR = ROOT / "flow"
CSV_PATH = ROOT / "results" / "flow_runs.csv"
FIGS = ROOT / "figs"
IMAGE = "ghcr.io/librelane/librelane:3.0.14"
PDK_ROOT = pathlib.Path(os.environ.get("PDK_ROOT", pathlib.Path.home() / ".ciel"))
# HDC_FLOW_NATIVE=1: call librelane/klayout directly (e.g. Colab with the Nix tool
# environment from LibreLane's official notebook). Default: the pinned Docker image.
NATIVE = os.environ.get("HDC_FLOW_NATIVE", "0") == "1"

FLOW_DEFAULTS = {
    "CLOCK_PORT": "clk",
    "FP_CORE_UTIL": 45,
    "PL_TARGET_DENSITY_PCT": 55,
    "RUN_KLAYOUT_XOR": False,
    "GRT_ALLOW_CONGESTION": True,
    # record problems instead of aborting, so every run produces a metrics row
    "ERROR_ON_MAGIC_DRC": False,
    "ERROR_ON_KLAYOUT_DRC": False,
    "ERROR_ON_LVS_ERROR": False,
    "ERROR_ON_TR_DRC": False,
    "ERROR_ON_LINTER_WARNINGS": False,
    "ERROR_ON_LONG_WIRE": False,
    "TIMING_VIOLATION_CORNERS": [],
}

# Fast mode for batch exploration: nominal-voltage corners only, no Magic DRC and no
# antenna-property report (together ~1 h of the ~2 h default run). KLayout DRC, LVS and
# routing DRC still run. Final Pareto points are re-run in "full" mode.
FAST = {"STA_CORNERS": ["nom_tt_025C_1v80", "nom_ss_100C_1v60", "nom_ff_n40C_1v95"],
        "RUN_MAGIC_DRC": False}
FAST_SKIP = ["Odb.CheckDesignAntennaProperties"]

METRICS = {   # csv column: LibreLane final metrics key
    "core_area_um2": "design__core__area",
    "die_area_um2": "design__die__area",
    "cell_area_um2": "design__instance__area__stdcell",      # excludes filler cells
    "cell_count": "design__instance__count__stdcell",
    "fill_area_um2": "design__instance__area__class:fill_cell",
    "utilization": "design__instance__utilization",
    "seq_area_um2": "design__instance__area__class:sequential_cell",
    "seq_count": "design__instance__count__class:sequential_cell",
    "comb_area_um2": "design__instance__area__class:multi_input_combinational_cell",
    "buf_area_um2": "design__instance__area__class:timing_repair_buffer",
    "clk_buf_area_um2": "design__instance__area__class:clock_buffer",
    "setup_ws_tt_ns": "timing__setup__ws__corner:nom_tt_025C_1v80",
    "setup_ws_ss_ns": "timing__setup__ws__corner:nom_ss_100C_1v60",
    "setup_ws_ns": "timing__setup__ws",
    "setup_tns_ns": "timing__setup__tns",
    "setup_vio_count": "timing__setup_vio__count",
    "hold_vio_count": "timing__hold_vio__count",
    "hold_ws_ns": "timing__hold__ws",
    "power_total_w": "power__total",
    "power_internal_w": "power__internal__total",
    "power_switching_w": "power__switching__total",
    "power_leakage_w": "power__leakage__total",
    "wirelength_um": "route__wirelength",
    "route_drc": "route__drc_errors",
    "magic_drc": "magic__drc_error__count",
    "klayout_drc": "klayout__drc_error__count",
    "lvs_errors": "design__lvs_error__count",
    "antenna_nets": "antenna__violating__nets",
}


def design_dir(cfg, clock_ns):
    return FLOW_DIR / f"{cfg.name}_clk{clock_ns:g}"


def prepare(cfg, clock_ns=20.0, overrides=None):
    d = design_dir(cfg, clock_ns)
    (d / "src").mkdir(parents=True, exist_ok=True)
    (d / "src" / "hdc_chip.v").write_text(generate_chip(cfg))
    conf = {"DESIGN_NAME": "hdc_chip", "VERILOG_FILES": ["dir::src/hdc_chip.v"],
            "CLOCK_PERIOD": clock_ns, **FLOW_DEFAULTS, **(overrides or {})}
    if cfg.cg:   # the clock gate becomes the sky130 integrated clock-gating cell (see rtlgen.CG_MODULE)
        conf.update({"VERILOG_DEFINES": ["HDC_SYNTH_ICG"], "LINTER_DEFINES": ["HDC_SYNTH_ICG"],
                     "LINTER_INCLUDE_PDK_MODELS": True, **(overrides or {})})
    (d / "config.json").write_text(json.dumps(conf, indent=2) + "\n")
    (d / "hdc_config.json").write_text(json.dumps(asdict(cfg), indent=2) + "\n")
    return d


def _get(m, key):
    v = m.get(key)
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else v


def _nix_python_home(yosys_path):
    """Find the Nix Python installation that a (possibly wrapped) Nix yosys embeds.

    Returns (PYTHONHOME or None, notes). Tries, in order: ldd on the yosys ELF (following a
    shell launcher script to the binary it execs), then the Python version encoded in the
    Nix store path (e.g. ...-python3-3.13.9-env) matched against /nix/store/*-python3-<ver>.
    """
    import glob
    import re
    notes, elf = [f"yosys={yosys_path}"], yosys_path
    with open(yosys_path, "rb") as fh:
        is_script = fh.read(2) == b"#!"
    if is_script:
        text = open(yosys_path, errors="replace").read()
        cands = [c for c in re.findall(r"/nix/store/[^\s\"']+", text)
                 if os.path.isfile(c) and open(c, "rb").read(4) == b"\x7fELF"]
        notes.append(f"launcher script -> {cands[-1] if cands else 'no ELF found'}")
        elf = cands[-1] if cands else None
    if elf:
        try:
            ldd = subprocess.run(["ldd", elf], capture_output=True, text=True).stdout
        except FileNotFoundError:
            ldd = ""
        m = re.search(r"=>\s*(/nix/store/[^ ]+?)/lib/libpython3[^ ]*", ldd)
        notes.append(f"ldd libpython: {m.group(0) if m else 'none'}")
        if m and glob.glob(os.path.join(m.group(1), "lib", "python3.*", "os.py")):
            return m.group(1), notes
    v = re.search(r"python3-(\d+\.\d+\.\d+)", yosys_path + " " + (elf or ""))
    if v:
        homes = [h for h in glob.glob(f"/nix/store/*-python3-{v.group(1)}")
                 if glob.glob(os.path.join(h, "lib", "python3.*", "os.py"))]
        notes.append(f"store match python3-{v.group(1)}: {homes[:1] or 'none'}")
        if homes:
            return homes[0], notes
    return None, notes


def _native_yosys_wrapper():
    """Native mode (Colab + Nix tools): make Yosys's embedded Python consistent.

    LibreLane's Yosys steps run Python scripts inside Yosys's embedded interpreter. In
    Colab that interpreter came up with the system prefix (/usr), loading a foreign
    standard library ("No module named '_opcode'") without `click`, the only third-party
    module those scripts need. This writes a `yosys` wrapper that pins PYTHONHOME to the
    Nix Python that Yosys belongs to and adds a private folder holding `click`, then
    probes it once. Returns the wrapper directory.
    """
    import shutil
    wrap_dir = FLOW_DIR / ".native_bin"
    wrapper = wrap_dir / "yosys"
    real = os.path.realpath(shutil.which("yosys"))
    home, notes = _nix_python_home(real)
    lines = ["#!/bin/bash"] + ([f'export PYTHONHOME="{home}"'] if home else [])
    deps = FLOW_DIR / ".pyosys_deps"
    if not (deps / "click").exists():
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--target", str(deps),
                        "click>=8,<8.3"], check=True)
    lines += [f'export PYTHONPATH="{deps}${{PYTHONPATH:+:$PYTHONPATH}}"', f'exec "{real}" "$@"']
    wrap_dir.mkdir(parents=True, exist_ok=True)
    wrapper.write_text("\n".join(lines) + "\n")
    wrapper.chmod(0o755)
    probe = wrap_dir / "probe.py"
    probe.write_text("import sys, click\nprint('yosys python', sys.version.split()[0], sys.prefix, 'click', click.__version__)\n")
    out = subprocess.run([str(wrapper), "-q", "-y", str(probe)], capture_output=True, text=True,
                         env={**os.environ, "PYTHONPATH": ""})
    print("native yosys wrapper:", " | ".join(lines[1:-1]))
    print("  python-home detection:", "; ".join(notes))
    print((out.stdout + out.stderr).strip()[-2000:])
    return wrap_dir


def _flow_env():
    env = dict(os.environ)
    if NATIVE:
        wrapper = _native_yosys_wrapper() / "yosys"
        env["_LLN_OVERRIDE_YOSYS"] = str(wrapper)   # LibreLane's own hook for the yosys binary
        print(f"native mode: LibreLane will use {wrapper}")
    return env


def run(cfg, clock_ns=20.0, overrides=None, threads=4, render=False, tag="run", mode="fast"):
    """Run the flow for one design point (mode 'fast' or 'full'); returns the CSV row."""
    overrides = {**(FAST if mode == "fast" else {}), **(overrides or {})}
    d = prepare(cfg, clock_ns, overrides)
    skip = sum((["-S", st] for st in FAST_SKIP), []) if mode == "fast" else []
    t0 = time.time()
    with (d / "flow.log").open("w") as log:
        proc = subprocess.run(
            ["librelane", *([] if NATIVE else ["--docker-no-tty", "--dockerized"]),
             "--run-tag", tag, "--overwrite",
             "--hide-progress-bar", "-j", str(threads), *skip, "config.json"],
            cwd=d, env=_flow_env(), stdout=log, stderr=subprocess.STDOUT)
    row = collect(cfg, clock_ns, d, tag, mode, time.time() - t0, proc.returncode)
    append_row(row)
    gds = ROOT / row["gds"] if row["gds"] else None
    if render and gds:
        try:
            render_gds(gds, FIGS / f"layout_{cfg.name}.png")
        except (subprocess.CalledProcessError, FileNotFoundError, StopIteration) as e:
            print(f"layout render failed (flow results are unaffected): {e}")
    return row


def collect(cfg, clock_ns, d, tag, mode, runtime, returncode=0):
    """Build the CSV row from a finished run directory."""
    mpath = d / "runs" / tag / "final" / "metrics.json"
    m = json.loads(mpath.read_text()) if mpath.exists() else {}
    gds = d / "runs" / tag / "final" / "gds" / "hdc_chip.gds"
    # flow_ok = the flow produced a GDS and metrics. LibreLane can still exit non-zero after
    # that (e.g. its hold checker always inspects every corner), which flow_rc records.
    row = {**asdict(cfg), "clock_ns": clock_ns, "mode": mode,
           "flow_ok": int(bool(m) and gds.exists()), "flow_rc": returncode,
           "runtime_s": round(runtime),
           **{k: _get(m, v) for k, v in METRICS.items()}}
    for corner in ("tt", "ss"):
        ws = row[f"setup_ws_{corner}_ns"]
        row[f"fmax_{corner}_mhz"] = round(1e3 / (clock_ns - ws), 2) if ws is not None else None
    row["power_mode"] = "vectorless"
    checks = ("klayout_drc", "lvs_errors", "route_drc") + (("magic_drc",) if mode == "full" else ())
    row["signoff_clean"] = int(row["flow_ok"] and all(row[c] == 0 for c in checks))
    row["gds"] = str(gds.relative_to(ROOT)) if gds.exists() else ""
    return row


def refresh_csv():
    """Rebuild flow_runs.csv from the run folders (current metric mapping), keeping each
    row's recorded mode, runtime and exit status. Run only when no batch is writing."""
    with CSV_PATH.open() as fh:
        old = list(csv.DictReader(fh))
    rows = []
    for r in old:
        cfg = RTLConfig(**{f: (type(v)(r[f]) if r.get(f) not in (None, "") else v)
                           for f, v in asdict(RTLConfig()).items()})
        clock = float(r["clock_ns"])
        rc = int(r.get("flow_rc") or (0 if r["flow_ok"] == "1" else 1))
        rows.append(collect(cfg, clock, design_dir(cfg, clock), "run", r["mode"],
                            float(r["runtime_s"]), rc))
    CSV_PATH.rename(CSV_PATH.with_suffix(".csv.bak"))
    for row in rows:
        append_row(row)
    print(f"rebuilt {len(rows)} rows ({sum(r['flow_ok'] for r in rows)} flow_ok)")


_CSV_LOCK = threading.Lock()


def append_row(row):
    """Append one result row; if the row has columns the file lacks (the schema grew, for example
    the `cg` column), rewrite the file with the union of columns first (old rows get '')."""
    with _CSV_LOCK:
        CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not CSV_PATH.exists():
            with CSV_PATH.open("w", newline="") as fh:
                wr = csv.DictWriter(fh, fieldnames=list(row))
                wr.writeheader()
                wr.writerow(row)
            return
        with CSV_PATH.open(newline="") as fh:
            rd = csv.DictReader(fh)
            cols, old = list(rd.fieldnames or []), list(rd)
        extra = [c for c in row if c not in cols]
        if extra:
            cols += extra
            with CSV_PATH.open("w", newline="") as fh:
                wr = csv.DictWriter(fh, fieldnames=cols, restval="")
                wr.writeheader()
                wr.writerows(old)
        with CSV_PATH.open("a", newline="") as fh:
            csv.DictWriter(fh, fieldnames=cols, restval="").writerow(row)


RENDER_PY = """
import pya
lv = pya.LayoutView()
lv.load_layout(gds, True)
lv.load_layer_props(lyp)
if box:    # zoom into a window (um): show every layer so the standard cells are visible
    x0, y0, x1, y1 = [float(v) for v in box.split(",")]
    lv.max_hier()
    lv.zoom_box(pya.DBox(x0, y0, x1, y1))
else:      # full chip: metal layers only (li1, met1..met5)
    KEEP = {(67, 20), (68, 20), (69, 20), (70, 20), (71, 20), (72, 20)}
    it = lv.begin_layers()
    while not it.at_end():
        lp = it.current().dup()
        lp.visible = (lp.source_layer, lp.source_datatype) in KEEP
        lv.set_layer_properties(it, lp)
        it.next()
    lv.max_hier()
    lv.zoom_fit()
lv.set_config("background-color", "#ffffff")
lv.set_config("grid-visible", "false")
lv.save_image(out, 1800, 1800)
"""


def render_gds(gds, png, box=None):
    """Render a GDS to PNG with KLayout (inside the LibreLane image) and the sky130A colors."""
    png.parent.mkdir(parents=True, exist_ok=True)
    lyp = next(PDK_ROOT.glob("**/sky130A/libs.tech/klayout/tech/sky130A.lyp"))
    script = png.parent / f".render_{png.stem}.py"
    script.write_text(RENDER_PY)
    cmd = []
    if not NATIVE:
        cmd = ["docker", "run", "--rm", "-u", f"{os.getuid()}:{os.getgid()}"]
        for mnt in sorted({str(p) for p in (gds.parent, png.parent, lyp.parent)}):
            cmd += ["-v", f"{mnt}:{mnt}"]
        cmd += [IMAGE]
    cmd += ["klayout", "-zz", "-r", str(script), "-rd", f"gds={gds}", "-rd", f"lyp={lyp}",
            "-rd", f"out={png}", "-rd", f"box={box or ''}"]
    subprocess.run(cmd, check=True, capture_output=True)
    return png


# ---------------------------------------------------------------------------- batch
def lhs_points(n, seed=0):
    """Latin-hypercube sample of the design genes, mapped onto legal configurations."""
    rng = np.random.default_rng(seed)
    u = (rng.permuted(np.tile(np.arange(n), (6, 1)), axis=1).T + rng.random((n, 6))) / n
    variants = [("exact", 0), ("trunc", 1), ("satcomp", 2), ("satcomp", 3), ("sampled", 4)]
    pts = []
    for a in u:
        D = [256, 512, 1024][int(a[0] * 3)]
        P = [32, 64, 128][int(a[1] * 3)]
        P = min(P, D)
        v, kn = variants[int(a[2] * len(variants))]
        learn = int(a[3] * 3)
        w = 2 + int(a[4] * 7)                  # 2..8
        k = int(a[5] * 5)                      # 0..4
        if D == 1024:
            w = min(w, 4)                      # keep the largest designs within runtime/memory
        if not learn:
            w, k = 8, 0
        pts.append(RTLConfig(D=D, P=P, variant=v, knob=kn, learn=learn, w=w, k=k))
    return pts


def pair_points():
    """Matched learning-off / learning-on designs (the never-cut comparison)."""
    pts = []
    for D in (256, 512, 1024):
        for P in (32, 64):
            pts.append(RTLConfig(D=D, P=P, learn=0))
            pts.append(RTLConfig(D=D, P=P, learn=2, w=4, k=3))
            if D <= 512:
                pts.append(RTLConfig(D=D, P=P, learn=2, w=8, k=0))
    return pts


def done_keys():
    if not CSV_PATH.exists():
        return set()
    with CSV_PATH.open() as fh:
        return {(r["D"], r["P"], r["variant"], r["knob"], r["learn"], r["w"], r["k"], r.get("cg") or "0",
                 r["clock_ns"]) for r in csv.DictReader(fh) if r["flow_ok"] == "1"}


def key(cfg, clock_ns):
    return tuple(str(x) for x in (cfg.D, cfg.P, cfg.variant, cfg.knob, cfg.learn, cfg.w, cfg.k, cfg.cg,
                                  float(clock_ns)))


def batch(n_lhs, jobs, threads, clock_ns=20.0):
    seen, todo = done_keys(), []
    for cfg in pair_points() + lhs_points(n_lhs):
        if key(cfg, clock_ns) not in seen and cfg not in todo:
            todo.append(cfg)
    # small designs first; P>=128 learning designs (hours in ABC synthesis) go last
    todo.sort(key=lambda c: (bool(c.learn and c.P >= 128), c.D * (c.w if c.learn else 1)))
    print(f"{len(todo)} flow runs queued ({jobs} in parallel)", flush=True)
    with ThreadPoolExecutor(jobs) as ex:
        for row in ex.map(lambda c: run(c, clock_ns, threads=threads), todo):
            print(f"{'OK ' if row['flow_ok'] else 'ERR'} {row['D']:>5} P={row['P']:<4} "
                  f"{row['variant']}{row['knob']} L{row['learn']} w{row['w']} k{row['k']}: "
                  f"core={row['core_area_um2']} cells={row['cell_area_um2']} ws_tt={row['setup_ws_tt_ns']} "
                  f"P={row['power_total_w']} clean={row['signoff_clean']} {row['runtime_s']}s",
                  flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    for fld, default in asdict(RTLConfig()).items():
        ap.add_argument(f"--{fld}", type=type(default), default=default)
    ap.add_argument("--clock", type=float, default=20.0, help="clock period, ns")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--mode", choices=["fast", "full"], default="fast")
    ap.add_argument("--refresh-csv", action="store_true", help="rebuild CSV from run folders")
    ap.add_argument("--batch", type=int, default=0, help="LHS points (plus fixed off/on pairs)")
    ap.add_argument("--jobs", type=int, default=3)
    a = vars(ap.parse_args())
    if a["refresh_csv"]:
        refresh_csv()
        sys.exit(0)
    if a["batch"]:
        batch(a["batch"], a["jobs"], a["threads"], a["clock"])
        sys.exit(0)
    cfg = RTLConfig(**{k: a[k] for k in asdict(RTLConfig())})
    row = run(cfg, a["clock"], threads=a["threads"], render=a["render"], mode=a["mode"])
    print(json.dumps(row, indent=2))
