"""Designer interrupts: the designer's actions take priority over the agent's edits.

Sources of an interrupt (all end up in the same queue, per session):
  hand_edit      the designer changed the design in the GUI, outside Viaduct. Detected when the
                 tool's content fingerprint differs from the one recorded after Viaduct's last
                 edit; the new state is recorded as a history step by the designer.
  designer_edit  an edit made through Viaduct as actor "designer".
  instruction    a message from the designer (`interrupt "..."`), with their current selection.
  pause          like instruction, and the agent's edits stay blocked until `resume`.

While an interrupt is unacknowledged (or the session is paused) every agent edit is refused
with status INTERRUPTED: the reply carries the interrupts, the changes since the agent's
last own edit (instance by instance) and the agent's saved plan. Reading is never blocked.
The agent acknowledges with `interrupt_ack` and continues from the modified design.

A schematic the designer has edited is also protected from being rebuilt: new_schematic
with replace=True on it is refused unless the call carries force_rebuild=true.

State: <state dir>/interrupts.json and plan.json.
"""
import contextlib
import fcntl
import json
import os
import re
import time

TOOLS = ("xschem", "klayout")
EDIT_KINDS = ("hand_edit", "designer_edit")


# ---- schematic diff ----------------------------------------------------------------------

def parse_sch(text):
    """{instance name: {"symbol", "at", "props"}}, wire count."""
    insts = {}
    for m in re.finditer(r"^C \{([^}]*)\}\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+\{(.*?)\}\s*$", text, re.M | re.S):
        props = dict((k, v.strip('"')) for k, v in re.findall(r'(\w+)=("[^"]*"|\S+)', m.group(6)))
        name = props.get("name") or "%s@%s,%s" % (m.group(1), m.group(2), m.group(3))
        insts[name] = {"symbol": m.group(1), "at": [m.group(2), m.group(3), m.group(4), m.group(5)], "props": props}
    return insts, len(re.findall(r"^N ", text, re.M))


def diff_sch(old_text, new_text):
    """Changes from old to new: added / removed instances, changed attributes, moves, wires."""
    if old_text is None or new_text is None:
        return None
    (a, wa), (b, wb) = parse_sch(old_text), parse_sch(new_text)
    out = {}
    added = sorted(set(b) - set(a))
    removed = sorted(set(a) - set(b))
    if added:
        out["added"] = {n: {"symbol": b[n]["symbol"], **{k: v for k, v in b[n]["props"].items() if k in ("W", "L", "nf", "value", "lab")}}
                        for n in added}
    if removed:
        out["removed"] = removed
    changed = {}
    for n in sorted(set(a) & set(b)):
        pa, pb = a[n]["props"], b[n]["props"]
        c = {k: [pa.get(k), pb.get(k)] for k in sorted(set(pa) | set(pb)) if pa.get(k) != pb.get(k)}
        if a[n]["symbol"] != b[n]["symbol"]:
            c["symbol"] = [a[n]["symbol"], b[n]["symbol"]]
        if a[n]["at"] != b[n]["at"]:
            c["moved"] = [a[n]["at"], b[n]["at"]]
        if c:
            changed[n] = c
    if changed:
        out["changed"] = changed
    if wa != wb:
        out["wires"] = [wa, wb]
    return out


# ---- state -------------------------------------------------------------------------------

