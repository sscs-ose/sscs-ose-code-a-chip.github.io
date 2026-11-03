"""Check actual XSPICE phase/reset behavior and incomplete-transient rejection."""
import shutil
from types import SimpleNamespace

import numpy as np
import pytest

from examples.microrobot.controller import phase_netlist
from examples.microrobot import electrical


@pytest.mark.skipif(not shutil.which('ngspice'), reason='optional ngspice/XSPICE')
def test_event_counter_period_phase_and_async_reset(tmp_path):
    deck = '* Event-phase functional verification\n'+phase_netlist(bits=4)+'''
Vclock clk 0 PULSE(0 1 1u 1n 1n 4.998u 10u)
Venable en 0 PWL(0 0 2u 0 2.001u 1 600u 1 600.001u 0 650u 0 650.001u 1)
Xphases clk en pa pb microrobot_event_phases
.control
set wr_vecnames
set wr_singlescale
tran .1u 1m 0 .1u
wrdata phases.dat v(pa) v(pb)
quit
.endc
.end
'''
    try:
        electrical.run_deck(tmp_path, deck)
    except RuntimeError:
        log=(tmp_path/'ngspice.log').read_text().lower()
        if 'unknown model type' in log or 'could not find a valid modelname' in log:
            pytest.skip('ngspice installation lacks the required XSPICE models')
        raise
    time,a,b=np.loadtxt(tmp_path/'phases.dat',skiprows=1).T
    def rises(v):
        i=np.flatnonzero((v[:-1]<.5)&(v[1:]>=.5))
        return time[i]
    ar=rises(a)
    br=rises(b)
    ar=ar[(ar>.0001)&(ar<.00055)]
    br=br[(br>.0001)&(br<.00055)]
    assert len(ar)>=2 and len(br)>=2
    assert np.diff(ar)==pytest.approx(160e-6,rel=.005)
    lags=[np.min(br[br>x]-x) for x in ar if np.any(br>x)]
    assert lags==pytest.approx(np.full(len(lags),40e-6),abs=.3e-6)
    reset=(time>.000602)&(time<.000649)
    assert np.max(abs(a[reset]))<1e-6 and np.max(abs(b[reset]))<1e-6
    restarted=(time>.000652)&(time<.00066)
    assert np.min(a[restarted])>.99 and np.max(abs(b[restarted]))<1e-6


def test_adapter_rejects_ngspice_zero_exit_after_transient_abort(tmp_path,monkeypatch):
    monkeypatch.setattr(electrical.shutil,'which',lambda _: '/fake/ngspice')
    monkeypatch.setattr(electrical.subprocess,'run',lambda *a,**kw:
                        SimpleNamespace(returncode=0,stdout='tran simulation(s) aborted',stderr=''))
    with pytest.raises(RuntimeError,match='ngspice failed'):
        electrical.run_deck(tmp_path,'* deliberately incomplete simulation')


@pytest.mark.parametrize("data,match", [
    (np.array([[0., 1.], [.0009, 1.]]), 'stop time'),
    (np.array([[0., 1.], [.001, np.nan]]), 'nonfinite'),
    (np.array([[0., 1.], [.0005, 1.], [.0004, 1.]]), 'time must not decrease'),
    (np.array([0., 1.]), 'shape'),
])
def test_controller_rejects_invalid_transient(data, match):
    from examples.microrobot.controller import validate_transient
    with pytest.raises(RuntimeError, match=match):
        validate_transient(data, 2, .001)


def test_controller_accepts_completed_adaptive_transient():
    from examples.microrobot.controller import validate_transient
    validate_transient(np.array([[0., 1.], [1e-8, 2.], [.001, 3.]]), 2, .001)


def source_samples():
    """Independent constant-port fixture with phase load behind a resistor."""
    values = {'time': [0., .25, 1.], 'v(logic)': 1.8, 'v(act)': 1.2,
              'v(mid)': .6, 'v(pa_source)': 1.8, 'v(pb_source)': 0.,
              'v(pa)': .4}
    for name in ['Vlogic', 'Vpvlo', 'Vpvhi', 'Vclock', 'Vdigital', 'Vproxy',
                 'Vresetlogic', 'Vmonitor', 'Vpa', 'Vpb', 'Vresetact']:
        values['i('+name+')'] = 0.
    values.update({'i(Vlogic)': -1e-9, 'i(Vpvlo)': 1e-9,
                   'i(Vpvhi)': 2e-9, 'i(Vpa)': 2e-9})
    columns = list(values)
    return columns, np.column_stack([np.broadcast_to(values[k], 3) for k in columns])


