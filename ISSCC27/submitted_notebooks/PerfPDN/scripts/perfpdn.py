"""One command for a configured circuit, candidate study or saved plots."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from perfpdn.project import load
from perfpdn.workflow import run

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("action",choices=("run","analyze","plot","check"))
parser.add_argument("input",type=Path,help="Project JSON, or a saved study directory for plot")
parser.add_argument("--output",type=Path)
parser.add_argument("--resume",action="store_true",help="Continue an unchanged saved baseline at --output")
parser.add_argument("--verify-all",action="store_true",help="Measure every refined candidate, including predicted constraint failures and negative benefits")
args=parser.parse_args()
if args.verify_all and args.action!="run":parser.error("--verify-all applies to run.")
if args.resume and not args.output:parser.error("--resume requires --output pointing to a baseline-only analysis.")
if args.action=="plot":
    from perfpdn.plots import plot
    plot(args.input)
else:
    project=load(args.input)
    if args.action=="check":
        from datetime import datetime,timezone
        from perfpdn.design import read_design,verify
        folder=args.output or ROOT/"output"/project["name"]/"checks"/datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        folder=folder.resolve()
        folder.mkdir(parents=True)
        read_design(project,folder/"input")
        verify(project,project["layout"],folder/"verification",folder/"input/reference.spice")
        print("DRC/LVS passed:",folder)
    else:
        run(project,args.output,baseline_only=args.action=="analyze",resume=args.resume,verify_all=args.verify_all)
