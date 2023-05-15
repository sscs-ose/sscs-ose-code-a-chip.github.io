"""
Copyright 2022 John William Kustin

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import sys
from charMOS import charMOS
import numpy as np
import argparse
import pdb

def parseArgs():
    parser = argparse.ArgumentParser(
        description='Characterize a 4-terminal MOSFET',
        fromfile_prefix_chars='@')
    parser.add_argument('nmosModelName',
                        help='name of the nmos model to characterize')
    parser.add_argument('pmosModelName', 
                        help='name of the nmos model to characterize')
    parser.add_argument('simulator', 
                        help='ngspice or spectre')
    parser.add_argument('--modelFilePath', dest='modelFilePath',
                        help='full path to sky130.lib.spice')
    parser.add_argument('corners', nargs='+',
                        help='corner(s) to simulate')

    return parser

def main():

    argsParser = parseArgs()    
    args = argsParser.parse_args()
    nmos = args.nmosModelName #  "sky130_fd_pr__nfet_01v8"
    pmos = args.pmosModelName #  "sky130_fd_pr__pfet_01v8_hvt"
    modelFilePath = args.modelFilePath
    simulator = args.simulator
    corners = args.corners

    if simulator == "ngspice":
        pass
    elif simulator == "spectre":
        pass
    else:
        AssertionError()

    assert type(corners) == list
    print(modelFilePath)

    # in microns
    mosWidthsN = [1, 2, 5]
    mosWidthsP = [2, 4, 10]
    mosLengthsN = [0.9, 1, 1.1]
    mosLengthsP = mosLengthsN

    # Beware,
    # More steps => More RAM usage.
    settings = {
        'simulator':    simulator,
        'mosWidthsNfet':    mosWidthsN,
        'mosLengthsNfet':   mosLengthsN,
        'mosWidthsPfet':    mosWidthsP,
        'mosLengthsPfet':   mosLengthsP,
        'modelFiles':   [modelFilePath],
        'modelN':   nmos,
        'modelP':   pmos,
        'simOptions':   "",
        'corners':  [corners],
        'subcktPath':   "",
        'datFileName':  "sky130.mos.dataNameFormat.dat",
        'vgsMax':   1.95, #  
        'vgsStep':  20e-3,
        'vdsMax':   1.95,
        'vdsStep':  20e-3,
        'vsbMax':   1.95,
        'vsbStep':  1,
        'numfing':  1,
        'temp': 300
    }

    c = charMOS(settings)

    # This function call finally generates the required database.
    c.genDB()

if __name__ == "__main__":
    main()

