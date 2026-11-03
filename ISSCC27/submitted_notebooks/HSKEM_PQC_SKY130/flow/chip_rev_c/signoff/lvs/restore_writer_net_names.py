#!/usr/bin/env python3
"""Restore KLayout SpiceWriter numeric node IDs from its own `* net` metadata."""

import argparse
from pathlib import Path


def spice_name(name):
    return "\\" + name if name.startswith("$") else name


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    mapping = None
    header = None
    metadata = None
    header_emitted = False
    circuit_count = 0
    mapped_tokens = 0

    def emit_header(out):
        nonlocal header_emitted, mapped_tokens
        if header is None or header_emitted:
            return
        words = header.split()
        restored = []
        for token in words:
            if token in mapping:
                restored.append(spice_name(mapping[token]))
                mapped_tokens += 1
            else:
                restored.append(token)
        out.write(" ".join(restored) + "\n")
        out.writelines(metadata or [])
        header_emitted = True

    with args.input.open("r", encoding="utf-8", errors="strict") as src, \
            args.output.open("w", encoding="utf-8", newline="\n") as out:
        pending = None
        while True:
            line = pending if pending is not None else src.readline()
            pending = None
            if not line:
                break
            if line.lstrip().upper().startswith(".SUBCKT "):
                parts = [line.strip()]
                while True:
                    following = src.readline()
                    if following and following.lstrip().startswith("+"):
                        parts.append(following.lstrip()[1:].strip())
                    else:
                        pending = following
                        break
                mapping = {}
                header = " ".join(parts)
                metadata = []
                header_emitted = False
                circuit_count += 1
                continue

            if mapping is not None and line.startswith("* net "):
                words = line.split(maxsplit=3)
                if len(words) == 4:
                    mapping[words[2]] = words[3].strip()
                metadata.append(line)
                continue

            if mapping is not None:
                emit_header(out)
                if line.lstrip().upper().startswith(".ENDS"):
                    out.write(line)
                    mapping = header = metadata = None
                    header_emitted = False
                    continue
                if line.lstrip().startswith("*") or not line.strip():
                    out.write(line)
                    continue
                parts = [line.strip()]
                while True:
                    following = src.readline()
                    if following and following.lstrip().startswith("+"):
                        parts.append(following.lstrip()[1:].strip())
                    else:
                        pending = following
                        break
                words = " ".join(parts).split()
                restored = []
                for token in words:
                    if token in mapping:
                        restored.append(spice_name(mapping[token]))
                        mapped_tokens += 1
                    else:
                        restored.append(token)
                out.write(" ".join(restored) + "\n")
                continue

            out.write(line)

        if mapping is not None:
            emit_header(out)

    if circuit_count < 100 or mapped_tokens < 1_000_000:
        raise RuntimeError(f"writer restore cardinality too small: circuits={circuit_count} tokens={mapped_tokens}")
    print("A3_RUN15_WRITER_NET_NAME_RESTORE=PASS")
    print(f"circuits={circuit_count}")
    print(f"mapped_node_tokens={mapped_tokens}")


if __name__ == "__main__":
    main()
