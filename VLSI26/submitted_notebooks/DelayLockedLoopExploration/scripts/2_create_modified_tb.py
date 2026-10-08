#!/usr/bin/env python3
import re
import argparse
import os

ALLOWED_PARAMS = {
    "CLK_PERIOD",
    "CTRL_BITS",
    "INIT_CTRL",
    "DELAY_PS",
    "UPDATE_DIV_BITS",
    "RESET_DELAY_PS",
    "LOCK_COUNT_MAX",
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("--set", nargs="+", required=True)
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()

    # Parse key=value
    updates = {}
    for kv in args.set:
        k, v = kv.split("=")
        updates[k.strip()] = v.strip()

    # Read file
    with open(args.input_file, "r") as f:
        content = f.read()

    # Apply updates
    for param, value in updates.items():
        if param not in ALLOWED_PARAMS:
            print(f"[SKIP] {param}")
            continue

        pattern = rf"(localparam\s+{param}\s*=\s*)([^;]+)(;.*)"
        replacement = rf"\g<1>{value}\g<3>"

        content, count = re.subn(pattern, replacement, content)

        print(f"{param}: replaced {count} occurrence(s)")

    # Output file name
    if args.output:
        out_file = args.output
    else:
        base, ext = os.path.splitext(args.input_file)
        out_file = base + "_CREATED" + ext

    # Write file
    with open(out_file, "w") as f:
        f.write(content)

    print(f"[DONE] Created: {out_file}")


if __name__ == "__main__":
    main()