"""Joint random search, independent EM evaluation and active refinement."""
from environment import ROOT,configure
configure()
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch,FancyBboxPatch
from matplotlib.path import Path as PlotPath
import figure_style as STYLE


def build(output):
    STYLE.configure()
    fig,ax=plt.subplots(figsize=(27,10))
    ax.set(xlim=(-.1,13.5),ylim=(-.8,4.1));ax.axis('off')
    ink='#354d5e';fill='#f3f6f7'
    def box(x,y,text,width=2.8,accent=False):
        ax.add_patch(FancyBboxPatch((x-width/2,y-.43),width,.86,
            boxstyle='round,pad=0.03,rounding_size=0.06',
            facecolor='#e5eee9' if accent else fill,edgecolor=ink,linewidth=.85))
        ax.text(x,y,text,ha='center',va='center',color='#172e3e',linespacing=1.3)
    def arrow(points,label=None,position=None):
        path=PlotPath(points,[PlotPath.MOVETO]+[PlotPath.LINETO]*(len(points)-1))
        ax.add_patch(FancyArrowPatch(path=path,arrowstyle='-|>',mutation_scale=10,color=ink,linewidth=.9))
        if label:ax.text(*position,label,ha='center',va='center',color=ink,
            bbox=dict(facecolor='white',edgecolor='none',pad=1))
    xs=(1.5,4.9,8.3,11.7)
    for x,text in zip(xs,('Random start','TPE: 22 → 23 → 25','Surrogates + SPICE','Candidate pool')):
        box(x,3.2,text)
    for a,b in zip(xs[:-1],xs[1:]):arrow([(a+1.45,3.2),(b-1.45,3.2)])
    for x,text in zip(xs,('Qualified TIA','Dense verification\nANN ≥34; EM >32 GHz',
                         'Active refinement\n8 R/C and bias variables','Independent EM\ntransformer, L1, Lb')):
        box(x,1.2,text)
    arrow([(11.7,2.72),(11.7,1.68)])
    arrow([(10.25,1.2),(9.75,1.2)])
    ax.text(10.,.54,'if needed',ha='center',va='bottom',color=ink)
    arrow([(6.85,1.2),(6.35,1.2)])
    arrow([(3.45,1.2),(2.95,1.2)])
    ax.text(3.2,1.5,'pass',ha='center',va='bottom',color=ink)
    ax.text(4.9,2.37,'6,000 proposals/stage; 256 random startup proposals',ha='center',va='center',color=ink)
    ax.text(8.3,2.03,'1 GHz circuit grid; up to five candidates',ha='center',va='center',color=ink)
    ax.text(6.7,.12,'Five unsuccessful random starts → best valid candidate → up to five restarts',
            ha='center',va='center',color=ink)
    ax.text(6.7,-.48,'Refinement fixes all three passive layouts; final SPICE grid: 0.1 GHz.',
            ha='center',va='center',color=ink)
    fig.subplots_adjust(left=.01,right=.995,bottom=.02,top=.99)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    STYLE.save(fig,output,'figure-09')
    plt.close(fig)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'runs/figures')
    build(parser.parse_args().output)