def test_offline_source_signs_pv_ports_and_phase_source_terminal():
    from examples.microrobot.controller import offline_source_energies
    columns, data = source_samples()
    energy = offline_source_energies(data, columns)
    assert energy['logic'] == pytest.approx(-1.8)  # Returned charge stays signed.
    assert energy['actuator'] == pytest.approx(1.8)  # Two separate PV spans.
    assert energy['phase'] == pytest.approx(3.6)  # Includes series-resistor loss.
    assert energy['resetact'] == 0.


def test_offline_nonuniform_time_linear_current_has_analytic_energy():
    from examples.microrobot.controller import offline_source_energies
    columns, data = source_samples()
    data[:, columns.index('i(Vlogic)')] = (-1+4*data[:, 0])*1e-9
    assert offline_source_energies(data, columns)['logic'] == pytest.approx(1.8)


def test_offline_requires_measured_source_terminals():
    from examples.microrobot.controller import offline_source_energies
    columns, data = source_samples()
    columns[columns.index('v(pa_source)')] = 'unmeasured_phase_terminal'
    with pytest.raises(ValueError, match='v\\(pa_source\\)'):
        offline_source_energies(data, columns)


def test_diagnostic_path_omits_auxiliary_states_and_preserves_legacy(monkeypatch):
    from examples.microrobot import controller
    monkeypatch.setattr(controller, 'header', lambda *a: '* test header\n')
    monkeypatch.setattr(controller, 'standard_cells', lambda *a: '')
    diagnostic = controller.diagnostic_deck()
    legacy, _ = controller.controller_deck()
    assert 'Benergy_' not in diagnostic and 'Cenergy_' not in diagnostic
    assert ' interp\n' not in diagnostic
    assert 'Xready ready reset_n reset_act_supply reset_supply 0 bp ' in diagnostic
    assert 'i(Vresetact)' in diagnostic and 'v(pa_source)' in diagnostic
    assert 'Benergy_logic' in legacy and ' interp\n' in legacy
    assert 'Xready ready reset_n act reset_supply 0 ' in legacy


def test_diagnostic_runner_rejects_incomplete_data_before_reporting(tmp_path, monkeypatch):
    from examples.microrobot import controller
    monkeypatch.setattr(controller, 'diagnostic_deck', lambda **kw: '* fake circuit')
    def fake_run(dest, deck, **kwargs):
        dest.mkdir()
        np.savetxt(dest/'controller.dat', [[0., 1.], [.0005, 1.]],
                   header='time v(logic)', comments='')
        return dest
    monkeypatch.setattr(controller, 'run_deck', fake_run)
    destination = tmp_path/'incomplete'
    with pytest.raises(RuntimeError, match='stop time'):
        controller.run_diagnostic(destination)
    assert not (destination/'metrics.json').exists()


def test_diagnostic_runner_preserves_existing_results(tmp_path):
    from examples.microrobot.controller import run_diagnostic
    marker = tmp_path/'previous_result.txt'
    marker.write_text('preserve')
    with pytest.raises(FileExistsError, match='fresh'):
        run_diagnostic(tmp_path)
    assert marker.read_text() == 'preserve'


@pytest.mark.parametrize('legacy', [False, True])
def test_cli_routes_short_diagnostic_and_explicit_legacy(tmp_path, monkeypatch, legacy):
    from examples.microrobot import controller
    calls = []
    def fake(name):
        def invoke(destination, **kwargs):
            calls.append((name, destination, kwargs))
            return {'actual_stop_s': kwargs['stop_s']}, None
        return invoke
    monkeypatch.setattr(controller, 'run_diagnostic', fake('diagnostic'))
    monkeypatch.setattr(controller, 'run', fake('legacy'))
    output = tmp_path/'fresh'
    argv = ['--output', str(output)]
    if legacy:
        argv += ['--legacy', '--stop', '.0008', '--max-step', '25e-9']
    controller.main(argv)
    assert calls == [('legacy' if legacy else 'diagnostic', output,
                      dict({'stop_s': .0008 if legacy else .002,
                            'max_step_s': 25e-9 if legacy else 50e-9},
                           **({} if legacy else {'driver_ready': 'independent'})))]


def test_cli_preserves_nonempty_output_before_running(tmp_path, monkeypatch):
    from examples.microrobot import controller
    marker = tmp_path/'previous.txt'
    marker.write_text('preserve')
    def unexpected(*args, **kwargs):
        pytest.fail('CLI must reject the destination before launching SPICE')
    monkeypatch.setattr(controller, 'run_diagnostic', unexpected)
    with pytest.raises(SystemExit) as error:
        controller.main(['--output', str(tmp_path)])
    assert error.value.code == 2
    assert marker.read_text() == 'preserve'


