"""Resolve native TT includes and brace quoted resistor model arithmetic.

No fitted constants or installed PDK edits. The derived library contains the
selected native TT section and its include closure, with a source/hash map.
Only double-quoted DW arithmetic on generic-resistor .model cards is changed.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re


def brace_resistor_dw(text):
    changes = []
    # A model can span continuation lines. Keep every other byte of its card.
    pattern = r"(?im)^[ \t]*\.model[ \t]+(sky130_fd_pr__res_generic_\w+)[ \t]+r\b[^\r\n]*(?:\r?\n[ \t]*\+[^\r\n]*)*"

    def card(match):
        value = match.group(0)
        def dw(m):
            expression = m.group(2) or m.group(3)
            if not re.fullmatch(r"[A-Za-z0-9_ .()+*/-]+", expression):
                raise ValueError("unsupported quoted generic-resistor DW expression")
            replacement = m.group(1)+"{"+expression+"}"
            changes.append({"model": match.group(1), "parameter": "dw",
                "before": m.group(0), "after": replacement,
                "expression": expression})
            return replacement
        return re.sub(r'(?i)(\bdw\s*=\s*)(?:\{\s*"([^"\r\n]+)"\s*\}|"([^"\r\n]+)")', dw, value)

    return re.sub(pattern, card, text), changes


def compile_tt(pdk):
    """Expand .include/.lib file directives using the declaring file's path.

    Select only TT, preserve .if/.param/model/subckt ordering and repetition,
    and reject unresolved/recursive/out-of-PDK references. Nothing is written.
    """
    pdk = Path(pdk).resolve()
    entry = pdk/"libs.tech/ngspice/sky130.lib.spice"
    sources, fixes, stack = {}, [], []
    total = 0
    directive = re.compile(r'^\s*\.(include|inc|lib)\s+(?:"([^"]+)"|\'([^\']+)\'|(\S+))(.*)$', re.I)

    def expand(path, section=None):
        nonlocal total
        path = path.resolve(strict=True)
        if not path.is_relative_to(pdk) or not path.is_file():
            raise ValueError(f"native model include escapes PDK: {path}")
        key = (path, section.lower() if section else None)
        if key in stack or len(stack) > 48:
            raise ValueError(f"recursive/deep model includes: {path}")
        data = path.read_bytes()
        total += len(data)
        if total > 512_000_000 or len(sources) > 4096:
            raise ValueError("native TT include closure exceeds size limit")
        relative = path.relative_to(pdk).as_posix()
        sources[relative] = {"path": relative, "sha256": sha256(data).hexdigest(), "bytes": len(data)}
        text, edits = brace_resistor_dw(data.decode("utf-8"))
        fixes.extend({"path": relative, **edit} for edit in edits)
        stack.append(key)
        output = [f"* AUTOMX_NATIVE_SOURCE {relative} section={section or 'include'}\n"]
        active, found, depth = section is None, 0, None
        for line in text.splitlines(keepends=True):
            m = directive.match(line)
            if m:
                kind, name, tail = m.group(1).lower(), next(x for x in m.group(2, 3, 4) if x is not None), m.group(5).strip()
                tail = re.split(r"(?:^|\s)[$;]", tail, maxsplit=1)[0].strip()
                # One-argument .lib starts a named section; two arguments
                # load the requested section from a different file.
                if kind == "lib" and not tail:
                    if section is None:
                        raise ValueError(f"unselected library section in .include file: {path}")
                    if depth is not None:
                        raise ValueError(f"nested library sections in {path}")
                    depth = name
                    active = name.lower() == section.lower()
                    found += int(active)
                    continue
                if not active:
                    continue
                if kind == "lib" and not re.fullmatch(r"[\w.-]+", tail):
                    raise ValueError(f"unsupported library selector: {line.strip()}")
                if kind != "lib" and tail:
                    raise ValueError(f"unexpected include suffix: {line.strip()}")
                output.append(expand(path.parent/name, tail if kind == "lib" else None))
            elif re.match(r"(?i)^\s*\.endl\b", line):
                if section is None or depth is None:
                    raise ValueError(f"unbalanced library section: {path}")
                depth, active = None, False
            elif active or line.lstrip().startswith("*"):
                output.append(line if line.endswith(("\n", "\r")) else line+"\n")
        stack.pop()
        if section is not None and (found != 1 or depth is not None):
            raise ValueError(f"expected one complete {section} library section: {path}")
        return "".join(output)

    body = expand(entry, "tt")
    # A missing poly definition must not silently fall back to another model.
    if len(re.findall(r"(?im)^\s*\.model\s+sky130_fd_pr__res_generic_po\s+r\b", body)) != 1:
        raise ValueError("native TT closure must define exactly one generic-poly resistor model")
    compiled = "* Native SKY130 TT; quoted DW arithmetic braced for ngspice\n.lib tt\n"+body+".endl tt\n"
    report = {"format": "automx-cim-native-tt-model-overlay-v1", "corner": "tt",
        "sources": list(sources.values()), "syntax_corrections": fixes,
        "derived_sha256": sha256(compiled.encode()).hexdigest(),
        "scope": "native selected TT include closure; DW expression tokens preserved, quotes changed to braces; no fitted model or PDK installation edits"}
    return compiled, report
