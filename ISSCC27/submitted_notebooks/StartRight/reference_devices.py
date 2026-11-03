"""Frozen schematic reference-supervisor adapter.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import hashlib, json
import pilot
from por_models import PR as HV,verify_sources
HERE=Path(__file__).resolve().parent
OUT=HERE/'results/reference'
UP=HERE/'upstream/reference_supervisor'
PNP=UP/'sky130_fd_pr/cells/pnp_05v5'
NONFET=UP/'sky130_fd_pr/models/corners/tt/nonfet.spice'
SOURCE=UP/'2AMLogic/sky130-bandgap/reference_with_injector.spice'
TEMPERATURES=(-40,27,125);CURRENTS=(.1,1.,5.)
sha=lambda b:hashlib.sha256(b).hexdigest()

def provenance():
    manifest=json.loads((HERE/'reference_sources.json').read_text(encoding='utf-8'))
    for row in manifest['files']:
        b=(HERE/row['path']).read_bytes()
        if sha(b)!=row['sha256'] or hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()!=row['git_blob']:
            raise ValueError('Reference source differs: '+row['path'])
    return dict(verified_reference_files=len(manifest['files']),source_manifest_sha256=sha((HERE/'reference_sources.json').read_bytes()),published_POR_model_sources=verify_sources())

def model_text(high_voltage=False):
    text=pilot.models()+'\n'+f'.include "{NONFET.as_posix()}"\n'
    for size in ('W0p68L0p68','W3p40L3p40'):
        text+=f'.include "{(PNP/("sky130_fd_pr__pnp_05v5_"+size+".model.spice")).as_posix()}"\n'
    if high_voltage:
        for kind in ('nfet','pfet'):
            name=kind+'_g5v0d10v5'
            for suffix in ('tt.corner','mismatch.corner'):
                text+=f'.include "{(HV/"cells"/name/("sky130_fd_pr__"+name+"__"+suffix+".spice")).as_posix()}"\n'
    return text

def char_deck(current_uA,temp_C):
    assert current_uA in CURRENTS and temp_C in TEMPERATURES
    current=current_uA*1e-6*(temp_C+273.15)/300.15
    return 'PNP mechanism characterization with explicit ideal PTAT current fixtures\n'+model_text()+f'''
.temp {temp_C}
.option reltol=1e-7 abstol=1e-15 vntol=1e-7 gmin=1e-15
VAVDD vdd 0 3.3
I1 vdd e1 {current:.17g}
I8 vdd e8 {current:.17g}
XQ1 0 0 e1 0 sky130_fd_pr__pnp_05v5_W3p40L3p40
XQ8 0 0 e8 0 sky130_fd_pr__pnp_05v5_W3p40L3p40 m=8 mult=8
.control
set numdgt=17
set wr_singlescale
set wr_vecnames
op
wrdata characterization.dat v(e1) v(e8) i(VAVDD)
quit
.endc
.end
'''
