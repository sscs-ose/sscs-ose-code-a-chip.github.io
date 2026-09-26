"""Analytical PTAT sensor model; separate from PDK/silicon evidence."""
from dataclasses import dataclass
import numpy as np

K_B = 1.380649e-23
Q_E = 1.602176634e-19
K_OVER_Q = K_B / Q_E

@dataclass(frozen=True)
class PTATParams:
    current_density_ratio: float = 8.0
    subthreshold_slope_factor: float = 1.40
    offset_v: float = 0.0
    curvature_per_k2_v: float = 0.0
    t_ref_k: float = 298.15
    def __post_init__(self):
        if not np.isfinite(self.current_density_ratio) or self.current_density_ratio <= 1: raise ValueError('current_density_ratio must be > 1')
        if not np.isfinite(self.subthreshold_slope_factor) or self.subthreshold_slope_factor <= 0: raise ValueError('subthreshold_slope_factor must be positive')
        if not np.isfinite(self.offset_v) or not np.isfinite(self.curvature_per_k2_v): raise ValueError('offset/curvature must be finite')
        if not np.isfinite(self.t_ref_k) or self.t_ref_k <= 0: raise ValueError('t_ref_k must be positive')

DEFAULT_PARAMS = PTATParams()

def _as_temperature_kelvin(temp_c):
    x = np.asarray(temp_c, dtype=float)
    if not np.all(np.isfinite(x)): raise ValueError('temperature must be finite')
    k = x + 273.15
    if np.any(k <= 0): raise ValueError('temperature must be above absolute zero')
    return k

def nominal_slope_v_per_k(params=DEFAULT_PARAMS):
    return float(params.subthreshold_slope_factor*K_OVER_Q*np.log(params.current_density_ratio))

def ideal_ptat_voltage(temp_c, params=DEFAULT_PARAMS):
    k = _as_temperature_kelvin(temp_c)
    return nominal_slope_v_per_k(params)*k + params.offset_v + params.curvature_per_k2_v*(k-params.t_ref_k)**2

def estimate_uncalibrated(v, params=DEFAULT_PARAMS):
    v=np.asarray(v,dtype=float)
    if not np.all(np.isfinite(v)): raise ValueError('voltage must be finite')
    return v/nominal_slope_v_per_k(params)-273.15

def calibrate_one_point(v,v_cal,t_cal_c,nominal_slope):
    s=float(nominal_slope); v=np.asarray(v,dtype=float)
    if not np.isfinite(s) or s<=0 or not np.all(np.isfinite(v)) or not np.isfinite(v_cal) or not np.isfinite(t_cal_c): raise ValueError('invalid one-point calibration inputs')
    return t_cal_c+(v-v_cal)/s

def calibrate_two_point(v,v1,t1_c,v2,t2_c):
    v=np.asarray(v,dtype=float); p=np.array([v1,t1_c,v2,t2_c],dtype=float)
    if not np.all(np.isfinite(v)) or not np.all(np.isfinite(p)) or np.isclose(v2,v1) or np.isclose(t2_c,t1_c): raise ValueError('invalid two-point calibration inputs')
    gain=(t2_c-t1_c)/(v2-v1); return gain*v+(t1_c-gain*v1)

def adc_lsb_v(bits,v_ref):
    if isinstance(bits,bool) or not isinstance(bits,(int,np.integer)) or bits<1 or bits>32: raise ValueError('bits must be 1..32')
    if not np.isfinite(v_ref) or v_ref<=0: raise ValueError('v_ref must be positive')
    return float(v_ref)/(2**bits)

def quantize_voltage(v,bits=12,v_ref=1.8):
    lsb=adc_lsb_v(bits,v_ref); x=np.asarray(v,dtype=float)
    if not np.all(np.isfinite(x)): raise ValueError('ADC input must be finite')
    code=np.clip(np.rint(np.clip(x,0,(2**bits-1)*lsb)/lsb),0,2**bits-1).astype(np.int64)
    return code,code.astype(float)*lsb

def temperature_lsb_c(bits,v_ref,analog_gain=1.0,params=DEFAULT_PARAMS):
    if not np.isfinite(analog_gain) or analog_gain<=0: raise ValueError('analog_gain must be positive')
    return adc_lsb_v(bits,v_ref)/(analog_gain*nominal_slope_v_per_k(params))

def minimum_gain_for_temperature_lsb(target_lsb_c,bits,v_ref,params=DEFAULT_PARAMS):
    if not np.isfinite(target_lsb_c) or target_lsb_c<=0: raise ValueError('target_lsb_c must be positive')
    return adc_lsb_v(bits,v_ref)/(nominal_slope_v_per_k(params)*target_lsb_c)

def sample_die(rng,nominal=DEFAULT_PARAMS,sigma_n_frac=0.03,sigma_offset_v=0.0006,sigma_curvature_v_per_k2=2e-8):
    if np.any(np.asarray([sigma_n_frac,sigma_offset_v,sigma_curvature_v_per_k2])<0): raise ValueError('synthetic sigmas must be non-negative')
    n=nominal.subthreshold_slope_factor*(1+rng.normal(0,sigma_n_frac))
    if n<=0: raise ValueError('synthetic sample produced non-positive slope factor')
    return PTATParams(nominal.current_density_ratio,n,rng.normal(0,sigma_offset_v),rng.normal(0,sigma_curvature_v_per_k2),nominal.t_ref_k)
