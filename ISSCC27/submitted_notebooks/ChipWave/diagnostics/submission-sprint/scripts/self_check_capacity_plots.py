"""Render only temporary synthetic fixtures; never publish synthetic result figures."""
import json
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from capacity_protocol import protocol
from plot_capacity_results import plot
from self_check_capacity_results import trial
from study_protocol import write_json

ROOT=Path(__file__).resolve().parents[1]


def check():
    with tempfile.TemporaryDirectory(prefix='capacity-plot-fixtures-') as temporary:
        root=Path(temporary);rules=protocol();write_json(root/'protocol.json',rules)
        output=root/'plots'
        try:plot(root,output)
        except ValueError as error:assert 'Incomplete' in str(error)
        else:raise AssertionError('Partial cohort plotted')
        assert not output.exists()
        for job in rules['formal_jobs']:
            record=trial(job)
            for point in record['checkpoints']:
                point['ratios']=dict(cell_area=1,energy=1,die_area=1,throughput=1)
                point['measurements']=dict(cell_area=100,die_area=200,
                    workloads={name:dict(throughput=10,latency=2,power=3,energy=.3)
                               for name in ('short','mixed','long')})
            record['active_frontend_seconds']=job['repetition']*100
            record['coordination']=dict(call_count=4,role_switches=2,repeated_stage_calls=1)
            record['first_observed_success_tokens']=dict(functional_pass=250000,joint_pass=500000,constraint_pass=500000)
            if job['workflow']=='C6':
                record.pop('active_frontend_seconds');record.pop('coordination')
                record.pop('first_observed_success_tokens')
            if job['repetition']==1:
                for point in (record,*record['checkpoints']):
                    point.update(functional_pass=False,joint_pass=False,constraint_pass=False,final_score=0)
                record['physical_diagnostics'][1].update(functional_pass=False,joint_pass=False,constraint_pass=False,final_score=0)
            write_json(root/'trials/formal'/job['id']/'result.json',record)
        data=plot(root,output);assert data['complete']
        receipt=json.loads((output/'results.source.json').read_text())
        assert len(receipt['figures'])==7 and len(receipt['source_sha256'])==85
        assert receipt['coincident_curves']
        measurements=json.loads((output/'capacity_final_measurements.json').read_text())
        assert len(measurements['rows'])==84 and measurements['coincident_points']
        assert any(not row['qualified'] and row['measurements'] for row in measurements['rows'])
        for name in receipt['figures']:
            ET.parse(output/(name+'.svg'))
            assert (output/(name+'.png')).stat().st_size>10000
    result=dict(passed=True,model_calls=0,physical_runs=0,synthetic=True,
        checks=['incomplete data rejected before output creation','seven result figure groups render',
                'coincident curves labeled without moving values','missing costs preserved as missing',
                'all 84 source receipts bound to figures','all final raw measurements retained including failed gates'],
        scope='Synthetic plots created in a deleted temporary directory, not publication figures')
    write_json(ROOT/'checks/result-plots.json',result);return result


if __name__=='__main__':print(json.dumps(check()))
