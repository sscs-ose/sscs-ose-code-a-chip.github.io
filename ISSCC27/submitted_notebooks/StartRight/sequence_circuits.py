"""Declared schematic circuits for reset-sequence experiments.
SPDX-License-Identifier: Apache-2.0
Main passives are ideal; this module does not qualify a supervisor threshold.
"""
import re
import schematic_support as arch
from schematic_support import apply_contacts
from schematic_support import junctions

def generate_detector(config, scenario, contract, settings):
    text, stop = arch.deck(config, scenario, contract, **settings)
    if config['variant'] == 'rc':
        return text, stop
    if config['variant'] != 'supply_sensitive':
        raise ValueError('Unknown exploratory variant')
    resistor = config['detector_resistance_ohm']
    extra = f'''RDET vdd det {resistor:.17g}
XMNDET det det 0 0 sky130_fd_pr__nfet_01v8 w={config['detector_n_width_um']} l=2
XMPDET c det vdd vdd sky130_fd_pr__pfet_01v8 w={config['inverter_p_width_um']} l=.5
XMNDRV c det 0 0 sky130_fd_pr__nfet_01v8 w={config['inverter_n_width_um']} l=.5
CDET det 0 20f
'''
    extra = apply_contacts(junctions(extra), scenario['contacts'])
    text = re.sub(r'(?m)^RC c vdd .*\n', extra, text)
    text = re.sub(r'(?m)^(wrdata cold.dat .*|\.save .*)$', r'\1 v(det)', text)
    return text, stop

def history(scenario, contract):
    end = scenario['ramp_s'] + 1e-6
    first_stop = end + contract['observation_after_ramp_s']
    voltage = scenario['supply_V']
    points = [[0., 0.], [1e-6, 0.], [end, voltage], [first_stop, voltage]]
    windows = [dict(id='cold', start_s=0., ramp_end_s=end, stop_s=first_stop)]
    if 'recovery' in scenario:
        h = scenario['recovery']
        down = first_stop + h['fall_s']
        low_end = down + h['low_hold_s']
        rise_end = low_end + h['rise_s']
        stop = rise_end + contract['observation_after_ramp_s']
        points += [[down, h['low_V']], [low_end, h['low_V']], [rise_end, voltage], [stop, voltage]]
        windows.append(dict(id='recovery', start_s=low_end, ramp_end_s=rise_end, stop_s=stop))
    return points, windows

def generate_history(config, scenario, contract, settings, passive_mode='ideal'):
    # Reuse the pilot's unchanged device topology, then add history and branch instrumentation.
    text, _ = generate_detector(config, scenario, contract, settings)
    points, windows = history(scenario, contract)
    pwl = ' '.join(f'{t:.17g} {v:.17g}' for t, v in points)
    text = re.sub(r'(?m)^VDD vdd 0 PWL.*$', f'VDD vdd 0 PWL({pwl})', text)
    text = re.sub(r'(?m)^tran .*$', f"tran 1u {points[-1][0]:.17g} 0 {settings['max_step']:.17g}", text)
    if config['variant'] == 'supply_sensitive':
        text = text.replace('RDET vdd det ', 'VDETECT vdd det_supply 0\nRDET det_supply det ')
        text = re.sub(r'(?m)^RDET det_supply det .*$',
                      f"RDET det_supply det {config['detector_resistance_ohm']*scenario['resistor_scale']:.17g}", text)

        text = re.sub(r'(?m)^(wrdata cold.dat .*|\.save .*)$', r'\1 i(VDETECT)', text)
    if passive_mode == 'mim_and_poly':
        resistance = config['detector_resistance_ohm'] if config['variant']=='supply_sensitive' else config['resistance_ohm']
        replacements = arch.passive_elements(resistance*scenario['resistor_scale'],
                                                   config['capacitance_F']*scenario['capacitor_scale'])
        if config['variant']=='supply_sensitive':
            replacements = '\n'.join(re.sub(r'\bc\b','det',line).replace(' vdd ', ' det_supply ')
                         if line.startswith('XRP') else line for line in replacements.splitlines())+'\n'
            text = re.sub(r'(?m)^RDET .*\n', replacements, text)
        else:
            text = re.sub(r'(?m)^RC c vdd .*\n', replacements, text)
        text = re.sub(r'(?m)^CC c 0 .*\n', '', text)
        text = text.replace('.temp ', arch.passive.includes()+'.temp ', 1)
    elif passive_mode != 'ideal':
        raise ValueError('Unknown passive mode')
    return text, points, windows

def extended_history(s,c):
    points,windows=history(s,c)
    f=s.get('disturbance',s.get('normal_set'))
    if f is None:return points,windows
    first=points[3][0];e=s['recovery']
    down_start=first+f['gap_before_fall_s'];down_end=down_start+e['fall_s']
    low_end=down_end+e['low_hold_s'];rise_end=low_end+e['rise_s'];stop=rise_end+c['observation_after_ramp_s']
    points=points[:4]+[[down_start,s['supply_V']],[down_end,e['low_V']],
                       [low_end,e['low_V']],[rise_end,s['supply_V']],[stop,s['supply_V']]]
    windows=[windows[0],dict(id='recovery',start_s=low_end,ramp_end_s=rise_end,stop_s=stop)]
    return points,windows

