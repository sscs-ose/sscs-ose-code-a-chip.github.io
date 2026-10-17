import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from pathlib import Path

fig,ax=plt.subplots(1,3,figsize=(12,5.6),gridspec_kw={'width_ratios':[1.6,1,1]},layout='constrained')
def wire(a,points):a.plot(*zip(*points),color='black',lw=1.3)
def dot(a,x,y,label=None):
    a.add_patch(Circle((x,y),.045,color='black'))
    if label:a.text(x+.08,y+.08,label,fontsize=12,fontweight='bold')
def mos(a,x,y,name,p=False,right=False):
    sign=1 if right else -1
    channel=x+sign*.15;gate=x+sign*.36;pin=x+sign*.7
    wire(a,[(x,y+.5),(x,y+.25),(channel,y+.25)])
    wire(a,[(x,y-.5),(x,y-.25),(channel,y-.25)])
    for lo,hi in [(-.25,-.1),(-.07,.07),(.1,.25)]:wire(a,[(channel,y+lo),(channel,y+hi)])
    wire(a,[(gate,y-.28),(gate,y+.28)])
    if p:
        bubble=x+sign*.48
        wire(a,[(pin,y),(bubble+sign*.055,y)])
        a.add_patch(Circle((bubble,y),.055,fill=False,lw=1.2))
        wire(a,[(bubble-sign*.055,y),(gate,y)])
    else:wire(a,[(pin,y),(gate,y)])
    a.text(x-sign*.15,y,name,ha='left' if sign==-1 else 'right',va='center',fontsize=11)
    return (pin,y)
def ground(a,x,y):
    for k,w in enumerate([.18,.12,.06]):wire(a,[(x-w,y-k*.07),(x+w,y-k*.07)])

c=ax[0]
mos(c,0,3.5,'M5',True,True);mos(c,4,3.5,'M4',True)
mos(c,0,1.5,'M1',right=True);mos(c,4,1.8,'M2');mos(c,4,.6,'M3')
wire(c,[(0,4),(0,4.4),(4,4.4),(4,4)])
c.text(2,4.5,'VDD',ha='center',fontweight='bold')
wire(c,[(0,3),(0,2),(0,1.5+.5)])
wire(c,[(0,2.7),(1.2,2.7),(1.2,3.5),(.7,3.5)])
wire(c,[(1.2,3.5),(3.3,3.5)])
wire(c,[(4,3),(4,2.3)])
wire(c,[(4,2.5),(2.4,2.5),(2.4,1.5),(.7,1.5)])
wire(c,[(4,2.5),(3.1,2.5),(3.1,1.8),(3.3,1.8)])
wire(c,[(4,1.3),(4,1.1)])
wire(c,[(4,1.2),(3.1,1.2),(3.1,.6),(3.3,.6)])
wire(c,[(0,1),(0,-.1),(4,-.1),(4,.1)])
ground(c,2,-.1)
for x,y,label in [(0,2.7,'a'),(4,2.5,'b'),(4,1.2,'c')]:dot(c,x,y,label)
dot(c,1.2,3.5);dot(c,3.1,2.5)
c.set_title('Inverse-Widlar core',fontsize=13)
c.set_xlim(-.6,4.7);c.set_ylim(-.6,4.9)

s=ax[1]
mos(s,2,2,'MS')
wire(s,[(2,2.5),(2,3.2),(1,3.2),(1,2),(1.3,2)])
wire(s,[(2,1.5),(2,1)])
dot(s,2,3.2,'a');dot(s,2,1,'b')
s.text(1.8,.35,'W = 0.42 or 1 µm\nL = 1 µm',ha='center',fontsize=10)
s.set_title('Startup device',fontsize=13)
s.set_xlim(.4,3.6);s.set_ylim(-.6,4.9)

u=ax[2]
mos(u,2,1.2,'MOUT')
wire(u,[(.6,1.2),(1.3,1.2)]);u.text(.45,1.2,'b',ha='right',va='center',fontweight='bold')
wire(u,[(2,1.7),(2,2.5)])
wire(u,[(2,3.5),(2,4.2)])
wire(u,[(1.8,2.5),(2.2,2.5),(2.2,3.5),(1.8,3.5),(1.8,2.5)])
u.text(2.35,3,'RLOAD',va='center',fontsize=10)
u.text(2,4.3,'VDD',ha='center',fontweight='bold')
dot(u,2,2,'out')
wire(u,[(2,.7),(2,.3)]);ground(u,2,.3)
u.text(1.9,-.3,'W/L = 0.42/20 µm',ha='center',fontsize=10)
u.set_title('Useful current output',fontsize=13)
u.set_xlim(.2,3.8);u.set_ylim(-.6,4.9)
for a in ax:a.set_aspect('equal');a.axis('off')
fig.suptitle('StartRight circuit connections',fontsize=15)
fig.supxlabel('NMOS bulks connect to VSS; PMOS bulks connect to VDD. Explicit capacitors and the zero-volt current sensor are omitted here.',fontsize=9)
folder=Path(__file__).resolve().parent/'results'/'loaded'
fig.savefig(folder/'circuit_connections.png',dpi=180)
fig.savefig(folder/'circuit_connections.svg')
print(folder/'circuit_connections.png')
