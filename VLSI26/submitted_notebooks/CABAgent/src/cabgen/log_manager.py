import sys
import logging

from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler


# ---- internal helpers ---- #
BLUE = "\033[34m"
RESET = "\033[0m"
class ColorFormatter(logging.Formatter):
    def format(self, record):
        # Apply blue color to levelname and stage
        record.levelname = f"{BLUE}{record.levelname}:{RESET}"
        if record.stage:
            record.stage = f"{BLUE}{record.stage}{RESET}"
        return super().format(record)
    
class EnsureStage(logging.Filter):
    """Guarantee record.stage exists; add colon+space only when present."""
    def filter(self, record):
        if not hasattr(record, "stage") or not record.stage:
            record.stage = ""          # no stage shown
        else:
            # normalize to "ALIGN: " style once
            if not record.stage.endswith(": "):
                record.stage = f"{record.stage}: "
        return True
    
def _reset_logger(
    logger: logging.Logger
) -> None:
    """Remove all handlers and stop propagation."""
    logger.propagate = False
    for h in list(logger.handlers):
        logger.removeHandler(h)

def _append_run_header(
    log_path: Path
) -> None:
    """Append a 'New run' header to the log file."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    rollover = log_path.exists() and log_path.stat().st_size > 0
    header = f" New run at {datetime.now():%Y-%m-%d %H:%M:%S} "
    with log_path.open("a", encoding="utf-8") as f:
        if rollover:
            f.write("\n" + header.center(70, "-") + "\n")
        else:
            f.write(header.center(70, "-") + "\n")

def _add_rotating_file_handler(
    logger: logging.Logger,
    log_path: Path,
    level: int,
    max_bytes: int,
    backup_count: int,
) -> None:
    """Add a rotating file handler to the logger."""
    stage_filter = EnsureStage()
    fh = RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backup_count)
    fh.setLevel(level)
    fh.addFilter(stage_filter)
    fmt_file = logging.Formatter("%(asctime)s [%(levelname)s] %(stage)s%(message)s", "%Y-%m-%d %H:%M:%S")
    fh.setFormatter(fmt_file)
    logger.addHandler(fh)


# ---- main function to setup logger ---- #
def setup_logger(
    log_name: str,       
    level: int          = logging.INFO,
    max_bytes: int      = 100_000_000,
    backup_count: int   = 3,
    console: bool       = False,
) -> logging.Logger:
    """
    Dedicated logger:
      - writes a 'New run' header every call
      - rotates ${log_name}.log
      - optional console output
    """
    log_path = Path("logs/"+log_name.lower()+".log")
    _append_run_header(log_path)

    logger = logging.getLogger(log_name)
    logger.setLevel(level)
    _reset_logger(logger)

    _add_rotating_file_handler(logger, log_path, level, max_bytes, backup_count)

    if console:
        ch = logging.StreamHandler(stream=sys.stdout)
        ch.setLevel(level)
        fmt_console = ColorFormatter("%(levelname)s %(stage)s%(message)s")
        ch.setFormatter(fmt_console)
        logger.addHandler(ch)

    return logger