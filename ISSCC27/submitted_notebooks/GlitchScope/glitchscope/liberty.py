from __future__ import annotations
from dataclasses import dataclass
import re
from pathlib import Path
from typing import Dict, Tuple, Optional
from .delay import DelayResult
from .model import ps_to_fs, fs_to_ps

@dataclass(frozen=True)
class Table2D:
    index_1: Tuple[float, ...]
    index_2: Tuple[float, ...]
    values: Tuple[Tuple[float, ...], ...]

@dataclass(frozen=True)
class TimingArc:
    output_pin: str
    related_pin: str
    timing_sense: str
    timing_type: str
    when: str
    cell_rise: Table2D
    cell_fall: Table2D
    rise_transition: Table2D
    fall_transition: Table2D

@dataclass(frozen=True)
class LibertyPin:
    name: str
    direction: str
    capacitance_ff: Optional[float]
    function: str

@dataclass(frozen=True)
class LibertyCell:
    name: str
    pins: Dict[str, LibertyPin]
    pin_capacitance: Dict[str, float]
    timing_arcs: Tuple[TimingArc, ...]
    # sequential: {"kind": "ff"|"latch", "state": (IQ, IQN), "clocked_on", "next_state",
    #              "clear", "preset"}  (None for combinational cells)
    seq: Optional[dict] = None

@dataclass(frozen=True)
class LibertyLibrary:
    time_unit_ps: float
    capacitance_unit_ff: float
    cells: Dict[str, LibertyCell]
    name: str = ""
    voltage_unit_v: float = 1.0
    nom_voltage: Optional[float] = None

COMBINATIONAL_TIMING_TYPES = {"", "combinational"}


def _strip_comments(s):
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    return re.sub(r'//.*?$', '', s, flags=re.M)


def _balanced(text, start):
    depth = 0
    in_string = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[start+1:i], i+1
    raise ValueError('Unbalanced Liberty braces')


def _blocks(text, key):
    pat = re.compile(r'\b' + re.escape(key) + r'\s*\(\s*([^)]*?)\s*\)\s*\{')
    pos = 0
    while True:
        m = pat.search(text, pos)
        if not m:
            break
        body, end = _balanced(text, m.end()-1)
        arg = m.group(1).strip().strip('"')
        yield arg, body
        pos = end


def _attr(body, name, default=None):
    m = re.search(r'\b' + re.escape(name) + r'\s*:\s*([^;]+);', body)
    if not m:
        return default
    return m.group(1).strip().strip('"')


def _csv(body, key):
    m = re.search(r'\b' + re.escape(key) + r'\s*\(\s*"([^"]+)"\s*\)\s*;', body, re.S)
    if not m:
        raise ValueError('Missing ' + key)
    return tuple(float(x.strip()) for x in m.group(1).split(','))


_TEMPLATES = {}     # template name -> (variable_1, variable_2, index_1, index_2)


def load_templates(text):
    """Register lu_table_template / power_lut_template groups (index defaults, variable order)."""
    for kind in ("lu_table_template", "power_lut_template"):
        for name, body in _blocks(text, kind):
            def opt(k):
                try:
                    return _csv(body, k)
                except ValueError:
                    return None
            _TEMPLATES[name.strip().strip('"')] = (_attr(body, "variable_1", ""), _attr(body, "variable_2", ""),
                                                   opt("index_1"), opt("index_2"))


def _table(body, template=None):
    """2-D NLDM / power table, always returned as [input transition][output capacitance];
    missing indices come from the template, capacitance-first templates are transposed."""
    tv = _TEMPLATES.get((template or "").strip().strip('"'))
    try:
        i1 = _csv(body, 'index_1')
    except ValueError:
        if not tv or tv[2] is None:
            raise
        i1 = tv[2]
    try:
        i2 = _csv(body, 'index_2')
    except ValueError:
        if not tv or tv[3] is None:
            raise
        i2 = tv[3]
    m = re.search(r'\bvalues\s*\((.*?)\)\s*;', body, re.S)
    if not m:
        raise ValueError('Missing values')
    rows = re.findall(r'"([^"]+)"', m.group(1))
    vals = tuple(tuple(float(x.strip()) for x in row.split(',')) for row in rows)
    if tv and "capacitance" in (tv[0] or "") and "transition" in (tv[1] or ""):
        i1, i2 = i2, i1
        vals = tuple(zip(*vals))
    if len(i1) < 2 or len(i2) < 2:
        raise ValueError('B1 requires 2-D tables with >=2 points per dimension')
    if len(vals) != len(i1) or any(len(row) != len(i2) for row in vals):
        raise ValueError('Table shape mismatch')
    return Table2D(i1, i2, vals)


