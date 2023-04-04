import subprocess, shutil
from pathlib import Path
from viper.typing import PathLike, OptionalPathLike


class XschemSchematic:

    xschemrc_path = Path("/foss/pdks/sky130A/libs.tech/xschem/xschemrc")
    
    def __init__(self, path: PathLike, 
                 netlist_dirpath: PathLike) -> None:
        self.path = Path(path)
        self.name = self.path.stem
        self.netlist_filepath = Path(netlist_dirpath) / (self.name + ".spice")

    def netlist(self) -> str:
        """netlist an xschem schematic using the xschem binary.
           Ignores all the options in the xschem directory"""
        self.check_tool_is_available()
        
        print(
            f"Netlisting {str(self.path.name)}\n"
            f"  From schematic path: {self.path}\n"
            f"  To netlist file: {self.netlist_filepath.name}\n"
            f"  To netlist path: {self.netlist_filepath}")
        self._delete_previous_netlist_dir()
        self.netlist_filepath.parent.mkdir(775, parents = True)
        options = [
            "-q","-x",
            "-n", "-o", str(self.netlist_filepath.parent),
            "-l", str(self.netlisting_log_path),
            "--rcfile", str(self.xschemrc_path),
            ]
        command = ["xschem"]
        command.extend(options)
        command.append(str(self.path))
        subprocess.run(command, capture_output=True, check=True)
        self.check_netlist()
        with open(self.netlist_filepath) as netlist_file:
            netlist = netlist_file.read()
        print(f"  Netlisting complete!\n")
        return netlist

    def convert_top_to_lib(self, lib_filepath: OptionalPathLike) -> str:
        """
        Updates the top-level netlist to a spice lib file.  This includes
        both the top-level design as  subckt and all the containing subckts.
        If "lib_filepath" is specified, the netlist.lib file will be saved to
        the specified file path.
        Returns the lib netlist.
        """
        with open(self.netlist_filepath) as netlist_file:
            netlist = netlist_file.read()
        netlist = self._update_top_level_subckt(netlist)
        if lib_filepath is not None:
            with open(lib_filepath,"w") as lib_file:
                lib_file.write(netlist)
        # TODO: We might want to remove any control and ".global" commands
        return netlist
        
    @staticmethod
    def _update_top_level_subckt(netlist: str) -> str:
        netlist.replace("**.subckt", ".subckt")
        netlist.replace("**.ends", ".ends")
        return netlist
    
    def export_svg(path: PathLike, 
                   log_path: OptionalPathLike = None) -> None:
        #sch_picture_path = self.netlist_path.parent / \
        #                   (self.path.stem + ".svg")
        options = ["-q","--svg","--plotfile",str(path)]
        if log_path is not None:
            options = options.extend(["-l", str(log_path)])
        run_result=subprocess.run(["xschem"].extend(options), 
                                  capture_output=True, check=True)

    @staticmethod
    def tool_is_available() -> bool:
        run_result=subprocess.run(["xschem", "--version"],
                       capture_output=True, check=False)
        return run_result.returncode == 0

    @staticmethod
    def tool_version() -> bool:
        run_result=subprocess.run(["xschem", "--version"],
                       capture_output=True, check=False)
        return run_result.returncode == 0

    @classmethod
    def check_tool_is_available(cls) -> None:
        if not cls.tool_is_available():
            raise Exception(
                """Xschem is not available!\n
                   Please make sure  the xschem binary is on $PATH""")

    def check_netlist(self) -> None:
        if not self.netlist_filepath.is_file():
            raise RuntimeError(f"Testbench netlist does not exist at:\n"
                               f"  {str(self.netlist_filepath)}")
    
    @property
    def netlisting_log_path(self):
        return self.netlist_filepath.parent \
               / (self.netlist_filepath.parent.stem + ".netlisting.log")
    
    @property
    def path(self) -> Path:
        return self._path

    @path.setter
    def path(self, path: PathLike) -> None:
         self._path = path
         self._check_path()

    def _check_path(self) -> None:
         if not self._path.is_file():
            raise RuntimeError(f"Testbench schematic does not exist at:\n"
                               f"  {str(self._path)}")

    def _delete_previous_netlist_dir(self):
        shutil.rmtree(str(self.netlist_filepath.parent))