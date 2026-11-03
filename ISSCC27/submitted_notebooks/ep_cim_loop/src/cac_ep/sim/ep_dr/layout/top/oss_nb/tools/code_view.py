"""Show the part of a generator (or RTL file) that describes one block, for sections 5 and 6 of the notebook.
The generator is only read, never run or imported. Comments in Korean are left out; English notes are added at the end of
chosen lines (BLOCKS below), so the file on disk stays as it was when the layout passed DRC and LVS.
    block(name, ep)            one entry of BLOCKS (ep = the ep_dr folder)
    show(path, names, notes)   top-level assignments / functions with these names
    show_lines(path, a, b, notes, lang)   a line range"""
import ast
import re
from pathlib import Path

HANGUL = re.compile('[ㄱ-ㆎ가-힣]')


def _clean(text, mark):
    """drop comments written in Korean (the notebook is in English); keep the code"""
    out = []
    for line in text.splitlines():
        code, sep, comment = line.partition(mark)
        if sep and HANGUL.search(comment):
            if not code.strip():
                continue
            line = code.rstrip()
        out.append(line)
    return out


def _annotate(lines, notes, mark):
    """append '<mark> note' to the first line that contains each key (in order)"""
    lines = list(lines)
    pos = 0
    for key, note in (notes or {}).items():
        for i in range(pos, len(lines)):
            if key in lines[i]:
                code = lines[i].split(f' {mark} ')[0].rstrip()          # an English comment already there is replaced
                lines[i] = f'{code:<70}  {mark} {note}'
                pos = i + 1
                break
        else:
            raise KeyError(f'note anchor not found: {key!r}')
    return '\n'.join(lines)


def _display(text, lang, title, notes):
    mark = '//' if lang == 'verilog' else '#'
    body = _annotate(_clean(text, mark), notes, mark)
    try:
        from IPython.display import Code, Markdown, display
        display(Markdown(f'`{title}`'))
        display(Code(body, language=lang))
    except ImportError:
        print(f'--- {title}\n{body}')


def show(path, names, notes=None):
    path = Path(path)
    src = path.read_text()
    want = set(names)
    parts = []
    for node in ast.parse(src).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            hit = node.name in want
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            tg = node.targets if isinstance(node, ast.Assign) else [node.target]
            hit = any(isinstance(t, ast.Name) and t.id in want for t in tg)
        else:
            hit = False
        if hit:
            parts.append((node.lineno, node.end_lineno, ast.get_source_segment(src, node)))
    assert len(parts) == len(want), f'{path.name}: found {len(parts)} of {sorted(want)}'
    lines = ', '.join(f'{a}–{b}' for a, b, _ in parts)
    _display('\n\n'.join(p[2] for p in parts), 'python', f'{path.name}, lines {lines}', notes)


def show_lines(path, first, last, notes=None, lang='python'):
    path = Path(path)
    text = '\n'.join(path.read_text().splitlines()[first - 1:last])
    _display(text, lang, f'{path.name}, lines {first}–{last}', notes)


