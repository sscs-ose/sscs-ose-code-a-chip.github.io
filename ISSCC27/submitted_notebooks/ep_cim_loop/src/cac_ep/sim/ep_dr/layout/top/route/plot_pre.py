"""chip_pre.def 의 특수 넷·전원 도형과 블록 경계를 그림으로 (확인용, 내부 라벨 없음)."""
import re, sys, json
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
H = sys.argv[1] if len(sys.argv) > 1 else 'chip/chip_pre.def'
P = json.load(open('../place/place_real.json'))
txt = open(H).read()
sn = txt[txt.index('SPECIALNETS'):txt.index('END SPECIALNETS')]
col = {'VDD': '#c0c0c0', 'VSS': '#909090', 'VWH': '#500000', 'VWLO': '#a04040', 'vw_f': '#3060a0', 'vw_n': '#6090d0',
       'VRAILP': '#208040', 'VRAILM': '#60b060', 'VCM': '#8040a0'}
fig, ax = plt.subplots(figsize=(14, 12))
for n, v in P['instances'].items():
    ax.add_patch(Rectangle((v['x'], v['y']), v['w'], v['h'], fill=False, lw=0.8, ec='k'))
    ax.text(v['x'] + v['w'] / 2, v['y'] + v['h'] / 2, n, ha='center', va='center', fontsize=7)
for blk in re.split(r'\n- ', sn)[1:]:
    net = blk.split()[0]
    if net not in col:
        continue
    for l, a, b, c, d in re.findall(r'\+ RECT (met[45]) \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)', blk):
        a, b, c, d = (int(x) / 1000 for x in (a, b, c, d))
        ax.add_patch(Rectangle((a, b), c - a, d - b, fc=col[net], ec='none', alpha=0.35 if l == 'met5' else 0.8))
ax.set_xlim(-10, P['core']['w'] + 10); ax.set_ylim(-10, P['core']['h'] + 10); ax.set_aspect('equal')
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=c, label=n) for n, c in col.items()], loc='upper right', fontsize=8)
fig.savefig(sys.argv[2] if len(sys.argv) > 2 else 'chip/pre_specials.png', dpi=110, bbox_inches='tight')
