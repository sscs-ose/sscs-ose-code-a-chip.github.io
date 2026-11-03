"""Check actual earlier evidence and an empty registered-cohort fixture without invented outcomes."""
import json
import re
import tempfile
from pathlib import Path

import nbformat

from build_capacity_manuscript import build
from capacity_integration_physical import ROOT
from capacity_protocol import protocol
from study_protocol import write_json


def check():
    with tempfile.TemporaryDirectory(prefix='capacity-manuscript-check-') as temporary:
        target=Path(temporary)/'ChipNebula_CPU.ipynb'
        source=Path(temporary)/'study';write_json(source/'protocol.json',protocol())
        try:build(source,target)
        except ValueError:pass
        else:raise AssertionError('Incomplete study presented as a final manuscript')
        assert not target.exists()
        book=build(source,target,draft=True);nbformat.validate(book)
        text='\n'.join(c.source for c in book.cells if c.cell_type=='markdown')
        assert text.count('# ChipNebula: A Configurable Platform for AI-Driven Chip Design and PPA Exploration')==1
        assert '**Working draft:**' in text and '0 of 84' in text
        assert '0 of nine sessions found Q < 1' in text
        assert text.index('Workloads that expose interactions') < text.index('Appendix: the earlier')
        assert 'All twelve' in text
        sections=[int(n) for n in re.findall(r'^## (\d+)\.',text,re.M)]
        assert sections==list(range(1,len(sections)+1))
        labels=[]
        for cell in book.cells:
            if cell.cell_type=='markdown' and re.search(r'!\[[^\]]*\]\(figures/',cell.source):
                figures=set(re.findall(r'Figure (\d+)\.',cell.source));assert len(figures)==1
                labels.append(int(figures.pop()))
        assert labels==list(range(1,len(labels)+1))
        assert book.metadata.chipnebula_submission.stage=='working_draft'
        assert any('results/capacity-study/analysis/formal-results.json' in c.source
                   for c in book.cells if c.cell_type=='code')
    result=dict(passed=True,model_calls=0,physical_runs=0,
        scope='Actual historical evidence and empty registered-cohort fixture; temporary notebook, not a submission or fresh archive execution',
        checks=['incomplete final export refused','one English title and explicit draft status',
                'earlier negative findings retained in separate appendix','sections and figures consistently numbered',
                'default new-study cell reads saved data without models or physical execution'])
    write_json(ROOT/'checks/manuscript-assembly.json',result)
    return result


if __name__=='__main__':print(json.dumps(check()))
