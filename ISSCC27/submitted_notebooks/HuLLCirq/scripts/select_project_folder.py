#!/usr/bin/env python3
"""Show a native chooser only after an explicit Browse action in the GUI."""
import argparse
import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial-directory")
    args = parser.parse_args()
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askdirectory(parent=root, title="HuLLCirq — Choose project folder", mustexist=True,
                                           initialdir=args.initial_directory or str(Path.home()))
    finally:
        root.destroy()
    result = {"status": "Completed", "directory": str(Path(selected).resolve())} if selected else {"status": "Cancelled", "directory": None}
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
