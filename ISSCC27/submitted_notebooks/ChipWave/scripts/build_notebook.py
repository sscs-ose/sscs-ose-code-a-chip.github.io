"""Build the single competition manuscript; HTML is exported from that notebook."""
import argparse
from pathlib import Path
from build_benchmark_notebook import build as build_manuscript

CASE=Path(__file__).resolve().parents[1]


def build(draft=False,source=None,output=None):
    return build_manuscript(source or CASE/'results/benchmark-study', output or CASE/'ChipWave.ipynb',draft=draft)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--draft',action='store_true')
    parser.add_argument('--source',type=Path,default=CASE/'results/benchmark-study')
    parser.add_argument('--output',type=Path,default=CASE/'ChipWave.ipynb')
    args=parser.parse_args();build(args.draft,args.source,args.output)
