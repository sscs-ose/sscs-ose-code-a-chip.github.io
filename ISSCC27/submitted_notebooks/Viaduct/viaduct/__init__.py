"""Viaduct: live bridge between LLM agents and the open-source analog stack.

    from viaduct import Viaduct
    vd = Viaduct.from_env()                    # live mode: the GUIs on the noVNC desktop
    vd.klayout.new_layout("TCOIL_DEMO")
    coil = vd.klayout.place_tcoil(params=dict(metalWidth=4.0, area=6400.0))
    png = vd.klayout.screenshot()              # local path; look at it
    vd.klayout.set_pcell_params(turnSpacing=3.0)   # same instance redraws in place
    em = vd.em.fasthenry(dict(metalWidth=4.0, area=6400.0))
    vd.klayout.annotate(results=em.result["annotation"], run_id=em.result["run_id"])

Every call returns a Result (status, result, error, ...), the same shape as
virtuoso-bridge's VirtuosoResult. Nothing here knows about ports or tokens:
the relay inside the container signs requests; this side only runs docker exec.
"""
import time
from dataclasses import dataclass, field
from typing import Any

from .transport import Config, Transport

__all__ = ["Viaduct", "Result", "ViaductError", "Config"]
__version__ = "0.3.0"


class ViaductError(RuntimeError):
    pass


@dataclass
class Result:
    status: str
    result: Any = None
    error: str = None
    ms: float = None
    extra: dict = field(default_factory=dict)

    @property
    def ok(self):
        return self.status == "SUCCESS"

    def check(self):
        """Return self, or raise ViaductError with the tool's message."""
        if not self.ok:
            hint = self.extra.get("hint")
            raise ViaductError("%s: %s%s" % (self.status, self.error, ("  (" + hint + ")") if hint else ""))
        return self

    @property
    def request_id(self):
        """Id this request was sent with; look its outcome up with tool.receipt(id)."""
        return self.extra.get("request_id")

    def __getitem__(self, key):
        return self.result[key]

    @classmethod
    def from_reply(cls, reply, ms):
        reply = dict(reply)
        return cls(status=reply.pop("status", "ERROR"), result=reply.pop("result", None),
                   error=reply.pop("error", None), ms=round(ms, 1), extra=reply)


class _Tool:
    tool = None

    def __init__(self, vd):
        self.vd = vd

    def call(self, op, timeout=None, **args):
        return self.vd.call(self.tool, op, timeout=timeout, **args)

    def __getattr__(self, op):
        # Any tap op not wrapped below is still reachable: vd.klayout.hierarchy(depth=2)
        if op.startswith("_"):
            raise AttributeError(op)
        return lambda **args: self.call(op, **args)

    def ping(self):
        return self.call("ping")

    def hello(self):
        """Handshake: protocol version, tap version, pid; the reply is signed with the session token."""
        return self.call("hello")

    def receipt(self, request_id):
        """Outcome of an earlier request by its id: unknown / running / completed (+ its reply).
        Use after a TIMEOUT instead of resending; the tap refuses a reused id anyway."""
        return self.call("receipt", request_id=request_id)

    def dialogs(self):
        """Read-only list of open dialogs: id, title, text, buttons. Changes nothing."""
        return self.call("dialogs")

    def close_dialog(self, id, expected_title, action="close"):
        """Close ONE dialog, after the designer agreed. id/expected_title from dialogs()
        (re-checked by the tap); action "close" or "button:<text>"."""
        return self.call("close_dialog", id=id, expected_title=expected_title, action=action)

    def dismiss_dialogs(self, confirm_all=False):
        """Legacy bulk close of every dialog, the designer's included; refused unless confirm_all."""
        return self.call("dismiss_dialogs", confirm_all=confirm_all)

    def snapshot(self):
        return self.call("snapshot")

    def selection(self):
        return self.call("selection")

    def reload(self):
        return self.call("reload")

    def zoom_fit(self):
        return self.call("zoom_fit")

    def screenshot(self, path=None, width=1400, height=900):
        """Save a PNG of the live window; result['local_path'] is readable here."""
        path = path or "%s/runs/%s_%s.png" % (self.vd.cfg.remote_dir, self.tool, time.strftime("%Y%m%d_%H%M%S"))
        r = self.call("screenshot", path=path, width=width, height=height)
        if r.ok:
            r.result["local_path"] = self.vd.transport.to_local(path)
        return r


