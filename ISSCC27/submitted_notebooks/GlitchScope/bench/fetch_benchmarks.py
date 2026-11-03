"""Fetch standard benchmark suites (pinned commits) and map them to SKY130 HD with Yosys.

    python bench/fetch_benchmarks.py [suite ...]        suites: iscas85 iscas89 itc99 epfl

Sources are downloaded into bench/external/src/ and are NOT part of this repository
(their licences differ: ISCAS via ISPRAS hdl-benchmarks, Apache-2.0; EPFL suite, MIT;
ITC'99 (PoliTo I99T), EUPL-1.2).  Mapped netlists go to bench/external/netlists/.
Only results derived from them are committed (data/benchmarks/).

Every netlist uses the calibrated cell subset (bench/basic_cells.lib, created from the
full Liberty by bench/make_basic_lib.py).  Sequential circuits get a clock port ``clk``;
their flip-flops become sky130 dfxtp.  Combinational circuits are also written as a
``<name>_r`` variant with input and output registers (for register-placement studies).
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "bench/external"
SRC, OUT = EXT / "src", EXT / "netlists"

REPOS = {
    "ispras": ("https://github.com/ispras/hdl-benchmarks.git", "10c3fb51d0810ce862659211862660dcc270a6af",
               ["/LICENSE", "/README.md", "/iscas85/verilog/", "/iscas89/verilog/"]),
    "epfl": ("https://github.com/lsils/benchmarks.git", "82d8cc6910419298e713a46644ed59fd3df53038",
             ["/LICENSE", "/README.md", "/arithmetic/*.v", "/random_control/*.v"]),
    "itc99": ("https://github.com/squillero/itc99-poli.git", "8a2c3b500ee7ff20e7031de92592b737bedc6d8c",
              ["/LICENSE", "/README.md", "/i99t/b*/b??.blif"]),
}
SUITES = {
    "iscas85": ["c17", "c432", "c499", "c880", "c1355", "c1908", "c2670", "c3540", "c5315", "c6288", "c7552"],
    "iscas89": ["s27", "s298", "s344", "s382", "s400", "s444", "s526", "s641", "s713", "s820", "s832", "s953",
                "s1196", "s1238", "s1423", "s1488", "s5378", "s9234", "s13207", "s15850", "s35932", "s38417",
                "s38584"],
    "itc99": [f"b{k:02d}" for k in list(range(1, 16)) + [17, 18, 20, 21, 22]],
    # the EPFL suite without its largest circuits (log2, sqrt, div, hyp, mem_ctrl: 20k-200k AIG nodes)
    "epfl": ["adder", "bar", "max", "sin", "square", "multiplier", "int2float", "dec", "priority", "router",
             "cavlc", "i2c", "ctrl", "arbiter", "voter"],
}
BIG = {"multiplier"}          # registered variant too slow to map within the time limit
REPO_OF = {"iscas85": "ispras", "iscas89": "ispras", "itc99": "itc99", "epfl": "epfl"}


def tools():
    env = {}
    p = ROOT / "tools.env"
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    env.update({k: v for k, v in os.environ.items() if k.startswith("GS_")})
    return env


def fetch(name):
    url, sha, paths = REPOS[name]
    d = SRC / name
    if (d / ".fetched").exists() and (d / ".fetched").read_text().strip() == sha:
        return d
    d.mkdir(parents=True, exist_ok=True)
    run = lambda *a: subprocess.run(a, cwd=d, check=True, capture_output=True, text=True)   # noqa: E731
    if not (d / ".git").exists():
        run("git", "init", "-q")
        run("git", "remote", "add", "origin", url)
    run("git", "config", "core.sparseCheckout", "true")
    (d / ".git/info/sparse-checkout").write_text("\n".join(paths) + "\n")
    run("git", "fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", sha)
    run("git", "checkout", "-q", "FETCH_HEAD")
    (d / ".fetched").write_text(sha)
    return d


def source_of(suite, name, src):
    """Path of a Verilog / BLIF file Yosys can read, preprocessed where needed."""
    pre = EXT / "pre"
    pre.mkdir(parents=True, exist_ok=True)
    if suite == "iscas85":
        return src / f"iscas85/verilog/{name}.v", "verilog", name
    if suite == "epfl":
        sub = "arithmetic" if (src / f"arithmetic/{name}.v").exists() else "random_control"
        text = (src / f"{sub}/{name}.v").read_text()
        top = re.search(r"\bmodule\s+(\w+)", text).group(1)
        return src / f"{sub}/{name}.v", "verilog", top
    if suite == "iscas89":
        text = (src / f"iscas89/verilog/{name}.v").read_text()
        # the suite's own dff model is switch-level in some files: use a plain behavioural one
        text = re.sub(r"\bmodule\s+dff\b.*?\bendmodule\b", "", text, flags=re.S)
        text += "\nmodule dff(CK, Q, D);\n  input CK, D;\n  output reg Q;\n  always @(posedge CK) Q <= D;\nendmodule\n"
        p = pre / f"{name}.v"
        p.write_text(text)
        return p, "verilog", name
    if suite == "itc99":
        text = (src / f"i99t/{name}/{name}.blif").read_text()
        text = re.sub(r"(\.inputs)", r"\1 clk", text, count=1)
        text = re.sub(r"^\.latch\s+(\S+)\s+(\S+)\s+(\d)\s*$", r".latch \1 \2 re clk \3", text, flags=re.M)
        text = re.sub(r"^\.model\s+\S+", f".model {name}", text, count=1, flags=re.M)
        p = pre / f"{name}.blif"
        p.write_text(text)
        return p, "blif", name
    raise ValueError(suite)


def synth(path, kind, top, out_name, lib, yosys, registered=False):
    out = OUT / f"{out_name}.v"
    reader = f"read_blif {path}" if kind == "blif" else f"read_verilog {path}"
    wrap = ""
    if registered:
        # wrap the combinational top with input and output registers
        w = OUT / f"{out_name}_wrap.v"
        info = subprocess.run([yosys, "-q", "-p", f"{reader}; hierarchy -top {top}; proc; write_json -"],
                              capture_output=True, text=True, check=True).stdout
        mod = json.loads(info)["modules"][top]
        ins = [(n, len(p["bits"])) for n, p in mod["ports"].items() if p["direction"] == "input"]
        outs = [(n, len(p["bits"])) for n, p in mod["ports"].items() if p["direction"] == "output"]
        rng = lambda k: f"[{k - 1}:0] " if k > 1 else ""                       # noqa: E731
        esc = lambda n: n if re.fullmatch(r"[A-Za-z_]\w*", n) else "\\" + n + " "   # noqa: E731
        q = {n: f"gs_in{i}" for i, (n, _) in enumerate(ins)}
        c = {n: f"gs_out{i}" for i, (n, _) in enumerate(outs)}
        v = [f"module {out_name}(clk, {', '.join(esc(n) for n, _ in ins + outs)});", "  input clk;"]
        v += [f"  input {rng(k)}{esc(n)};" for n, k in ins] + [f"  output reg {rng(k)}{esc(n)};" for n, k in outs]
        v += [f"  reg {rng(k)}{q[n]};" for n, k in ins] + [f"  wire {rng(k)}{c[n]};" for n, k in outs]
        v += [f"  {top} core({', '.join(f'.{esc(n)}({q[n]})' for n, _ in ins)}, "
              f"{', '.join(f'.{esc(n)}({c[n]})' for n, _ in outs)});"]
        v += ["  always @(posedge clk) begin"] + [f"    {q[n]} <= {esc(n)};" for n, _ in ins] + \
             [f"    {esc(n)} <= {c[n]};" for n, _ in outs] + ["  end", "endmodule"]
        w.write_text("\n".join(v) + "\n")
        wrap = f"read_verilog {w}; "
        top = out_name
    script = (f"{reader}; {wrap}synth -flatten -top {top}; dfflibmap -liberty {lib}; abc -liberty {lib}; "
              f"opt_clean -purge; setundef -zero; splitnets -ports; rename -top {out_name}; rename -enumerate; "
              f"write_verilog -noattr -noexpr {out}")
    r = subprocess.run([yosys, "-q", "-l", str(OUT / f"{out_name}.yosys.log"), "-p", script],
                       capture_output=True, text=True, timeout=1200)
    if r.returncode:
        raise RuntimeError(f"yosys failed on {out_name}: {r.stderr[-800:]}")
    return out


def main():
    env = tools()
    yosys = env.get("GS_YOSYS", "yosys")
    lib = ROOT / "bench/basic_cells.lib"
    if not lib.exists():
        subprocess.run([sys.executable, str(ROOT / "bench/make_basic_lib.py")], check=True)
    OUT.mkdir(parents=True, exist_ok=True)
    suites = sys.argv[1:] or list(SUITES)
    index = json.loads((OUT / "index.json").read_text()) if (OUT / "index.json").exists() else {}
    for suite in suites:
        src = fetch(REPO_OF[suite])
        for name in SUITES[suite]:
            try:
                path, kind, top = source_of(suite, name, src)
                variants = [(name, False)] + ([(name + "_r", True)] if suite in ("iscas85", "epfl")
                                              and name not in BIG else [])
                for out_name, reg in variants:
                    if (OUT / f"{out_name}.v").exists() and out_name in index:
                        continue
                    out = synth(path, kind, top, out_name, lib, yosys, registered=reg)
                    t = out.read_text()
                    cells = len(re.findall(r"^\s*sky130_fd_sc_hd__\w+\s", t, re.M))
                    flops = t.count("sky130_fd_sc_hd__dfxtp_1 ")
                    index[out_name] = dict(suite=suite, source=name, registered=reg, cells=cells, flops=flops)
                    print(f"{suite:8s} {out_name:14s} {cells:7d} cells {flops:6d} flops", flush=True)
            except Exception as e:                       # noqa: BLE001
                print(f"{suite:8s} {name:14s} FAILED: {str(e)[:200]}", flush=True)
            (OUT / "index.json").write_text(json.dumps(index, indent=1))


if __name__ == "__main__":
    main()
