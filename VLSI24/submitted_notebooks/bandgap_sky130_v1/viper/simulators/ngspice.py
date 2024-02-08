from typing import Union
from pathlib import Path
import subprocess
from viper.simulators.SimResult import SimResult


class NgSpice():
    def __init__(self, netlist_filepath: Path, 
                 result_dirpath: Union[Path, str]):
        self.netlist_filepath = netlist_filepath
        self.result_dirpath = Path(result_dirpath)

    def simulate(self) -> SimResult:
        """Simulate using ngspice"""
        print(f'Simulating {self.netlist_filepath.name} at \n'
              f'  {self.netlist_filepath}\n'
              f"  using ngspice")
        result = self.result()
        options = [
             f"-b"
             f"-o", str(result.output_filepath),
             f"-r", str(result.raw_output_filepath),
             f'--soa-log={result.soa_log_filepath}',
             ]
        command = ["ngspice"]
        command.extend(options)
        command.append(str(self.netlist_filepath))
        run_result=subprocess.run(command,
            capture_output=True, check=True)
        with open(result.sim_log_filepath, mode="w") as log:
                 log.write(str(run_result.stdout))
        print("  Simulation completed!")
        return result
    
    def result(self) -> SimResult:
        return SimResult(
            dirpath = self.result_dirpath,
            netlist_filepath = self.netlist_filepath,
            output_filename = self.output_filename,
            raw_output_filename = self.raw_output_filename,
            soa_log_filename = self.soa_log_filename,
            sim_log_filename = self.log_filename,
            simulator = "ngspice",
            )

    @property
    def output_filename(self) -> str:
        return str(self.netlist_filepath.stem) + ".out"

    @property
    def raw_output_filename(self) -> str:
        return str(self.netlist_filepath.stem) + ".raw"

    @property
    def soa_log_filename(self) -> str:
        return str(self.netlist_filepath.stem) + ".soa.log"
    
    @property
    def log_filename(self) -> str:
        return str(self.netlist_filepath.stem) + ".sim.log"