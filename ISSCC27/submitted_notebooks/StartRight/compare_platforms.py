"""Compare saved Windows and Linux reproduction records. No SPICE is rerun."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
RESULTS=HERE/'results/reproduction'


def compare():
    linux=json.loads((RESULTS/'linux_short_run.json').read_text())
    windows=json.loads((RESULTS/'reuse_short_run.json').read_text())
    ls=json.loads((RESULTS/'linux_portability.json').read_text())
    ws=json.loads((RESULTS/'windows_portability.json').read_text())
    assert all(r['status']=='passed' for r in [linux,windows,ls,ws])
    for name,digest in ls['numeric_source_hashes'].items():
        assert digest==ws['numeric_source_hashes'][name]==hashlib.sha256((HERE/name).read_bytes()).hexdigest(),name
    signature=lambda r:(r['circuit'],r['parameters']['startup_width_um'],r['parameters']['gmin_S'],r['parameters']['load_resistance_ohm'],r['parameters']['ramp_s'])
    assert len(linux['runs'])==len(windows['runs'])==5
    assert {signature(r) for r in linux['runs']}=={signature(r) for r in windows['runs']}
    cases=[]
    for left in linux['runs']:
        right=next(r for r in windows['runs'] if signature(r)==signature(left))
        assert left['startup_verdict']==right['startup_verdict']
        assert len(left['candidate_operating_points'])==len(right['candidate_operating_points'])
        error=max(abs(a['intact_b_V']-b['intact_b_V']) for a,b in zip(left['candidate_operating_points'],right['candidate_operating_points']))
        current=abs(left['loaded_test']['nominal_target_A']/right['loaded_test']['nominal_target_A']-1)
        assert error<1e-5 and current<.001,(error,current)
        cases.append({'circuit':left['circuit'],'parameters':left['parameters'],'verdict':left['startup_verdict'],'root_count':len(left['candidate_operating_points']),'max_intact_bias_difference_V':error,'target_current_relative_difference':current})
    sizes=[]
    assert len(ls['sizing_cases'])==len(ws['sizing_cases'])==2
    for left in ls['sizing_cases']:
        right=next(r for r in ws['sizing_cases'] if r['width_um']==left['width_um'])
        for setting in ['ramp_s','load_resistance_ohm','maximum_step_s','reltol','target_output_A','deadline_s','hold_s']:
            assert abs(left[setting]/right[setting]-1)<1e-6,setting
        assert left['meets_contract'] and right['meets_contract']
        energy=left['source_energy_to_ready_J']/right['source_energy_to_ready_J']-1
        ready=left['ready_time_s']/right['ready_time_s']-1
        assert abs(energy)<.01 and abs(ready)<.01,(energy,ready)
        sizes.append({'width_um':left['width_um'],'linux_energy_J':left['source_energy_to_ready_J'],'windows_energy_J':right['source_energy_to_ready_J'],'energy_relative_difference':energy,'ready_relative_difference':ready})
    result={'status':'passed','scope':'Saved-record comparison for an Alpine Linux QEMU/WHPX guest and Windows on the same computer. Linux uses source-built ngspice 47; Windows uses the official portable binary. This is cross-OS and cross-build evidence, not a second simulator, independent machine or Colab run.','linux_platform':linux['platform'],'linux_python':linux['python'],'linux_packages':ls['packages'],'comparison_limits':{'max_bias_difference_V':1e-5,'max_target_current_relative_difference':.001,'max_refined_time_or_energy_relative_difference':.01},'nominal_cases':cases,'matched_slow_ramp_energy':sizes,'linux_wider_startup_energy_increase_fraction':ls['larger_width_energy_increase_fraction'],'windows_wider_startup_energy_increase_fraction':ws['larger_width_energy_increase_fraction'],'numeric_source_hashes':ls['numeric_source_hashes']}
    (RESULTS/'cross_platform_comparison.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print('PASS: five circuit signatures and two working sizing cases agree within the declared limits.')
    return result

if __name__=='__main__':compare()
