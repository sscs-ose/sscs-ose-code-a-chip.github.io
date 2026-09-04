import shutil

from pathlib import Path
from typing import Set, Dict

import src.cabgen.netlist as netlist


def init_design_workspace(
    base_dir: str | Path,
    steps: dict[str, str],
    design_cfg: object,
) -> None:
    """
    Initialize a design workspace by creating necessary folders for each step.

    For each step in `steps`, creates a corresponding folder under `base_dir`.
    """
    base = Path(base_dir).resolve()
    base.mkdir(parents=True, exist_ok=True)

    for step in steps.keys():
        step_folder = base / steps[step].lower()
        step_folder.mkdir(parents=True, exist_ok=True)
    
    if steps.get("pre-sim") == None:
        pass
    elif steps.get("pre-sim").lower() == "ngspice":
        init_file = design_cfg.get_path("ngspice.work_dir") / ".spiceinit"
        with open(init_file, "w") as f:
            f.write(f"set ngbehavior=hsa \nset ng_nomodcheck \n")
        
        param_file = design_cfg.get_path("ngspice.work_dir") / "param.spice"
        shutil.copy(design_cfg.get_path("inputs.param_file"), param_file)
    else:
        raise NotImplementedError(f"Pre-simulation tool {steps.get('pre-sim')} not supported for workspace initialization.")
    
    if steps.get("layout") == None:
        pass
    elif steps.get("layout").lower() == "align":
        netlist.input2align(
            input_netlist=design_cfg["inputs.netlist_file"],
            input_param=design_cfg["inputs.param_file"],
            input_constraint=design_cfg["inputs.const_file"],
            output_dir=design_cfg["align.input_dir"],
            ckt_name=design_cfg["design.circuit"],
            ckt_pins=design_cfg["design.pin_order"],
        )
    else:
        raise NotImplementedError(f"Layout tool {steps.get('layout')} not supported for workspace initialization.")
    
    if steps.get("lvs") == None:
        pass
    elif steps.get("lvs").lower() == "netgen":
        netlist.input2netgen(
            input_netlist=design_cfg["inputs.netlist_file"],
            input_param=design_cfg["inputs.param_file"],
            output_netlist=design_cfg["netgen.schematic_spice_file"],
            ckt_name=design_cfg["design.circuit"],
            ckt_pins=design_cfg["design.pin_order"],
        )
    else:
        raise NotImplementedError(f"LVS tool {steps.get('lvs')} not supported for workspace initialization.")


def _is_preserved(
    path: Path, 
    folder_name: str, 
    preserved: Dict[str, Set[Path]],
) -> bool:
    """
    Return True if `path` should be preserved based on preserved mapping.

    A path is preserved if it exactly matches a preserved target
    or if it lies under a preserved directory subtree.
    """
    targets = preserved.get(folder_name, set())
    p = path.resolve()
    for t in targets:
        if p == t:
            return True
        try:
            if t.is_dir() and t in p.parents:
                return True
        except FileNotFoundError:
            pass
    return False

def reset_design_workspace(
    base_dir: str | Path,
    keep_top: set[str],
    keep_path: dict[str, set[str]],
    verbose: bool = True,
) -> None:
    """
    Reset a design workspace so only selected top-level folders remain,
    and within those, preserve specific files/subtrees.

    - Ensures all folders in `keep_top` exist.
    - In each kept folder, preserves any relative paths listed in `keep_path[folder]`.
      Entire subtrees of preserved directories are retained.
    - Deletes all other files/subfolders in kept folders.
    - Removes unexpected top-level files/folders under `base_dir`.
    """
    base = Path(base_dir).resolve()

    if not base.is_dir():
        raise FileNotFoundError(f"{base} does not exist or is not a directory")

    # Defensive copies so defaults aren't mutated
    keep_top = set(keep_top)
    keep_path = {k: set(v) for k, v in keep_path.items()}

    # Any folder mentioned in keep_path must also be kept
    keep_top |= set(keep_path.keys())

    # Normalize preserved targets into resolved Paths
    preserved: Dict[str, Set[Path]] = {}
    for folder, rels in keep_path.items():
        folder_root = (base / folder).resolve()
        preserved[folder] = {(folder_root / rel).resolve() for rel in rels}

    # 0) Remove files directly under base
    for entry in base.iterdir():
        if entry.is_file():
            entry.unlink()
            print(f"Deleted file: {entry}") if verbose else None

    # 1) Ensure kept top-level folders exist
    for name in keep_top:
        folder = base / name
        folder.mkdir(parents=True, exist_ok=True)

    # 2) Clean inside each kept folder
    for name in keep_top:
        folder = base / name
        if not folder.exists():
            continue
        for child in folder.iterdir():
            if _is_preserved(child, name, preserved):
                print(f"Preserved: {child}")
                continue
            if child.is_dir():
                shutil.rmtree(child)
                print(f"Deleted folder: {child}") if verbose else None
            else:
                child.unlink()
                print(f"Deleted file: {child}") if verbose else None

    # 3) Remove unexpected top-level items
    for entry in base.iterdir():
        if entry.name in keep_top:
            continue
        if entry.is_dir():
            shutil.rmtree(entry)
            print(f"Deleted unexpected folder: {entry}") if verbose else None
        else:
            entry.unlink()
            print(f"Deleted unexpected file: {entry}") if verbose else None