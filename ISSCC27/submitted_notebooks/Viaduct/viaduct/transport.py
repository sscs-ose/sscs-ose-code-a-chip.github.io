"""How the Windows/host side reaches the container.

Every call is `<prefix> docker exec -i <container> python3 <remote_dir>/container/relay.py`
with one JSON request on stdin. The prefix is the only transport-specific part:

    wsl  (default on Windows):  wsl -d <distro> --exec docker exec ...
    local (inside the container, e.g. Jupyter): python3 relay.py directly, no docker
    ssh  (reserved): ssh [-J jump] <host> docker exec ...   -- not enabled yet, see README

Settings come from VIADUCT_* environment variables, then
%USERPROFILE%/.viaduct/config.json (written by `viaduct init`), then defaults.
"""
import json
import os
import subprocess
import uuid
from dataclasses import dataclass, asdict, field
from pathlib import Path

CONFIG_FILE = Path.home() / ".viaduct" / "config.json"


@dataclass
class Config:
    transport: str = "wsl"
    distro: str = "Ubuntu"
    container: str = "opencad-desktop"
    remote_dir: str = "/foss/designs/viaduct"
    local_dir: str = r"\\wsl.localhost\Ubuntu\home\ash\idamic\workspace\viaduct"
    pdk: str = "sky130A"
    # reconnect=true: the page reconnects by itself (password kept) after WSL/laptop sleep
    novnc_url: str = "http://localhost:18080/vnc.html?autoconnect=true&reconnect=true&reconnect_delay=3000&resize=remote"
    ssh_host: str = ""
    ssh_jump: str = ""
    extra: dict = field(default_factory=dict)

    @classmethod
    def load(cls):
        cfg = cls()
        if os.name == "posix" and os.path.isdir("/foss/designs"):
            # Running inside the IIC-OSIC-TOOLS container (Jupyter, terminal): no docker hop.
            cfg.transport = "local"
            cfg.local_dir = cfg.remote_dir
        if CONFIG_FILE.exists():
            for k, v in json.loads(CONFIG_FILE.read_text(encoding="utf-8")).items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)
        for k in asdict(cfg):
            env = os.environ.get("VIADUCT_" + k.upper())
            if env:
                setattr(cfg, k, env)
        return cfg

    def save(self):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        return CONFIG_FILE


class Transport:
    def __init__(self, cfg=None):
        self.cfg = cfg or Config.load()
        if self.cfg.transport == "ssh":
            raise NotImplementedError("ssh transport is reserved but not enabled yet "
                                      "(planned: ssh [-J jump] host docker exec ...)")
        if self.cfg.transport not in ("wsl", "local"):
            raise ValueError("unknown transport %r" % self.cfg.transport)
        self.local = self.cfg.transport == "local"

    def prefix(self):
        # --exec: arguments go to docker verbatim (plain `--` re-parses them in a shell)
        return ["wsl", "-d", self.cfg.distro, "--exec"]

    def docker(self, args, stdin=None, timeout=90):
        return subprocess.run(self.prefix() + ["docker"] + args, input=stdin, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=timeout)

    def shell(self, script, timeout=120, detach=False):
        """Run a login-shell script inside the container (PDK and tool paths set)."""
        if self.local:
            if detach:
                subprocess.Popen(["bash", "-lc", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 start_new_session=True)
                return subprocess.CompletedProcess(script, 0, "", "")
            return subprocess.run(["bash", "-lc", script], capture_output=True, text=True, timeout=timeout)
        args = ["exec"] + (["-d"] if detach else []) + [self.cfg.container, "bash", "-lc", script]
        return self.docker(args, timeout=timeout)

    def call(self, tool, op, args=None, timeout=None, safe=False, session="live", request_id=None, actor=None):
        # Every request carries a fresh id, so its outcome can be looked up (receipt)
        # even when the reply never arrives; the same id is never sent twice.
        rid = request_id or uuid.uuid4().hex
        req = {"tool": tool, "op": op, "args": args or {}, "session": session, "request_id": rid}
        if actor:
            req["actor"] = actor          # who the edit is attributed to in history and audit
        if timeout:
            req["timeout"] = timeout
        if safe:
            req["safe"] = True
        wait = (timeout or 60) + 30 if tool in ("klayout", "xschem", "hub") else max(timeout or 0, 900)
        try:
            relay = self.cfg.remote_dir + "/container/relay.py"
            if self.local:
                proc = subprocess.run(["python3", relay], input=json.dumps(req), capture_output=True,
                                      text=True, encoding="utf-8", errors="replace", timeout=wait)
            else:
                proc = self.docker(["exec", "-i", self.cfg.container, "python3", relay],
                                   stdin=json.dumps(req), timeout=wait)
        except subprocess.TimeoutExpired:
            return {"status": "TRANSPORT_TIMEOUT", "request_id": rid,
                    "error": "no reply from the container within %ss; outcome unknown, "
                             "query receipt %s (do not resend)" % (wait, rid)}
        out = proc.stdout.strip().splitlines()
        if proc.returncode != 0 or not out:
            return {"status": "TRANSPORT_ERROR", "request_id": rid, "error": (proc.stderr or proc.stdout).strip()}
        reply = json.loads(out[-1])
        reply.setdefault("request_id", rid)
        return reply

    def to_local(self, remote_path):
        """Container path under remote_dir -> path readable from this machine."""
        if remote_path and remote_path.startswith(self.cfg.remote_dir):
            rel = remote_path[len(self.cfg.remote_dir):].lstrip("/")
            return str(Path(self.cfg.local_dir) / rel)
        return remote_path