class Batch:
    """Queue ops and send them in one request (one round trip, one tool lock).

        with vd.xschem.batch() as b:
            b.place("res.sym", 20, -100, name="R1", value="2k")
            b.wire(20, -70, 20, -30)
        print(b.result.result["done"])

    The tap runs the ops in order and stops at the first failure; result.result has
    ok, done, total, results (one per completed op) and failure {index, op, error}.
    On exit the batch is sent and checked (ViaductError on failure)."""

    def __init__(self, tool):
        self._tool = tool
        self.ops = []
        self.result = None

    def add(self, op, **args):
        self.ops.append({"op": op, "args": args})
        return len(self.ops) - 1

    def run(self, timeout=None):
        if not self.ops:
            self.result = Result("SUCCESS", result={"ok": True, "done": 0, "total": 0, "results": []})
            return self.result
        r = self._tool.call("batch", timeout=timeout or max(60, 2 * len(self.ops)), ops=self.ops)
        if r.ok and isinstance(r.result, dict) and not r.result.get("ok", False):
            f = r.result.get("failure", {})
            r = Result("ERROR", result=r.result, ms=r.ms,
                       error="batch stopped at op %s (%s) after %s of %s ops: %s" % (
                           f.get("index"), f.get("op"), r.result.get("done"), r.result.get("total"), f.get("error")))
        self.result = r
        self.ops = []
        return r

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.run().check()
        return False


class XschemBatch(Batch):
    def place(self, symbol, x, y, rot=0, flip=0, props="", **set_props):
        """Place with the symbol template; set_props (name=..., W=..., value=...) applied in the same op."""
        return self.add("place", symbol=symbol, x=x, y=y, rot=rot, flip=flip, props=props, set=set_props)

    def wire(self, *points):
        return self.add("wire", points=list(points))

    def set_props(self, instance, props=None, **more):
        return self.add("set_props", name=instance, props=dict(props or {}, **more))

    def wire_pins(self, a, pin_a, b, pin_b):
        return self.add("wire_pins", **{"from": a, "from_pin": pin_a, "to": b, "to_pin": pin_b})

    def label_pin(self, instance, pin, net, length=40):
        return self.add("label_pin", name=instance, pin=pin, net=net, length=length)


class KLayoutBatch(Batch):
    def new_layout(self, cell="TOP"):
        return self.add("new_layout", cell=cell)

    def place_tcoil(self, name="DUT", x=0.0, y=0.0, params=None):
        return self.add("place_tcoil", name=name, x=x, y=y, params=params or {})

    def set_pcell_params(self, name="DUT", **params):
        return self.add("set_pcell_params", name=name, params=params)

    def add_shapes(self, layer, datatype=20, boxes=None, polygons=None):
        return self.add("add_shapes", layer=layer, datatype=datatype, boxes=boxes, polygons=polygons)

    def add_label(self, text, x, y, layer, datatype=5):
        return self.add("add_label", text=text, x=x, y=y, layer=layer, datatype=datatype)