# ── what each section shows: (kind, file relative to ep_dr, names or (first, last), notes) ──
BLOCKS = {
    'arr': ('lines', 'layout/top/strap/gen_arr_1t1r_w3s.py', (58, 83), {
        "C = ly.create_cell('c1t1r_w3')": 'one 1T1R cell; every number below is a coordinate in nm',
        "b('diff', 180, 180, 2000, 1680)": 'active area of the access NMOS, n+ implant, 5 V region (hvi)',
        'for g0, g1 in (G1, G2):': 'two poly gates (two fingers) ...',
        "b('poly', G1[0], 1810, G2[1], 1960)": '... joined above the device: the word line of this row',
        "b('poly', 525, 1855, 855, 2185)": 'gate contact stack: poly -> licon -> li -> mcon -> met1 -> via -> met2',
        'YS = (': 'source / drain: three diffusion strips, four contacts each',
        "b('m1', -460, 345, 2020, 635)": 'met1 joining the two outer strips (shared terminal of the two fingers)',
        "b('m1', 945, 1145, 2665, 1435)": 'met1 from the middle strip to the RRAM',
        "b('via', 2430, 1215, 2580, 1365)": 'the RRAM cell: via1 with the RRAM marker, between met1 and met2',
        "b('m2', 2345, -620, 2665, 1300)": 'met2 from the RRAM top electrode to the cell line',
        "b('tap', 180, -600, 2000, -190)": 'p+ tap: body contact of the NMOS (VSS)',
    }),
    'clamp': ('lines', 'digital/macros/gen_clamp.py', (70, 117), {
        "box('nwell', NW_IN, 1.10, W - NW_IN, 3.41)": 'diode DDb: p+ diffusion (anode) in its own n-well (cathode)',
        "box('met1', 0, 1.55, W, 2.10)": 'VRAILP rail (met1, runs through the whole column block)',
        'rx0 = round(': 'two 100-ohm n+ diffusion resistors, one per diode',
        "box('nsdm', rx0 - 0.125, 3.775, rx1 + 0.125, 6.525)": 'one n+ implant over both resistors',
        "box('li1', xl - 0.08, 3.995, xl + CUT + 0.08, 6.305)": 'li1: column node -> left end of both resistors',
        "box('met2', xm0, 0, xm1, HT)": 'column pin: a met2 strip over the full height (abuts the array column)',
        "box('nwell', NW_IN, 6.85, W - NW_IN, HT - NW_IN)": 'diode DDa: same structure, cathode on VRAILM',
        "box('met1', 0, 8.33, W, 8.88)": 'VRAILM rail',
        'pins = {': 'pins for LVS and for the router',
    }),
    'hog': ('names', 'sern_hog_classab_opamp/sim/layout/gen_hog.py', ['ROWS', 'CDLDEV'], {
        'ROWS = [': 'the op-amp as rows of transistors: (name, type, islands, ...); the drawing order is set right after',
        '("mirror_a"': 'isl(L, finger W, source/drain nets left to right, gate nets, device names)',
        '("pair_a"': 'input pair split over two rows, ABBA / BAAB, with dummies (~) at both ends',
        'CDLDEV = {': 'the netlist the layout must match in LVS: device -> (d g s b, type, W, L)',
    }),
    'sa': ('names', 'layout/blk_wu/wu_cells.py', ['SA_DEV', 'SA_ROWS'], {
        'SA_DEV = {': 'the circuit: device -> ("drain gate source", n/p, W, L)',
        '"M1": ("sp inp tl"': 'input pair M1 / M2',
        '"L1p1"': 'NOR2 SR latch after the two inverters',
        'SA_ROWS = [': 'the layout: four rows of diffusion islands (bottom to top)',
        'isl(1.0, 2.0, ["sp", "tl", "sn"': 'input pair interleaved ABBA, sharing the tail node tl',
        '("p_cc"': 'cross-coupled PMOS and the four reset switches (clk)',
    }),
    'pre': ('names', 'layout/blk_wu/wu_cells.py', ['PRE_DEV', 'PRE_ROWS'], {
        'PRE_DEV = {': 'tail, input pair, diode-connected PMOS loads',
        'PRE_ROWS = [': 'three rows: tail (4 fingers), input pair (ABBA), loads',
    }),
    'dlatch': ('names', 'layout/blk_wu/wu_cells.py', ['DL_DEV', 'DL_ROWS'], {
        'DL_DEV = {': 'TG (Tn, Tp) from d to the storage node s, then two inverters',
        'DL_ROWS = [': 'one NMOS row and one PMOS row',
    }),
    'nudge': ('names', 'layout/blk_analog/gen_nudge_bias.py', ['tg_devs', 'nudge_inj'], {
        'def tg_devs': 'one switch = transmission gate: NMOS W 2 + PMOS W 4',
        'for j in range(3):': 'one injector per output pair y_k (3 outputs)',
        't = [tg_devs(': 'SW1-SW4: route +beta / -beta to y+ or y- by the target bit',
        "dev(f'XMN{j}'": 'NMOS mirror branch (pulls beta) ...',
        "dev(f'XMP{j}'": '... and PMOS mirror branch (pushes beta)',
        "build_cell('nudge_inj'": 'place the devices in rows and route them (shared row-cell builder)',
    }),
    'data': ('lines', 'layout/blk_digital/rtl/data_blk.v', (24, 39), {
        'always @(posedge data_clk': 'shift register: one bit per data clock',
        'else       q <=': 'the new bit enters at q[0]',
        'if (dload) dl = q;': 'latches: transparent while load is high, hold otherwise',
        'assign ga': 'row drivers: input bit -> x+ / x- rails, only in READ',
        'assign sp': 'nudge switches: target bits -> SW1-SW4 enables',
    }),
    'rowl': ('lines', 'digital/rtl/rowl.v', (25, 37), {
        'wire s = t & sel_en;': 'this row is selected: token bit AND select enable',
        'assign wsel ': 'row -> write bus (program / verify, selected row)',
        'assign wz ': 'row -> 0 V (program / verify, other rows)',
        'assign sns ': 'row -> sense bus (sensing, selected row)',
        'assign wlv ': 'word line -> VDD (READ, or verify of the selected row)',
        'assign wlw ': 'word line -> write voltage (program, selected row)',
        'assign wl0 ': 'word line -> VSS (all other cases)',
    }),
}


def block(name, ep):
    kind, rel, what, notes = BLOCKS[name]
    ep = Path(ep).resolve()
    path = (ep.parents[2] / rel) if rel.startswith('sern_hog_classab_opamp') else (ep / rel)
    if kind == 'names':
        show(path, what, notes)
    else:
        show_lines(path, *what, notes=notes, lang='verilog' if rel.endswith('.v') else 'python')
