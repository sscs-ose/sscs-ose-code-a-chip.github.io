"""Checkpointed tool steps and portable evidence for the wrapper integration pilot."""
from __future__ import annotations

from datetime import datetime, timezone
from contextlib import contextmanager
from contextvars import ContextVar
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED

from scripts.run_flow2_remaining_measurements import _save, _sha
from scripts.run_flow2_acquisition_layout import _call, _item, _verified

BASE = Path("results/sky130/flow2_wrapper_integration")
BUILD = Path("build/flow2_wrapper_integration")
PHYSICAL = Path("physical/sky130/wrapper_prototype/integration")
_EXPORT_MODE = ContextVar('flow2_export_mode', default='legacy')


@contextmanager
def export_mode(mode):
    """A parent campaign can defer child archives and export one final ZIP."""
    if mode not in ('legacy','deferred','zip_only'):
        raise ValueError('unknown integration export mode')
    token = _EXPORT_MODE.set(mode)
    try:
        yield
    finally:
        _EXPORT_MODE.reset(token)


def save_summary(path, report):
    """Retain the previous analysis when reinterpreting the same raw evidence."""
    path = Path(path)
    content = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") != content:
        prior = path.with_name(f"summary.prior_{_sha(path)[:16]}.json")
        if not prior.is_file():
            shutil.copy2(path, prior)
    _save(path, report)


def tag_ok(tag):
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", tag):
        raise ValueError("use an alphanumeric/underscore tag of at most 64 characters")


