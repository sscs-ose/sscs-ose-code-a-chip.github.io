"""Plot only measured pre-edge samples from the local circuit lesson."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

CASE=Path(__file__).resolve().parents[1]


def main():
    lesson=json.loads((CASE/'results/teaching/handshake/lesson.json').read_text())
    assert lesson['passed'] and lesson['mutant_rejected']
    rows=lesson['trace']; x=[int(r['cycle']) for r in rows]
    signals=('req_valid','req_ready','rsp_valid','rsp_ready','kill')
    fig,axes=plt.subplots(6,1,figsize=(12,6.4),sharex=True,layout='constrained')
    colors=['#0284c7','#0891b2','#4f46e5','#0d9488','#e11d48']
    for ax,name,color in zip(axes,signals,colors):
        ax.step(x,[int(r[name]) for r in rows],where='post',color=color,lw=2)
        ax.set(yticks=[0,1],ylim=(-.15,1.25),ylabel=name)
        ax.yaxis.label.set_rotation(0); ax.yaxis.label.set_ha('right')
    axes[-1].plot(x,[int(r['rsp_data']) for r in rows],'.-',color='#334155')
    axes[-1].set(ylabel='rsp_data',yticks=[-7,0],xlabel='Rising-edge index (sample immediately before edge)',xticks=x,xlim=(-.3,16.3))
    axes[-1].yaxis.label.set_rotation(0);axes[-1].yaxis.label.set_ha('right')
    for ax in axes:
        ax.axvspan(4,6,alpha=.1,color='#4f46e5')
        for edge in (6,8,14):ax.axvline(edge,color='#64748b',lw=.8,ls=':')
        ax.spines[['top','right']].set_visible(False);ax.grid(axis='x',alpha=.12)
    axes[0].set_title('One result delivered; two requests cancelled\nA held at edges 4–5 → delivered at 6     |     B cancelled at 8     |     C cancelled at 14',loc='left',fontsize=13,pad=16)
    fig.suptitle('Real RTL simulation · signed dot2 reference · no model or physical design run',fontsize=11,color='#475569')
    fig.savefig(CASE/'figures/handshake_lesson.svg')
    plt.close(fig)


if __name__=='__main__':main()
