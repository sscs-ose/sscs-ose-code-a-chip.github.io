#!/usr/bin/env python3
import os
import re
import sys
import argparse  # argument parsing

# Parse and validate arguments
# ==============================================================================
parser = argparse.ArgumentParser(
    description="Inserts DUMMY based on a macro into a lef"
)
parser.add_argument("--refMacro", "-r", required=True, help="Reference Macro")
parser.add_argument("--inputLef", "-i", required=True, help="Input Lef")
parser.add_argument("--outputLef", "-o", required=True, help="Output Lef")
args = parser.parse_args()


if not os.path.isfile(args.inputLef):
    print(f"Error: Input LEF not found: {args.inputLef}", file=sys.stderr)
    sys.exit(1)

with open(args.inputLef) as f:
    content = f.read()

# refMacro = "BUFH_X1M_A12TR"

pattern = r"MACRO (" + args.refMacro + ")(.*?)END (" + args.refMacro + ")"
replace = r"MACRO \1\2END \3\nMACRO DUMMY\2END DUMMY"

result, count = re.subn(pattern, replace, content, 1, re.S)

if count > 0:
    with open(args.outputLef, "w") as f:
        f.write(result)
else:
    print("Error: Pattern not found", file=sys.stderr)
    sys.exit(1)