def _named_optional(body, name):
    m = re.search(r'\b' + re.escape(name) + r'\s*\(([^)]*)\)\s*\{', body)
    if not m:
        return None
    q, _ = _balanced(body, m.end()-1)
    try:
        return _table(q, m.group(1))
    except ValueError:
        return None


def _parse_time_unit(token):
    s = token.strip().strip('"').lower()
    m = re.fullmatch(r'([0-9.eE+-]+)\s*(fs|ps|ns|us)', s)
    if not m:
        raise ValueError('Unsupported time unit ' + s)
    scale = float(m.group(1))
    unit = m.group(2)
    factor_ps = {'fs':0.001, 'ps':1.0, 'ns':1000.0, 'us':1_000_000.0}[unit]
    return scale * factor_ps


def _parse_cap_unit(text):
    m = re.search(r'\bcapacitive_load_unit\s*\(\s*([0-9.eE+-]+)\s*,\s*"?([a-zA-Z]+)"?\s*\)\s*;', text)
    if not m:
        raise ValueError('Missing capacitive_load_unit')
    scale = float(m.group(1))
    unit = m.group(2).lower()
    factor_ff = {'ff':1.0, 'pf':1000.0}.get(unit)
    if factor_ff is None:
        raise ValueError('Unsupported capacitance unit ' + unit)
    return scale * factor_ff


def parse_liberty_text(text):
    text = _strip_comments(text)
    load_templates(text)
    m = re.search(r'\btime_unit\s*:\s*"?\s*([0-9.]*\s*[a-z]+)\s*"?\s*;', text)
    if not m:
        raise ValueError('Missing time_unit')
    tps = _parse_time_unit(m.group(1))
    cff = _parse_cap_unit(text)

    cells = {}
    for cell_name, cell_body in _blocks(text, 'cell'):
        pins = {}
        caps = {}
        arcs = []
        for pin_name, pin_body in _blocks(cell_body, 'pin'):
            direction = (_attr(pin_body, 'direction', '') or '').strip().strip('"')
            cap = _attr(pin_body, 'capacitance')
            cap_ff = None if cap is None else float(cap) * cff
            function = _attr(pin_body, 'function', '') or ''
            pins[pin_name] = LibertyPin(pin_name, direction, cap_ff, function)
            if cap_ff is not None:
                caps[pin_name] = cap_ff

            # Timing blocks reside under the output pin in ordinary Liberty.
            for _, tb in _blocks(pin_body, 'timing'):
                related = (_attr(tb, 'related_pin', '') or '').strip().strip('"')
                sense = (_attr(tb, 'timing_sense', 'non_unate') or 'non_unate').strip().strip('"')
                ttype = (_attr(tb, 'timing_type', '') or '').strip().strip('"')
                when = (_attr(tb, 'when', '') or '').strip().strip('"')

                cr = _named_optional(tb, 'cell_rise')
                cf = _named_optional(tb, 'cell_fall')
                rt = _named_optional(tb, 'rise_transition')
                ft = _named_optional(tb, 'fall_transition')

                # B1 stores only complete NLDM combinational propagation arcs.
                # Sequential constraints, pulse width checks, and incomplete
                # three-state arcs are intentionally excluded from propagation.
                if not related or ttype not in COMBINATIONAL_TIMING_TYPES:
                    continue
                if None in (cr, cf, rt, ft):
                    continue
                arcs.append(TimingArc(pin_name, related, sense, ttype, when, cr, cf, rt, ft))

        seq = None
        for kind in ("ff", "latch"):
            for hdr, body in _blocks(cell_body, kind):
                names = tuple(re.findall(r'[A-Za-z_][\w]*', hdr))
                seq = {"kind": kind, "state": names}
                for a in ("clocked_on", "next_state", "clear", "preset", "enable", "data_in"):
                    v = _attr(body, a)
                    if v is not None:
                        seq[a] = v.strip().strip('"').strip()
        cells[cell_name] = LibertyCell(cell_name, pins, caps, tuple(arcs), seq)

    if not cells:
        raise ValueError('No cells parsed')
    lm = re.search(r'\blibrary\s*\(\s*"?([^")]+)"?\s*\)', text)
    vu = re.search(r'\bvoltage_unit\s*:\s*"?\s*([0-9.eE+-]*)\s*(m?V)\s*"?\s*;', text)
    vscale = (float(vu.group(1) or 1) * (1e-3 if vu.group(2) == "mV" else 1.0)) if vu else 1.0
    nv = re.search(r'\bnom_voltage\s*:\s*([0-9.eE+-]+)\s*;', text)
    return LibertyLibrary(tps, cff, cells, lm.group(1).strip() if lm else "", vscale,
                          float(nv.group(1)) * vscale if nv else None)


_TEXT_CACHE = {}


