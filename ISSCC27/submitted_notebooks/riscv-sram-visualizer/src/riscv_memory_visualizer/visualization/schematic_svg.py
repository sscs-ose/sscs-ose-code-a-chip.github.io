"""Small reusable SVG schematic vocabulary and teaching scene renderer."""

from html import escape


def wire(points, *, stroke="#65748b", width=3, ident=""):
    attr = f' id="{ident}"' if ident else ""
    return f'<polyline{attr} points="{points}" fill="none" stroke="{stroke}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>'


def junction(x, y, color="#334155"):
    return f'<circle cx="{x}" cy="{y}" r="4" fill="{color}"/>'


def label(x, y, value, *, size=20, color="#17233a", anchor="middle", ident=""):
    attr = f' id="{ident}"' if ident else ""
    return f'<text{attr} x="{x}" y="{y}" text-anchor="{anchor}" fill="{color}" font-size="{size}" font-family="system-ui, sans-serif" font-weight="650">{escape(str(value))}</text>'


def arrow(x1, y1, x2, y2, color="#e89428"):
    return f'<path d="M{x1} {y1} L{x2} {y2}" fill="none" stroke="{color}" stroke-width="4" marker-end="url(#arrow)"/>'


def highlight_path(points, color="#f97355"):
    return wire(points, stroke=color, width=7)


def vdd(x, y):
    return wire(f"{x},{y+20} {x},{y} {x-18},{y}") + label(x-24, y+5, "VDD", size=16, anchor="end")


def gnd(x, y):
    return wire(f"{x},{y-20} {x},{y} {x-18},{y} {x+18},{y}") + wire(f"{x-12},{y+6} {x+12},{y+6}") + wire(f"{x-5},{y+12} {x+5},{y+12}") + label(x+30, y+5, "GND", size=15, anchor="start")


def _mos(x, y, name, kind, *, gate_side="left", active=False):
    """Vertical MOS channel, insulated gate, PMOS gate bubble and terminals."""
    color = "#dc4b72" if active else "#52627c"
    gx = x-28 if gate_side == "left" else x+28
    near = x-11 if gate_side == "left" else x+11
    bubble = f'<circle cx="{gx+5 if gate_side == "left" else gx-5}" cy="{y}" r="5" fill="white" stroke="{color}" stroke-width="2.5"/>' if kind == "PMOS" else ""
    return (f'<g id="{name.lower()}" data-device="{kind}" stroke="{color}" fill="none" stroke-width="3">'
            f'<path d="M{x} {y-31} V{y-17} M{x} {y+17} V{y+31} M{x} {y-17} V{y+17}"/>'
            f'<path d="M{near} {y-19} V{y+19} M{gx} {y} H{near}"/>{bubble}</g>'
            + label(x+25 if gate_side == "left" else x-25, y+5, name, size=15,
                    anchor="start" if gate_side == "left" else "end", color=color))


def nmos(x, y, name, **kwargs):
    return _mos(x, y, name, "NMOS", **kwargs)


def pmos(x, y, name, **kwargs):
    return _mos(x, y, name, "PMOS", **kwargs)


def _frame(content, *, title="", viewbox="0 0 960 540"):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}" role="img" aria-label="{escape(title)}" '
            'style="width:100%;height:100%;background:#f8fafc;border-radius:18px">'
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 Z" fill="#e89428"/></marker></defs>'
            '<style>'
            '@keyframes teaching-glow{0%{opacity:0;stroke-width:2}45%{opacity:1;stroke-width:8}100%{opacity:.65;stroke-width:4}}'
            '@keyframes teaching-selected{0%,100%{transform:scale(1)}50%{transform:scale(1.06)}}'
            '@keyframes sram-reveal{from{opacity:0;transform:scale(.96)}to{opacity:1;transform:scale(1)}}'
            '.teaching-glow{fill:none;stroke:#f2a12a;stroke-width:4;opacity:0;filter:drop-shadow(0 0 5px #f7b94e);animation:teaching-glow .52s ease-out forwards;pointer-events:none}'
            '.teaching-selected{transform-box:fill-box;transform-origin:center;animation:teaching-selected .55s ease-out 1.1s both}'
            '.sram-reveal{transform-box:fill-box;transform-origin:center;animation:sram-reveal .45s ease-out both}'
            '@media(prefers-reduced-motion:reduce){.teaching-glow{animation:none!important;opacity:.65}.sram-reveal,.teaching-selected{animation:none!important}}'
            '</style>'
            + content + '</svg>')