class Store:
    def __init__(self, root, tag, identity, *, result_base=BASE, build_base=BUILD,
                 physical_base=PHYSICAL):
        self.root, self.tag = Path(root).resolve(), tag
        tag_ok(tag)
        self.folder, self.build = self.root / result_base / tag, self.root / build_base / tag
        self.physical = self.root / physical_base / tag
        for path in (self.folder, self.build, self.physical):
            if not path.resolve().is_relative_to(self.root):
                raise ValueError("integration output escapes checkout")
        snapshot = self.folder / "inputs.json"
        if snapshot.is_file() and json.loads(snapshot.read_text(encoding="utf-8")) != identity:
            raise FileExistsError(f"inputs changed; retain old evidence and use a new tag: {tag}")
        self.folder.mkdir(parents=True, exist_ok=True)
        self.build.mkdir(parents=True, exist_ok=True)
        if not snapshot.is_file():
            _save(snapshot, identity)
        self.identity = _sha(snapshot)

    def note(self, text):
        line = f"[{datetime.now(timezone.utc).isoformat()}] {text}"
        print(line, flush=True)
        with (self.folder / "history.log").open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")

    def step(self, name, command, *, tcl=None, executor=None):
        """Reuse only complete successful steps; archive interrupted output before retry."""
        tag_ok(name)
        work, log = self.build / name, self.folder / f"{name}.log"
        checkpoint = self.folder / f"{name}.step.json"
        spec = {"inputs": self.identity, "command": command, "tcl": tcl}
        if checkpoint.is_file():
            try:
                saved = json.loads(checkpoint.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                saved = None  # Interrupted write: preserve it in the archive below.
            if saved is not None and saved.get("spec") != spec:
                raise FileExistsError(f"step changed; use a new integration tag: {name}")
            if saved is not None and saved.get("returncode") == 0:
                for item in saved["artifacts"]:
                    _verified(self.root, item)
                self.note(f"REUSE {name}")
                return subprocess.CompletedProcess(command, 0, log.read_text(encoding="utf-8"), ""), work
        if work.exists() or log.exists() or checkpoint.exists():
            old = self.build / "interrupted" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            old.mkdir(parents=True)
            for path in (work, log, checkpoint):
                if path.exists():
                    # Both resolved paths are within this checked output tree.
                    if not path.resolve().is_relative_to(self.root):
                        raise ValueError("refuse to move an external artifact")
                    shutil.move(str(path), str(old / path.name))
            self.note(f"ARCHIVE partial/failed {name}: {old.relative_to(self.root).as_posix()}")
        work.mkdir(parents=True)
        if tcl is not None:
            (work / "commands.tcl").write_text(tcl, encoding="utf-8")
        self.note(f"RUN {name}")
        result = _call(executor, work)
        log.write_text(result.stdout + result.stderr, encoding="utf-8")
        items = [_item(self.root, log)] + [_item(self.root, p) for p in sorted(work.rglob("*")) if p.is_file()]
        _save(checkpoint, {"spec": spec, "returncode": result.returncode, "artifacts": items})
        self.note(f"DONE {name}: exit={result.returncode}")
        return result, work


def bundle(root, tag, source_items=()):
    """One download folder, preserving build/results/physical paths and raw source proofs."""
    root = Path(root).resolve()
    tag_ok(tag)
    destination = root / "server_results/flow2_wrapper_integration" / tag
    if not destination.resolve().is_relative_to(root):
        raise ValueError("unsafe export destination")
    destination.mkdir(parents=True, exist_ok=True)
    mode = _EXPORT_MODE.get()
    if mode == 'deferred':
        # The parent collects native artifacts. Do not mirror them or create
        # a second copy of every child's OpenLane run and ADC waveform.
        path = destination/'export.json'
        if not path.exists():
            _save(path, {'format':'automx-cim-wrapper-integration-export-v1','tag':tag,
                         'status':'DEFERRED_TO_PARENT_EXPORT','files':[],
                         'native_roots':[str(p/tag) for p in (BUILD,BASE,PHYSICAL)]})
        return path
    paths = {}
    for base in (BUILD / tag, BASE / tag, PHYSICAL / tag):
        for path in (root / base).rglob("*"):
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError("unsafe export source")
            if path.is_file():
                paths[path.relative_to(root).as_posix()] = path
    for item in source_items:
        path = _verified(root, item)
        paths[path.relative_to(root).as_posix()] = path
    # Also mirror the three buckets for browsing without extracting the ZIP.
    if mode == 'legacy':
        for rel, path in sorted(paths.items()):
            target = destination / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    summary = root / BASE / tag / "summary.json"
    if summary.is_file():
        shutil.copy2(summary, destination / "summary.json")
    history = root / BASE / tag / "history.log"
    if history.is_file():
        shutil.copy2(history, destination / "history.log")
    index = {"format": "automx-cim-wrapper-integration-export-v1", "tag": tag,
             "files": [_item(root, p) for _, p in sorted(paths.items())],
             "storage_mode":mode}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    if mode == 'zip_only':
        stamp = sha256(json.dumps(index,sort_keys=True).encode()).hexdigest()[:20]
    archive = destination / f"diagnostics_{stamp}.zip"
    if archive.is_file() and mode == 'zip_only':
        prior_index=destination/'export.json'
        prior=json.loads(prior_index.read_text(encoding='utf-8')) if prior_index.is_file() else {}
        saved=prior.get('archive',{})
        if (prior.get('files')!=index['files'] or saved.get('path')!=archive.relative_to(root).as_posix()
                or saved.get('sha256')!=_sha(archive)):
            raise ValueError('existing diagnostics archive differs; retain it for inspection')
    if not archive.is_file():
        temporary = archive.with_suffix('.zip.tmp')
        try:
            with ZipFile(temporary, "w", compression=ZIP_DEFLATED) as output:
                for rel, path in sorted(paths.items()):
                    output.write(path, rel)
                output.writestr("diagnostic_index.json", json.dumps(index, indent=2) + "\n")
            temporary.replace(archive)
        except BaseException:
            # Remove only this incomplete archive, never the native evidence.
            temporary.unlink(missing_ok=True)
            raise
    index["archive"] = _item(root, archive)
    _save(destination / "export.json", index)
    return archive
