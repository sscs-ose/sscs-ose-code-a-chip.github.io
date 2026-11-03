"""Local linear response fitting; silk owns model binding and execution.

A six-bit-memory, phase-dependent linear model of the complete link. It is
valid only for the calibrated configuration, rate and operating point; it
cannot predict serializer errors, stress, power, or arbitrary process changes.
"""
from characterization.stimulus import prbs_stimulus
import numpy as np
from silk import Module, Port, sources
from silk.signals import Signal
from silk.metrics import error_norm, sample
from silk.simulation import Transient
from characterization.link_metrics import serdes_link_measurements
from circuits.process import TECHNOLOGIES

PHASE_GRID = np.linspace(0,1,21)
MEMORY = 6


def fit_response(t, y, experiment, *, first=64, stop=192):
    """Fit the linear response using 128 output bits by default (64–191).

    At each phase, fit an offset plus the current bit and five preceding bits.
    The coefficients describe this configured link, not a transistor model.
    """
    t,y=np.asarray(t,float),np.asarray(y,float)
    ui=1/experiment['bit_rate_hz']
    bits=np.asarray(prbs_stimulus(experiment)['bits'])
    if first<MEMORY or stop>len(bits) or stop-first<MEMORY+1:
        raise ValueError('Training window must contain enough complete known bits')
    if t.ndim!=1 or len(t)<2 or y.shape!=t.shape or not np.isfinite(t).all() or np.any(np.diff(t)<=0) or not np.isfinite(y).all():
        raise ValueError('Require finite strictly increasing transient waveform')
    if t[0]>(2+first)*ui or t[-1]<(2+stop)*ui:
        raise ValueError('Waveform does not cover training window')
    indices=np.arange(first,stop)
    x=np.column_stack([np.ones(len(indices))]+[2*bits[indices-k]-1 for k in range(MEMORY)])
    measured = Signal("measured", "tran", "time", "voltage", t, y)
    coefficients={}
    residual=[]
    for p,phase in enumerate(PHASE_GRID):
        # Silk API: sample SPICE at the same phase of each training bit.
        target=sample(measured, x_new=(2+indices+phase)*ui).y
        # Demo model: least-squares fitting of the six bit contributions.
        beta,_,rank,_=np.linalg.lstsq(x,target,rcond=None)
        if rank!=MEMORY+1:
            raise ValueError('Training bits do not identify the response')
        for k,v in enumerate(beta):
            coefficients[f'h{k}_{p}']=float(v)
        residual.extend(target-x@beta)
    return {'coefficients':coefficients,'training_output_bit_range':[first,stop],
            'training_rmse_v':float(np.sqrt(np.mean(np.square(residual)))),
            'model':'six-bit-memory linear polyphase response; 21 phase samples',
            'settings':dict(experiment)}


def _evaluate(t, symbols, ui, coefficients):
    phase=np.mod(t/ui-2+1e-9,1)
    result=np.interp(phase,PHASE_GRID,[coefficients[f'h0_{p}'] for p in range(len(PHASE_GRID))])
    for k in range(MEMORY):
        gain=np.interp(phase,PHASE_GRID,[coefficients[f'h{k+1}_{p}'] for p in range(len(PHASE_GRID))])
        result+=gain*symbols[k]
    return result


def predict_response(t,bits,ui,coefficients):
    """Predict the fitted response from known bits for comparison in tests."""
    bits=np.asarray(bits)
    index=np.floor(t/ui-2+1e-9).astype(int)
    symbols=[2*bits[np.clip(index-k,0,len(bits)-1)]-1 for k in range(MEMORY)]
    return _evaluate(np.asarray(t),symbols,ui,coefficients)


def response_model(ports,t,params):
    ui=params['ui_s']
    index=np.floor(t/ui-2+1e-9).astype(int)
    # Example model policy: native sampling followed by a Python threshold.
    din = Signal('DIN', 'tran', 'time', 'voltage', t, ports.DIN.v)
    symbols=[2*(sample(din, x_new=(2+index-k+.5)*ui).y>.5)-1 for k in range(MEMORY)]
    ports.DOUT.v = _evaluate(t,symbols,ui,params)