def _sequence_glow(step, *, cell=False):
    """Draw finite outline emphasis in the order recorded by the lesson."""
    targets = {}
    if step.scene == 1:
        targets = {"processor": (90, 155, 340, 245), "request-port": (415, 272, 38, 45),
                   "sram": (650, 180, 210, 190)}
    elif step.scene == 2:
        targets = {"address-input": (95, 202, 105, 58), "row-decoder": (310, 110, 190, 110),
                   "column-selector": (310, 330, 190, 110), "sram-array": (565, 110, 260, 170),
                   "periphery": (575, 340, 255, 110)}
    elif step.scene == 3:
        targets = {"address-input": (110, 223, 105, 58), "row-decoder": (385, 120, 210, 110),
                   "column-selector": (385, 315, 210, 110), "selected-cell": (740, 223, 100, 65)}
    elif step.scene == 4:
        if step.title == "Bitcell close-up":
            for r in range(step.array_state.rows):
                for c in range(step.array_state.columns):
                    targets[f"cell-r{r}-c{c}"] = (100+c*66, 205+r*47, 58, 38)
            targets["bitcell-closeup"] = (430, 120, 500, 330)
        else:
            targets[f"row-r{step.row}"] = (202, 132 + step.row*76, 42, 39)
            targets[f"column-c{step.column}"] = (282 + step.column*122, 73, 48, 40)
            for r in range(step.array_state.rows):
                for c in range(step.array_state.columns):
                    targets[f"cell-r{r}-c{c}"] = (260+c*122, 120+r*76, 93, 58)
    elif cell:
        def box(x, y, w, h):
            return ((-5 + .8*x, 60 + .8*y, .8*w, .8*h) if step.scene in (6, 7)
                    else (x, y, w, h))
        targets = {
            "left-inverter": box(300, 100, 80, 280), "right-inverter": box(580, 100, 80, 280),
            "feedback": box(235, 49, 515, 421), "q": box(320, 230, 42, 42),
            "q-bar": box(600, 230, 42, 42), "m5": box(145, 140, 55, 74),
            "m6": box(765, 140, 55, 74), "wl": box(62, 150, 837, 55),
            "bl": box(150, 72, 40, 145), "bl-bar": box(770, 72, 40, 145),
            "stored-state": box(292, 209, 375, 82),
        }
        if step.scene in (6, 7):
            targets.update({"precharge": (683, 192, 251, 303),
                            "sense-amplifier": (683, 192, 251, 303),
                            "sense-output": (890, 295, 42, 43),
                            "data-input": (792, 253, 59, 35),
                            "write-driver": (683, 192, 251, 303),
                            "result": (766, 257, 134, 55)})
    elif step.scene == 8:
        targets = {name: (45+i*153, 220, 130, 90) for i, name in enumerate(
            ("summary-decode", "summary-select", "summary-prepare", "summary-access",
             "summary-finish", "summary-result"))}
    outlines = []
    for order, target in enumerate(step.animation_sequence):
        if target not in targets:
            raise ValueError(f"No SVG target for teaching animation: {target}")
        x, y, width, height = targets[target]
        outlines.append(
            f'<rect id="glow-{target}" data-target="{target}" data-order="{order}" '
            f'class="teaching-glow teaching-glow-delay-{order}" x="{x:g}" y="{y:g}" '
            f'width="{width:g}" height="{height:g}" rx="9" '
            f'style="animation-delay:{order*.55:.2f}s"/>')
    return (f'<g data-animation-sequence="{",".join(step.animation_sequence)}">'
            + ''.join(outlines) + '</g>')