class KLayout(_Tool):
    tool = "klayout"

    def batch(self):
        """Queue layout ops and send them as one request / one undo step."""
        return KLayoutBatch(self)

    def eval(self, code):
        """Python inside KLayout (developer mode; disabled in safe mode). Set `result`."""
        return self.call("exec_python", code=code)

    def windows(self):
        return self.call("windows")

    def new_layout(self, cell="TOP"):
        return self.call("new_layout", cell=cell)

    def open(self, path, cell=None):
        return self.call("open", path=path, cell=cell)

    def save(self, path):
        return self.call("save", path=path)

    def use_library(self, device="tcoil", reload_code=True):
        return self.call("use_library", device=device, reload_code=reload_code)

    def place_tcoil(self, name="DUT", x=0.0, y=0.0, params=None):
        return self.call("place_tcoil", name=name, x=x, y=y, params=params or {})

    def set_pcell_params(self, name="DUT", **params):
        return self.call("set_pcell_params", name=name, params=params)

    def describe(self, name="DUT"):
        return self.call("describe", name=name)

    def annotate(self, name="DUT", results=None, run_id=""):
        return self.call("annotate", name=name, results=results or {}, run_id=run_id)

    def add_shapes(self, layer, datatype=20, boxes=None, polygons=None):
        return self.call("add_shapes", layer=layer, datatype=datatype, boxes=boxes, polygons=polygons)

    def add_label(self, text, x, y, layer, datatype=5):
        return self.call("add_label", text=text, x=x, y=y, layer=layer, datatype=datatype)

    def hierarchy(self, depth=3):
        return self.call("hierarchy", depth=depth)


class Xschem(_Tool):
    tool = "xschem"

    def batch(self):
        """Queue schematic ops and send them as one request (drawing suspended until the end)."""
        return XschemBatch(self)

    def eval(self, code):
        """Tcl inside xschem (developer mode; disabled in safe mode)."""
        return self.call("eval", code=code)

    def new_schematic(self, path, replace=False):
        return self.call("new_schematic", path=path, replace=replace)

    def open(self, path):
        return self.call("load", path=path)

    def place(self, symbol, x, y, rot=0, flip=0, props=""):
        return self.call("place", symbol=symbol, x=x, y=y, rot=rot, flip=flip, props=props)

    def wire(self, *points):
        return self.call("wire", points=list(points))

    def set_props(self, instance, props=None, **more):
        """Set instance properties; props may include 'name' to rename the instance."""
        return self.call("set_props", name=instance, props=dict(props or {}, **more))

    def create(self, path, replace=False):
        """New empty schematic at path (alias of new_schematic)."""
        return self.new_schematic(path, replace=replace)

    def modify(self, path):
        """Open an existing schematic for editing (error if it does not exist)."""
        return self.call("modify", path=path)

    def pins(self, instance):
        """Pins of one instance: name, x, y and the net each is on now."""
        return self.call("pins", name=instance)

    def wire_pins(self, a, pin_a, b, pin_b):
        """Wire pin_a of instance a to pin_b of instance b (straight, or L: horizontal then vertical)."""
        return self.call("wire_pins", **{"from": a, "from_pin": pin_a, "to": b, "to_pin": pin_b})

    def label_pin(self, instance, pin, net, length=40):
        """Short stub out of the pin, in the direction it faces, ending in a net label."""
        return self.call("label_pin", name=instance, pin=pin, net=net, length=length)

    def connectivity(self):
        """Read back what is connected: instances -> pin -> net, nets -> pins and labels."""
        return self.call("connectivity")

    def check(self):
        """Floating pins, label-only nets, single-pin nets; result['ok'] is False on any warning."""
        return self.call("check")

    def describe(self):
        return self.call("describe")

    def netlist(self):
        return self.call("netlist")

    def save(self):
        return self.call("save")


