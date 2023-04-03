import subprocess, os
from pathlib import Path
from typing import Union, Optional
from ngspice_result import ngspice_result

optional_path = Optional[Union[Path, str]]


class xschem_testbench:
    #default_root_result_path = Path.home() / "sim_results"
    xschemrc_path = Path("/foss/pdks/sky130A/libs.tech/xschem/xschemrc")
    def __init__(self, name: str, schematic_path: Union[Path, str],
                 test_dirpath: Union[Path, str],
                 result_path: optional_path = None) -> None:
        self.name = name
        self.schematic_path = Path(schematic_path)
        self.test_dirpath = Path(test_dirpath)
        if result_path is not None:
            self.result_path = Path(result_path)
        else:
            self.result_path = self.test_dirpath
        netlist_filename = self.schematic_path.stem + ".spice"
        self.netlist_path = self.result_path / "netlist" / netlist_filename
        self.netlist_log_path = self.netlist_path.parent / ".netlisting.log"
        soa_log_filename = self.test_dirpath.stem + ".soa.log"
        self.soa_log_path = self.test_dirpath / soa_log_filename
        sim_log_filename = self.test_dirpath.stem + ".sim.log"
        self.sim_log_path = self.result_path / sim_log_filename

    def netlist(self):
        """netlist an xschem schematic."""
        print("\n\n"
            f"Netlisting schematic:\n"
            f"  FROM: {str(self.schematic_path)}\n"
            f"  TO: {self.netlist_path}\n\n")
        #self.netlist_path.parent.rmdir()
        self.netlist_path.parent.mkdir(parents=True,exist_ok=True)
        sch_picture_path = self.netlist_path.parent / \
                           (self.test_dirpath.stem + ".svg")
        run_result=subprocess.run(["xschem", "-q",
                        "-n", "-o", str(self.netlist_path.parent),
                        "--svg", "--plotfile", str(sch_picture_path),
                        "-l", str(self.netlist_log_path),
                        "--rcfile", str(self.xschemrc_path),
                        str(self.schematic_path)], 
                       capture_output=True, check=True)

    def simulate(self) -> ngspice_result:
        """Simulate using ngspice"""
        if not self.netlist_path.is_file():
            raise RuntimeError("Testbench netlist does not exist.")
        print(f'Simulating {self.netlist_path.name} at \n'
              f'  {self.netlist_path}')
        raw_output_path = f'{self.result_path/self.name}.raw'
        output_path = f'{self.result_path/self.name}.out'
        run_result=subprocess.run(
            ["ngspice", "-b",
             "-o", str(output_path),
             "-r", raw_output_path,
             f'--soa-log={self.soa_log_path}',
             str(self.netlist_path),
            ],
            capture_output=True, check=True)
        with open(self.sim_log_path,mode="w") as log:
                 log.write(str(run_result.stdout))
        return ngspice_result(self, output_path, raw_output_path)

    def run_schematic(self) -> ngspice_result:
        self.netlist()
        return self.simulate()

    @classmethod
    def run(cls, name: str, schematic_path: Union[Path, str],
            test_path: Union[Path, str]):
        "Netlists and then simulates a schematic"
        tb = cls(name, schematic_path, test_path)
        result = tb.run_schematic()
        result.print_summary()

    def _check_schematic_path(self) -> None:
         if not self._schematic_path.is_file():
            raise RuntimeError(f"Testbench schematic does not exist at:\n"
                               f"  {str(self._schematic_path)}")

    @property
    def schematic_path(self) -> Path:
        return self._schematic_path

    @schematic_path.setter
    def schematic_path(self,path: Union[Path, str]) -> None:
         self._schematic_path = path
         self._check_schematic_path()
