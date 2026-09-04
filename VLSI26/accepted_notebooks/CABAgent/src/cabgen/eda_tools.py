import shlex
import logging
import subprocess
import xml.etree.ElementTree as ET

from pathlib import Path

from src.cabgen.log_manager import setup_logger


# ---- simulation using Ngspice ---- #
def ngspice_simulation(
    netlist_path: str | Path,
    working_dir: str | Path,
    logger: logging.Logger | None = None,
) -> None:
    log = logger or logging.getLogger("eda_pipeline")
    ngspice_log = setup_logger("ngspice")

    netlist_path = Path(netlist_path)
    working_dir = Path(working_dir)

    cmd = [
        "ngspice",
        "-b",  # batch mod
        str(netlist_path),
    ]
    cmd_str = " ".join(shlex.quote(x) for x in cmd)
    log.info("%s", cmd_str, extra={"stage": "NGSPICE"})

    proc = subprocess.Popen(
        cmd,
        cwd=str(working_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    out, err = proc.communicate()

    # Log ngspice output to logs/ngspice.log via ngspice_log
    if out:
        ngspice_log.info("%s", out)

    # only fail on real fatal messages (ignore warnings)
    fatal = err and any(
        k in err.lower()
        for k in ["fatal:", "fatal error", "run simulation(s) aborted", "doanalyses:", "no such parameter on this device"]
    )

    if fatal:
        ngspice_log.error(
            "Simulation Failed! Fatal ngspice error detected (returncode=%d). %s",
            proc.returncode,
            err,
            extra={"stage": "NGSPICE"},
        )
        log.error("Simulation Failed! Please check logs/ngspice.log for details.", extra={"stage": "NGSPICE"})
        raise subprocess.CalledProcessError(
            proc.returncode,
            cmd,
            output=out,
            stderr=err,
        )
    
    log.info("Simulation Finished! Please check logs/ngspice.log for details.", extra={"stage": "NGSPICE"})


# ---- layout generation using ALIGN ---- #
def align_layout(
    input_path: str | Path, 
    pdk_path: str | Path,
    output_path: str | Path,
    ckt_name: str,
    verbose: bool                   = True,
    logger: logging.Logger | None   = None,
) -> None:
    log = logger or logging.getLogger("eda_pipeline")

    cmd = [
        "schematic2layout.py",
        input_path,
        "-p", pdk_path,
        "-w", output_path,
        "-s", ckt_name,
    ]
    cmd_str = " ".join(shlex.quote(x) for x in cmd)
    log.info("%s", cmd_str, extra={"stage": "ALIGN"})

    if verbose:
        stdout_target = None
        stderr_target = None
        log_msg = "Layout Generation Finished!"
    else:
        stdout_target = subprocess.DEVNULL  # discard
        stderr_target = subprocess.DEVNULL
        log_msg = "Layout Generation Finished! Please check logs/align.log for details."

    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=stdout_target,
            stderr=stderr_target,
        )
        log.info(log_msg, extra={"stage": "ALIGN"})
    except subprocess.CalledProcessError as e:
        log.error("Layout Generation Failed! Please check logs/align.log for details.", extra={"stage": "ALIGN"})
        raise e


# ---- check drc using KLayout ---- #
def _drc_errors(
    xml_path: str | Path,
) -> tuple[bool, int]:
    """ Check if the DRC report has errors.
    Args:
        xml_path (str | Path): Path to the DRC report XML file.
    Returns:
        tuple[bool, int]: (has_error, error_count)
    
    If <items> is present but empty → (False, 0).
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    items = root.find("items")
    if items is None:
        # Some reports might omit <items> entirely when clean
        return (False, 0)
    # In KLayout DRC XML, each violation is an <item> element under <items>
    count = sum(1 for _ in items.findall("item"))
    return (count > 0, count)

def klayout_drc(
    drc_path: str | Path,
    gds_path: str | Path,
    working_dir: str | Path,
    logger: logging.Logger | None   = None,
) -> None:
    log = logger or logging.getLogger("eda_pipeline")
    klayout_log = setup_logger("klayout")

    output_path = Path(working_dir) / "drc_report.xml"
    cmd = [
        "klayout",
        "-b",  # batch mode
        "-r", str(drc_path),  # DRC rule file
        "-rd", f"input={gds_path}",  # input GDS file
        "-rd", f"report={output_path}",  # output report file
    ]
    cmd_str = " ".join(shlex.quote(x) for x in cmd)
    log.info("%s", cmd_str, extra={"stage": "KLAYOUT"})

    proc = subprocess.Popen(
        cmd,
        cwd=working_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,  # to get string output instead of bytes
    )
    out, err = proc.communicate()

    if err != '':
        log.error("Compiling Failed! \nError Message: %s", err, extra={"stage": "KLAYOUT"})
        klayout_log.error("KLAYOUT: Compiling Failed! \nRunning Output: \n%s \nError Message: %s", out, err)
        raise RuntimeError(f"KLayout DRC Failed! {err}")
    else:
        log.info("DRC Finished! Please check %s/drc_report.xml or logs/klayout.log for results.", working_dir, extra={"stage": "KLAYOUT"})
        klayout_log.info("KLAYOUT: DRC Finished! \n%s", out)

    if output_path.exists():
        has_error, n_error = _drc_errors(output_path)
        if has_error:
            msg = f"{n_error} Errors found"
        else:
            msg = "No errors"
        log.info("DRC Report: %s", msg, extra={"stage": "KLAYOUT"})
        klayout_log.info("KLAYOUT: DRC Report: %s", msg)
    else:
        log.error("DRC report file not found at %s", output_path, extra={"stage": "KLAYOUT"})
        klayout_log.error("KLAYOUT: DRC report file not found at %s", output_path)
        raise FileNotFoundError(f"DRC report file not found at {output_path}")


# ---- extraction using Magic ---- #
def magic_extract(
    tcl_path: str | Path,
    working_dir: str | Path,
    verbose: bool                   = False,
    make_clean: bool                = True,
    logger: logging.Logger | None   = None,
) -> None:
    log = logger or logging.getLogger("eda_pipeline")
    magic_log = setup_logger("magic")

    cmd = [
        "magic",
        "-dnull",
        "-noconsole",
        tcl_path,
    ]
    cmd_str = " ".join(shlex.quote(x) for x in cmd)
    log.info("%s", cmd_str, extra={"stage": "MAGIC"})

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        out, err = proc.communicate(timeout=5)
        log.info("Extraction Finished! Please check logs/magic.log for details.", extra={"stage": "MAGIC"})
        if verbose:
            magic_log.info("MAGIC: Extraction Output: %s \nPotential Error: \n%s", out, err)
        else:
            magic_log.info("MAGIC: Extraction Finished! %s", out)
    except subprocess.TimeoutExpired as e:
        proc.kill()
        out, err = proc.communicate()
        log.error("Extraction Timed Out! \nError Message: %s", err, extra={"stage": "MAGIC"})
        magic_log.error("MAGIC: Extraction Timed Out! \nRunning Output: %s \nError Message: \n%s", out, err)
        raise e
    
    if make_clean:
        try:
            patterns = ["*.ext", "*.sim", "*.nodes"]
            for pattern in patterns:
                for f in Path(working_dir).glob(pattern):
                    f.unlink()
            log.info("Temporary files (.ext, .sim, .nodes) cleaned.", extra={"stage": "MAGIC"})
        except Exception as e:
            log.warning("Failed to clean temporary files: %s", e, extra={"stage": "MAGIC"})


# ---- check lvs using Netgen ---- #
def netgen_lvs(
    lvs_path: str | Path,
    top_module: str,
    spice_path: str | Path,
    ckt_name: str,
    setup_path: str | Path,
    working_dir: str | Path,
    logger: logging.Logger | None   = None,
) -> None:
    log = logger or logging.getLogger("eda_pipeline")
    netgen_log = setup_logger("netgen")

    cmd = [
        "netgen",
        "-batch",
        "lvs",
        lvs_path + " " + top_module,
        spice_path + " " + ckt_name,
        setup_path,
    ]
    cmd_str = " ".join(shlex.quote(x) for x in cmd)
    log.info("%s", cmd_str, extra={"stage": "NETGEN"})

    proc = subprocess.Popen(
        cmd,
        cwd=working_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    out, err = proc.communicate()

    if err != '':
        log.error("Compiling Failed! \nError Message: %s", err, extra={"stage": "NETGEN"})
        netgen_log.error("NETGEN: Compiling Failed! \nRunning Output: \n%s \nError Message: %s", out, err)
        raise RuntimeError(f"Netgen LVS Failed! {err}")
    elif "Circuits match uniquely." not in out:
        log.error("LVS Failed! Please check %s/comp.out or logs/netgen.log for details.", working_dir, extra={"stage": "NETGEN"})
        netgen_log.error("NETGEN: LVS Failed! \n%s", out)
        raise RuntimeError("Netgen LVS failed!")
    elif "Property errors were found." in out:
        log.info("LVS done with property errors! Please check %s/comp.out or logs/netgen.log for results.", working_dir, extra={"stage": "NETGEN"})
        netgen_log.info("NETGEN: LVS done with property errors! \n%s", out)
    else:
        log.info("LVS Finished! Please check %s/comp.out or logs/netgen.log for results.", working_dir, extra={"stage": "NETGEN"})
        netgen_log.info("NETGEN: LVS Finished! \n%s", out)