def read_liberty_text(path):
    """Text of a Liberty file (plain or .gz), cached by path and modification time."""
    p = Path(path)
    key = (str(p), p.stat().st_mtime)
    if key not in _TEXT_CACHE:
        if p.suffix == ".gz":
            import gzip
            with gzip.open(p, "rt", errors="replace") as fh:
                _TEXT_CACHE[key] = fh.read()
        else:
            _TEXT_CACHE[key] = p.read_text(errors="replace")
    return _TEXT_CACHE[key]


def parse_liberty_file(path):
    return parse_liberty_text(read_liberty_text(path))


def _bracket(xs, x):
    if len(xs) < 2:
        raise ValueError('Need at least 2 table points')
    if x <= xs[0]:
        return 0, 1, xs[0]
    if x >= xs[-1]:
        return len(xs)-2, len(xs)-1, xs[-1]
    for i in range(len(xs)-1):
        if xs[i] <= x <= xs[i+1]:
            return i, i+1, x
    raise AssertionError('Unreachable interpolation bracket')


def bilinear(t, x, y):
    i0,i1,xc = _bracket(t.index_1, x)
    j0,j1,yc = _bracket(t.index_2, y)
    x0,x1 = t.index_1[i0], t.index_1[i1]
    y0,y1 = t.index_2[j0], t.index_2[j1]
    tx = 0.0 if x1 == x0 else (xc-x0)/(x1-x0)
    ty = 0.0 if y1 == y0 else (yc-y0)/(y1-y0)
    q00=t.values[i0][j0]; q01=t.values[i0][j1]
    q10=t.values[i1][j0]; q11=t.values[i1][j1]
    return (q00*(1-ty)+q01*ty)*(1-tx) + (q10*(1-ty)+q11*ty)*tx


# ---- Liberty `when` subset -------------------------------------------------
# B1 deliberately supports the Boolean syntax used for combinational side-pin
# conditions: !, &, |, ^, parentheses, identifiers, and constants 0/1.

_TOKEN = re.compile(r"\s*([A-Za-z_][A-Za-z0-9_\[\].]*|[01]|&&|\|\||[!&|^()*+']|&|\|)")

def _tokens(expr):
    """Liberty Boolean syntax: ! ' (postfix) NOT; & * AND (also juxtaposition); | + OR; ^ XOR."""
    pos=0; raw=[]
    expr = expr.strip()
    while pos < len(expr):
        if expr[pos:].strip() == "":
            break
        m=_TOKEN.match(expr,pos)
        if not m:
            raise ValueError('Unsupported when expression near: '+expr[pos:])
        raw.append(m.group(1)); pos=m.end()
    raw = [{'*': '&', '&&': '&', '+': '|', '||': '|'}.get(t, t) for t in raw]
    # postfix ' -> prefix ! on the preceding operand (identifier, constant or parenthesised group)
    out = []
    for t in raw:
        if t == "'":
            if out and out[-1] == ')':
                depth, j = 0, len(out) - 1
                while j >= 0:
                    depth += out[j] == ')'; depth -= out[j] == '('
                    if depth == 0:
                        break
                    j -= 1
                out.insert(j, '!')
            else:
                out.insert(len(out) - 1, '!')
            continue
        out.append(t)
    # implicit AND between adjacent operands: "A B", "A (B)", ") (", ") A", "A !B"
    res = []
    for t in out:
        if res:
            prev = res[-1]
            prev_operand = prev == ')' or re.fullmatch(r'[A-Za-z_0-9][A-Za-z0-9_\[\].]*', prev)
            starts = t in ('(', '!') or re.fullmatch(r'[A-Za-z_0-9][A-Za-z0-9_\[\].]*', t)
            if prev_operand and starts:
                res.append('&')
        res.append(t)
    return res

class _BoolParser:
    def __init__(self,toks,vals): self.t=toks; self.i=0; self.v=vals
    def peek(self): return self.t[self.i] if self.i<len(self.t) else None
    def take(self,x=None):
        q=self.peek()
        if q is None or (x is not None and q!=x): raise ValueError('Malformed when expression')
        self.i+=1; return q
    def parse(self):
        v=self.or_()
        if self.peek() is not None: raise ValueError('Trailing when tokens')
        return int(v)
    def or_(self):
        v=self.xor_()
        while self.peek()=='|':
            self.take('|'); rhs=self.xor_(); v=int(bool(v) or bool(rhs))
        return v
    def xor_(self):
        v=self.and_()
        while self.peek()=='^': self.take('^'); v=int(bool(v) ^ bool(self.and_()))
        return v
    def and_(self):
        v=self.unary()
        while self.peek()=='&':
            self.take('&'); rhs=self.unary(); v=int(bool(v) and bool(rhs))
        return v
    def unary(self):
        if self.peek()=='!': self.take('!'); return 1-self.unary()
        if self.peek()=='(':
            self.take('('); v=self.or_(); self.take(')'); return v
        q=self.take()
        if q in ('0','1'): return int(q)
        if q not in self.v: raise KeyError('when pin value missing: '+q)
        return int(self.v[q])