class Sim(_Tool):
    tool = "sim"

    def run(self, netlist, nodes=("out",)):
        return self._localize(self.call("run", netlist=netlist, nodes=list(nodes), pdk=self.vd.cfg.pdk))

    def xschem(self, nodes=("out",), live=True):
        """Netlist the schematic open in xschem, simulate, show graphs on it (live)."""
        return self._localize(self.call("xschem", nodes=list(nodes), pdk=self.vd.cfg.pdk, live=live))

    def op(self, netlist=None):
        """DC operating point per MOSFET (Id, gm, gds, Vgs, Vds, Vth, Vdsat, Vds margin, region).
        Without a netlist: the schematic open in xschem. result['warnings'] lists devices
        in or near triode."""
        r = self.call("op", netlist=netlist, pdk=self.vd.cfg.pdk)
        if isinstance(r.result, dict) and "run_dir" in r.result:
            r.result["local_run_dir"] = self.vd.transport.to_local(r.result["run_dir"])
        return r

    def sweep(self, netlist, params=None, node="out", fixed=None, cases=None, ac="dec 40 1e8 2e11"):
        """One ngspice process: every combination of params {name: [values]}, or the explicit
        cases [{"label":..., name: value}]; AC metrics of node per point (+ compare.png for <= 8)."""
        return self._localize(self.call("sweep", netlist=netlist, params=params, node=node, cases=cases,
                                        fixed=fixed or {}, ac=ac, pdk=self.vd.cfg.pdk))

    def _localize(self, r):
        if isinstance(r.result, dict) and "run_dir" in r.result:
            r.result["local_run_dir"] = self.vd.transport.to_local(r.result["run_dir"])
            r.result["local_images"] = [self.vd.transport.to_local(p) for p in r.result.get("images", [])]
        return r


class EM(_Tool):
    tool = "em"

    def fasthenry(self, params=None, freqs_hz=(1e9, 5e9, 10e9, 20e9), mesh="normal"):
        """Quasi-static L, R, Q, k of the T-coil for these PCell parameters."""
        r = self.call("fasthenry", params=params or {}, freqs_hz=list(freqs_hz), mesh=mesh, pdk=self.vd.cfg.pdk)
        if isinstance(r.result, dict) and "run_dir" in r.result:
            r.result["local_run_dir"] = self.vd.transport.to_local(r.result["run_dir"])
        return r

    def fastercap(self, params=None, accuracy=0.01):
        """Parasitic C of the T-coil (FasterCap): bridging C between the halves P1-P3 / P3-P2
        and each half to the substrate, plus a pi-split for SPICE (spice_parasitics)."""
        r = self.call("fastercap", params=params or {}, accuracy=accuracy, pdk=self.vd.cfg.pdk)
        if isinstance(r.result, dict) and "run_dir" in r.result:
            r.result["local_run_dir"] = self.vd.transport.to_local(r.result["run_dir"])
        return r

    def palace(self, params=None, fstop=50e9, fstep=1e9, cell=2.5, order=2, np=8, substrate_ohm_cm=10.0,
               timeout=6 * 3600):
        """Full-wave FEM (gds2palace + Palace) of the T-coil with a met1 ground frame and fingers,
        compared with FastHenry on the identical structure. Takes minutes to an hour."""
        r = self.call("palace", timeout=timeout, params=params or {}, fstop=fstop, fstep=fstep, cell=cell,
                      order=order, np=np, substrate_ohm_cm=substrate_ohm_cm, pdk=self.vd.cfg.pdk)
        if isinstance(r.result, dict) and "run_dir" in r.result:
            r.result["local_run_dir"] = self.vd.transport.to_local(r.result["run_dir"])
            r.result["local_images"] = [self.vd.transport.to_local(p) for p in r.result.get("images", [])]
        return r

    def convergence(self, params=None, freq_hz=10e9):
        return self.call("convergence", params=params or {}, freq_hz=freq_hz, pdk=self.vd.cfg.pdk)


class Verify(_Tool):
    tool = "verify"

    def drc(self, gds=None, live=True, options=None):
        """PDK DRC deck in batch. Without gds: checks the layout open in KLayout and
        shows the markers there (Marker Browser). options: deck switches, e.g. {"feol": "false"}."""
        r = self.call("drc", gds=gds, live=live, options=options or {}, pdk=self.vd.cfg.pdk)
        if isinstance(r.result, dict) and "run_dir" in r.result:
            r.result["local_run_dir"] = self.vd.transport.to_local(r.result["run_dir"])
        return r


