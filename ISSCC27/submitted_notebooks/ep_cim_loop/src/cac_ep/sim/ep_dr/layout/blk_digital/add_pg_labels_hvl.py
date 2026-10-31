#!/usr/bin/env python3
# [layout/blk_digital 사본 10/28: ep_dr/digital/add_pg_labels_hvl.py 에서 입출력 폴더만 현재 폴더 (work_<top>/) 로]
# [ep_dr/digital 사본 10/28: ep_demo/digital/add_pg_labels.py 를 고침] hvl 블록용.
#   바꾼 것: well/implant 메움 (heal) 과 areaid.ce 는 scl 9T 셀 때문에 넣은 것 → 기본으로 끔 (DR_HEAL=1, DR_CE=1 로 켬).
#   hvl 셀 시험 (layout/hvl_test.py, digital/hvl_cells_test.py) 은 둘 없이 DRC 밀도만이었다. ADDHX1 poly.2b 고침은 scl 셀 전용 → 뺌.
#   핀 dt16 → dt20 복사와 VDD/VSS 이름표는 그대로.
# add_pg_labels.py -- put VDD/VSS texts on the P&R GDS so LVS can name the
# digibank_l1_pnr.gds); the PG geometry is read from <top>_pg_shapes.txt that
# Run: klayout -b -r add_pg_labels.py  (DR_TOP env selects the block)
import os
try:
    import pya
except ImportError:
    import klayout.db as pya

TOP = os.environ['DR_TOP']
HERE = os.getcwd()
LMAP = {'met1': (68, 5), 'met2': (69, 5), 'met3': (70, 5),
        'met4': (71, 5), 'met5': (72, 5)}

want = {}
try:
    for ln in open(os.path.join(HERE, TOP + '_pg_shapes.txt')):
        t = ln.replace('{', ' ').replace('}', ' ').split()
        if len(t) < 6 or t[0] in want:
            continue
        net, x0, y0, x1, y1, lyr = t[0], *map(float, t[1:5]), t[5]
        if lyr in LMAP:
            want[net] = ((x0 + x1) / 2.0, (y0 + y1) / 2.0, lyr)
except FileNotFoundError:
    pass
if len(want) < 2:
    # fall back to the DEF SPECIALNETS section (dbu = 1000/um in DEF units)
    import re
    txt = open(os.path.join(HERE, TOP + '_pnr.def')).read()
    m = re.search(r'^SPECIALNETS.*?^END SPECIALNETS', txt, re.S | re.M)
    if m:
        cur = None
        for ln in m.group(0).splitlines():
            t = ln.split()
            if t and t[0] == '-':
                cur = t[1]
            if cur in ('VDD', 'VSS') and cur not in want:
                sm = re.search(r'\+ (?:ROUTED|FIXED|COVER)\s+(met\d)\s+(\d+)\s+'
                               r'(?:\+ SHAPE \w+\s+)?\(\s*(-?\d+)\s+(-?\d+)\s*\)'
                               r'\s*\(\s*(-?\d+|\*)\s+(-?\d+|\*)\s*\)', ln)
                if sm:
                    lyr, w, x0, y0, x1, y1 = sm.groups()
                    x0, y0 = int(x0) / 1000.0, int(y0) / 1000.0
                    x1 = x0 if x1 == '*' else int(x1) / 1000.0
                    y1 = y0 if y1 == '*' else int(y1) / 1000.0
                    want[cur] = ((x0 + x1) / 2.0, (y0 + y1) / 2.0, lyr)
if len(want) < 2:
    raise SystemExit('FATAL: found PG shapes for %s only' % list(want))

ly = pya.Layout()
ly.read(os.path.join(HERE, TOP + '_pnr.gds'))
top = ly.top_cells()[0]

