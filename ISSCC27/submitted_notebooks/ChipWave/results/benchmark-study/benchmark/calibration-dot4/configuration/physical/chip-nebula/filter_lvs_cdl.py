"""Keep only schematic subcircuits reachable from the LVS top cell.

The source CDL is retained unchanged. The filtered file contains exact original
text for every retained definition, in original order; no net or device is
rewritten. Missing or ambiguous references fail closed before KLayout starts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def _digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def filter_cdl(source: Path, target: Path, top: str) -> dict[str, object]:
    original = source.read_bytes()
    text = original.decode("utf-8")
    segments: list[tuple[str, str, list[str]]] = []
    outside: list[str] = []
    block: list[str] | None = None
    name = ""
    definitions: dict[str, list[str]] = {}
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        tokens = stripped.split()
        directive = tokens[0].upper() if tokens else ""
        if directive == ".SUBCKT":
            if block is not None or len(tokens) < 2:
                raise ValueError("nested or unnamed .SUBCKT")
            if outside:
                segments.append(("text", "", outside))
                outside = []
            name = tokens[1].lower()
            if name in definitions:
                raise ValueError(f"duplicate subcircuit: {name}")
            block = [line]
        elif directive == ".ENDS":
            if block is None:
                raise ValueError(".ENDS without .SUBCKT")
            if len(tokens) > 1 and tokens[1].lower() != name:
                raise ValueError(f".ENDS name mismatch: {name}")
            block.append(line)
            definitions[name] = block
            segments.append(("subckt", name, block))
            block = None
            name = ""
        elif block is not None:
            block.append(line)
        else:
            outside.append(line)
    if block is not None:
        raise ValueError(f"unterminated subcircuit: {name}")
    if outside:
        segments.append(("text", "", outside))
    top_key = top.lower()
    if top_key not in definitions:
        raise ValueError(f"top subcircuit missing: {top}")

    dependencies: dict[str, set[str]] = {}
    for parent, lines in definitions.items():
        logical: list[str] = [lines[0].strip()]
        for line in lines[1:-1]:
            stripped = line.strip()
            if not stripped or stripped.startswith("*"):
                continue
            if stripped.startswith("+"):
                if not logical:
                    raise ValueError(f"orphan CDL continuation in {parent}")
                logical[-1] += " " + stripped[1:].strip()
            else:
                logical.append(stripped)
        dependencies[parent] = {
            statement.split()[-1].lower()
            for statement in logical
            if re.match(r"^[xX][^\s]+\s", statement)
        }
    needed = {top_key}
    frontier = [top_key]
    while frontier:
        parent = frontier.pop()
        for child in dependencies[parent]:
            if child not in definitions:
                raise ValueError(f"undefined subcircuit {child} in {parent}")
            if child not in needed:
                needed.add(child)
                frontier.append(child)
    filtered = "".join(
        "".join(lines)
        for kind, subckt, lines in segments
        if kind == "text" or subckt in needed
    ).encode("utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(filtered)
    manifest: dict[str, object] = {
        "schema_version": 1,
        "method": "transitive-subcircuit-prune-v1",
        "top": top,
        "source": source.name,
        "source_sha256": _digest(original),
        "filtered": target.name,
        "filtered_sha256": _digest(filtered),
        "original_subcircuits": len(definitions),
        "retained_subcircuits": len(needed),
        "retained_names": sorted(needed),
    }
    target.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("top")
    args = parser.parse_args()
    print(json.dumps(filter_cdl(args.source, args.target, args.top), sort_keys=True))


if __name__ == "__main__":
    main()
