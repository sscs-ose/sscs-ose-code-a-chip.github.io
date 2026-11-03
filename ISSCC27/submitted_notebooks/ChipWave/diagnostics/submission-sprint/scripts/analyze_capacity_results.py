"""Produce plot-ready tables from the complete planned roster without running models."""
import argparse
import json
from capacity_integration_physical import ROOT
from capacity_results import analyze
from study_protocol import write_json

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--category',choices=('pilot','formal'),default='formal')
    args=parser.parse_args()
    result=analyze(ROOT,args.category)
    write_json(ROOT/'analysis'/(args.category+'-results.json'),result)
    print(json.dumps({k:result[k] for k in ('category','planned','terminal','complete')}))
