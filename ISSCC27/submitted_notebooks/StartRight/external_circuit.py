"""Pinned upstream flip-flop bench, preserving the original circuit topology.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import re,math
from sequence_circuits import generate_sequence
from detector_design import scale_detector
HERE=Path(__file__).resolve().parent

def generate_original(config,scenario,contract,settings):
    text,points,windows=generate_sequence(config,scenario,contract,settings)
    remove=['XMPA1','XMPA2','XMPB1','XMPB2','XMNA1','XMNA2','XMNB1','XMNB2','XMOUT','RUSE','VSENSE','CA','CB','COUT','VCOMMAND','VSETN','RSETDRIVE']
    for name in remove:text=re.sub(r'(?m)^'+name+r' .*\n','',text)
    text=re.sub(r'(?m)^\.save .*\n','',text);text=re.sub(r'(?m)^wrdata .*\n','',text)
    upstream=HERE/'upstream';hvt=upstream/'skywater-pdk-libs-sky130_fd_pr/cells/pfet_01v8_hvt'
    includes=''.join(f'.include "{(hvt/name).as_posix()}"\n' for name in [f'sky130_fd_pr__pfet_01v8_hvt__{scenario["corner"]}.corner.spice','sky130_fd_pr__pfet_01v8_hvt__mismatch.corner.spice'])
    cell=upstream/'skywater-pdk-libs-sky130_fd_sc_hd/cells/dfrtp/sky130_fd_sc_hd__dfrtp_1.spice'
    text=text.replace('.temp ',includes+f'.include "{cell.as_posix()}"\n.temp ',1)
    start=points[3][0]+scenario['normal_set']['delay_after_first_observation_s'];end=start+scenario['normal_set']['duration_s'];edge=scenario['normal_set']['edge_s'];stop=points[-1][0];V=scenario['supply_V']
    dpoints=[[0.,0.],[stop,0.]] if scenario['normal_set'].get('skip_command') else [[0.,0.],[start,0.],[start+edge,V],[end,V],[end+edge,0.],[stop,0.]]
    clkpoints=[[0.,0.],[start+5e-6,0.],[start+5e-6+edge,V],[start+6e-6,V],[start+6e-6+edge,0.],[stop,0.]]
    pwl=lambda p:' '.join(f'{t:.17g} {v:.17g}' for t,v in p)
    circuit=f'''VCLK clkdrv 0 PWL({pwl(clkpoints)})
VDATA ddrv 0 PWL({pwl(dpoints)})
RCLK clkdrv clk 1k
RDATA ddrv d 1k
XDUT clk d c 0 0 vdd vdd q sky130_fd_sc_hd__dfrtp_1
CQ q 0 10f
'''
    vectors='v(q) v(c) v(vdd) i(VDD) v(clk) v(d) v(clkdrv) i(VCLK) v(ddrv) i(VDATA)'
    if config['variant']=='supply_sensitive':vectors+=' v(det) i(VDETECT)'
    text=text.replace('.control\n',circuit+'.save '+vectors+'\n.control\nset numdgt=17\n',1)
    text=text.replace('quit\n','wrdata sequence.dat '+vectors+'\nquit\n')
    return text,points,windows,dpoints,clkpoints


def generate(config, scenario, contract, settings, absolute_tolerances=None):
    text, points, windows, data_points, clock_points = generate_original(config, scenario, contract, settings)
    if absolute_tolerances is not None:
        if set(absolute_tolerances) != {'abstol_A', 'vntol_V'}:
            raise ValueError('Declare both absolute convergence tolerances')
        for key, option in [('abstol_A', 'abstol'), ('vntol_V', 'vntol')]:
            value = absolute_tolerances[key]
            if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
                raise ValueError('Positive finite absolute convergence tolerance required')
            text, count = re.subn(r'\b' + option + r'=\S+', f'{option}={value:.17g}', text)
            if count != 1:
                raise ValueError('Expected one declared ' + option + ' option')
    if 'detector_scale' in config:
        if config['variant']!='supply_sensitive':raise ValueError('Scaling applies only to the sensing branch')
        text=scale_detector(text,config['detector_scale'])
    return text, points, windows, data_points, clock_points