def _cell(step, *, with_periphery=False, embed=False):
    active = set(step.highlight_ids)
    snap = step.circuit_snapshot
    q = snap.q if snap else step.q
    qb = snap.q_bar if snap else step.q_bar
    wl = snap.word_line if snap else 0
    bl = snap.bit_line if snap else None
    blb = snap.bit_line_bar if snap else None
    s = "" if with_periphery else label(480, 40, "6T SRAM BITCELL", size=25)
    # M1/M2 and M3/M4 are the left/right CMOS inverters; M5/M6 access.
    for x, p, n in ((340, "M1", "M2"), (620, "M3", "M4")):
        s += f'<g id="{"left" if x == 340 else "right"}-inverter">'
        s += vdd(x, 67) + wire(f"{x},87 {x},104")
        side = "left" if x == 340 else "right"
        s += pmos(x, 135, p, gate_side=side, active=p in active)
        s += wire(f"{x},166 {x},250") + junction(x, 250)
        s += nmos(x, 340, n, gate_side=side, active=n in active)
        s += wire(f"{x},250 {x},309") + wire(f"{x},371 {x},433") + gnd(x, 453)
        s += '</g>'
    # Cross coupling: each output connects to the opposite inverter's gate bus.
    s += '<g id="feedback">'
    s += wire("340,250 270,250 270,465 720,465 720,135 648,135", stroke="#7352b5")
    s += wire("720,135 720,340 648,340", stroke="#7352b5")
    s += wire("620,250 745,250 745,55 240,55 240,135 312,135", stroke="#7352b5")
    s += wire("240,135 240,340 312,340", stroke="#7352b5")
    s += junction(720, 135) + junction(240, 135) + junction(720, 340) + junction(240, 340)
    s += '</g>'
    # Access devices are shown as vertical NMOS branches from the bit-lines.
    for x, name, node, bitname, bit in ((170, "M5", 340, "BL", bl), (790, "M6", 620, "BL_bar", blb)):
        s += wire(f"{x},75 {x},146", stroke="#16a6b1" if bitname in active else "#65748b",
                  ident="bl" if bitname == "BL" else "bl-bar")
        s += nmos(x, 177, name, gate_side="left" if x == 170 else "right", active=name in active)
        s += wire(f"{x},208 {x},250 {node},250") + junction(x, 250)
        s += label(x, 65, f"{bitname} = {'?' if bit is None else bit}", size=18,
                   color="#088b99" if bitname in active else "#334155")
    s += wire("70,177 142,177", stroke="#d7a71d" if wl else "#65748b", width=4, ident="wl")
    s += wire("818,177 890,177", stroke="#d7a71d" if wl else "#65748b", width=4)
    s += wire("100,177 100,510 860,510 860,177", stroke="#d7a71d" if wl else "#65748b", width=3)
    s += label(70, 165, f"WL = {wl}", anchor="start", size=18, color="#a87700")
    s += '<g id="q">' + junction(340, 250, "#16855d") + label(340, 238, f"Q = {q}", size=18, color="#16855d" if q else "#334155") + '</g>'
    s += '<g id="q-bar">' + junction(620, 250, "#16855d") + label(620, 238, f"Q_bar = {qb}", size=18, color="#16855d" if qb else "#334155") + '</g>'
    if with_periphery:
        s = (label(480, 42, f"6T SRAM {step.operation}", size=25)
             + '<g transform="translate(-5 60) scale(.8)">' + s + '</g>'
             + '<g transform="translate(665 -150) scale(1.2)">' + _periphery(step) + '</g>')
        if step.title == "Cell overwrite":
            s += label(480, 523, f"BEFORE Q={step.before_q} / Q_bar={1-step.before_q}  →  AFTER Q={q} / Q_bar={qb}", size=17)
        elif step.title == "Read result":
            s += '<g id="result">' + label(480, 523, f"READ DATA = {step.result}", size=21, color="#087e89") + '</g>'
        elif step.title == "Write complete":
            s += '<g id="result">' + label(480, 523, f"STORED DATA = {step.result}", size=21, color="#087e89") + '</g>'
    if embed:
        return s
    return _frame(s + _sequence_glow(step, cell=True), title="Six transistor SRAM schematic with cross-coupled CMOS inverters and access transistors")


