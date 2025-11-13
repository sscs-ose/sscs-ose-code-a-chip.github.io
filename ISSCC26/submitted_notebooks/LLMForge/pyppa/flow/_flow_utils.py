# Adapted from the OpenROAD Flow Scripts - https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts
#!/usr/bin/env python3
import re
import gzip

def markDontUse(patterns: str, inputFile: str, outputFile: str, logFile):
    # Convert * wildcards to regex wildcards
    patternList = patterns.replace('*','.*').split()

    # Read input file
    print("Opening file for replace:", inputFile, file=logFile)
    if inputFile.endswith(".gz") or inputFile.endswith(".GZ"):
        f = gzip.open(inputFile, 'rt', encoding="utf-8")
    else:
        f = open(inputFile, encoding="utf-8")
    content = f.read().encode("ascii", "ignore").decode("ascii")
    f.close()

    # Pattern to match a cell header
    pattern = r"(^\s*cell\s*\(\s*([\"]*"+"[\"]*|[\"]*".join(patternList)+"[\"]*)\)\s*\{)"

    # print(pattern)
    replace = r"\1\n    dont_use : true;"
    content, count = re.subn(pattern, replace, content, 0, re.M)
    print("Marked", count, "cells as dont_use", file=logFile)


    # Yosys-abc throws an error if original_pin is found within the liberty file.
    # removing
    pattern = r"(.*original_pin.*)"
    replace = r"/* \1 */;"
    content, count = re.subn(pattern, replace, content)
    print("Commented", count, "lines containing \"original_pin\"", file=logFile)

    # Yosys, does not like properties that start with : !, without quotes
    pattern = r":\s+(!.*)\s+;"
    replace = r': "\1" ;'
    content, count = re.subn(pattern, replace, content)
    print("Replaced malformed functions", count, file=logFile)

    # Write output file
    print("Writing replaced file:", outputFile, file=logFile)
    f = open(outputFile, "w")
    f.write(content)
    f.close()