class History(_Tool):
    """Time scroll. Every successful edit of xschem / KLayout is a step; designers add
    checkpoints; restore brings any step back into the windows (the replaced state is
    recorded first, so nothing is lost)."""
    tool = "hub"

    def list(self, n=50):
        return self.call("history", n=n)

    def checkpoint(self, label="", actor="designer"):
        return self.call("checkpoint", label=label, actor=actor)

    def restore(self, step, tools=None):
        return self.call("restore", step=step, tools=tools)

    def config(self, enabled=None, thumbs=None):
        return self.call("history_config", enabled=enabled, thumbs=thumbs)

    def timeline(self, path=None):
        r = self.call("timeline", path=path)
        if r.ok:
            r.result["local_path"] = self.vd.transport.to_local(r.result["path"])
        return r


class Interrupts(_Tool):
    """Designer interrupts. The designer (or a script acting as one) sends an instruction or a
    pause; hand edits in the GUI raise one by themselves. While one is unacknowledged the
    agent's edits come back with status INTERRUPTED (the reply lists the interrupts, the
    changes since the agent's last edit and its saved plan); the agent reads, acknowledges
    and continues from the modified design."""
    tool = "hub"

    def send(self, message, pause=False, selection=None):
        """Designer side: an instruction (selection: {tool: [names]}, default: current selection)."""
        return self.call("interrupt", message=message, pause=pause, selection=selection)

    def resume(self):
        """Designer side: end a pause."""
        return self.call("resume")

    def status(self, n=20):
        """Pending and recent interrupts, pause state, plan (runs hand-edit detection first)."""
        return self.call("interrupts", n=n)

    def ack(self, ids="all", note=""):
        """Agent side: acknowledge interrupts (after reading their changes / instruction)."""
        return self.call("interrupt_ack", ids=ids, note=note)

    def plan(self, steps=None, done=None, note=None):
        """Agent side: save the remaining plan (list of steps) / how many are done; shown to
        the designer on the timeline page and returned with every INTERRUPTED reply."""
        args = {k: v for k, v in (("steps", steps), ("done", done), ("note", note)) if v is not None}
        return self.call("plan", **args)


class Hub(_Tool):
    tool = "hub"

    def status(self):
        return self.call("status")

    def safe(self, on=True):
        return self.call("safe", on=on)

    def audit(self, n=20):
        return self.call("audit", n=n)