def test_offline_qualifier_branch_is_separate_from_total_pv():
    from examples.microrobot.controller import offline_source_energies
    columns, data = source_samples()
    columns.append('i(Vdriverbuffer)')
    data = np.column_stack([data, np.full(len(data), -2e-9)])
    energy = offline_source_energies(data, columns)
    assert energy['driverbuffer'] == pytest.approx(-2.4)
    assert energy['actuator'] == pytest.approx(1.8)


def test_public_qualifier_wires_both_inputs_and_real_driver_gates(monkeypatch):
    from examples.microrobot import controller
    monkeypatch.setattr(controller, 'header', lambda *a: '* test header\n')
    monkeypatch.setattr(controller, 'standard_cells', lambda *a: '')
    deck = controller.diagnostic_deck(driver_ready='qualified-lvt')
    assert 'Xdriverbuffer reset_n ready driver_ready driverbuffer_supply 0 ' in deck
    assert 'Xda pa driver_ready ea' in deck and 'Xdb pb driver_ready eb' in deck
    assert 'i(Vdriverbuffer)' in deck and 'Cload' not in deck
    assert 'Benergy_' not in deck


def test_cli_selects_explicit_qualified_driver_policy(tmp_path, monkeypatch):
    from examples.microrobot import controller
    calls = []
    def fake(destination, **kwargs):
        calls.append(kwargs)
        return {'actual_stop_s': kwargs['stop_s']}, None
    monkeypatch.setattr(controller, 'run_diagnostic', fake)
    controller.main(['--output', str(tmp_path/'fresh'), '--driver-ready', 'qualified-lvt'])
    assert calls == [{'stop_s': .002, 'max_step_s': 50e-9,
                      'driver_ready': 'qualified-lvt'}]


def test_standard_cells_preserves_exact_upstream_preamble(tmp_path):
    from examples.microrobot.controller import standard_cells
    path = tmp_path/'libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice'
    path.parent.mkdir(parents=True)
    preamble = ('* Copyright 2020 The SkyWater PDK Authors\n*\n'
                '* Licensed under the Apache License, Version 2.0 (the "License");\n'
                '* SPDX-License-Identifier: Apache-2.0\n\n\n')
    cells = ['.subckt '+name+' a b\n.ends' for name in
             ['sky130_fd_sc_hd__dfrtp_1', 'sky130_fd_sc_hd__inv_1']]
    path.write_text(preamble+'\n'.join(cells)+'\n')
    extracted = standard_cells(tmp_path)
    assert extracted.startswith(preamble)
    assert extracted == preamble+'\n'.join(cells)+'\n'


@pytest.mark.parametrize('history', [
    [(0, 0), (1, -1)], [(0, 0), (1, np.nan)], [(0, 0), (np.inf, 1)],
    [(0, 0), (0, 1)], [(0, 0), (2, 1), (1, 1)], [(.1, 0), (1, 1)],
    [(0, 0), (-1, 0)], [], [(0, 0)], [(0, 0, 1), (1, 1, 1)],
])
def test_illumination_history_rejects_invalid_protocols(history):
    from examples.microrobot.controller import illumination_pwl
    with pytest.raises(ValueError, match='Illumination'):
        illumination_pwl(history)


def test_custom_illumination_replaces_fixed_dark_timing_in_seconds(monkeypatch):
    from examples.microrobot import controller
    monkeypatch.setattr(controller, 'header', lambda *a: '* test header\n')
    monkeypatch.setattr(controller, 'standard_cells', lambda *a: '')
    history = [(0, 0), (.001, 1000), (.0016, 0), (.0031, 0), (.004, 1000)]
    deck = controller.diagnostic_deck(illumination_history=history)
    line = next(line for line in deck.splitlines() if line.startswith('Vlight '))
    pairs = np.fromstring(line.split('PWL(')[1][:-1], sep=' ').reshape(-1, 2)
    assert pairs == pytest.approx(np.asarray(history))
    assert '.751' not in line and ' interp\n' not in deck
    assert controller.illumination_pwl(None) == '0 0 100u 0 1m 1000 0.75 1000 0.751 0 0.85 0 0.851 1000'
    assert controller.illumination_pwl(None, dark_interval=False) == '0 0 100u 0 1m 1000'
