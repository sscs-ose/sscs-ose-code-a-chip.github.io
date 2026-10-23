"""Frozen conventional digital guard and declared matched histories.
SPDX-License-Identifier: Apache-2.0
"""
import re
from por_circuit import generate as base_generate
from reset_contract import Window
CONDITIONS={
 'half_depth':dict(low_V=.9,hold_s=.001,rise_s=.002,temp_C=27,storage=False),
 'shallow_depth':dict(low_V=1.35,hold_s=.001,rise_s=.002,temp_C=27,storage=False),
 'short_zero':dict(low_V=0.,hold_s=2e-6,rise_s=10e-6,temp_C=27,storage=False),
 'slow_zero':dict(low_V=0.,hold_s=.001,rise_s=.010,temp_C=27,storage=False),
 'warm_zero':dict(low_V=0.,hold_s=.001,rise_s=.002,temp_C=85,storage=False),
 'warm_storage':dict(low_V=1.8,hold_s=.001,rise_s=.002,temp_C=85,storage=True)}
GUARD='''RDB dvdd dbsense 40meg
XDBS dbsense dbsense 0 0 sky130_fd_pr__nfet_01v8 w=.42 l=8
XDBP dbok dbsense dvdd dvdd sky130_fd_pr__pfet_01v8 w=2 l=2
XDBN dbok dbsense 0 0 sky130_fd_pr__nfet_01v8 w=.42 l=2
CDBS dbsense 0 20f
CDBO dbok 0 1p
XANDP1 nand_reset porb_l dvdd dvdd sky130_fd_pr__pfet_01v8 w=2 l=.15
XANDP2 nand_reset dbok dvdd dvdd sky130_fd_pr__pfet_01v8 w=2 l=.15
XANDN1 nand_reset porb_l and_mid 0 sky130_fd_pr__nfet_01v8 w=.84 l=.15
XANDN2 and_mid dbok 0 0 sky130_fd_pr__nfet_01v8 w=.84 l=.15
XOUTP combined_reset nand_reset dvdd dvdd sky130_fd_pr__pfet_01v8 w=2 l=.15
XOUTN combined_reset nand_reset 0 0 sky130_fd_pr__nfet_01v8 w=.42 l=.15
'''
def generate(event,command,variant,max_step=2e-6):
 text,*args=base_generate(event,command,max_step)
 if variant=='digital_guard':
  text,count=re.subn(r'(?m)^XDUT clk d porb_l ', 'XDUT clk d combined_reset ',text);assert count==1
  text=text.replace('CQ q 0 10f\n','CQ q 0 10f\n'+GUARD)
  for start in ['.save ','wrdata history.dat ']:
   text=re.sub(r'(?m)^'+re.escape(start)+r'(.*)$',lambda m:start+m[1].replace('v(porb_l)','v(combined_reset)')+' v(porb_l) v(dbok) v(dbsense)',text)
 else:assert variant=='original'
 return text,args
def generate_condition(condition,variant,max_step=2e-6):
 c=CONDITIONS[condition];text,args=generate('none' if c['storage'] else 'digital_zero',True,variant,max_step)
 ap,vp,dp,cp,_=args;old_stop=vp[-1][0];low_end=.025001+c['hold_s'];rise_end=low_end+c['rise_s'];stop=rise_end+.020
 for points in [ap,vp]:
  points[6][0]=low_end;points[7][0]=rise_end;points[8][0]=stop
 vp[5][1]=vp[6][1]=c['low_V']
 for points in [dp,cp]:assert points[-1][0]==old_stop;points[-1][0]=stop
 for source,node,points in [('VAVDD','avdd',ap),('VDVDD','dvdd',vp),('VDATA','ddrv',dp),('VCLK','clkdrv',cp)]:
  pwl=' '.join(f'{t:.17g} {v:.17g}' for t,v in points)
  text,n=re.subn(r'(?m)^'+source+r' .*$',source+' '+node+' 0 PWL('+pwl+')',text);assert n==1
 text,n=re.subn(r'(?m)^tran .*$',f'tran 1u {stop:.17g} 0 {max_step:.17g}',text);assert n==1
 text,n=re.subn(r'(?m)^\.temp 27$',f'.temp {c["temp_C"]}',text);assert n==1
 return text,[ap,vp,dp,cp,[Window('cold',0.,.0053,.020),Window('recovery',low_end,rise_end,stop)]]
