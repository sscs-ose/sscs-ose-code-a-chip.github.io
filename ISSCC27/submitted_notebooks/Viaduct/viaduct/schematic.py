"""Small helpers for building xschem schematics live through the tap.

    from viaduct import Viaduct
    from viaduct.schematic import Builder
    sb = Builder(Viaduct.from_env())
    sb.new("/foss/designs/viaduct/xschem/demo.sch", replace=True)
    sb.place("sky130_fd_pr/nfet_01v8.sym", 0, 0, name="M1", W="2", L="0.15")
    sb.wire(20, -30, 20, -60); sb.label("OUT", 20, -60)
    sb.connect("R1", "M", "M1", "D"); sb.label_pin("M1", "G", "IN")   # by pin name, no coordinates
    netlist = sb.finish()        # one request: everything above + save + zoom + netlist
    vd.xschem.check()            # floating pins / single-pin nets, read back from xschem

Everything is queued and sent as ONE batch request by finish() (or flush()): one
round trip and one redraw instead of one ~0.8 s round trip per element. Pass
batch=False to send each call immediately (useful when stepping through by hand).

Symbols are placed with their template properties, then the given properties are
set in the same op, so PDK defaults (ad/as/pd/ps formulas, model names) are kept.
Pin offsets of the symbols used here (x right, y down, rotation 0):
    sky130_fd_pr/nfet_01v8.sym, pfet_01v8.sym: D(20,-30) G(-20,0) S(20,30) B(20,0)
    res.sym, capa.sym, ind.sym, vsource.sym, isource.sym: two pins at (0,-30) and (0,30)
    gnd.sym, lab_pin.sym: pin at (0,0)
"""


class Builder:
    def __init__(self, vd, batch=True):
        self.xs = vd.xschem
        self.batched = batch
        self.queue = self.xs.batch()

    def _do(self, op, **args):
        if self.batched:
            self.queue.add(op, **args)
            return None
        return self.xs.call(op, **args).check().result

    def new(self, path, replace=False):
        return self._do("new_schematic", path=path, replace=replace)

    def place(self, symbol, x, y, name=None, rot=0, **props):
        p = dict(props)
        if name:
            p["name"] = name
        r = self._do("place", symbol=symbol, x=x, y=y, rot=rot, flip=0, props="", set=p)
        return name or (r["name"] if r else None)

    def modify(self, path):
        """Open an existing schematic instead of starting a new one."""
        return self._do("modify", path=path)

    def wire(self, *points):
        self._do("wire", points=list(points))

    def connect(self, a, pin_a, b, pin_b):
        """Wire instance pins by name: connect("R1", "M", "M1", "D")."""
        return self._do("wire_pins", **{"from": a, "from_pin": pin_a, "to": b, "to_pin": pin_b})

    def label_pin(self, instance, pin, net, length=40):
        """Stub + net label on a pin, facing outward: label_pin("M1", "G", "IN")."""
        return self._do("label_pin", name=instance, pin=pin, net=net, length=length)

    def label(self, net, x, y, rot=0):
        return self.place("lab_pin.sym", x, y, rot=rot, lab=net)

    def gnd(self, x, y):
        return self.place("gnd.sym", x, y)

    def code(self, x, y, text, name="NGSPICE"):
        return self.place("devices/code_shown.sym", x, y, name=name, only_toplevel="true", value=text)

    def flush(self):
        """Send the queued ops now; returns the batch Result (raises on failure)."""
        return self.queue.run().check()

    def finish(self):
        """Save, zoom, netlist; returns the netlist result {path, netlist}."""
        self._do("save")
        self._do("zoom_fit")
        if not self.batched:
            return self.xs.netlist().check().result
        self._do("netlist")
        r = self.flush()
        return r.result["results"][-1]