def build_response_model(experiment, output_dir):
    """Return a Silk model with zero response coefficients and the chosen bit period."""
    tech=TECHNOLOGIES[experiment['process']]
    model=Module(tech.label,str(output_dir),'response.cir',pdk_details=tech.load(),module_name='measured_link')
    model.define_module_ports({'DIN':Port.analog_input(),'DOUT':Port.analog_output()})
    params={f'h{k}_{p}':0. for k in range(MEMORY+1) for p in range(len(PHASE_GRID))}
    params['ui_s']=1/experiment['bit_rate_hz']
    # Silk API: attach the model and expose coefficients for calibration.
    model.set_behavioral_model(response_model,params=params)
    return model


def build_behavioral_bench(model,experiment,output_dir):
    """Register the same link checks on a serialized-input behavioral bench.

    The model represents the complete measured link, so it receives serial
    bits rather than the transistor serializer's parallel lanes. Electrical
    power and device stress are intentionally not inferred from this model.
    """
    ui=1/experiment['bit_rate_hz']
    # Each invocation owns a fresh registered test; the calibrated child is
    # shared by reference so later calibration reaches every validation bench.
    owner=Module(model.pdk_name,str(output_dir),'validation.cir',
                 pdk_details=model.pdk_details,module_name='measured_link_validation')
    owner.define_module_ports({'DIN':Port.analog_input(),'DOUT':Port.analog_output()})
    owner.add_module(model,'response',nets={'DIN':'DIN','DOUT':'DOUT'})
    owner.set_output_options(mode='new')
    # Silk API: execute the registered test with the behavioral engine.
    owner.simulator='behavioral'
    stimulus=sources.voltage.bitpattern('din', p='din', n='0',
        bits=prbs_stimulus(experiment)['bits'], v1=0, v2=1,
        ui=ui, td=2*ui, tr=.01*ui, tf=.01*ui)
    # Silk API: register the behavioral test and reuse the link metrics/specs.
    tb=owner.create_test('link_validation', parameters={
        'stimulus':stimulus.selected_waveform().as_parameters(),
        'calibrated_configuration':dict(experiment)})
    tb.add_module_under_test({'DIN':'din','DOUT':'dout'})
    tb.add_source(stimulus)
    tb.add_sim_type(Transient(step=ui/100,
        stop=(len(prbs_stimulus(experiment)['bits'])+10)*ui))
    tb.add_metric('link',serdes_link_measurements,sig=tb.probe('dout'),
        bit_rate_hz=experiment['bit_rate_hz'],run_length=experiment['run_length'],
        prbs_offset=experiment['prbs_offset'])
    tb.add_spec('bit_errors','link.bit_errors','==',0)
    tb.add_spec('eye_height_v','link.eye_height_v','>=',experiment['min_eye_height_v'])
    tb.add_spec('eye_width_ui','link.eye_width_ui','>=',experiment['min_eye_width_ui'])
    return tb


def validation_residual(t, predicted, spice_t, spice_y, experiment):
    ui=1/experiment['bit_rate_hz']
    first,stop=prbs_stimulus(experiment)['measurement_bit_range']
    t,predicted,spice_t,spice_y=(np.asarray(value,float) for value in (t,predicted,spice_t,spice_y))
    start,end=(first+8)*ui,(stop+2)*ui
    for times,values in ((t,predicted),(spice_t,spice_y)):
        if (times.ndim!=1 or len(times)<2 or values.shape!=times.shape
            or not np.isfinite(times).all() or not np.isfinite(values).all()
            or np.any(np.diff(times)<=0)):
            raise ValueError('Validation requires finite strictly increasing waveforms')
        if times[0]>start or times[-1]<end:
            raise ValueError('Waveform does not cover validation window')
    mask=(t>=(first+8)*ui)&(t<(stop+2)*ui)
    # Keep the declared half-open sample window; native norms weight elapsed time.
    prediction = Signal('prediction', 'tran', 'time', 'voltage', t[mask], predicted[mask])
    reference = Signal('spice_reference', 'tran', 'time', 'voltage', spice_t, spice_y)
    # Silk API: compute time-weighted RMS and maximum waveform errors.
    return {'rmse_v': error_norm(prediction, reference, kind='rms'),
            'max_absolute_error_v': error_norm(prediction, reference, kind='max'),
            'samples': int(mask.sum()), 'output_time_range_s': [start, end],
            'rms_definition': 'silk error_norm: time-weighted RMS over retained samples',
            'sample_time_range_s': [float(prediction.x[0]), float(prediction.x[-1])]}
