"""Shared 24-point typography for the notebook's scientific figures."""
from environment import ROOT,configure as configure_environment
configure_environment()
import hashlib
import json
import os
from pathlib import Path

import matplotlib
from matplotlib import font_manager
from matplotlib.text import Text
from matplotlib.ticker import FuncFormatter,LogFormatterMathtext,NullFormatter

FONT_FILE=None
FAMILY='Arial Narrow'
FONT_SHA256='bd31d0cf2e5a1a3a9074e98ebe4964c641121e9e660f31627614c4acb6c89c1c'
SIZE=24


def configure():
    global FONT_FILE
    configured=os.environ.get('TIA_FIGURE_FONT')
    if configured:
        FONT_FILE=Path(configured).expanduser().resolve()
    elif (ROOT/'assets/fonts/arial-narrow.ttf').is_file():
        FONT_FILE=ROOT/'assets/fonts/arial-narrow.ttf'
    elif (ROOT.parent/'arial-narrow.ttf').is_file():
        FONT_FILE=ROOT.parent/'arial-narrow.ttf'
    else:
        try:
            FONT_FILE=Path(font_manager.findfont(font_manager.FontProperties(family=FAMILY),fallback_to_default=False))
        except ValueError as error:
            raise FileNotFoundError('Set TIA_FIGURE_FONT to arial-narrow.ttf before rendering figures') from error
    if not FONT_FILE.is_file():raise FileNotFoundError('TIA_FIGURE_FONT must name an existing arial-narrow.ttf')
    if hashlib.sha256(FONT_FILE.read_bytes()).hexdigest()!=FONT_SHA256:
        raise ValueError('Use the exact arial-narrow.ttf recorded for these figures')
    font_manager.fontManager.addfont(str(FONT_FILE))
    if font_manager.FontProperties(fname=str(FONT_FILE)).get_name()!=FAMILY:
        raise ValueError('Unexpected figure font family')
    resolved=font_manager.findfont(font_manager.FontProperties(family=FAMILY),fallback_to_default=False)
    if Path(resolved).resolve()!=FONT_FILE.resolve():raise ValueError('Figure font resolved to a different file')
    matplotlib.rcParams.update({'font.family':[FAMILY],'font.size':SIZE,
        'axes.labelsize':SIZE,'axes.titlesize':SIZE,'xtick.labelsize':SIZE,'ytick.labelsize':SIZE,
        'legend.fontsize':SIZE,'legend.title_fontsize':SIZE,'figure.titlesize':SIZE,
        'axes.unicode_minus':False,'axes.formatter.use_mathtext':False,'svg.fonttype':'path',
        'svg.hashsalt':'tia-notebook-figures','pdf.fonttype':42,
        'mathtext.fontset':'custom','mathtext.rm':FAMILY,'mathtext.it':FAMILY,
        'mathtext.bf':FAMILY,'mathtext.sf':FAMILY,'mathtext.tt':FAMILY,'mathtext.cal':FAMILY,
        'mathtext.default':'regular','mathtext.fallback':None})


def panel(ax,text,y=-.25):
    ax.text(.5,y,text,transform=ax.transAxes,ha='center',va='top',fontsize=SIZE)


def apply(fig):
    for ax in fig.axes:
        for axis in (ax.xaxis,ax.yaxis):
            if isinstance(axis.get_major_formatter(),LogFormatterMathtext):
                axis.set_major_formatter(FuncFormatter(lambda value,position:f'{value:g}'))
                axis.set_minor_formatter(NullFormatter())
    for text in fig.findobj(Text):
        text.set_fontfamily([FAMILY]);text.set_fontsize(SIZE)
    for ax in fig.axes:
        if any(ax.get_title(loc=loc) for loc in ('left','center','right')):
            raise ValueError('Move subplot titles below the panel before saving')
    if fig._suptitle is not None and fig._suptitle.get_text():
        raise ValueError('Top figure titles are not used in the submission')
    fig.canvas.draw()
    visible=[t for t in fig.findobj(Text) if t.get_visible() and t.get_text()]
    if any(t.get_fontsize()!=SIZE or t.get_fontfamily()!=[FAMILY] for t in visible):
        raise ValueError('Figure typography is inconsistent')
    return dict(font_family=FAMILY,font_size_pt=SIZE,symbol_fallback=None,
                font_sha256=hashlib.sha256(FONT_FILE.read_bytes()).hexdigest(),
                visible_texts=len(visible),all_text_base_sizes_24=True,top_titles_removed=True)


def save(fig,output,stem,dpi=140):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    audit=apply(fig)
    for extension in ('png','svg'):
        options={'metadata':{'Date':None}} if extension=='svg' else {}
        fig.savefig(output/(stem+'.'+extension),dpi=dpi,bbox_inches='tight',pad_inches=.12,**options)
    (output/(stem+'.style.json')).write_text(json.dumps(audit,indent=2)+'\n')
    return output/(stem+'.png')
