from pathlib import Path
from typing import Union


class SimResult:
    def __init__(self, 
                 dirpath: Union[Path, str],
                 netlist_filepath: Union[Path, str], 
                 output_filename: Union[Path, str], 
                 raw_output_filename: str,
                 soa_log_filename: str,
                 sim_log_filename: str,
                 simulator: str,
                 ) -> None:
        self.dirpath = dirpath
        self.netlist_filepath = netlist_filepath
        self.output_filename = output_filename
        self.raw_output_filename = raw_output_filename
        self.soa_log_filename = soa_log_filename
        self.sim_log_filename = sim_log_filename
        self.simulator = simulator
    
    @property
    def raw_output_filepath(self) -> Path:
        return self.dirpath / self.raw_output_filename
    
    @property
    def output_filepath(self) -> Path:
        return self.dirpath / self.output_filename
    
    @property
    def soa_log_filepath(self) -> Path:
        return self.dirpath / self.soa_log_filename
    
    @property
    def sim_log_filepath(self) -> Path:
        return self.dirpath / self.sim_log_filename

    def __str__(self):
        return (
            f"Simulation Result Details:\n"
            f"  simulator: {self.simulator}\n"
            f"  directory path: {self.dirpath}\n"
            f"  output file: {self.output_filename}\n"
            f"  raw output file: {self.raw_output_filename}\n"
            f"  SOA log file: {self.soa_log_filename}\n"
            f"  sim log file: {self.sim_log_filename}\n"
            f"  netlist filepath: {self.netlist_filepath}\n"
            )
