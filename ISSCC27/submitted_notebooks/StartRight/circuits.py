"""Circuit adapters for a second self-biased family and an acyclic control.
SPDX-License-Identifier: Apache-2.0
"""
from dataclasses import dataclass
from pilot import models
from widlar_confirm import junctions


@dataclass(frozen=True)
class Circuit:
    name: str
    description: str
    intended_state: tuple
    minimum_intended_bias_V: float = .4

    def setup(self,gmin,broken=False,load_resistance=1e5):
        gate='vin' if broken else 'b'
        if self.name=='beta_multiplier':
            core=f'''XM1 a a vdd vdd sky130_fd_pr__pfet_01v8 w=4 l=2
XM2 b a vdd vdd sky130_fd_pr__pfet_01v8 w=4 l=2
XM3 b b 0 0 sky130_fd_pr__nfet_01v8 w=2 l=2
XM4 a {gate} s 0 sky130_fd_pr__nfet_01v8 w=8 l=2
RSET s 0 100k
CA a 0 100f
CB b 0 100f
CS s 0 100f
'''
            load_gate='b'
        elif self.name=='resistor_biased_mirror':
            core='''RBIAS vdd b 1Meg
XMREF b b 0 0 sky130_fd_pr__nfet_01v8 w=2 l=2
CB b 0 100f
'''
            load_gate=gate
        else:
            raise ValueError(self.name)
        load=f'''RUSE vdd sense {load_resistance}
VSENSE sense out 0
XMOUT out {load_gate} 0 0 sky130_fd_pr__nfet_01v8 w=2 l=2
COUT out 0 100f
'''
        return models().replace('.option scale=1u',f'.option scale=1u method=gear maxord=2 gmin={gmin} abstol=1e-16 reltol=1e-6 vntol=1e-8')+'.temp 27\n'+junctions(core+load)

    @property
    def state_vectors(self):
        return ('a','b','s') if self.name=='beta_multiplier' else ('out','b','sense')

    def return_deck(self,gmin,direction=1,load_resistance=1e5):
        start,end,step=(0,1.8,.0005) if direction==1 else (1.8,0,-.0005)
        a,b,c=self.state_vectors
        return f'{self.name} loaded gate-cut return curve\n'+self.setup(gmin,True,load_resistance)+f'''VDD vdd 0 1.8
VIN vin 0 0
.control
set wr_singlescale
set wr_vecnames
dc VIN {start} {end} {step}
wrdata return.dat v({b}) v({a}) v({c}) i(VDD) i(VIN)
quit
.endc
.end
'''

    def intact_deck(self,state,gmin,load_resistance=1e5,transient=False,ramp=1e-6):
        a,b,c=self.state_vectors
        if transient:
            stop=ramp+.02
            source=f'VDD vdd 0 PWL(0 0 1u 0 {ramp+1e-6} 1.8 {stop} 1.8)\n'
            analysis=f'tran 1u {stop} 0 10u';filename='cold.dat'
        else:
            source='VDD vdd 0 1.8\n'+'.nodeset '+' '.join(f'v({node})={value}' for node,value in zip(self.state_vectors,state) if node!='0')+'\n'
            analysis='op';filename='op.dat'
        return f'{self.name} intact loaded circuit\n'+self.setup(gmin,False,load_resistance)+source+f'''.control
set wr_singlescale
set wr_vecnames
{analysis}
wrdata {filename} v({a}) v({b}) v({c}) i(VDD) v(vdd) v(out) i(VSENSE)
quit
.endc
.end
'''


    def loaded_deck(self,gmin,load_resistance=1e5,ramp=1e-6,op=False):
        return self.intact_deck(self.intended_state,gmin,load_resistance,not op,ramp)


@dataclass(frozen=True)
class WidlarCircuit:
    startup_width: float | None = .42
    name: str = 'inverse_widlar'
    description: str = 'Inverse-Widlar core with optional conventional NMOS startup.'
    state_vectors: tuple = ('a','b','c')
    minimum_intended_bias_V: float = .8

    def return_deck(self,gmin,direction=1,load_resistance=1e5):
        from widlar_confirm import return_deck
        return return_deck(gmin,self.startup_width,direction)

    def intact_deck(self,state,gmin,load_resistance=1e5):
        from widlar_confirm import intact_deck
        return intact_deck(state,gmin,self.startup_width)

    def loaded_deck(self,gmin,load_resistance=1e5,ramp=1e-6,op=False):
        from loaded_startup import loaded_deck
        return loaded_deck(self.startup_width,load_resistance,ramp,op=op,gmin=gmin)


CIRCUITS={
    'beta_multiplier':Circuit('beta_multiplier','Conventional 4:1 beta multiplier with ideal 100 kohm setting resistor; cut only the source-degenerated NMOS gate.',(1.1,.6,.06)),
    'resistor_biased_mirror':Circuit('resistor_biased_mirror','Acyclic NMOS mirror biased by a 1 Mohm resistor; cut only the output NMOS gate. The reference node is independent of the scan input.',(1.7,.6,1.7)),
}