def _periphery(step):
    snap = step.circuit_snapshot
    if snap is None:
        return ""
    # Educational periphery: precharge equalization, gated differential sense,
    # and complementary CMOS output drivers. The branch highlights its active path.
    s = '<rect x="18" y="285" width="210" height="253" rx="9" fill="#e8f7f7" stroke="#5fbdbe"/>'
    if step.operation == "READ":
        if snap.precharge_enabled:
            s += '<g id="precharge" class="schematic-precharge">'
            s += label(123, 309, "PMOS PRECHARGE", size=15)
            for x, name, line in ((77, "P1", "BL"), (174, "P2", "BL_bar")):
                s += vdd(x, 343) + pmos(x, 389, name, active=True)
                s += wire(f"{x},420 {x},470", stroke="#0f9aa7")
                s += label(x, 488, line, size=14)
            s += wire("77,448 174,448", stroke="#0f9aa7") + junction(77,448) + junction(174,448)
            s += label(123, 519, "PRECHARGE_EN", size=12)
            s += '</g>'
        else:
            s += '<g id="sense-amplifier" class="schematic-sense-amp">'
            s += label(123, 307, "DIFFERENTIAL SENSE", size=14)
            for x, name in ((78, "P1"), (174, "P2")):
                s += vdd(x, 322) + pmos(x, 359, name, active=snap.sense_enabled)
                s += wire(f"{x},390 {x},391")
            # Diode-connected PMOS loads; the differential NMOS pair shares S3.
            s += wire("50,359 35,359 35,391 78,391")
            s += wire("202,359 218,359 218,391 174,391")
            s += nmos(78, 422, "S1", active=snap.sense_enabled)
            s += nmos(174, 422, "S2", gate_side="right", active=snap.sense_enabled)
            s += wire("78,453 126,463 174,453") + junction(126,463)
            s += nmos(126, 484, "S3", active=snap.sense_enabled)
            s += gnd(126, 526)
            s += wire("78,391 29,391 29,366", stroke="#0f9aa7") + junction(78,391)
            s += label(38, 420, "BL", size=12) + label(215, 420, "BL_bar", size=12)
            s += label(58, 485, "SENSE_EN", size=11)
            s += ('<g id="sense-output"><path d="M174 391 H213" fill="none" stroke="#0f9aa7" stroke-width="3"/>'
                  '<circle cx="216" cy="391" r="5" fill="white" stroke="#0f9aa7" stroke-width="2"/>'
                  + label(209, 377, "OUT", size=12) + '</g></g>')
    else:
        s += '<g id="write-driver" class="schematic-driver">'
        s += label(130, 309, "CMOS WRITE DRIVER", size=15)
        for x, p, n in ((78, "D1", "D2"), (180, "D3", "D4")):
            s += vdd(x, 332) + pmos(x, 378, p, active=snap.write_driver_enabled)
            s += wire(f"{x},409 {x},423") + nmos(x, 454, n, active=snap.write_driver_enabled)
            s += gnd(x, 499)
            bus = x-39
            s += wire(f"{x-28},378 {bus},378 {bus},454 {x-28},454", stroke="#d56246")
        s += label(78, 424, "BL", size=12) + label(180, 424, "BL_bar", size=12)
        s += ('<g id="data-input"><circle cx="130" cy="338" r="6" fill="white" '
              'stroke="#d56246" stroke-width="2"/>'
              + label(130, 359, f"DATA={snap.write_value}", size=12) + '</g>')
        s += '</g>'
    return s


