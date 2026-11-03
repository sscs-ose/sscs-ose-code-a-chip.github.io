"""Compatibility entry point: `python client.py <command>` == `python -m viaduct.cli <command>`."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from viaduct.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
