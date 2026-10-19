"""Shared model checks and schematic helpers for the reset experiments.
SPDX-License-Identifier: Apache-2.0
"""


from dataclasses import dataclass
import hashlib, json, math, re, subprocess
from pilot import HERE, PDK, EXE, models
import passive_models as passive


def verify_models():
    manifest=json.loads((HERE/'dependency_manifest.json').read_text())
    for relative,info in manifest['pdk_files'].items():
        path=PDK/relative
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=info['sha256']:
            raise RuntimeError(f'Model source check failed: {relative}')
    version=subprocess.check_output([str(EXE),'--version'],text=True)
    if 'ngspice-47 ' not in version:raise RuntimeError('This validated example requires ngspice 47.')
    return {'model_commit':manifest['pdk_commit'],'verified_files':len(manifest['pdk_files']),'ngspice_version':version}


def junctions(text):
    lines=[]
    for line in text.splitlines():
        if line.startswith('XM') or line.startswith('XMS'):
            w=float(line.split(' w=')[1].split()[0])
            line+=f' ad={w*.29:.12g} as={w*.29:.12g} pd={2*(w+.29):.12g} ps={2*(w+.29):.12g}'
        lines.append(line)
    return '\n'.join(lines)+'\n'


def apply_contacts(deck, mode):
    """Declare diffusion resistance using the pinned models' RSH=1 ohm.

    The 0.29 um extension is schematic geometry, not extracted layout.
    Explicit resistors and native NRD/NRS are separate formulations.
    """
    if mode not in ('zero', 'native', 'explicit'):
        raise ValueError('Unknown contact formulation')
    lines=[]
    for line in deck.splitlines():
        if line.startswith(('XM', 'XUSE')):
            words=line.split()
            width=float(re.search(r'\bw=([^\s]+)',line)[1])
            resistance=.29/width
            if mode=='native':
                line+=f' nrd={resistance:.12g} nrs={resistance:.12g}'
            elif mode=='explicit':
                name=words[0]; drain,source=words[1],words[3]
                words[1]=name+'_d';words[3]=name+'_s'
                line=' '.join(words)+f'\nRD_{name} {drain} {name}_d {resistance:.12g}\nRS_{name} {source} {name}_s {resistance:.12g}'
        lines.append(line)
    return '\n'.join(lines)+'\n'


@dataclass(frozen=True)
class ResetLatch:
    reset: bool = True
    reset_resistance: float = 1e7
    name: str = 'rc_reset_latch'
    description: str = 'Cross-coupled CMOS latch with optional RC power-on reset; intended b is high.'
    state_vectors: tuple = ('a','b','c')
    minimum_intended_bias_V: float = .8
    intended_state: tuple = (0.,1.8,1.8)

    def setup(self,gmin,broken=False,load_resistance=1e5):
        gate='vin' if broken else 'b'
        core=f'''XMPA a {gate} vdd vdd sky130_fd_pr__pfet_01v8 w=1 l=1
XMNA a {gate} 0 0 sky130_fd_pr__nfet_01v8 w=.42 l=2
XMPB b a vdd vdd sky130_fd_pr__pfet_01v8 w=.42 l=2
XMNB b a 0 0 sky130_fd_pr__nfet_01v8 w=.42 l=2
CA a 0 100f
CB b 0 100f
CC c 0 1p
RC c vdd {self.reset_resistance}
RUSE vdd sense {load_resistance}
VSENSE sense out 0
XMOUT out b 0 0 sky130_fd_pr__nfet_01v8 w=.42 l=20
COUT out 0 100f
'''
        if self.reset:core+='XMRESET b c vdd vdd sky130_fd_pr__pfet_01v8 w=2 l=.5\n'
        return models().replace('.option scale=1u',f'.option scale=1u method=gear maxord=2 gmin={gmin} abstol=1e-16 reltol=1e-6 vntol=1e-8')+'.temp 27\n'+junctions(core)


    def intact_deck(self,state,gmin,load_resistance=1e5):
        nodes=' '.join(f'v({n})={v}' for n,v in zip(self.state_vectors,state))
        return 'RC power-on latch intact operating point\n'+self.setup(gmin,False,load_resistance)+f'VDD vdd 0 1.8\n.nodeset {nodes}\n.control\nset wr_singlescale\nset wr_vecnames\nop\nwrdata op.dat v(a) v(b) v(c) i(VDD) v(vdd) v(out) i(VSENSE)\nquit\n.endc\n.end\n'

    def loaded_deck(self,gmin,load_resistance=1e5,ramp=1e-6,op=False):
        deck=self.intact_deck(self.intended_state,gmin,load_resistance)
        if op:return deck
        stop=ramp+.02
        deck=re.sub(r'(?m)^\.nodeset .*\n','',deck)
        return deck.replace('VDD vdd 0 1.8',f'VDD vdd 0 PWL(0 0 1u 0 {ramp+1e-6} 1.8 {stop} 1.8)').replace('\nop\n',f'\ntran 1u {stop} 0 10u\n').replace('wrdata op.dat','wrdata cold.dat')


