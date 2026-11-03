"""Pinned dual-rail POR source/model adapter.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import hashlib,json,re
import pilot,passive_models
HERE=Path(__file__).resolve().parent
UP=HERE/'por_sources/upstream';PR=UP/'skywater-pdk-libs-sky130_fd_pr';HVL=UP/'skywater-pdk-libs-sky130_fd_sc_hvl'


def verify_sources():
    manifest=json.loads((HERE/'por_sources.json').read_text())
    for item in manifest['files']:
        b=(HERE/item['path']).read_bytes()
        if hashlib.sha256(b).hexdigest()!=item['sha256'] or hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()!=item['git_blob']:
            raise ValueError('POR source differs: '+item['path'])
    passive_models.verify()
    return dict(verified_files=len(manifest['files']),manifest_sha256=hashlib.sha256((HERE/'por_sources.json').read_bytes()).hexdigest())


def models(mapped):
    text=pilot.models()+passive_models.includes()
    sources=[(PR/n).read_text() for n in ['models/r+c/res_typical__cap_typical.spice','models/r+c/res_typical__cap_typical__lin.spice','models/sky130_fd_pr__model__r+c.model.spice']]
    names=['m4_dw','tol_m4','rm4','rcvia4','tc1rm4','tc2rm4','tc1rvia4','tc2rvia4','tol_nfom','tol_pfom','nfom_dw','pfom_dw','tc1rsn_h','tc2rsn_h','tc1rsp_h','tc2rsp_h','rdn_hv','rdp_hv']
    for name in names:
        values={m[1] for source in sources for m in re.finditer(r'(?<![\w])'+name+r'\s*=\s*([^\s$]+)',source)}
        assert len(values)==1,(name,values)
        text+=f'.param {name}={next(iter(values))}\n'
    for name in ['nfet_g5v0d10v5','pfet_g5v0d10v5']:
        for suffix in ['tt.corner','mismatch.corner']:text+=f'.include "{(PR/"cells"/name/("sky130_fd_pr__"+name+"__"+suffix+".spice")).as_posix()}"\n'
    for path in ['cells/cap_mim_m3/sky130_fd_pr__cap_mim_m3_2.model.spice','cells/res_xhigh_po/sky130_fd_pr__res_xhigh_po_0p69.model.spice']:text+=f'.include "{(PR/path).as_posix()}"\n'
    if mapped:
        source=sources[-1]
        for polarity,letter in [('nd','n'),('pd','p')]:
            model='sky130_fd_pr__res_generic_'+polarity+'__hv'
            lines=[line for line in source.splitlines() if line.startswith('.model '+model+' ')];assert len(lines)==1;text+=lines[0]+'\n'
            # Upstream legacy name -> foundry semiconductor-resistor model.
            # The present foundry R model has two electrical terminals and no
            # substrate-capacitance parameter. The old bulk pin is unused.
            text+=f'.subckt mrd{letter}_hv p n bulk w=1 l=1\nRLEGACY p n {model} w={{w}} l={{l}}\n.ends\n'
    for cell,drive in [('buf',8),('inv',8),('schmittbuf',1)]:text+=f'.include "{(HVL/"cells"/cell/(f"sky130_fd_sc_hvl__{cell}_{drive}.spice")).as_posix()}"\n'
    original=(UP/'sky130_ef_ip__simple_por/netlist/schematic/sky130_ef_ip__simple_por.spice').read_text()
    adapted,count=re.subn(r'(?im)^\.end\s*$', '',original);assert count==1
    # Only the terminal deck directive is removed. Device topology is unchanged.
    text+=adapted+'\n';return text


def nominal_deck(mapped):
    return 'Published simple POR, source CACE nominal supply functions\n'+models(mapped)+'''
.temp 27
.option reltol=1e-6 abstol=1e-15 vntol=1e-7 gmin=1e-15 method=gear warn=1
VAVDD avdd 0 PWL(0 0 100u 0 5m 3.3 20m 3.3)
VDVDD dvdd 0 PWL(0 0 300u 0 5.3m 1.8 20m 1.8)
XPOR avdd dvdd porb_h porb_l por_l 0 0 sky130_ef_ip__simple_por
.save v(porb_h) v(porb_l) v(por_l) v(avdd) v(dvdd) i(VAVDD) i(VDVDD) v(xpor.net9) v(xpor.net10)
.control
set numdgt=17
set wr_singlescale
set wr_vecnames
tran 1u 20m 0 2u
print @m.xpor.xm1.msky130_fd_pr__pfet_g5v0d10v5[l] @m.xpor.xm1.msky130_fd_pr__pfet_g5v0d10v5[w]
wrdata reference.dat v(porb_h) v(porb_l) v(por_l) v(avdd) v(dvdd) i(VAVDD) i(VDVDD) v(xpor.net9) v(xpor.net10)
quit
.endc
.end
'''
