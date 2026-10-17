"""Connections for the two additional verification examples."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Rectangle


def wire(ax,points,**kw):ax.plot(*zip(*points),color='black',lw=1.2,**kw)
def dot(ax,x,y,label=None):
    ax.add_patch(Circle((x,y),.045,color='black'))
    if label:ax.text(x+.09,y+.1,label,fontsize=11,fontweight='bold')
def mos(ax,x,y,name,p=False,right=False):
    sign=1 if right else -1
    ch=x+sign*.15;gate=x+sign*.36;pin=x+sign*.7
    wire(ax,[(x,y+.5),(x,y+.25),(ch,y+.25)])
    wire(ax,[(x,y-.5),(x,y-.25),(ch,y-.25)])
    for lo,hi in [(-.25,-.1),(-.07,.07),(.1,.25)]:wire(ax,[(ch,y+lo),(ch,y+hi)])
    wire(ax,[(gate,y-.28),(gate,y+.28)])
    if p:
        bubble=x+sign*.48
        wire(ax,[(pin,y),(bubble+sign*.055,y)])
        ax.add_patch(Circle((bubble,y),.055,fill=False,lw=1.2))
        wire(ax,[(bubble-sign*.055,y),(gate,y)])
    else:wire(ax,[(pin,y),(gate,y)])
    ax.text(x-sign*.15,y,name,ha='left' if sign==-1 else 'right',va='center',fontsize=10)
def ground(ax,x,y):
    for k,w in enumerate([.18,.12,.06]):wire(ax,[(x-w,y-k*.07),(x+w,y-k*.07)])
def resistor(ax,x,y,label):
    ax.add_patch(Rectangle((x-.16,y-.4),.32,.8,fill=False,lw=1.2))
    ax.text(x+.25,y,label,va='center',fontsize=10)


def main():
    fig,axes=plt.subplots(1,3,figsize=(13,6),gridspec_kw={'width_ratios':[1.7,1,1]},layout='constrained')
    a=axes[0]
    mos(a,0,3.5,'P1',True,True);mos(a,4,3.5,'P2',True)
    mos(a,0,1.5,'N2',right=True);mos(a,4,1.5,'N1')
    wire(a,[(0,4),(0,4.4),(4,4.4),(4,4)])
    a.text(2,4.5,'VDD',ha='center',fontweight='bold')
    wire(a,[(0,3),(0,2)])
    wire(a,[(0,2.7),(1.2,2.7),(1.2,3.5),(.7,3.5)])
    wire(a,[(1.2,3.5),(3.3,3.5)])
    wire(a,[(4,3),(4,2)])
    wire(a,[(4,2.5),(2.3,2.5),(2.3,1.5),(.7,1.5)])
    wire(a,[(4,2.5),(3,2.5),(3,1.5),(3.3,1.5)])
    wire(a,[(4,1),(4,-.4),(0,-.4)])
    wire(a,[(0,1),(0,.7)])
    resistor(a,0,.3,'RSET 100 kΩ')
    wire(a,[(0,-.1),(0,-.4)])
    ground(a,2,-.4)
    dot(a,0,2.7,'a');dot(a,4,2.5,'b');dot(a,0,.85,'s');dot(a,1.2,3.5);dot(a,3,2.5)
    a.text(1.1,1.15,'Cut N2 gate only',fontsize=9,color='#af4827')
    a.text(2,-1.05,'P1/P2: W/L = 4/2 µm\nN1: 2/2 µm; N2: 8/2 µm',ha='center',fontsize=9)
    a.set_title('Second self-biased family',fontsize=13);a.set_xlim(-.65,4.6)
    a=axes[1]
    mos(a,1.5,1.5,'NREF')
    wire(a,[(1.5,4.4),(1.5,3.9)])
    resistor(a,1.5,3.5,'1 MΩ')
    wire(a,[(1.5,3.1),(1.5,2)])
    wire(a,[(1.5,2.3),(.4,2.3),(.4,1.5),(.8,1.5)])
    wire(a,[(1.5,1),(1.5,.5)]);ground(a,1.5,.5)
    dot(a,1.5,2.3,'b')
    a.text(1.5,4.5,'VDD',ha='center',fontweight='bold')
    a.text(1.5,-1.05,'NREF: W/L = 2/2 µm\nNo self-bias feedback',ha='center',fontsize=9)
    a.set_title('Healthy positive control',fontsize=13);a.set_xlim(-.05,3.7)
    a=axes[2]
    mos(a,1.8,1.5,'NOUT')
    wire(a,[(.4,1.5),(1.1,1.5)])
    a.text(.3,1.5,'b',va='center',ha='right',fontweight='bold')
    wire(a,[(1.8,4.4),(1.8,3.9)]);resistor(a,1.8,3.5,'RLOAD')
    wire(a,[(1.8,3.1),(1.8,2)])
    wire(a,[(1.8,1),(1.8,.5)]);ground(a,1.8,.5)
    a.text(1.8,4.5,'VDD',ha='center',fontweight='bold');dot(a,1.8,2.4,'out')
    a.text(1.7,-1.05,'NOUT: W/L = 2/2 µm\nControl cuts NOUT gate only',ha='center',fontsize=9)
    a.set_title('Output used by each',fontsize=13);a.set_xlim(0,3.8)
    for a in axes:a.set_ylim(-1.4,5);a.set_aspect('equal');a.axis('off')
    fig.suptitle('Additional StartRight circuit connections',fontsize=15)
    fig.supxlabel('NMOS bulks: VSS. PMOS bulks: VDD. Declared 100 fF node capacitors and the zero-volt output current sensor are omitted.',fontsize=9)
    output=Path(__file__).resolve().parent/'results/reuse';output.mkdir(exist_ok=True)
    fig.savefig(output/'additional_circuits.png',dpi=180)
    fig.savefig(output/'additional_circuits.svg')
    print(output/'additional_circuits.png')

if __name__=='__main__':main()