def _box(x, y, w, h, title, color="#7555b8", subtitle="", font_size=19):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="white" stroke="{color}" stroke-width="3"/>'
            + label(x+w/2, y+h/2+1, title, size=font_size, color=color)
            + (label(x+w/2, y+h/2+27, subtitle, size=14) if subtitle else ""))


def input_port(x, y, name, value="", *, ident="address-input"):
    return (f'<g id="{ident}" class="schematic-input">'
            f'<circle cx="{x+22}" cy="{y+28}" r="19" fill="white" stroke="#d28721" stroke-width="3"/>'
            + wire(f"{x+41},{y+28} {x+100},{y+28}", stroke="#d28721")
            + label(x+22, y+34, name, size=14, color="#9d6114")
            + label(x+70, y+12, value, size=15) + '</g>')


def output_port(x, y, name, *, ident="sense-output"):
    return (f'<g id="{ident}" class="schematic-output">'
            + wire(f"{x},{y} {x+45},{y}", stroke="#0f9aa7")
            + f'<circle cx="{x+52}" cy="{y}" r="7" fill="white" stroke="#0f9aa7" stroke-width="3"/>'
            + label(x+45, y-15, name, size=14) + '</g>')


def decoder(x, y, w, h, name="ROW DECODER", *, ident="row-decoder"):
    points = f"{x},{y+12} {x+w-34},{y} {x+w},{y+h/2} {x+w-34},{y+h} {x},{y+h-12}"
    return (f'<g id="{ident}" class="schematic-decoder">'
            f'<polygon points="{points}" fill="#f4efff" stroke="#7951bb" stroke-width="3"/>'
            + label(x+w/2-8, y+h/2+5, name, size=17, color="#62409c")
            + f'<path d="M{x+w} {y+h/2-16} H{x+w+15} M{x+w} {y+h/2+16} H{x+w+15}" fill="none" stroke="#7951bb" stroke-width="3"/>'
            + '</g>')


def selector(x, y, w, h, name="COLUMN SELECT", *, ident="column-selector"):
    points = f"{x},{y} {x+w-30},{y+15} {x+w},{y+h/2} {x+w-30},{y+h-15} {x},{y+h}"
    return (f'<g id="{ident}" class="schematic-selector">'
            f'<polygon points="{points}" fill="#eaf9fa" stroke="#0f9aa7" stroke-width="3"/>'
            + label(x+w/2-5, y+h/2+5, name, size=16, color="#087e89")
            + label(x+w/2-5, y+h-17, "SEL", size=12, color="#087e89") + '</g>')


def array_symbol(x, y, w, h, rows=4, columns=4, *, ident="sram-array"):
    cell_w, cell_h = min(36, (w-42)/columns), min(29, (h-52)/rows)
    left = x + (w-columns*cell_w)/2
    top = y+37
    content = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" '
               'fill="#fff9ef" stroke="#dd7624" stroke-width="3"/>')
    content += label(x+w/2, y+25, "SRAM ARRAY", size=17, color="#a85213")
    for r in range(rows):
        for c in range(columns):
            content += (f'<rect x="{left+c*cell_w:g}" y="{top+r*cell_h:g}" '
                        f'width="{cell_w-4:g}" height="{cell_h-4:g}" rx="3" '
                        'fill="white" stroke="#d99960" stroke-width="1.5"/>')
    return f'<g id="{ident}" class="schematic-array">{content}</g>'


