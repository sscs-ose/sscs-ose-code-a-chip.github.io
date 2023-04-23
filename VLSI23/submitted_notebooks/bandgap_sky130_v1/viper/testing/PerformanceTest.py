"""
A circuit performance test
"""

from importlib import resources
import toml
from pathlib import Path
from typing import Optional
from viper.typing import PathLike
from viper.simulators.TestSimulator import TestSimulator
from viper.simulators.SimResult import SimResult

class PerformanceTest:

    def __init__(self, name: str, dirpath: PathLike, 
                 schematic_filepath: Optional[PathLike] = None) -> None:
        self.name = name
        self.dirpath = Path(dirpath)
        if schematic_filepath is not None:
            self.schematic_filepath = Path(schematic_filepath)
        else:
            self.schematic_filepath = None
    
    @property
    def sim_result(self) -> SimResult:
        test_simulator = TestSimulator(
            schematic_filepath=self.schematic_filepath,
            test_dirpath=self.dirpath,
            )
        simulator = test_simulator.simulator
        return simulator.result()

    @classmethod
    def read_directory(cls, dirpath: PathLike) -> "PerformanceTest":
        for test_file_path in Path(dirpath).iterdir():
            if cls.is_toml_config_file(test_file_path):
                return cls.read_toml_file(test_file_path)

    @staticmethod
    def is_toml_config_file(path: PathLike) -> bool:
        return path.is_file() and path.name.endswith(".test.toml")

    @classmethod
    def read_toml_file(cls, path: PathLike) -> "PerformanceTest":
        config = toml.load(str(path))
        config["dirpath"] = Path(path.parent)
        test = cls(
            name=config["name"],
            dirpath=config["dirpath"]
        )
        if "schematic_filepath" in config.keys():
            test.schematic_filepath = config["schematic_filepath"]
        return test

    @classmethod
    def read_package(cls, package: resources.Package) -> "PerformanceTest":
        with resources.files(package) as test_dirpath:
            return cls.read_directory(test_dirpath)