def eval_when(expr, pin_values):
    if not expr:
        return True
    return bool(_BoolParser(_tokens(expr), pin_values).parse())


def _sense_expected_output_transition(sense, input_transition):
    if input_transition is None or sense == 'non_unate':
        return None
    old,new = input_transition
    if old == new:
        raise ValueError('Input transition must toggle')
    inp_rise = new > old
    if sense == 'positive_unate':
        return 1 if inp_rise else 0
    if sense == 'negative_unate':
        return 0 if inp_rise else 1
    raise ValueError('Unsupported timing_sense '+sense)


class LibertyDelayProvider:
    def __init__(self, lib):
        self.lib = lib

    def _output_pin(self, cell, lc):
        if getattr(cell, 'library_output_pin', ''):
            return cell.library_output_pin
        outs = sorted({a.output_pin for a in lc.timing_arcs})
        if len(outs) != 1:
            raise ValueError('B1 requires library_output_pin when cell has !=1 timed output')
        return outs[0]

    def select_arc(self, cell, new_output, related_pin=None,
                   pin_values=None, input_transition=None):
        """
        Select exactly one active combinational propagation arc.

        B5 policy:
        1. restrict by output pin and related input pin;
        2. evaluate Liberty ``when`` using the current pin state;
        3. when an input transition is known, remove unate arcs whose
           timing_sense is inconsistent with the observed logical output
           transition;
        4. require exactly one remaining arc.

        This resolves real XOR/XNOR mixed positive/negative-unate arc sets
        without guessing.  Duplicate same-sense or non-unate ambiguities
        remain fail-closed.
        """
        libname = cell.library_cell or cell.kind
        if libname not in self.lib.cells:
            raise KeyError('Liberty cell not found: '+libname)
        lc = self.lib.cells[libname]
        outpin = self._output_pin(cell, lc)

        if related_pin is None:
            if len(cell.inputs) != 1:
                raise ValueError('B1 multi-input cell requires unambiguous related_pin')
            related_pin = next(iter(cell.inputs))

        candidates = [
            a for a in lc.timing_arcs
            if a.output_pin == outpin and a.related_pin == related_pin
        ]

        if pin_values is not None:
            candidates = [a for a in candidates if eval_when(a.when, pin_values)]
        else:
            # No pin state means unconditional arcs only; fail closed instead
            # of guessing a conditional arc.
            candidates = [a for a in candidates if not a.when]

        if not candidates:
            raise ValueError(
                'No active combinational Liberty arc for %s %s->%s' %
                (libname, related_pin, outpin)
            )

        # B5: mixed-sense multi-arc disambiguation.
        if input_transition is not None:
            consistent = []
            for a in candidates:
                expected = _sense_expected_output_transition(
                    a.timing_sense, input_transition
                )
                # non_unate returns None and therefore remains a candidate.
                if expected is None or expected == int(new_output):
                    consistent.append(a)
            candidates = consistent

        if not candidates:
            raise ValueError(
                'No timing_sense-consistent Liberty arc for %s %s->%s '
                'input_transition=%s new_output=%s' %
                (libname, related_pin, outpin, input_transition, new_output)
            )

        if len(candidates) != 1:
            sig = [
                (a.timing_sense, a.when)
                for a in candidates
            ]
            raise ValueError(
                'Ambiguous active Liberty arcs for %s %s->%s after '
                'timing_sense filtering: %s' %
                (libname, related_pin, outpin, sorted(sig))
            )

        a = candidates[0]
        expected = _sense_expected_output_transition(
            a.timing_sense, input_transition
        )
        if expected is not None and expected != int(new_output):
            raise ValueError(
                'timing_sense/output transition mismatch for %s %s' %
                (libname, related_pin)
            )
        return a

    def delay(self, cell, new_output, input_slew_fs=0, load_ff=0.0,
              related_pin=None, pin_values=None, input_transition=None):
        a = self.select_arc(
            cell, new_output,
            related_pin=related_pin,
            pin_values=pin_values,
            input_transition=input_transition,
        )
        x = fs_to_ps(input_slew_fs) / self.lib.time_unit_ps
        y = load_ff / self.lib.capacitance_unit_ff
        dt = a.cell_rise if new_output else a.cell_fall
        st = a.rise_transition if new_output else a.fall_transition
        d = bilinear(dt, x, y)
        s = bilinear(st, x, y)
        return DelayResult(
            ps_to_fs(d*self.lib.time_unit_ps),
            ps_to_fs(s*self.lib.time_unit_ps),
            'LIBERTY_B1_NLDM'
        )
