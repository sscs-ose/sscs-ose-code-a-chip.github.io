"""Temporary special-net obstacles for pinned DRT partial routing.

Regular dbWire FIXED paths alone are not a routing obstacle contract in this
version. Retain the original wires; import conservative SWire copies only
while routing, then clear those copies before final validation/export.
"""
import re
from itertools import product


def patch_wires(box):
    """Cover an integer box exactly with positive-length, even-width wires.

    Odd dimensions use overlapping even rectangles, never rounded edges.
    Special-wire end caps are width/2 in the pinned DEF reader.
    """
    x1, y1, x2, y2 = box
    if min(x2-x1, y2-y1) < 4:
        raise ValueError('patch too narrow for positive-length special wires')
    def intervals(lo, hi):
        return [(lo, hi)] if (hi-lo) % 2 == 0 else [(lo, hi-1), (lo+1, hi)]
    result = []
    for (a, c), (b, d) in product(intervals(x1, x2), intervals(y1, y2)):
        boxes = [(a, b, c, d)]
        if c-a == d-b:
            half = ((c-a)//4)*2
            boxes = [(a, b, a+half, d), (a+half, b, c, d)]
        for left, bottom, right, top in boxes:
            width = min(right-left, top-bottom)
            if right-left > top-bottom:
                p = (left+width//2, bottom+width//2)
                q = (right-width//2, bottom+width//2)
            else:
                p = (left+width//2, bottom+width//2)
                q = (left+width//2, top-width//2)
            result.append((width, p, q))
    return result


def widths_from_tlef(text, units=1000):
    widths = {}
    for name, body in re.findall(r'(?ms)^LAYER (\S+)\s*\n(.*?)^END \1\s*$', text):
        if re.search(r'\bTYPE\s+ROUTING\s*;', body):
            match = re.search(r'\bWIDTH\s+([\d.]+)\s*;', body)
            if not match: raise ValueError('routing layer width missing: '+name)
            widths[name] = round(float(match[1])*units)
    if not all(name in widths for name in ('li1', 'met1', 'met2', 'met3', 'met4', 'met5')):
        raise ValueError('pinned SKY130 routing widths required')
    return widths


def as_special(text, widths):
    if re.search(r'\b(?:NONDEFAULTRULE|TAPER|MASK|POLYGON)\b', text):
        raise ValueError('unsupported fixed obstacle path; inspect geometry')
    # The measured source contains 719 explicit zero end extensions. Removing
    # them adds half-width end caps to TEMPORARY obstacles, conservatively.
    point = r'\(\s*(-?\d+|\*)\s+(-?\d+|\*)\s+(-?\d+)\s*\)'
    def endpoint(m):
        if int(m[3]) != 0: raise ValueError('nonzero custom end extension unsupported')
        return '( '+m[1]+' '+m[2]+' )'
    text = re.sub(point, endpoint, text)
    # Regular-net RECT patch wires are not accepted by this special-net DEF
    # reader. Represent each exact box as a positive-length special wire.
    def patch(m):
        indent, first, layer = m[1], m[2], m[3]
        ox, oy, dx1, dy1, dx2, dy2 = map(int, m.groups()[3:])
        x1, y1, x2, y2 = ox+dx1, oy+dy1, ox+dx2, oy+dy2
        wires = []
        for width, p, q in patch_wires((x1, y1, x2, y2)):
            prefix = first if not wires else 'NEW'
            wires.append(indent+prefix+' '+layer+' '+str(width)+' ( '+str(p[0])+' '+str(p[1])+' ) ( '+str(q[0])+' '+str(q[1])+' )')
        return '\n'.join(wires)
    text = re.sub(r'([ \t]*)(NEW|\+ FIXED)\s+(\S+)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+RECT\s+\(\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*\)', patch, text)
    if re.search(r'\bRECT\b', text): raise ValueError('unsupported remaining patch wire')
    def width(m):
        if m[2] not in widths: raise ValueError('unknown obstacle layer: '+m[2])
        return m[1]+m[2]+' '+str(widths[m[2]])
    text = re.sub(r'((?:\+ FIXED|NEW)\s+)(\S+)(?=\s+\()', width, text)
    text = re.sub(r'(?m)^NETS ', 'SPECIALNETS ', text)
    return text.replace('END NETS', 'END SPECIALNETS')
