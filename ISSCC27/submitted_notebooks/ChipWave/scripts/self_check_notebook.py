"""Publication checks reject invented gains and keep failed/censored searches visible."""
from pathlib import Path
import json
import tempfile
from unittest.mock import patch

from build_benchmark_notebook import ppa_findings,token_cell
from study_protocol import write_json
import plot_benchmark_results as plots


def run():
    assert 'in progress' in ppa_findings(dict(ppa_complete=False))
    empty=dict(ppa_complete=True,rows=[dict(terminal=True,candidates=[])])
    assert 'No new candidate qualifies' in ppa_findings(empty)
    candidate=dict(rank_eligible=True,score=.918,energy_ratio=1.02,area_ratio=.9,cell_area_um2=900,candidate_index=1)
    data=dict(ppa_complete=True,rows=[dict(terminal=True,candidates=[candidate])])
    text=ppa_findings(data)
    assert '-10.00%' in text and '+2.00%' in text and '-8.20%' in text
    candidate['rank_eligible']=False
    assert 'No new candidate qualifies' in ppa_findings(data)
    partial=dict(tokens=None,reported_tokens=dict(input_tokens=100,output_tokens=10),
                 token_coverage=dict(reported_model_sessions=1,budgeted_role_dispatches=2))
    assert token_cell(partial)=='≥100 / ≥10 (partial; 1/2 sessions)'
    assert token_cell(dict(tokens=None))=='Unavailable'
    with tempfile.TemporaryDirectory(prefix='chip-benchmark-publication-') as temp:
        root=Path(temp);rows=[]
        for flow in ('F0','F1','F2'):
            candidate=dict(candidate_index=1,rank_eligible=flow!='F1',score=.98,area_ratio=.98,energy_ratio=1.,
                           elapsed_search_seconds=60.,cell_area_um2=98.,failure_classes=[] if flow!='F1' else ['electrical'])
            rows.append(dict(job=dict(id=flow+'-1',workflow=flow,repetition=1),terminal=True,
                accepted_candidates=1,candidates=[candidate],total_seconds=65.,agent_seconds=None,
                tokens=None,reviews=0 if flow=='F0' else 1))
        write_json(root/'analysis.json',dict(rows=rows));write_json(root/'protocol.json',dict(synthetic=True))
        original=plots.save
        def inspect(fig,output,name):
            if name=='benchmark_search_efficiency':
                trace=next(line for line in fig.axes[0].lines if line.get_label()=='F1-1')
                assert list(trace.get_xdata())==[0,1] and list(trace.get_ydata())==[1,1]
                clock=next(line for line in fig.axes[1].lines if line.get_label()=='F1-1')
                assert list(clock.get_xdata())==[0,1.,65/60]
                text=' '.join(t.get_text() for t in fig.texts)
                assert 'F0-1 = F2-1' in text, 'Coincident data must be labeled, not moved'
            original(fig,output,name)
        with patch.object(plots,'save',inspect):plots.plot(root,root/'figures')
        receipt=json.loads((root/'figures/benchmark_measured_sources.json').read_text())
        assert receipt['qualified_points']==2 and receipt['unqualified_or_incomplete_slots']==1
        assert receipt['coincident_points'][0]['candidates']==['F0-1/1','F2-1/1']
    print('NOTEBOOK_TEXT_SELF_CHECK_PASS: area/energy signs, failed incumbent, missing costs and coincident data retained; model_calls=0 physical_calls=0')


if __name__=='__main__':run()
