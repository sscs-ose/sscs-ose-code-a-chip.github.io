"""Generator-first SKY130 SPICE hierarchy for the Stage-4 demonstrator."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Iterable, Sequence

from ..config import Sky130MHAConfig

E2M1_MAGNITUDES_X2 = (0, 1, 2, 3, 4, 6, 8, 12)
STAGE_ORDER = ("cell", "column4", "column8", "macro4x4")

@dataclass(frozen=True)
class Stage4Artifact:
    stage: str
    level: str
    netlist: str
    testbench: str
    receipt: str
    cases: tuple[dict[str, object], ...]
    delay_measurements: tuple[str, ...]
    jobs: tuple[dict[str, object], ...] = ()
    energy_measurement: str = "energy_j"

    def to_mapping(self) -> dict[str, object]:
        value = asdict(self)
        value["cases"] = list(self.cases)
        value["delay_measurements"] = list(self.delay_measurements)
        return value

def discover_sky130_model_library(pdk_root: str | Path | None = None) -> Path:
    """Find sky130.lib.spice in common Volare/Ciel directory layouts."""
    roots = []
    if pdk_root is not None:
        roots.append(Path(pdk_root).expanduser())
    elif os.environ.get("PDK_ROOT"):
        roots.append(Path(os.environ["PDK_ROOT"]).expanduser())
    roots += [Path.home() / ".volare", Path.home() / ".ciel"]
    rel = Path("sky130A/libs.tech/ngspice/sky130.lib.spice")
    candidates: list[Path] = []
    for root in dict.fromkeys(p.resolve() for p in roots):
        candidates += [root / rel, root / "sky130" / rel]
        versions = root / "sky130" / "versions"
        if versions.is_dir():
            candidates += sorted(versions.glob(f"*/{rel}"), reverse=True)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    searched = "\n".join(f"  - {p}" for p in candidates)
    raise FileNotFoundError(
        "Cannot locate sky130.lib.spice. Set PDK_ROOT or pass --model-library. Searched:\n" + searched
    )

def _header(name: str, cfg: Sky130MHAConfig) -> str:
    return (f"* AutoMX-CIM generated {name}\n* config_sha256={cfg.sha256}\n"
            "* E2M1 magnitude: PWM. WLP/WLN select activation sign.\n\n")

def _cell(cfg: Sky130MHAConfig) -> str:
    return _header("differential ternary cell", cfg) + """.subckt automx_ternary_cell BLP BLN WLP WLN WPOS WNEG VGND VSUBS
