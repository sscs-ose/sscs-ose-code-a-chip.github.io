from pathlib import Path
from importlib.resources import Package, files

from viper.schematics.XschemSchematic import XschemSchematic
from viper.simulators.ngspice import NgSpice
from viper.typing import PathLike
from viper.simulators.SimResult import SimResult


class TestSimulator:

    def __init__(self, schematic_filepath: PathLike, 
                 test_dirpath: PathLike) -> None:
        self.schematic_filepath = schematic_filepath
        self.test_dirpath = test_dirpath

    def netlist(self) -> Path:
        self.schematic.netlist()
        return self.netlist_filepath

    def simulate(self) -> SimResult:
        return self.simulator.simulate()

    @property
    def simulator(self) -> NgSpice:
        return NgSpice(netlist_filepath=self.netlist_filepath,
                       result_dirpath=self.result_dirpath)
    
    @classmethod
    def run(cls, schematic_filepath: PathLike, 
            test_dirpath: PathLike) -> SimResult:
        runner = cls(schematic_filepath, test_dirpath)
        runner.netlist()
        result = runner.simulate()
        return result

    def run_package_tests(cls, schematic_filepath: PathLike, 
                          package: Package):
        with files(package) as package_files:
            for file in package_files:
                if file.isdir():
                    cls.run(schematic_filepath=schematic_filepath,
                            test_dirpath=file)

    @property
    def netlist_dirpath(self) -> Path:
        return self.test_dirpath / "netlist"
    
    @property
    def result_dirpath(self) -> Path:
        return self.test_dirpath / "simulation"

    @property
    def schematic(self):
        return XschemSchematic(
            path=self.schematic_filepath,
            netlist_dirpath=self.netlist_dirpath
            )
    
    @property
    def netlist_filepath(self) -> Path:
        return self.schematic.netlist_filepath
