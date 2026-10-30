"""Rectangular resistance mesh with explicit device and boundary maps."""
import re
from pathlib import Path

import klayout.db as db
import numpy as np


METALS = {"li": (67, 20, "allli"), "m1": (68, 20, "allm1"),
          "m2": (69, 20, "allm2"), "m3": (70, 20, "allm3"),
          "m4": (71, 20, "allm4"), "m5": (72, 20, "allm5")}


def build_network(gds, technology, max_local_um=0.25, placements=None, port_specs=None):
    layout = db.Layout()
    layout.read(str(gds))
    top, unit = layout.top_cell(), layout.dbu
    technology_text = Path(technology).read_text()
    typical = technology_text.split("variants (),(orig),(si)\n", 1)[1].split("variants (hrhc)", 1)[0]

    def parameter(kind, name):
        pattern = rf"^\s*{kind}\s+{re.escape(name)}\s+([\d.]+)"
        match = re.search(pattern, typical, re.MULTILINE)
        if match is None:
            raise ValueError(f"Missing typical resistance: {kind} {name}")
        return float(match[1]) / 1000  

    def region(cell, layer):
        return db.Region(cell.begin_shapes_rec(layout.layer(*layer))).merged()

    sheets = {name: region(top, values[:2]) for name, values in METALS.items()}
    rho = {name: parameter("resist", f"({values[2]})/{'locali' if name == 'li' else 'metal'+name[1]}")
           for name, values in METALS.items()}
    contacts = []
    for pair, bottom, upper, rule in (
            ((67, 44), "li", "m1", "mcon"), ((68, 44), "m1", "m2", "m2c"),
            ((69, 44), "m2", "m3", "m3c"), ((70, 44), "m3", "m4", "via3"),
            ((71, 44), "m4", "m5", "via4")):
        for polygon in region(top, pair).each():
            contacts.append((polygon.bbox(), bottom, upper, parameter("contact", rule), rule))


    if placements is None or port_specs is None:
        raise ValueError("Supply the verified device map and external port specifications.")
    seen, device_ports = set(), []
    excluded_li = db.Region()
    for instance in top.each_inst():
        trans = instance.dcplx_trans
        key = (round(trans.disp.x, 6), round(trans.disp.y, 6))
        if key not in placements or trans.angle % 90 != 0 or trans.mag != 1:
            raise ValueError("The terminal map requires the documented device positions and orientations.")
        name, kind = placements[key]
        if name in seen or not instance.cell.name.startswith(kind):
            raise ValueError(f"Unexpected cell at {key}")
        seen.add(name)
        islands = list(region(instance.cell, (67, 20)).each())
        body = [p for p in islands if p.holes()]
        others = [p for p in islands if not p.holes()]
        if kind == "res_poly":
            if len(body) != 1 or len(others) != 2:
                raise ValueError("Expected two resistor end islands and one guard ring.")


            for pin, pad in zip(("a","b"), sorted(region(instance.cell,(68,20)).each(),key=lambda p:p.bbox().bottom)):
                device_ports.append((f"t_{name}_{pin}","m1",pad.transformed(instance.cplx_trans)))
            for island in others:
                excluded_li.insert(island.transformed(instance.cplx_trans))
            terminals = {"w":body[0]}
        else:
            gate = [p for p in others if p.bbox().width() > p.bbox().height()]
            diffusion = sorted((p for p in others if p not in gate), key=lambda p: p.bbox().left)
            if len(body) != 1 or len(gate) != 1 or len(diffusion) != 2:
                raise ValueError("Unsupported local-interconnect terminal geometry.")
            terminals = dict(zip(("s", "d", "g", "b"), (*diffusion, gate[0], body[0])))
        for polygon in region(instance.cell, (66, 44)).each():
            matches = [pin for pin, island in terminals.items() if island.inside(polygon.bbox().center())]
            if kind == "res_poly" and not matches:
                continue
            if len(matches) != 1:
                raise ValueError("A LICON cut must belong to exactly one terminal.")
            pin = matches[0]

            rule = "pdc,psc" if kind == "res_poly" else "pc,xpc" if pin == "g" else (
                "ndc,nsc" if (kind == "nfet") != (pin == "b") else "pdc,psc")
            box = polygon.transformed(instance.cplx_trans).bbox()
            contacts.append((box, "li", f"t_{name}_{pin}", parameter("contact", rule), rule))
    if seen != {item[0] for item in placements.values()}:
        raise ValueError("The layout and declared device identities differ.")

    sheets["li"] = (sheets["li"]-excluded_li).merged()
    contacts = [c for c in contacts if not (c[4]=="mcon" and any(p.inside(c[0].center()) for p in excluded_li.each()))]
    ports = list(device_ports)
    specs = port_specs
    for name, layer, number, label in specs:
        labels = [(shape.text.string.lower(), shape.text.trans.disp)
                  for shape in top.shapes(layout.layer(number, 5)).each() if shape.is_text()]
        points = [point for text, point in labels if text == label]
        footprints = [p for p in region(top, (number, 16)).each()
                      if len(points) == 1 and p.inside(db.Point(points[0].x, points[0].y))]
        if len(footprints) != 1:
            raise ValueError(f"Expected one labeled supply footprint for {name}")
        ports.append((name, layer, footprints[0]))


    coordinates = [set(), set()]
    polygons = [p for metal in sheets.values() for p in metal.each()]
    polygons += [db.Polygon(cut[0]) for cut in contacts] + [p for _, _, p in ports]
    for polygon in polygons:
        rings = [list(polygon.each_point_hull())]
        rings += [list(polygon.each_point_hole(h)) for h in range(polygon.holes())]
        for ring in rings:
            for a, b in zip(ring, ring[1:] + ring[:1]):
                if a.x != b.x and a.y != b.y:
                    raise ValueError("This mesh supports Manhattan geometry only.")
                coordinates[0].add(a.x)
                coordinates[1].add(a.y)

    axes = []
    for values in coordinates:
        values = sorted(values)
        axis = []
        for a, b in zip(values, values[1:]):

            limit = (50 if (b-a)*unit > 25 else max_local_um) / unit
            count = max(1, int(np.ceil((b-a)/limit)))
            axis.extend(round(a + (b-a)*k/count) for k in range(count))


            if (b-a)*unit > 25:
                step = round(max_local_um/unit)
                axis.extend((a+step, b-step))
        axes.append(np.array(sorted(set(axis + [values[-1]])), dtype=int))
    x, y = axes
    nodes, lookup, edges = [], {}, []

    def add_edge(a, b, resistance, kind, face_um=0.0):
        if a != b:
            edges.append((a, b, float(resistance), kind, float(face_um)))

    for layer, metal in sheets.items():
        polygons = list(metal.each())
        bbox = metal.bbox()
        for ix, (left, right) in enumerate(zip(x, x[1:])):
            if left < bbox.left or right > bbox.right:
                continue
            for iy, (bottom, upper) in enumerate(zip(y, y[1:])):
                if bottom < bbox.bottom or upper > bbox.top:
                    continue
                point = db.Point((int(left)+int(right))//2, (int(bottom)+int(upper))//2)
                if not any(p.inside(point) for p in polygons):
                    continue
                name = next((n for n, m, p in ports if m == layer and p.inside(point)),
                            f"n{len(nodes)}")
                lookup[layer, ix, iy] = name
                nodes.append((name, layer, (left+right)*unit/2, (bottom+upper)*unit/2,
                              (right-left)*unit, (upper-bottom)*unit))
                for dx, dy in ((-1, 0), (0, -1)):
                    other = lookup.get((layer, ix+dx, iy+dy))
                    if other is not None:
                        distance = (right-x[ix-1])/2 if dx else (upper-y[iy-1])/2
                        face = upper-bottom if dx else right-left
                        add_edge(other, name, rho[layer]*distance/face, layer, face*unit)

    for box, bottom, upper, resistance, rule in contacts:
        ix0, ix1 = np.searchsorted(x, [box.left, box.right])
        iy0, iy1 = np.searchsorted(y, [box.bottom, box.top])
        for ix in range(ix0, ix1):
            for iy in range(iy0, iy1):
                a = lookup.get((bottom, ix, iy))
                b = upper if upper.startswith("t_") else lookup.get((upper, ix, iy))
                if a is None or b is None:
                    raise ValueError(f"Contact {rule} is not enclosed by both modeled conductors.")

                fraction = (x[ix+1]-x[ix])*(y[iy+1]-y[iy])/box.area()
                add_edge(a, b, resistance/fraction, "contact:"+rule)
    return {"nodes":nodes, "edges":edges, "sheet_ohms_per_square":rho,
            "contact_cuts":len(contacts), "max_local_um":max_local_um,
            "contact_ohms_per_cut":{c[4]:c[3] for c in contacts}}