def sense_amp(x, y, w, h, *, ident="sense-amplifier"):
    return (f'<g id="{ident}" class="schematic-sense-amp">'
            f'<path d="M{x+40} {y+10} L{x+w-10} {y+h/2} L{x+40} {y+h-10} Z" '
            'fill="#eaf9fa" stroke="#0f9aa7" stroke-width="3"/>'
            + f'<path d="M{x} {y+h*.32:g} H{x+40} M{x} {y+h*.68:g} H{x+40}" fill="none" stroke="#0f9aa7" stroke-width="3"/>'
            + label(x+9, y+h*.32-8, "BL", size=11)
            + label(x+9, y+h*.68-8, "BL_bar", size=11)
            + label(x+w*.52, y+h/2+5, "SENSE", size=14, color="#087e89")
            + output_port(x+w-10, y+h/2, "DATA") + '</g>')


def driver(x, y, w, h, *, ident="write-driver"):
    return (f'<g id="{ident}" class="schematic-driver">'
            f'<path d="M{x+28} {y+10} L{x+w-34} {y+h/2} L{x+28} {y+h-10} Z" '
            'fill="#fff1e9" stroke="#d56246" stroke-width="3"/>'
            + label(x+w*.42, y+h/2+5, "DRIVE", size=13, color="#a84731")
            + f'<path d="M{x} {y+h/2} H{x+28} M{x+w-34} {y+h/2} H{x+w}" fill="none" stroke="#d56246" stroke-width="3"/>'
            + label(x+9, y+h/2-11, "DATA", size=11)
            + label(x+w-5, y+h/2-11, "BL/BL_bar", size=11) + '</g>')


def array_cell(x, y, value, r, c, *, color="#9daaba", fill="white", width=93, height=58,
               emphasized=False):
    css = "schematic-array-cell teaching-selected" if emphasized else "schematic-array-cell"
    return (f'<g id="cell-r{r}-c{c}" class="{css}">'
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="8" '
            f'fill="{fill}" stroke="{color}" stroke-width="3"/>'
            + label(x+width/2, y+height/2+8, value, size=24,
                    color="#16855d" if value else "#334155") + '</g>')


def _closeup_scene(step):
    s = label(480, 60, step.title.upper(), size=27)
    s += label(230, 165, f"ARRAY CELL ({step.row},{step.column})", size=18, color="#62409c")
    for r, row in enumerate(step.array_state.cells):
        for c, value in enumerate(row):
            selected = (r, c) == step.selected_cell
            s += array_cell(100+c*66, 205+r*47, value, r, c,
                            color="#e67928" if selected else "#9daaba",
                            fill="#fff1e4" if selected else "white", width=58, height=38)
    s += arrow(375, 284, 412, 284)
    s += ('<g id="bitcell-closeup" class="sram-reveal">'
          '<rect x="430" y="120" width="500" height="330" rx="12" fill="white" stroke="#e67928" stroke-width="3"/>'
          '<g transform="translate(445 132) scale(.49 .56)">' + _cell(step, embed=True)
          + '</g></g>')
    s += label(680, 482, f"Q={step.q}  ·  Q_bar={step.q_bar}", size=20, color="#16855d")
    return _frame(s + _sequence_glow(step), title=step.title)


