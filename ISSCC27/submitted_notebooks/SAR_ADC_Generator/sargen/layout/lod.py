"""Length of diffusion (LOD) of every drawn finger, for layout-aware simulation and the matching audit.

SKY130's BSIM4 models carry the LOD stress effect (instance parameters sa / sb: distance from the gate edge to the
end of its diffusion on either side): a 2 um NMOS at sa = sb = 0.26 um carries ~20 % less current than the
sa = sb = 0 netlist default (which switches the effect off).  Magic's extraction does not write sa / sb, so the
generator computes them from its own finger placement: fingers that share contact bars sit in one continuous
diffusion, and each finger's sa / sb run to that diffusion's two ends.

Result per block: a list of fingers {dev, kind, flavor, w, l, d, g, s, sa, sb, shared_d, shared_s} (mirrored halves under their own names,
dummies included), from which sargen.netlist builds a layout-aware schematic (lod_lines).
Runs in the layout environment (PCell geometry); the JSON it writes is read by sargen.netlist (lod_lines, sar_testbench(lod=...)).
"""

import json
from pathlib import Path


def _finger(f, sa, sb, shared_d, shared_s):
    dv = f["dv"]
    return dict(dev=f["name"].partition(".")[0], kind=dv.kind, flavor=dv.flavor or "std", w=round(dv.w, 4),
                l=dv.l, d=f["left"], g=f["g"], s=f["right"], sa=round(sa, 4), sb=round(sb, 4),
                shared_d=shared_d, shared_s=shared_s)


def row_lod(row):
    """Per-finger LOD of a placed Row (sargen.layout.strongarm.Row)."""
    out, run = [], []

    def close():
        if not run:
            return
        x0 = run[0]["x"] + run[0]["fe"].diff[0]
        x1 = run[-1]["x"] + run[-1]["fe"].diff[1]
        for i, f in enumerate(run):
            l = f["dv"].l
            out.append(_finger(f, f["x"] - l / 2 - x0, x1 - f["x"] - l / 2, i > 0, i < len(run) - 1))
        run.clear()

    for f in row.f:
        if not f.get("shared"):
            close()
        run.append(f)
    close()
    return out


def strongarm_lod(c, end_dummies=True):
    from .strongarm import strongarm_rows
    r = strongarm_rows(c, end_dummies)
    tied = {"d_outn": "outn", "d_outp": "outp"}      # the latch dummies' outer bar is wired to the output bar
    out = [e for key in ("tail", "inp", "nl", "nr", "pl", "pr") for e in row_lod(r[key])]
    return [dict(e, d=tied.get(e["d"], e["d"]), s=tied.get(e["s"], e["s"])) for e in out]


def topswitch_lod(design, matched=True):
    from .topswitch import top_switch_rows
    return [e for row in top_switch_rows(design, matched) for e in row_lod(row)]


def unitcell_lod(design):
    """The unit cell's four devices are stand-alone PCells (no shared diffusion): {device: (sa, sb)}."""
    from .unitcell import GATE_SIDE, _Fet, cell_devices
    devs = cell_devices(design, dict(en="a", enb="b", pg="c", ng="d"), "proto")
    out = {}
    for d, side in zip(devs, GATE_SIDE):
        ext = round(-_Fet(d, side).diff[0] - d.l / 2, 4)
        out[d.name.split("_")[0]] = (ext, ext)
    return out


def write(design, path, matched=True):
    """LOD of the comparator, the top-plate switch and the CDAC unit-cell switches -> JSON.  matched=False: the
    earlier layout (no end dummies on the latch rows and the switch, separate switch finger counts)."""
    data = dict(strongarm=strongarm_lod(design["cmp"], matched), topsw=topswitch_lod(design, matched),
                unit=unitcell_lod(design))
    Path(path).write_text(json.dumps(data, indent=1))
    return data