* +W,+A and -W,-A discharge BLP; -W,+A and +W,-A discharge BLN.
XPP_W BLP WPOS NPP VSUBS sky130_fd_pr__nfet_01v8 W=0.84 L=0.15
XPP_A NPP WLP VGND VSUBS sky130_fd_pr__nfet_01v8 W=0.84 L=0.15
XPN_W BLP WNEG NPN VSUBS sky130_fd_pr__nfet_01v8 W=0.84 L=0.15
XPN_A NPN WLN VGND VSUBS sky130_fd_pr__nfet_01v8 W=0.84 L=0.15
XNP_W BLN WNEG NNP VSUBS sky130_fd_pr__nfet_01v8 W=0.84 L=0.15
XNP_A NNP WLP VGND VSUBS sky130_fd_pr__nfet_01v8 W=0.84 L=0.15
XNN_W BLN WPOS NNN VSUBS sky130_fd_pr__nfet_01v8 W=0.84 L=0.15
XNN_A NNN WLN VGND VSUBS sky130_fd_pr__nfet_01v8 W=0.84 L=0.15
.ends automx_ternary_cell
"""

def _column(rows: int, cfg: Sky130MHAConfig) -> str:
    pins = ["BLP", "BLN"]
    for r in range(rows):
        pins += [f"WLP{r}", f"WLN{r}", f"WPOS{r}", f"WNEG{r}"]
    pins += ["VGND", "VSUBS"]
    body = [_cell(cfg), f".subckt automx_ternary_column_{rows}x1 {' '.join(pins)}"]
    for r in range(rows):
        body.append(f"XCELL{r} BLP BLN WLP{r} WLN{r} WPOS{r} WNEG{r} VGND VSUBS automx_ternary_cell")
    body += [f".ends automx_ternary_column_{rows}x1", ""]
    return "\n".join(body)

def _macro(rows: int, cols: int, cfg: Sky130MHAConfig) -> str:
    pins = [p for c in range(cols) for p in (f"BLP{c}", f"BLN{c}")]
    pins += [p for r in range(rows) for p in (f"WLP{r}", f"WLN{r}")]
    pins += [p for r in range(rows) for c in range(cols) for p in (f"WPOS_{r}_{c}", f"WNEG_{r}_{c}")]
    pins += ["VGND", "VSUBS"]
    body = [_column(rows, cfg), f".subckt automx_ternary_cim_{rows}x{cols}_core {' '.join(pins)}"]
    for c in range(cols):
        rowpins = [p for r in range(rows) for p in (f"WLP{r}", f"WLN{r}", f"WPOS_{r}_{c}", f"WNEG_{r}_{c}")]
        body.append(f"XCOL{c} BLP{c} BLN{c} {' '.join(rowpins)} VGND VSUBS automx_ternary_column_{rows}x1")
    body += [f".ends automx_ternary_cim_{rows}x{cols}_core", ""]
    return "\n".join(body)

def _tb_header(title: str, model: Path, cfg: Sky130MHAConfig, include: str) -> list[str]:
    return [f".title {title}", f'.lib "{model.as_posix()}" tt', f'.include "{include}"',
            f".param VDD={cfg.vdd}", f".temp {cfg.temperature_c}",
            ".option method=gear reltol=1e-4 abstol=1e-12", "VVDD VPWR 0 {VDD}",
            "VPRE PREB 0 DC 0 PULSE(0 {VDD} 0.4n 5p 5p 1.8n 4n)",
            "BPOWER POWER 0 V=-V(VPWR)*I(VVDD)", ""]

def _precharge(lines: list[str], tag: str, blp: str, bln: str, capacitance_f: int = 50) -> None:
    lines += [f"XPREP_{tag} {blp} PREB VPWR VPWR sky130_fd_pr__pfet_01v8 W=1.68 L=0.15",
              f"XPREN_{tag} {bln} PREB VPWR VPWR sky130_fd_pr__pfet_01v8 W=1.68 L=0.15",
              f"CBLP_{tag} {blp} 0 {capacitance_f}f IC={{VDD}}", f"CBLN_{tag} {bln} 0 {capacitance_f}f IC={{VDD}}",
              f"BDIFF_{tag} DIFF_{tag} 0 V=V({bln})-V({blp})"]

def _dc(lines: list[str], name: str, node: str, enabled: bool) -> None:
    lines.append(f"V{name} {node} 0 {'{VDD}' if enabled else '0'}")

def _wl(lines: list[str], name: str, node: str, mag: int) -> None:
    lines.append(f"V{name} {node} 0 " + (f"DC 0 PULSE(0 {{VDD}} 0.5n 5p 5p {mag * 100}p 5n)" if mag else "0"))

def _finish(lines: list[str]) -> str:
    # Let ngspice solve the precharge DC operating point.  UIC initializes
    # only the explicit bitline capacitors, leaving extracted parasitic caps
    # at zero and creating a false differential offset before WL fires.
    lines += [".measure tran energy_j INTEG V(POWER) FROM=2.2n TO=3.8n", ".tran 5p 4n", ".end", ""]
    return "\n".join(lines)

def _add_delay(lines: list[str], key: str, trigger: str, diff_node: str, expected: int) -> str:
    delay = key.replace("_diff", "_delay")
    edge = "RISE" if expected > 0 else "FALL"
    target = "1m" if expected > 0 else "-1m"
    lines.append(f".measure tran {delay} TRIG V({trigger}) VAL=10m RISE=1 TARG V({diff_node}) VAL={target} {edge}=1")
    return delay

def _cell_tb(model: Path, cfg: Sky130MHAConfig):
    lines = _tb_header("AutoMX ternary-cell sweep", model, cfg, "ternary_cell.spice")
    cases, delays = [], []
    i = 0
    for weight in (-1, 0, 1):
        for mag in E2M1_MAGNITUDES_X2:
            tag = f"w{'n' if weight < 0 else 'z' if weight == 0 else 'p'}{abs(weight)}_a{mag}"
            blp, bln, wlp, wln, wp, wn = [f"{x}_{i}" for x in ("BLP", "BLN", "WLP", "WLN", "WPOS", "WNEG")]
            _precharge(lines, tag, blp, bln); _wl(lines, f"WLP_{i}", wlp, mag)
            _dc(lines, f"WLN_{i}", wln, False); _dc(lines, f"WPOS_{i}", wp, weight > 0); _dc(lines, f"WNEG_{i}", wn, weight < 0)
            lines.append(f"XCELL_{i} {blp} {bln} {wlp} {wln} {wp} {wn} 0 0 automx_ternary_cell")
            key, expected = f"cell_{tag}_diff", weight * mag
            sample_ns = 0.6 if mag == 0 else 0.5 + 0.1 * mag
            diff_node = f"DIFF_{tag}"
            lines.append(f".measure tran {key} FIND V({diff_node}) AT={sample_ns:.3f}n")
            if expected: delays.append(_add_delay(lines, key, wlp, diff_node, expected))
            cases.append({"measurement": key, "expected": expected, "group": f"weight_{weight}"}); i += 1
    return _finish(lines), tuple(cases), tuple(delays)

def _column_tb(rows: int, model: Path, cfg: Sky130MHAConfig):
    lines = _tb_header(f"AutoMX {rows}x1 column sweep", model, cfg, f"column_{rows}x1.spice")
    cases, delays, i, act = [], [], 0, 4
    active_counts = tuple(dict.fromkeys((0, 1, max(1, rows // 2), rows)))
    for sign in (1, -1):
        for active in active_counts:
            tag, blp, bln = f"{'pos' if sign > 0 else 'neg'}_n{active}", f"BLP_{i}", f"BLN_{i}"
            _precharge(lines, tag, blp, bln, capacitance_f=50 * rows); pins = [blp, bln]
            for r in range(rows):
                suf = f"{i}_{r}"; wlp, wln, wp, wn = [f"{x}_{suf}" for x in ("WLP", "WLN", "WPOS", "WNEG")]
                _wl(lines, f"WLP_{suf}", wlp, act); _dc(lines, f"WLN_{suf}", wln, False)
                _dc(lines, f"WPOS_{suf}", wp, r < active and sign > 0); _dc(lines, f"WNEG_{suf}", wn, r < active and sign < 0)
                pins += [wlp, wln, wp, wn]
            lines.append(f"XCOL_{i} {' '.join(pins)} 0 0 automx_ternary_column_{rows}x1")
            key, expected = f"column_{rows}_{tag}_diff", sign * active * act
            diff_node = f"DIFF_{tag}"
            lines.append(f".measure tran {key} FIND V({diff_node}) AT=0.900n")
            if expected: delays.append(_add_delay(lines, key, f"WLP_{i}_0", diff_node, expected))
            cases.append({"measurement": key, "expected": expected, "group": f"sign_{sign}"}); i += 1
    return _finish(lines), tuple(cases), tuple(delays)

def _patterns(rows: int, cols: int):
    identity = tuple(tuple(1 if r == c else 0 for c in range(cols)) for r in range(rows))
    plus = tuple(tuple(1 for _ in range(cols)) for _ in range(rows))
    mixed = tuple(tuple(1 if (r+c)%3 == 0 else -1 if (r+c)%3 == 1 else 0 for c in range(cols)) for r in range(rows))
    zero = tuple(tuple(0 for _ in range(cols)) for _ in range(rows))
    return (("identity", tuple(range(1, rows+1)), identity), ("all_plus", tuple(range(1, rows+1)), plus),
            ("signed_mix", tuple((-1)**r*(r+1) for r in range(rows)), mixed), ("zero", tuple(range(1, rows+1)), zero))

def _macro_tb(rows: int, cols: int, model: Path, cfg: Sky130MHAConfig):
    lines = _tb_header(f"AutoMX differential {rows}x{cols} macro", model, cfg, f"automx_ternary_cim_{rows}x{cols}_core.spice")
    cases, delays = [], []
    for i, (name, acts, weights) in enumerate(_patterns(rows, cols)):
        pins = []
        for c in range(cols):
            blp, bln = f"BLP_{i}_{c}", f"BLN_{i}_{c}"; _precharge(lines, f"{name}_{c}", blp, bln, capacitance_f=50 * rows); pins += [blp, bln]
        for r, act in enumerate(acts):
            wlp, wln = f"WLP_{i}_{r}", f"WLN_{i}_{r}"; _wl(lines, f"WLP_{i}_{r}", wlp, max(act, 0)); _wl(lines, f"WLN_{i}_{r}", wln, max(-act, 0)); pins += [wlp, wln]
        for r in range(rows):
            for c in range(cols):
                wp, wn, value = f"WPOS_{i}_{r}_{c}", f"WNEG_{i}_{r}_{c}", weights[r][c]
                _dc(lines, f"WPOS_{i}_{r}_{c}", wp, value > 0); _dc(lines, f"WNEG_{i}_{r}_{c}", wn, value < 0); pins += [wp, wn]
        lines.append(f"XMACRO_{i} {' '.join(pins)} 0 0 automx_ternary_cim_{rows}x{cols}_core")
        for c in range(cols):
            expected = sum(acts[r] * weights[r][c] for r in range(rows)); blp, bln = f"BLP_{i}_{c}", f"BLN_{i}_{c}"
            key = f"macro_{name}_c{c}_diff"
            diff_node = f"DIFF_{name}_{c}"
            lines.append(f".measure tran {key} FIND V({diff_node}) AT=0.900n")
            cases.append({"measurement": key, "expected": expected, "group": f"{name}_c{c}"})
            if expected:
                r = next(r for r, value in enumerate(acts) if value); trigger = f"{'WLP' if acts[r] > 0 else 'WLN'}_{i}_{r}"
                delays.append(_add_delay(lines, key, trigger, diff_node, expected))
    return _finish(lines), tuple(cases), tuple(delays)

def _column_case_tb(rows: int, sign: int, active: int, model: Path, cfg: Sky130MHAConfig):
    name = f"column_{rows}x1.spice"; tag = f"{'pos' if sign > 0 else 'neg'}_n{active}"
    lines = _tb_header(f"AutoMX {rows}x1 {tag}", model, cfg, name)
    blp, bln = "BLP", "BLN"; _precharge(lines, tag, blp, bln, capacitance_f=50 * rows); pins = [blp, bln]; act = 4
    for r in range(rows):
        wlp, wln, wp, wn = f"WLP_{r}", f"WLN_{r}", f"WPOS_{r}", f"WNEG_{r}"
        _wl(lines, f"WLP_{r}", wlp, act); _dc(lines, f"WLN_{r}", wln, False)
        _dc(lines, f"WPOS_{r}", wp, r < active and sign > 0); _dc(lines, f"WNEG_{r}", wn, r < active and sign < 0)
        pins += [wlp, wln, wp, wn]
    lines.append(f"XCOL {' '.join(pins)} 0 0 automx_ternary_column_{rows}x1")
    key, expected, diff = f"column_{rows}_{tag}_diff", sign * active * act, f"DIFF_{tag}"
    lines.append(f".measure tran {key} FIND V({diff}) AT=0.900n")
    delays = () if not expected else (_add_delay(lines, key, "WLP_0", diff, expected),)
    return _finish(lines), ({"measurement": key, "expected": expected, "group": f"sign_{sign}"},), delays

def _macro_pattern_tb(rows: int, cols: int, pattern, model: Path, cfg: Sky130MHAConfig):
    name, acts, weights = pattern
    lines = _tb_header(f"AutoMX {rows}x{cols} {name}", model, cfg, f"automx_ternary_cim_{rows}x{cols}_core.spice")
    pins = []
    for c in range(cols):
        blp, bln = f"BLP_{c}", f"BLN_{c}"; _precharge(lines, f"{name}_{c}", blp, bln, capacitance_f=50 * rows); pins += [blp, bln]
    for r, act in enumerate(acts):
        wlp, wln = f"WLP_{r}", f"WLN_{r}"; _wl(lines, f"WLP_{r}", wlp, max(act, 0)); _wl(lines, f"WLN_{r}", wln, max(-act, 0)); pins += [wlp, wln]
    for r in range(rows):
        for c in range(cols):
            wp, wn, value = f"WPOS_{r}_{c}", f"WNEG_{r}_{c}", weights[r][c]
            _dc(lines, f"WPOS_{r}_{c}", wp, value > 0); _dc(lines, f"WNEG_{r}_{c}", wn, value < 0); pins += [wp, wn]
    lines.append(f"XMACRO {' '.join(pins)} 0 0 automx_ternary_cim_{rows}x{cols}_core")
    cases, delays = [], []
    for c in range(cols):
        expected = sum(acts[r] * weights[r][c] for r in range(rows)); key = f"macro_{name}_c{c}_diff"; diff = f"DIFF_{name}_{c}"
        lines.append(f".measure tran {key} FIND V({diff}) AT=0.900n")
        cases.append({"measurement": key, "expected": expected, "group": f"{name}_c{c}"})
        if expected:
            r = next(r for r, value in enumerate(acts) if value); trigger = f"{'WLP' if acts[r] > 0 else 'WLN'}_{r}"
            delays.append(_add_delay(lines, key, trigger, diff, expected))
    return _finish(lines), tuple(cases), tuple(delays)

def _levels(levels: Iterable[str]) -> tuple[str, ...]:
    requested = tuple(levels)
    if "all" in requested: return STAGE_ORDER
    unknown = set(requested) - set(STAGE_ORDER)
    if unknown: raise ValueError(f"unknown Stage-4 levels: {sorted(unknown)}")
    return tuple(x for x in STAGE_ORDER if x in requested)

def generate_stage4_spice(cfg: Sky130MHAConfig, output_root: str | Path, model_library: str | Path,
                          levels: Sequence[str] = ("all",), receipt_root: str | Path = "results/receipts/spice") -> dict[str, object]:
    output, model, receipts = Path(output_root), Path(model_library).expanduser().resolve(), Path(receipt_root)
    if not model.is_file(): raise FileNotFoundError(f"SKY130 model library does not exist: {model}")
    artifacts: list[Stage4Artifact] = []
    def emit(stage, level, folder, netname, nettext, tbname, tb):
        target = output / folder; target.mkdir(parents=True, exist_ok=True)
        net, deck = target / netname, target / tbname; net.write_text(nettext, encoding="utf-8"); deck.write_text(tb[0], encoding="utf-8")
        artifacts.append(Stage4Artifact(stage, level, str(net.resolve()), str(deck.resolve()),
                                        str((receipts / f"{Path(netname).stem}.json").resolve()), tb[1], tb[2]))
    def emit_jobs(stage, level, folder, netname, nettext, job_defs):
        target = output / folder; target.mkdir(parents=True, exist_ok=True); net = target / netname; net.write_text(nettext, encoding="utf-8")
        jobs, cases, delays = [], [], []
        for job_name, tb in job_defs:
            deck = target / f"tb_{Path(netname).stem}_{job_name}.spice"; deck.write_text(tb[0], encoding="utf-8")
            jobs.append({"name": job_name, "testbench": str(deck.resolve()), "cases": list(tb[1]),
                         "delay_measurements": list(tb[2]), "energy_measurement": "energy_j"})
            cases.extend(tb[1]); delays.extend(tb[2])
        artifacts.append(Stage4Artifact(stage, level, str(net.resolve()), jobs[0]["testbench"],
                                        str((receipts / f"{Path(netname).stem}.json").resolve()),
                                        tuple(cases), tuple(delays), tuple(jobs)))
    selected = _levels(levels)
    if "cell" in selected: emit("cell", "Level 0 / Milestone 2", "cell", "ternary_cell.spice", _cell(cfg), "tb_ternary_cell.spice", _cell_tb(model, cfg))
    for stage, rows in (("column4", 4), ("column8", 8)):
        if stage in selected:
            counts = tuple(dict.fromkeys((0, 1, max(1, rows // 2), rows)))
            defs = [(f"{'pos' if sign > 0 else 'neg'}_n{active}", _column_case_tb(rows, sign, active, model, cfg))
                    for sign in (1, -1) for active in counts]
            emit_jobs(stage, "Level 1 / Milestone 3", "column", f"column_{rows}x1.spice", _column(rows, cfg), defs)
    if "macro4x4" in selected:
        defs = [(pattern[0], _macro_pattern_tb(4, 4, pattern, model, cfg)) for pattern in _patterns(4, 4)]
        emit_jobs("macro4x4", "Level 2 / physical demonstrator", "macro", "automx_ternary_cim_4x4_core.spice", _macro(4, 4, cfg), defs)
    manifest = {"format": "automx-cim-stage4-spice-manifest-v1", "config_sha256": cfg.sha256, "pdk": cfg.pdk,
                "corner": "tt", "vdd": cfg.vdd, "temperature_c": cfg.temperature_c,
                "activation_encoding": {"type": "signed-two-phase-pwm", "positive_phase": "WLP", "negative_phase": "WLN",
                                        "pulse_width_ps_per_act_x2": 100, "e2m1_magnitudes_x2": list(E2M1_MAGNITUDES_X2), "e8m0_location": "digital"},
                "circuit_assumptions": {"bitline_capacitance_f_per_row": 50, "precharge_pfet_width_um": 1.68},
                "model_library": str(model), "model_library_sha256": sha256(model.read_bytes()).hexdigest(),
                "artifacts": [a.to_mapping() for a in artifacts]}
    output.mkdir(parents=True, exist_ok=True); (output / "stage4_manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    return manifest