def generate_sequence(config, s, c, settings):
    text, _, _ = generate_history(config, s, c, settings)
    if config.get('load') == 'nand_sr_latch':
        text = re.sub('(?m)^XM(?:PA|NA|PB|NB|RESET) .*\\n', '', text)
        core = 'XMPA1 a b vdd vdd sky130_fd_pr__pfet_01v8 w=1 l=1\nXMPA2 a vdd vdd vdd sky130_fd_pr__pfet_01v8 w=1 l=1\nXMNA1 a b na 0 sky130_fd_pr__nfet_01v8 w=.42 l=2\nXMNA2 na vdd 0 0 sky130_fd_pr__nfet_01v8 w=.42 l=2\nXMPB1 b a vdd vdd sky130_fd_pr__pfet_01v8 w=.42 l=2\nXMPB2 b c vdd vdd sky130_fd_pr__pfet_01v8 w=.42 l=2\nXMNB1 b a nb 0 sky130_fd_pr__nfet_01v8 w=.42 l=2\nXMNB2 nb c 0 0 sky130_fd_pr__nfet_01v8 w=.42 l=2\n'
        text = text.replace('.control\n', apply_contacts(junctions(core), s['contacts']) + '.control\n', 1)
    if config.get('reset_fingers', 1) > 1:
        count = config['reset_fingers']
        if config.get('load') == 'nand_sr_latch':
            raise ValueError('No injected reset PMOS on the NAND load')
        text = re.sub('(?m)^XMRESET .*\\n', '', text)
        fingers = ''.join((f'XMRESET{i} b c vdd vdd sky130_fd_pr__pfet_01v8 w={config['direct_width_um']} l=.5\n' for i in range(count)))
        text = text.replace('.control\n', apply_contacts(junctions(fingers), s['contacts']) + '.control\n', 1)
    if config.get('pn_diode_area_um2'):
        raise ValueError('Junction-diode development is outside this supported lesson interface')
    if config.get('discharge_mos'):
        diode = 'XMREARM c c vdd 0 sky130_fd_pr__nfet_01v8 w=2 l=.5\n'
        text = text.replace('.control\n', apply_contacts(junctions(diode), s['contacts']) + '.control\n', 1)
    points, windows = extended_history(s, c)
    pwl = ' '.join((f'{t:.17g} {v:.17g}' for t, v in points))
    text = re.sub('(?m)^VDD vdd 0 PWL.*$', f'VDD vdd 0 PWL({pwl})', text)
    text = re.sub('(?m)^tran .*$', f'tran 1u {points[-1][0]:.17g} 0 {settings['max_step']:.17g}', text)
    if 'disturbance' in s:
        f = s['disturbance']
        start = points[3][0] + f['delay_after_first_observation_s']
        end = start + f['duration_s']
        edge = 1e-09
        fixture = f'VFAULTCTL faultctl 0 PWL(0 0 {start:.17g} 0 {start + edge:.17g} 1 {end:.17g} 1 {end + edge:.17g} 0 {points[-1][0]:.17g} 0)\nBFAULT b 0 I=V(faultctl)*V(b)/{f['resistance_ohm']}\n'
        text = text.replace('.control\n', fixture + '.control\n', 1)
    if 'normal_set' in s:
        if config.get('load') != 'nand_sr_latch':
            raise ValueError('Normal set requires the declared SR latch')
        text = text.replace('XMPA2 a vdd vdd vdd', 'XMPA2 a setn vdd vdd')
        text = text.replace('XMNA2 na vdd 0 0', 'XMNA2 na setn 0 0')
        f = s['normal_set']
        start = points[3][0] + f['delay_after_first_observation_s']
        end = start + f['duration_s']
        edge = f.get('edge_s', 1e-09)
        command_points = [] if f.get('skip_command') else [[start, s['supply_V']], [start + edge, 0.0], [end, 0.0], [end + edge, s['supply_V']]]
        input_points = sorted(points + command_points)
        input_pwl = ' '.join((f'{t:.17g} {v:.17g}' for t, v in input_points))
        command = f'VCOMMAND command 0 PWL(0 1 {start:.17g} 1 {start + edge:.17g} 0 {end:.17g} 0 {end + edge:.17g} 1 {points[-1][0]:.17g} 1)\nVSETN setn 0 PWL({input_pwl})\n'
        if f.get('skip_command'):
            command = re.sub('(?m)^VCOMMAND .*$', 'VCOMMAND command 0 1', command)
        if config.get('input_driver_ohm'):
            command = command.replace('VSETN setn 0', 'VSETN setdrv 0') + f'RSETDRIVE setdrv setn {config['input_driver_ohm']}\n'
        text = text.replace('.control\n', command + '.control\n', 1)
        text = text.replace('.save ', '.save v(setn) v(command) ', 1)
        text = text.replace('quit\n', 'wrdata interface.dat v(vdd) v(setn) v(c) v(a) v(b)\nquit\n')
        if config.get('include_input_power'):
            node = 'setdrv' if config.get('input_driver_ohm') else 'setn'
            text = text.replace('.save ', f'.save v({node}) i(VSETN) i(VCOMMAND) ', 1)
            text = text.replace('v(a) v(b)\nquit', f'v(a) v(b) v({node}) i(VSETN) v(command) i(VCOMMAND)\nquit')
    saved = set(' '.join(re.findall('(?m)^\\.save (.*)$', text)).lower().split())
    requested = set(' '.join(re.findall('(?m)^wrdata \\S+ (.*)$', text)).lower().split())
    if requested - saved:
        raise ValueError('Requested but unsaved output vectors: ' + str(sorted(requested - saved)))
    return (text, points, windows)