class Viaduct:
    # live: the GUIs on the noVNC desktop (DISPLAY :1).  headless: the same tools and taps on an
    # invisible Xvfb display with their own ports and state dir, for notebooks and CI.
    SESSIONS = {"live": {"display": ":1", "ports": None},
                "headless": {"display": ":99", "ports": {"klayout": 18775, "xschem": 18776}}}

    def __init__(self, cfg=None, mode="live", safe=False, actor=None):
        if mode not in self.SESSIONS:
            raise ValueError("mode must be 'live' or 'headless'")
        self.cfg = cfg or Config.load()
        self.transport = Transport(self.cfg)
        self.mode = mode
        self.safe = safe
        self.actor = actor       # e.g. "designer": edits made through this instance are attributed to them
        self.timeout = None      # default per-request tool timeout (s); relay default 60
        self.klayout = KLayout(self)
        self.xschem = Xschem(self)
        self.sim = Sim(self)
        self.em = EM(self)
        self.verify = Verify(self)
        self.hub = Hub(self)
        self.history = History(self)
        self.interrupts = Interrupts(self)

    @classmethod
    def from_env(cls, mode="live", safe=False, actor=None):
        return cls(Config.load(), mode=mode, safe=safe, actor=actor)

    def call(self, tool, op, timeout=None, **args):
        t0 = time.time()
        reply = self.transport.call(tool, op, args, timeout=timeout or self.timeout, safe=self.safe,
                                    session=self.mode, actor=self.actor)
        return Result.from_reply(reply, (time.time() - t0) * 1000)

    # ---- lifecycle (container side) --------------------------------------------------

    def install(self):
        """Idempotent: KLayout autorun macro + xschemrc block inside the container."""
        rd = self.cfg.remote_dir
        script = r'''
set -e
mkdir -p ~/.viaduct ~/.klayout/pymacros ~/.xschem && chmod 700 ~/.viaduct
cp {rd}/taps/klayout/viaduct_autorun.lym ~/.klayout/pymacros/viaduct_autorun.lym
rc=~/.xschem/xschemrc
touch $rc
if ! grep -q "viaduct tap begin" $rc; then
  cp $rc $rc.before-viaduct
  cat >> $rc <<'RC'
# --- viaduct tap begin (added by `viaduct install`; remove this block to uninstall)
if {{[info commands winfo] ne {{}}}} {{
  catch {{ source {rd}/taps/xschem/viaduct_tap.tcl }}
}}
# --- viaduct tap end
RC
  echo xschemrc-updated
else
  echo xschemrc-already
fi
echo klayout-macro-installed
'''.format(rd=rd)
        p = self.transport.shell(script)
        return Result("SUCCESS" if p.returncode == 0 else "ERROR",
                      result=[l for l in p.stdout.splitlines() if not l.startswith("[INFO]")],
                      error=p.stderr.strip() or None)

    def start(self, tools=("klayout", "xschem"), wait=45):
        """Start the container and any tool whose tap is not answering (taps autoload).
        Headless: also starts the Xvfb display and gives the tools their own ports/state dir."""
        if not self.transport.local:
            self.transport.docker(["start", self.cfg.container])
        self.install().check()
        sess = self.SESSIONS[self.mode]
        display = sess["display"]
        env = ""
        if self.mode != "live":
            state = "$HOME/.viaduct/%s" % self.mode
            env = "export VIADUCT_STATE_DIR=%s VIADUCT_KLAYOUT_PORT=%d VIADUCT_XSCHEM_PORT=%d; mkdir -p %s; " % (
                state, sess["ports"]["klayout"], sess["ports"]["xschem"], state)
            # '^Xvfb' anchors the match: an unanchored pattern also matches this very bash command line.
            running = self.transport.shell("pgrep -f '^Xvfb %s' >/dev/null && echo yes || echo no" % display)
            if "yes" not in running.stdout:
                self.transport.shell("Xvfb %s -screen 0 1600x1000x24 >/tmp/viaduct_xvfb.log 2>&1" % display,
                                     detach=True)
                time.sleep(2)
        launch = {"klayout": "klayout -e", "xschem": "xschem"}
        workdir = {"klayout": "/foss/designs", "xschem": self.cfg.remote_dir + "/xschem"}
        out = {}
        for tool in tools:
            if getattr(self, tool).ping().ok:
                out[tool] = "already running"
                continue
            self.transport.shell(
                "%sexport DISPLAY=%s; source /foss/tools/sak/sak-pdk-script.sh %s >/dev/null; mkdir -p %s; cd %s; "
                "nohup %s > /tmp/viaduct_%s_%s.log 2>&1 &" % (env, display, self.cfg.pdk, workdir[tool], workdir[tool],
                                                            launch[tool], self.mode, tool), detach=True)
            deadline = time.time() + wait
            r = None
            while time.time() < deadline:
                time.sleep(1.5)
                r = getattr(self, tool).ping()
                if r.ok:
                    break
            out[tool] = r.result if r and r.ok else "did not answer: see /tmp/viaduct_%s_%s.log" % (self.mode, tool)
        # Report (never close) open dialogs: even on a freshly started tool they are left to the designer.
        for tool in tools:
            d = getattr(self, tool).dialogs()
            if d.ok and d.result:
                out.setdefault("dialogs", {})[tool] = d.result
        ok = all(isinstance(v, dict) or v == "already running" for k, v in out.items() if k != "dialogs")
        return Result("SUCCESS" if ok else "ERROR", result=out)

    def stop(self, tools=("klayout", "xschem"), force=False):
        return Result("SUCCESS", result={t: getattr(self, t).call("stop", force=force).__dict__ for t in tools})
