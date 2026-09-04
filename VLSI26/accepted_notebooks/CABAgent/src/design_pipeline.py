from __future__ import annotations

import os
import json
import shutil

from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional

from src import cabgen
from src.cabgen import netlist, viz


class EDAPipeline:
    """
    Orchestrate an analog EDA flow using a schema-first YAML config.
    
    Key features
    ------------
    - LoadDesignConfig providing:
        * dot-key access (e.g., cfg["align.gds_file"])
        * ${ENV} + ${dot.key} interpolation
        * recursive path normalization for *_dir/_path/_file
    - Early validation of required config keys
    - Centralized environment export
    - Tool dispatch via registries (ALIGN/KLayout/Magic/Netgen by default)
    """

    DEFAULT_PDK = "SKY130"

    DEFAULT_STEPS: Dict[str, str] = {
        "pre-sim"   : "Ngspice",
        "layout"    : "ALIGN",
        "drc"       : "KLayout",
        "extract"   : "Magic",
        "lvs"       : "Netgen",
        "post-sim"  : "Ngspice",
    }

    DEFAULT_SPECS: List[str] = [
        "gain.txt", "phase.txt", "inoise.txt", "transient_out.txt", "THD.txt"
    ]

    DEFAULT_RESET: Dict[str, Any] = {
        "keep_top"  : {"align", "klayout", "magic", "netgen", "ngspice"},
        "keep_path" : {"align": {"0_netlist"}, "ngspice": {".spiceinit", "param.spice"}},
        "verbose"   : False,
    }

    def __init__(
        self,
        design: str,
        *,
        pdk: Optional[str]                      = None,
        steps: Optional[Dict[str, str]]         = None,
        specs: Optional[List[str]]              = None,
        reset_kwargs: Optional[Dict[str, Any]]  = None,
        verbose: bool                           = True,
    ):
        """
        Parameters
        ----------
        design : str
            Logical design name; 
            resolves default YAML path at spec2layout/dconfigs/{design}.yaml
        pdk : Optional[str]
            PDK name to export (default: SKY130).
        steps : Optional[Dict[str, str]]
            Override tool selections (default: self.DEFAULT_STEPS).
        specs : Optional[List[str]]
            List of spec files to generate for CAB (default: self.DEFAULT_SPECS).
        reset_kwargs : Optional[Dict[str, Any]]
            Passed to cabgen.reset_design_workspace; defaults provided.
        verbose : bool
            Print stage logs.
        """
        self.verbose = verbose
        self.pdk = pdk or self.DEFAULT_PDK
        os.environ["PDK"] = self.pdk
        self.pdk_lower = self.pdk.lower()   # normalize PDK name for config key lookups

        self.steps = dict(steps or self.DEFAULT_STEPS)
        self.specs = list(specs or self.DEFAULT_SPECS)
        self.reset_kwargs = dict(reset_kwargs or self.DEFAULT_RESET)
        
        cfg_path = Path(f"src/dconfigs/{design}.yaml")

        # Keys that depend on selected tools/PDK
        self.layout_tool = self.steps.get("layout", "ALIGN")    # default to ALIGN
        self.gds_key = f"{self.layout_tool.lower()}.gds_file"
        self.mag_key = f"magic.{self.pdk_lower}_magicrc"

        # Load & validate config (absolute paths computed relative to YAML folder)
        self.cfg = cabgen.LoadDesignConfig(
            config_path=cfg_path,
            required=["design.top_module", self.gds_key, self.mag_key],
        )

        # Frequently-used cfg fields
        self.design_name: str = self.cfg["design.name"]
        self.ckt_name: str = self.cfg["design.circuit"]
        self.top_module: str = self.cfg["design.top_module"]

        # Export core env vars for downstream tools
        cabgen.export2env(
            {
                "TOP_MODULE": self.top_module,
                "GDS_PATH": self.cfg[self.gds_key],
                "PDK_MCFG": self.cfg[self.mag_key],
            }
        )

        # Print config/env summary
        if self.verbose:
            self._print_cfg_env()

        # Tool registries
        self._presim_runners: Dict[str, Callable[[], None]] = {
            "Ngspice": self._run_presim_ngspice,
        }
        self._layout_runners: Dict[str, Callable[[], None]] = {
            "ALIGN": self._run_layout_align,
        }
        self._drc_runners: Dict[str, Callable[[], None]] = {
            "KLayout": self._run_drc_klayout,
        }
        self._extract_runners: Dict[str, Callable[[], None]] = {
            "Magic": self._run_extract_magic,
        }
        self._lvs_runners: Dict[str, Callable[[], None]] = {
            "Netgen": self._run_lvs_netgen,
        }
        self._postsim_runners: Dict[str, Callable[[], None]] = {
            "Ngspice": self._run_postsim_ngspice,
        }
        
        # Step -> registry map
        self._step_registries: Dict[str, Mapping[str, Callable[[], None]]] = {
            "pre-sim"   : self._presim_runners,
            "layout"    : self._layout_runners,
            "drc"       : self._drc_runners,
            "extract"   : self._extract_runners,
            "lvs"       : self._lvs_runners,
            "post-sim"  : self._postsim_runners,
        }
        # Canonical run order
        self._step_order = ("pre-sim", "layout", "drc", "extract", "lvs", "post-sim")  

        # Initialize workspace
        self._init_workspace()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def run_all(self) -> None:
        log = cabgen.setup_logger("eda_pipeline", console=True)

        log.info("Starting EDA pipeline for %s", self.design_name, extra={"stage": "PIPELINE"})

        self._reset_workspace()
        log.info("Workspace reset", extra={"stage": "RESET"})

        unknown = set(self.steps) - set(self._step_registries)  # validate step keys
        if unknown:
            raise ValueError(f"Unknown step key(s) in steps: {sorted(unknown)}")
        
        # Run only steps that are present in self.steps, but in a stable order
        for step_key in self._step_order:
            if step_key not in self.steps:
                continue
            self._dispatch(self._step_registries[step_key], step_key)

        log.info("Completed EDA pipeline for %s", self.design_name, extra={"stage": "PIPELINE"})

    def run_cabgen(self, num_trials: int = 9) -> None:
        log = cabgen.setup_logger("eda_pipeline", console=True)

        log.info("Starting Benchmark Generation for %s", self.design_name, extra={"stage": "PIPELINE"})

        width = len(str(num_trials-1))
        pkg_dict: Dict[str, Any] = {}
        # Genearte param dict
        param_dict = cabgen.create_params(
            const_path=self.cfg["inputs.const_file"],
            trial=num_trials,
        )

        for i in range(num_trials):
            netlist._write(self.cfg.get_path("ngspice.work_dir") / "param.spice", param_dict[i])

            self._reset_workspace(bench_gen=True)
            log.info("Workspace reset for benchmark generation trail %d", i, extra={"stage": "RESET"})

            unknown = set(self.steps) - set(self._step_registries)  # validate step keys
            if unknown:
                raise ValueError(f"Unknown step key(s) in steps: {sorted(unknown)}")
        
            # Run only steps that are present in self.steps, but in a stable order
            for step_key in self._step_order:
                if step_key not in self.steps:
                    continue
                self._dispatch(self._step_registries[step_key], step_key)
            
            # Generate CAB package for this trial
            trial = f"Pkg{i:0{width}d}"
            pkg = cabgen.create_pkg(
                design_cfg=self.cfg,
                dst=self.cfg.get_path("results.work_dir") / trial,
                specs=self.specs,
            )
            pkg_dict[trial] = pkg

        # dump pkg into json with key dst under results dir
        results_dir = self.cfg.get_path("results.work_dir")
        results_dir.mkdir(parents=True, exist_ok=True)
        pkg_path = results_dir / f"benchmark.json"
        with open(pkg_path, "w") as f:
            json.dump(pkg_dict, f, indent=4)

        log.info("Completed Benchmark Generation for %s", self.design_name, extra={"stage": "PIPELINE"})

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _print_cfg_env(self) -> None:
        print("Design configuration loaded:") 
        print(viz.format_dict(self.cfg.as_dict())) 
        print("\nEnvironment variables set:\n" 
            f" PDK_ROOT   = {os.environ.get('PDK_ROOT')}\n" 
            f" CAD_ROOT   = {os.environ.get('CAD_ROOT')}\n" 
            f" TOP_MODULE = {os.environ.get('TOP_MODULE')}\n" 
            f" PDK        = {os.environ.get('PDK')}\n" 
            f" GDS_PATH   = {os.environ.get('GDS_PATH')}\n" 
            f" PDK_MCFG   = {os.environ.get('PDK_MCFG')}\n" 
        )

    def _init_workspace(self) -> None:
        # Initialize workspace for each step under: designs/<design>/<PDK>/runs
        base_ws = Path("designs", self.design_name, self.pdk, "runs")
        cabgen.init_design_workspace(base_dir=base_ws, steps=self.steps, design_cfg=self.cfg)
        # Clear results directory
        results_path = self.cfg.get_path("results.work_dir")
        results_path.mkdir(parents=True, exist_ok=True) 
        for item in results_path.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

    def _reset_workspace(self, bench_gen=False) -> None:
        # Base workspace: designs/<design>/<PDK>/runs
        base_ws = Path("designs", self.design_name, self.pdk, "runs")
        cabgen.reset_design_workspace(base_dir=base_ws, **self.reset_kwargs)
        if bench_gen:
            if self.steps.get("layout") == None:
                pass
            elif self.steps.get("layout").lower() == "align":
                netlist.input2align(
                    input_netlist=self.cfg["inputs.netlist_file"],
                    input_param=self.cfg.get_path("ngspice.work_dir") / "param.spice",
                    input_constraint=self.cfg["inputs.const_file"],
                    output_dir=self.cfg["align.input_dir"],
                    ckt_name=self.cfg["design.circuit"],
                    ckt_pins=self.cfg["design.pin_order"],
                )
                print("Replaced: align input netlist with CAB-generated param.spice")
            else:
                raise NotImplementedError(f"Layout tool {self.steps.get('layout')} not supported for workspace initialization.")

    def _dispatch(
        self, 
        registry: Mapping[str, Callable[[], None]], 
        step_key: str
    ) -> None:
        tool = self.steps.get(step_key)
        if not tool:
            raise ValueError(f"No tool configured for step '{step_key}'")
        runner = registry.get(tool)
        if runner is None:
            raise ValueError(f"Unsupported {step_key} tool: '{tool}'. Available: {list(registry.keys())}")
        if self.verbose:
            print(f"[{step_key.upper()}] → {tool}")
        runner()

    # ------------------------------------------------------------------ #
    # Tool implementations
    # ------------------------------------------------------------------ #
    def _run_presim_ngspice(self) -> None:
        netlist.sch2tb(
            input_netlist=self.cfg["inputs.netlist_file"],
            testbench_path=self.cfg["inputs.tb_file"],
            output_netlist=self.cfg["ngspice.presim_file"],
            ckt_name=self.ckt_name,
            ckt_pins=self.cfg["design.pin_order"],
        )
        cabgen.ngspice_simulation(
            netlist_path=self.cfg["ngspice.presim_file"],
            working_dir=self.cfg["ngspice.work_dir"],
        )
        cabgen.move_spec_files(
            src=self.cfg["ngspice.work_dir"],
            dst=self.cfg["results.work_dir"],
            specs=self.specs,
            step="pre",
        )

    def _run_layout_align(self) -> None:
        pdk_dir_key = f"align.{self.pdk_lower}_dir"
        cabgen.align_layout(
            input_path=self.cfg["align.input_dir"],
            pdk_path=self.cfg[pdk_dir_key],
            output_path=self.cfg["align.output_dir"],
            ckt_name=self.ckt_name,
            verbose=self.verbose,
        )

        gds_path = self.cfg.get_path("align.gds_file")
        if gds_path.exists() and not self.verbose:
            print(f"Use KLayout to visualize the generated GDS: {gds_path}")
        elif not gds_path.exists():
            raise RuntimeError(f"Expected GDS not found after ALIGN: {gds_path}")
        
    def _run_drc_klayout(self) -> None:
        if not self.cfg.get_path(self.gds_key).exists():
            raise FileNotFoundError(f"GDS file for DRC not found at {self.cfg.get_path(self.gds_key)}")
        drc_key = f"klayout.{self.pdk_lower}_lydrc"
        cabgen.klayout_drc(
            drc_path=self.cfg[drc_key],
            gds_path=self.cfg[self.gds_key],
            working_dir=self.cfg["klayout.work_dir"],
        )

    def _run_extract_magic(self) -> None:
        if not self.cfg.get_path(self.gds_key).exists():
            raise FileNotFoundError(f"GDS file for extraction not found at {self.cfg.get_path(self.gds_key)}")
        cabgen.magic_extract(
            tcl_path=self.cfg["magic.ext_tcl_file"],
            working_dir=self.cfg["magic.work_dir"],
        )
    
    def _run_lvs_netgen(self) -> None:
        if not self.cfg.get_path("netgen.layout_spice_file").exists():
            raise FileNotFoundError(f"Layout SPICE file for LVS not found at {self.cfg.get_path('netgen.layout_spice_file')}")
        if not self.cfg.get_path("netgen.schematic_spice_file").exists():
            # Convert ALIGN SPICE → netgen-compatible schematic netlist if layout tool is ALIGN
            if self.steps.get("layout") == "ALIGN":
                align_netlist = self.cfg.get_path("align.input_dir") / f"{self.ckt_name}.sp"
                netlist.align2netgen(
                    input_netlist=align_netlist,
                    output_netlist=self.cfg["netgen.schematic_spice_file"],
                    ckt_name=self.ckt_name,
                )
            else:
                raise ValueError(f"Unsupported LVS netlist source for layout tool: {self.steps.get('layout')}")

        setup_key = f"netgen.{self.pdk_lower}_setup_tcl"
        cabgen.netgen_lvs(
            lvs_path=self.cfg["netgen.layout_spice_file"],
            top_module=self.top_module,
            spice_path=self.cfg["netgen.schematic_spice_file"],
            ckt_name=self.ckt_name,
            setup_path=self.cfg[setup_key],
            working_dir=self.cfg["netgen.work_dir"],
        )

    def _run_postsim_ngspice(self) -> None:
        pex_netlist = self.cfg.get_path("magic.work_dir") / f"{self.top_module}_pex.spice"
        netlist.pex2tb(
            input_netlist=pex_netlist,
            testbench_path=self.cfg["inputs.tb_file"],
            output_netlist=self.cfg["ngspice.postsim_file"],
            top_module=self.top_module,
            ckt_name=self.ckt_name,
            ckt_pins=self.cfg["design.pin_order"],
        )
        cabgen.ngspice_simulation(
            netlist_path=self.cfg["ngspice.postsim_file"],
            working_dir=self.cfg["ngspice.work_dir"],
        )
        cabgen.move_spec_files(
            src=self.cfg["ngspice.work_dir"],
            dst=self.cfg["results.work_dir"],
            specs=self.specs,
            step="post",
        )