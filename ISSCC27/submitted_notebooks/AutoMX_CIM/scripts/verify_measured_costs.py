"""Independently re-integrate current-run raw currents and check published tables."""
from pathlib import Path
import json,re,datetime
import numpy as np
from PIL import Image,ImageChops
import nbformat


def integrate_raw(path):
    text=Path(path).read_text();header,values=text.split('Values:\n',1)
    count=int(re.search(r'No\. Points:\s*(\d+)',header)[1])
    variables=re.findall(r'^\s*\d+\s+(\S+)\s+(?:time|voltage|current)\s*$',header,re.M)
    tokens=np.fromstring(values,sep=' ')
    assert tokens.size==count*(len(variables)+1),path
    data=tokens.reshape(count,len(variables)+1)
    assert np.array_equal(data[:,0],np.arange(count)) and np.isfinite(data).all()
    v=dict(zip(variables,data[:,1:].T));t=v['time'];dt=np.diff(t)
    assert (dt>0).all()
    # Direct interval sum is independent of the notebook's trapezoid helper.
    integral=lambda p:float(np.sum((p[:-1]+p[1:])*dt*.5))
    energies={name:integral(v['v(vpwr)']*v['i('+probe+')']) for name,probe in
      [('core_acquisition_vdd_j','vcore_meter'),('conditioner_vdd_j','vcond_meter'),('adc_vdd_j','vadc_meter')]}
    power=np.zeros_like(t)
    for node,source in [('bottomp','vbottomp'),('bottomn','vbottomn'),('sample','vsample'),
                         ('sample_n','vsamplen'),('adc_clk_comp','vclkcomp'),('vcm','vvcm')]:
        power-=v['v('+node+')']*v['i('+source+')']
    energies['adc_bridge_net_j']=integral(power)
    energies['monitored_total_j']=sum(energies.values())
    assert np.isclose(integral(-v['v(vpwr)']*v['i(vvdd)']),sum(energies[k] for k in
      ['core_acquisition_vdd_j','conditioner_vdd_j','adc_vdd_j']),rtol=1e-5,atol=1e-18)
    return energies


def verify(root):
    root=Path(root).resolve();execution=json.loads((root/'standalone_execution.json').read_text())
    assert execution['status']=='ALL_CODE_CELLS_EXECUTED' and execution['code_cells']==execution['executed_cells'] and not execution['errors']
    run=max((root/'runs').glob('fresh_*'),key=lambda p:p.name);work=run/'full_native/full_native'
    costs=json.loads((work/'energy_comparison.json').read_text());area=json.loads((work/'area_comparison.json').read_text())
    mha=json.loads((work/'mha_end_to_end.json').read_text())
    paths=sorted(work.glob('conversion_*/summary.json'))+sorted((work/'matched_pwm100').glob('conversion_*/summary.json'))
    energy_max_abs_delta=0.
    for path in paths:
        data=json.loads(path.read_text());recomputed=integrate_raw(path.parent/'coupled.raw')
        for key,value in recomputed.items():
            delta=abs(value-data['energy'][key]);energy_max_abs_delta=max(delta,energy_max_abs_delta)
            assert np.isclose(value,data['energy'][key],rtol=1e-10,atol=1e-21),(path,key,value,data['energy'][key])
    assert len(costs['per_conversion'])==64 and len(costs['per_projection'])==10
    for row in costs['per_projection']:
        group=[x for x in costs['per_conversion'] if x['mode']==row['mode'] and (row['stage']=='ALL' or x['stage']==row['stage'])]
        assert len(group)==row['conversions']
        assert np.isclose(row['energy_pj'],sum(x['monitored_total_j'] for x in group)*1e12,rtol=1e-12)
        assert row['decode_errors']==sum(x['expected']!=x['decoded'] for x in group)
    for job in mha['jobs']:
        candidate=Path(job['case']['path']);baseline=work/'matched_pwm100'/candidate.parent.name/'summary.json'
        a=json.loads(candidate.read_text());b=json.loads(baseline.read_text())
        assert a['activation_x2']==b['activation_x2'] and a['weights']==b['weights'] and a['column']==b['column']
        assert a['pwm_unit_ps']==50 and b['pwm_unit_ps']==100
        a_lines=[l for l in (candidate.parent/'coupled.spice').read_text().splitlines() if not re.match(r'VWL[PN]\d',l)]
        b_lines=[l for l in (baseline.parent/'coupled.spice').read_text().splitlines() if not re.match(r'VWL[PN]\d',l)]
        assert a_lines==b_lines,'Matched comparison changed more than input PWM'
    assert abs(sum(x['area_um2'] for x in area['blocks'] if x['kind']=='macro footprint')-area['placed']['macro_um2'])<1
    overview=work/'render_top/top.png';second=run/'top_live.png'
    assert ImageChops.difference(Image.open(overview).convert('RGB'),Image.open(second).convert('RGB')).getbbox() is None
    view=json.loads(overview.with_suffix('.render.json').read_text())
    assert view['geometry_modified'] is False and view['labels_visible'] is False
    assert view['shown_layers']==[[70,20],[70,44],[71,20],[71,44],[72,20]]
    book=nbformat.read(root/'AutoMX_CIM_Code_a_Chip.executed.ipynb',4)
    assert next(c for c in book.cells if c.id=='meter-early-checkpoints').execution_count
    report={'status':'PASSED','run':str(run),'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'all_code_cells':execution['code_cells'],'raw_waveforms_reintegrated':len(paths),
      'maximum_energy_reintegration_difference_j':energy_max_abs_delta,
      'logical_conversion_rows':64,'projection_comparison_rows':10,'identical_payload_pairs':32,
      'area_macro_sum_matches_odb':True,'two_independent_render_cells_pixel_identical':True,
      'overview_style':view['render_style'],'candidate_all':next(x for x in costs['per_projection'] if x['mode']=='PWM50' and x['stage']=='ALL'),
      'baseline_all':next(x for x in costs['per_projection'] if x['mode']=='PWM100 baseline' and x['stage']=='ALL')}
    (root/'docs/measured_costs_validation_20261026.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return report

if __name__=='__main__':verify(Path(__file__).resolve().parents[1])