class Interrupts:
    def __init__(self, state_dir, gui, history):
        self.dir = state_dir
        self.gui = gui
        self.history = history
        self.file = os.path.join(state_dir, "interrupts.json")
        self.plan_file = os.path.join(state_dir, "plan.json")

    @contextlib.contextmanager
    def _state(self):
        """Read-modify-write the state under a file lock."""
        os.makedirs(self.dir, exist_ok=True)
        with open(self.file + ".lock", "w") as lk:
            fcntl.flock(lk, fcntl.LOCK_EX)
            st = json.load(open(self.file)) if os.path.exists(self.file) else {}
            st.setdefault("next_id", 1)
            st.setdefault("items", [])
            st.setdefault("paused", False)
            st.setdefault("baseline", {})          # tool -> {"sha", "step"}
            yield st
            tmp = self.file + ".tmp"
            json.dump(st, open(tmp, "w"), indent=1)
            os.replace(tmp, self.file)

    def _snapshot_text(self, step, tool="xschem"):
        if step is None or self.history is None:
            return None
        try:
            e = self.history._entry(step)
            st = e["state"].get(tool)
            return open(os.path.join(self.history.dir, st["file"]), errors="replace").read() if st else None
        except Exception:
            return None

    def _fingerprint(self, tool):
        try:
            r = self.gui[tool]("fingerprint", {}, 10, "")
        except Exception:
            return None
        res = r.get("result") or {}
        return res.get("sha") if r.get("status") == "SUCCESS" else None

    def _new_item(self, st, kind, **fields):
        item = {"id": st["next_id"], "kind": kind, "t": round(time.time(), 3),
                "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "acked": False}
        item.update({k: v for k, v in fields.items() if v is not None})
        st["next_id"] += 1
        st["items"].append(item)
        return item

    # ---- detection ----------------------------------------------------------------------
    def detect(self, tools=TOOLS):
        """Compare fingerprints with the baseline; a difference is a hand edit in the GUI."""
        new = []
        for tool in tools:
            fp = self._fingerprint(tool)
            if fp is None:
                continue
            with self._state() as st:
                base = st["baseline"].get(tool)
                if base is None or base.get("sha") is None:
                    st["baseline"][tool] = {"sha": fp, "step": None}
                    continue
                if base["sha"] == fp:
                    continue
            # outside the state lock: the snapshot talks to the tool
            step = None
            if self.history is not None and self.history.config()["enabled"]:
                e = self.history.record([tool], actor="designer", kind="hand_edit", op="%s: edited in the GUI" % tool)
                step = e["step"]
            diff = diff_sch(self._snapshot_text(base.get("step")), self._snapshot_text(step)) if tool == "xschem" else None
            with self._state() as st:
                item = self._new_item(st, "hand_edit", tool=tool, step=step, since_step=base.get("step"),
                                      changes=diff or ({"layout": "changed"} if tool == "klayout" else None))
                st["baseline"][tool] = {"sha": fp, "step": step}
                new.append(item)
        return new

    def after_edit(self, tool, actor, step):
        """A Viaduct edit succeeded: new baseline; an edit by the designer is an interrupt."""
        fp = self._fingerprint(tool)
        with self._state() as st:
            prev = st["baseline"].get(tool) or {}
            st["baseline"][tool] = {"sha": fp, "step": step}
        if actor == "designer":
            diff = diff_sch(self._snapshot_text(prev.get("step")), self._snapshot_text(step)) if tool == "xschem" else None
            with self._state() as st:
                return self._new_item(st, "designer_edit", tool=tool, step=step, since_step=prev.get("step"),
                                      changes=diff or ({"layout": "changed"} if tool == "klayout" else None))
        return None

    def rebaseline(self, step=None, tools=TOOLS):
        """After a restore (or anything Viaduct itself put into the windows): new baseline."""
        for tool in tools:
            fp = self._fingerprint(tool)
            with self._state() as st:
                st["baseline"][tool] = {"sha": fp, "step": step}

    def restored(self, step, target):
        """The designer restored an earlier step: new baseline, and an interrupt with the change."""
        with self._state() as st:
            prev = (st["baseline"].get("xschem") or {}).get("step")
        self.rebaseline(step)
        diff = diff_sch(self._snapshot_text(prev), self._snapshot_text(step))
        with self._state() as st:
            return self._new_item(st, "restore", step=step, target=target, since_step=prev, changes=diff,
                                  message="the designer restored step %d; continue from it" % target)

    # ---- the designer's commands --------------------------------------------------------
    def raise_(self, message, pause=False, selection=None):
        step = None
        if self.history is not None and self.history.config()["enabled"]:
            e = self.history.checkpoint("interrupt: %s" % (message or ("pause" if pause else "")), actor="designer")
            step = e["step"]
        with self._state() as st:
            if pause:
                st["paused"] = True
            return self._new_item(st, "pause" if pause else "instruction", message=message,
                                  selection=selection or None, step=step)

    def resume(self):
        with self._state() as st:
            st["paused"] = False
            return {"paused": False}

    # ---- the agent's side ---------------------------------------------------------------
    def pending(self):
        with self._state() as st:
            return [i for i in st["items"] if not i["acked"]], st["paused"]

    def ack(self, ids="all", note=""):
        with self._state() as st:
            done = []
            for i in st["items"]:
                if not i["acked"] and (ids == "all" or i["id"] in ids):
                    i.update(acked=True, ack_t=round(time.time(), 3), ack_note=note)
                    done.append(i["id"])
            return {"acknowledged": done, "still_pending": [i["id"] for i in st["items"] if not i["acked"]],
                    "paused": st["paused"]}

    def status(self, n=20):
        with self._state() as st:
            return {"paused": st["paused"], "pending": [i for i in st["items"] if not i["acked"]],
                    "recent": st["items"][-n:], "baseline": st["baseline"], "plan": self.plan()}

    def designer_edited(self, schematic):
        """History steps in which the designer changed this schematic."""
        if self.history is None:
            return []
        out = []
        for e in self.history.entries():
            st = (e.get("state") or {}).get("xschem") or {}
            if e.get("actor") == "designer" and e.get("kind") in ("hand_edit", "edit") and "xschem" in e.get("tools", []) \
                    and os.path.normpath(st.get("name", "")) == os.path.normpath(schematic):
                out.append(e["step"])
        return out

    # ---- plan (the agent's task stack) ----------------------------------------------------
    def plan(self):
        return json.load(open(self.plan_file)) if os.path.exists(self.plan_file) else None

    def set_plan(self, steps=None, done=None, note=None):
        p = self.plan() or {"steps": [], "done": 0}
        if steps is not None:
            p = {"steps": list(steps), "done": 0}
        if done is not None:
            p["done"] = max(0, min(int(done), len(p["steps"])))
        if note is not None:
            p["note"] = note
        p["t"] = round(time.time(), 3)
        os.makedirs(self.dir, exist_ok=True)
        json.dump(p, open(self.plan_file, "w"), indent=1)
        return p