HEAL = os.environ.get('DR_HEAL', '0') == '1'
CE = os.environ.get('DR_CE', '0') == '1'
regs = {}
if HEAL:
    # WELL / IMPLANT HEALING.  The deck's own notes on these rules read "Manual
    # merge wells if less than minimum" -- std-cell abutment leaves sub-minimum
    # nwell/nsdm/psdm gaps and slivers between neighbouring cells and fillers
    # (measured: CDR.nwell.2a.lv x15, CDR.psd.1a x19, CDR.psd.2 x13).  A
    # morphological CLOSE (grow+shrink) drawn at top level merges them exactly as
    # the deck asks.  Patches only ADD the closed-minus-original difference.
    SPEC = (((64, 20), 640, 840, 1270, None),    # nwell: minw 0.84, space 1.27
            ((93, 44), 195, 380, 380, (94, 20)),  # nsdm
            ((94, 20), 195, 380, 380, (93, 44)))  # psdm
    regs = {}
    for (lyr, dt), d, minw, mins, other in SPEC:
        regs[(lyr, dt)] = pya.Region(top.begin_shapes_rec(ly.layer(lyr, dt))).merged()
    # implant patches must NEVER touch diffusion/tap of the opposite type: a psdm
    # patch over n-type diff creates bogus pSourceDrain slivers (measured:
    # "Malformed device ... too many pins" + nwell stamped by a signal net)
    # HALO: 50 nm, not 200.  Only OVERLAP is illegal (psd.8); the old 200 nm halo
    # reached from the row taps (tap top +200) exactly into the patch band above
    # psdm and clipped the close-fill there, leaving 60 nm nsdm notches/teeth at
    # the filler seams (measured on digibank_dr: psd.2 x44 + psd.1b x23, marker
    # top y == tap top + 200 at every site).  50 nm keeps the no-overlap guard.
    _difftap = (pya.Region(top.begin_shapes_rec(ly.layer(65, 20)))
                + pya.Region(top.begin_shapes_rec(ly.layer(65, 44)))).merged()

    def _marks(check, grow=0):
        # ORTHOGONAL, GRID-SNAPPED bounding boxes of the violation markers -- raw
        # marker polygons carry off-grid vertices and 45-degree edges (measured:
        # x.1b x50 + x.3.psdm x33 from the first patch attempt)
        m = pya.Region()
        for ep in check.each():
            b = ep.polygon(0).bbox().enlarged(grow, grow)
            m.insert(pya.Box((b.left // 5) * 5, (b.bottom // 5) * 5,
                             -(-b.right // 5) * 5, -(-b.top // 5) * 5))
        return m

    # SEQUENTIAL healing: each layer's grow avoids the counterpart's CURRENT
    # (already-patched) region, so nsdm and psdm patches can never claim the same
    # ground (the earlier parallel version measured psd.10b x14 overlaps).
    for (lyr, dt), d, minw, mins, other in SPEC:
        li = ly.layer(lyr, dt)
        reg = regs[(lyr, dt)]
        r = reg.dup()
        for it in range(4):
            r = (r.sized(d).sized(-d)).merged()          # close sub-min gaps
            viol = (_marks(r.width_check(minw), minw // 2 + 5)
                    + _marks(r.space_check(mins), minw // 2 + 5))
            if not viol.is_empty():
                r = (r + viol).merged()
            if other:
                # additions must not OVERLAP the counterpart implant (psd.10) and
                # must stay off any diff/tap the original implant did not cover;
                # original geometry stays untouched (legal abutments included)
                foreign = (_difftap - reg).sized(50)
                r = (reg + (r - regs[other] - foreign)).merged()
            if viol.is_empty():
                break
        resid_w = r.width_check(minw).count()
        resid_s = r.space_check(mins).count()
        patch = r - reg
        n = 0
        for p in patch.each():
            top.shapes(li).insert(p); n += 1
        regs[(lyr, dt)] = r
        print(f'healed {lyr}/{dt}: {n} patches, residual width {resid_w} '
              f'space {resid_s}')
n_sig = 0
for li in ly.layer_indexes():
    info = ly.get_info(li)
    if info.datatype == 5:
        n_sig += sum(1 for s in top.shapes(li).each() if s.is_text())
# NO drawing metal under them; extraction reads drawing only, so every pin
# x.5.m2 x109 = exactly the 109 met2 dt16 pin pads).  Copy pin -> drawing.
# met2/met3 ONLY: met1 dt16 are the CELL-INTERNAL pin markers, drawn larger
# than the real pin metal -- copying them bridged unrelated met1 inside cells
# (measured: "Malformed device ... too many pins", nwell stamped by acc[146])
for l in (69, 70):
    r16 = pya.Region(top.begin_shapes_rec(ly.layer(l, 16)))
    n = 0
    for p in r16.each():
        top.shapes(ly.layer(l, 20)).insert(p); n += 1
    print(f'pin dt16 -> dt20 layer {l}: {n} pads')

if CE:
    # areaid.ce (81/2, "memory core id") over the placed core.  The deck splits
    # difftap/licon/poly/npc checks into core vs notcore and the abutted-row
    # patterns of the scl cells only satisfy the CORE variants (measured: bare
    # cells clean, the 70%-density bank threw licon.8 x70 / licon.18 x46 / npc.4
    # x24 / difftap.* -- all "outside areaid.ce" rules).
    _core = pya.Box()
    for inst in top.each_inst():
        _core += inst.bbox()
    # the core box must also COVER the healed implant/well geometry: the deck
    # splits every implant shape by the areaid.ce edge and width-checks the
    # fragments separately, so a legal 0.39 um psdm heal tab sliced at the old
    # inst-bbox+200 edge measured as psd.1a x4 (0.135 outside) + psd.1b x4
    # (0.255 inside) on dig_ch_dr.  Taking the bbox of nwell/nsdm/psdm too keeps
    # every implant shape strictly inside one region.
    for _r in regs.values():
        _core += _r.bbox()
    if not _core.empty():
        top.shapes(ly.layer(81, 2)).insert(_core.enlarged(200, 200))
        print(f'areaid.ce over core {_core.enlarged(200,200)}')

# healed-but-unlabelled copy for the top assembler (which names the PG nets
# itself: the bank's VDD is `vdd_dig` at macro level)
ly.write(os.path.join(HERE, TOP + '_heal.gds'))
for net, (x, y, lyr) in want.items():
    li = ly.layer(*LMAP[lyr])
    top.shapes(li).insert(pya.Text(net, pya.Trans(int(round(x * 1000)),
                                                  int(round(y * 1000)))))
    print(f'label {net} on {lyr} at ({x:.3f},{y:.3f})')
print(f'existing signal-pin texts: {n_sig}')
out = os.path.join(HERE, TOP + '_lbl.gds')
ly.write(out)
print('wrote', out)