@dataclass(frozen=True)
class ConfiguredCircuit:
    base: object
    contacts: str = 'zero'
    corner: str = 'tt'
    temperature_C: float = 27.
    capacitance_scale: float = 1.


    def change(self,deck):
        if self.corner not in ('tt','ff','ss','sf','fs'):raise ValueError('Unknown model corner')
        deck=deck.replace('__tt.corner.spice',f'__{self.corner}.corner.spice').replace('.temp 27',f'.temp {self.temperature_C}')
        if self.capacitance_scale<=0:raise ValueError('Capacitance scale must be positive')
        if self.capacitance_scale!=1:
            deck=re.sub(r'(?m)^(C\S+\s+\S+\s+\S+\s+)([\d.]+)([fp])$',lambda m:m[1]+str(float(m[2])*self.capacitance_scale)+m[3],deck)
        return apply_contacts(deck,self.contacts)

    def loaded_deck(self,*args,**kwargs):return self.change(self.base.loaded_deck(*args,**kwargs))


@dataclass(frozen=True)
class ResetImplementation(ResetLatch):
    reset_width_um: float = 2.
    reset_capacitance_F: float = 1e-12
    def setup(self,*args,**kwargs):
        if not math.isfinite(self.reset_width_um) or self.reset_width_um<.42:raise ValueError("Invalid reset width")
        if not math.isfinite(self.reset_capacitance_F) or self.reset_capacitance_F<=0:raise ValueError("Invalid reset capacitor")
        text=super().setup(*args,**kwargs)
        line=junctions(f"XMRESET b c vdd vdd sky130_fd_pr__pfet_01v8 w={self.reset_width_um} l=.5").strip()
        return re.sub(r"(?m)^XMRESET .*",line,text).replace("CC c 0 1p",f"CC c 0 {self.reset_capacitance_F:.17g}")


@dataclass(frozen=True)
class Architecture(ResetImplementation):
    architecture: str = "direct"
    reset_n_width_um: float = 2.
    def setup(self,*args,**kwargs):
        text=super().setup(*args,**kwargs)
        if self.architecture not in ("direct","buffered","dual"):raise ValueError("Unsupported architecture")
        if self.architecture=="direct":return text
        if not math.isfinite(self.reset_n_width_um) or self.reset_n_width_um<.42:raise ValueError("Invalid reset NMOS width")
        if self.architecture=="buffered":text=re.sub(r"(?m)^XMRESET .*\n","",text)
        extra=f"XMPBUF en c vdd vdd sky130_fd_pr__pfet_01v8 w=2 l=.5\nXMNBUF en c 0 0 sky130_fd_pr__nfet_01v8 w=.42 l=.5\nXMNRST a en 0 0 sky130_fd_pr__nfet_01v8 w={self.reset_n_width_um} l=.5\nCEN en 0 20f\n"
        return text+junctions(extra)


def passive_elements(resistance,capacitance):
    p=passive.bank(capacitance);lines=[]
    for i in range(p["units"]):lines.append(f'XCP{i} c 0 sky130_fd_pr__cap_mim_m3_1 w={p["width_um"]:.17g} l={p["length_um"]:.17g}')
    w=.35;n=25;contact=-46.62/(w*w)+331.73/w+20.576;length=(resistance/n-contact)*w/2000
    if length<=0:raise ValueError("Resistance below fixed contact contribution")
    for i in range(n):
        a="c" if i==0 else f"rseg{i}";b="vdd" if i==n-1 else f"rseg{i+1}"
        lines.append(f'XRP{i} {a} {b} 0 sky130_fd_pr__res_xhigh_po__base w={w} l={length:.17g}')
    return "\n".join(lines)+"\n"


def deck(config,s,contract,passives="ideal",gmin=1e-15,method="gear",max_step=.5e-6,reltol=1e-8):
    if method not in ("gear","trap"):raise ValueError("Unsupported integration method")
    if passives not in ("ideal","mim_and_poly"):raise ValueError("Unsupported passive implementation")
    if not all(math.isfinite(x) and x>0 for x in (config["resistance_ohm"],config["capacitance_F"],gmin,max_step,reltol)):raise ValueError("Positive finite settings required")
    R=config["resistance_ohm"]*s["resistor_scale"];C=config["capacitance_F"]*s["capacitor_scale"]
    base=Architecture(reset_width_um=config["direct_width_um"],reset_capacitance_F=C,reset_resistance=R,architecture=config["architecture"],reset_n_width_um=config["reset_n_width_um"])
    text=ConfiguredCircuit(base,s["contacts"],s["corner"],s["temperature_C"]).loaded_deck(gmin,s["load_ohm"],s["ramp_s"])
    if passives=="mim_and_poly":
        text=re.sub(r"(?m)^CC c 0 .*",passive_elements(R,C).rstrip(),text)
        text=re.sub(r"(?m)^RC c vdd .*\n","",text)
        text=text.replace(".temp ",passive.includes()+".temp ",1)
    end=s["ramp_s"]+1e-6;stop=end+contract["observation_after_ramp_s"]
    text=re.sub(r"(?m)^VDD vdd 0 PWL.*$",f'VDD vdd 0 PWL(0 0 1u 0 {end:.17g} {s["supply_V"]} {stop:.17g} {s["supply_V"]})',text)
    text=re.sub(r"(?m)^tran .*$",f"tran 1u {stop:.17g} 0 {max_step:.17g}",text)
    text=text.replace("method=gear",f"method={method}").replace("reltol=1e-6",f"reltol={reltol:.17g}")
    drive="c" if config["architecture"]=="direct" else "en"
    vectors=f"v(a) v(b) v(c) i(VDD) v(vdd) v(out) i(VSENSE) v({drive})"
    text=re.sub(r"(?m)^wrdata cold.dat .*",f"wrdata cold.dat {vectors}",text)
    text=text.replace(".control\n",f".save {vectors}\n.control\n",1)
    return text,stop