def render_scene(step):
    """Render exactly one immutable teaching step; no backend access occurs."""
    scene = step.scene
    if scene in (5, 6, 7):
        return _cell(step, with_periphery=scene in (6, 7))
    if scene == 4 and step.title == "Bitcell close-up":
        return _closeup_scene(step)
    s = label(480, 65, step.title.upper(), size=27)
    if scene == 1:
        s += '<g id="processor"><rect x="90" y="155" width="340" height="245" rx="18" fill="#ecebff" stroke="#403d99" stroke-width="3"/>'
        s += label(260, 190, "PROCESSOR", size=22, color="#403d99")
        s += label(260, 225, step.instruction, size=18, color="#bd7415")
        for x, name in ((150, "FETCH"), (255, "EXEC"), (360, "MEM")):
            s += f'<circle cx="{x}" cy="295" r="30" fill="#fff" stroke="#6859ba" stroke-width="3"/>'
            s += label(x, 302, name, size=12, color="#403d99")
        s += wire("180,295 225,295 285,295 330,295 410,295", stroke="#8070bc") + '</g>'
        s += f'<g id="request-port">{output_port(400, 295, "REQ", ident="cpu-output")}</g>'
        s += '<g id="sram">' + array_symbol(650, 180, 210, 190, ident="intro-array") + '</g>'
        s += arrow(455, 295, 630, 295) + label(535, 268, f"request • {step.address:#04x}", size=17, color="#c57912")
    elif scene == 2:
        s += input_port(95, 203, "A", f"{step.address:#04x}")
        s += decoder(310, 110, 190, 110)
        s += array_symbol(565, 110, 260, 170)
        s += selector(310, 330, 190, 110)
        s += '<g id="periphery">' + (sense_amp(575, 340, 210, 110) if step.operation == "READ"
                                      else driver(575, 340, 230, 110)) + '</g>'
        for a in ((240,220,300,165),(500,165,555,165),(240,250,300,385),(500,385,565,385),(695,290,695,330)):
            s += arrow(*a)
        s += label(540, 99, "WLs", size=15) + label(710, 320, "BL / BL_bar", size=14)
    elif scene == 3:
        s += input_port(110, 224, "A", f"{step.address:#04x}")
        s += decoder(385, 120, 210, 110, f"ROW {step.row}")
        s += selector(385, 315, 210, 110, f"COLUMN {step.column}")
        s += '<g id="selected-cell">' + array_cell(740, 223, step.q, step.row, step.column,
                                                     color="#db6f24", width=100, height=65) + '</g>'
        s += label(790, 207, f"CELL ({step.row},{step.column})", size=17, color="#a85213")
        s += arrow(300,250,375,175)+arrow(300,265,375,365)+arrow(605,175,695,245)+arrow(605,370,695,280)
        index = step.address // 4
        columns = step.array_state.columns
        s += label(480, 449, f"{step.address:#04x} = {step.address}; index = {step.address} // 4 = {index}", size=18)
        s += label(480, 480, f"row = {index} // {columns} = {step.row}; column = {index} % {columns} = {step.column}", size=18)
    elif scene == 4:
        state = step.array_state
        active = set(step.highlight_ids)
        for r, row in enumerate(state.cells):
            s += f'<g id="row-r{r}">' + label(220, 160+r*76, f"R{r}", size=17) + '</g>'
            for c, value in enumerate(row):
                selected = (r,c) == step.selected_cell and "cell" in active
                x,y = 260+c*122, 120+r*76
                row_on = "row" in active and r == step.row
                column_on = "column" in active and c == step.column
                color = "#e67928" if selected else ("#7555b8" if row_on else ("#0f9aa7" if column_on else "#9daaba"))
                fill = "#fff1e4" if selected else ("#f4efff" if row_on else ("#eaf9fa" if column_on else "#fff"))
                s += array_cell(x, y, value, r, c, color=color, fill=fill,
                                emphasized=selected and step.title == "Selected bitcell")
        for c in range(state.columns):
            s += f'<g id="column-c{c}">' + label(305+c*122, 105, f"C{c}", size=17) + '</g>'
        s += label(480, 475, f"Selected cell ({step.row}, {step.column}) • Q={step.q}", size=18)
    elif scene == 8:
        names = (["DECODE", "SELECT CELL", "PRECHARGE", "ACCESS", "SENSE", f"READ {step.result}"]
                 if step.operation == "READ" else
                 ["DECODE", "SELECT CELL", "DRIVE BL", "WL ON", "OVERWRITE", f"STORED {step.result}"])
        for i,name in enumerate(names):
            x = 45+i*153
            ident = ("summary-decode", "summary-select", "summary-prepare",
                     "summary-access", "summary-finish", "summary-result")[i]
            s += f'<g id="{ident}">' + _box(x, 220, 130, 90, name,
                    "#0f9aa7" if i>2 else "#7951bb", font_size=14) + '</g>'
            if i<5: s += arrow(x+132, 265, x+150, 265)
    return _frame(s + _sequence_glow(step), title=step.title)
