import re
import json
import random
import shutil

from typing import List
from pathlib import Path


def rand_float_2(vmin: float, vmax: float) -> float:
    return round(random.uniform(vmin, vmax), 2)


def calc_width(min_width: float, width_unit: int, nf: int) -> float:
    return round(min_width * width_unit * nf, 2)


def fmt_value(name: str, value) -> str:
    if name == "IB":
        return f"{value}u"
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value)


def build_param_line(names: list[str], params: dict) -> str:
    return ".param " + " ".join(f"{name}={fmt_value(name, params[name])}" for name in names)


def get_device_suffixes(circuit_params: list[str]) -> list[str]:
    suffixes = set()
    for name in circuit_params:
        m = re.match(r"^(L|W|NF)(.+)$", name)
        if m:
            suffixes.add(m.group(2))
    return sorted(suffixes)


def sample_test_param(name: str, value_cfg: dict):
    range_key = f"{name}_range"
    if range_key in value_cfg:
        vmin, vmax = value_cfg[range_key]
        return random.randint(vmin, vmax) if name == "IB" else rand_float_2(vmin, vmax)
    if name in value_cfg:
        return value_cfg[name]
    raise KeyError(f"Missing constraint for {name}")


def sample_even_int(vmin: int, vmax: int) -> int:
    evens = list(range(vmin + (vmin % 2), vmax + 1, 2))
    if not evens:
        raise ValueError(f"No even number exists in range [{vmin}, {vmax}]")
    return random.choice(evens)


def create_params(
    const_path: str | Path, 
    trial: int, 
    seed: int | None = None
) -> dict[int, str]:
    if seed is not None:
        random.seed(seed)

    with open(const_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    value_cfg = cfg["param_align"][0]
    name_cfg = cfg["param_align"][1]
    same_cfg = cfg["param_align"][2].get("same_param", []) if len(cfg["param_align"]) > 2 else []

    test_params = name_cfg["test_param"]
    circuit_params = name_cfg["circuit_param"]
    ordered_names = test_params + circuit_params

    exact_length = value_cfg["exact_length"]
    min_width = value_cfg["min_width"]
    unit_width_range = value_cfg["unit_width_range"]
    nf_range = value_cfg["nf_range"]

    device_suffixes = get_device_suffixes(circuit_params)

    seen = set()
    result = {}
    idx = 0
    attempts = 0
    max_attempts = max(1000, 200 * trial)

    while idx < trial:
        if attempts >= max_attempts:
            raise RuntimeError(f"Cannot generate {trial} unique samples within {max_attempts} attempts.")
        attempts += 1

        params = {name: sample_test_param(name, value_cfg) for name in test_params}
        shared_width_unit = random.randint(unit_width_range[0], unit_width_range[1])

        for suffix in device_suffixes:
            nf = sample_even_int(nf_range[0], nf_range[1])
            params[f"L{suffix}"] = exact_length
            params[f"NF{suffix}"] = nf
            params[f"W{suffix}"] = calc_width(min_width, shared_width_unit, nf)

        for group in same_cfg:
            ref = group[0]
            for name in group[1:]:
                params[name] = params[ref]

        key = tuple(params[name] for name in ordered_names)
        if key in seen:
            continue

        seen.add(key)
        result[idx] = build_param_line(ordered_names, params)
        idx += 1

    return result


def create_pkg(
    design_cfg: object,
    dst: str | Path,
    specs: List[str],
):
    # Create a package directory and gather all required design artifacts into it.
    dst_dir = Path(dst)
    dst_dir.mkdir(parents=True, exist_ok=True)

    pkg_dict = {}

    # Copy parameter file
    param = design_cfg.get_path("ngspice.work_dir") / "param.spice"
    if not param.is_file():
        raise FileNotFoundError(f"Param file not found: {param}")
    shutil.copy(str(param), str(dst_dir / param.name))
    pkg_dict["param"] = [param.name]

    # Copy constraint file
    const = design_cfg.get_path("inputs.const_file")
    if not const.is_file():
        raise FileNotFoundError(f"Const file not found: {const}")
    shutil.copy(str(const), str(dst_dir / const.name))
    pkg_dict["const"] = [const.name]

    # Collect pre-simulation result files
    pre_sim = design_cfg.get_path("results.work_dir")
    for spec in specs:
        spec = Path(spec)
        pre_spec = pre_sim / f"{spec.stem}_pre{spec.suffix}"
        if not pre_spec.is_file():
            print(f"Skip, pre-sim spec not found: {pre_spec}")
            continue
        shutil.move(str(pre_spec), str(dst_dir / pre_spec.name))
        pkg_dict.setdefault("pre-sim", []).append(pre_spec.name)

    if pkg_dict.get("pre-sim", []) == []:
        pkg_dict["pre-sim"] = "pre-sim specs not found"

    # Collect layout file
    layout = design_cfg.get_path("align.gds_file")
    if layout.is_file():
        shutil.move(str(layout), str(dst_dir / layout.name))
        pkg_dict["layout"] = [layout.name]
    else:
        pkg_dict["layout"] = "layout file not found"

    # Collect extracted netlists
    lvs_netlist = design_cfg.get_path("netgen.layout_spice_file")
    pex_netlist = (
        design_cfg.get_path("magic.work_dir")
        / f"{design_cfg['design.top_module']}_pex.spice"
    )
    extract = [lvs_netlist, pex_netlist]

    for netlist in extract:
        if netlist.is_file():
            shutil.move(str(netlist), str(dst_dir / netlist.name))
            pkg_dict.setdefault("extract", []).append(netlist.name)

    if pkg_dict.get("extract", []) == []:
        pkg_dict["extract"] = "extract files not found"

    # Collect DRC report
    drc = design_cfg.get_path("klayout.work_dir") / "drc_report.xml"
    if drc.is_file():
        shutil.move(str(drc), str(dst_dir / drc.name))
        pkg_dict["drc"] = [drc.name]
    else:
        pkg_dict["drc"] = "DRC report not found"

    # Collect LVS report
    lvs = design_cfg.get_path("netgen.work_dir") / "comp.out"
    if lvs.is_file():
        shutil.move(str(lvs), str(dst_dir / lvs.name))
        pkg_dict["lvs"] = [lvs.name]
    else:
        pkg_dict["lvs"] = "LVS report not found"

    # Collect post-simulation result files
    post_sim = design_cfg.get_path("results.work_dir")
    for spec in specs:
        spec = Path(spec)
        post_spec = post_sim / f"{spec.stem}_post{spec.suffix}"
        if not post_spec.is_file():
            print(f"Skip, post-sim spec not found: {post_spec}")
            continue
        shutil.move(str(post_spec), str(dst_dir / post_spec.name))
        pkg_dict.setdefault("post-sim", []).append(post_spec.name)

    if pkg_dict.get("post-sim", []) == []:
        pkg_dict["post-sim"] = "post-sim specs not found"

    return pkg_dict