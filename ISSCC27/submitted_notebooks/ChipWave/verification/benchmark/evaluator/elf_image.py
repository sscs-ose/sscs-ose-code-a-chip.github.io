"""Turn a bounded RV32 little-endian ELF into a byte image for the CPU harness."""

from __future__ import annotations

import struct
from pathlib import Path

MEMORY_BASE = 0x8000_0000
MEMORY_SIZE = 256 * 1024
TOHOST = 0x8003_F000
_ELF_HEADER = struct.Struct("<16sHHIIIIIHHHHHH")
_PROGRAM_HEADER = struct.Struct("<IIIIIIII")


def load_elf(path: Path) -> bytearray:
    elf = path.read_bytes()
    if len(elf) < _ELF_HEADER.size:
        raise ValueError("ELF header is truncated")
    (ident, elf_type, machine, version, entry, phoff, _shoff, _flags,
     ehsize, phentsize, phnum, _shentsize, _shnum, _shstrndx) = _ELF_HEADER.unpack_from(elf)
    if ident[:4] != b"\x7fELF" or ident[4:7] != b"\x01\x01\x01":
        raise ValueError("expected ELF32 little-endian version 1")
    if elf_type != 2 or machine != 243 or version != 1:
        raise ValueError("expected RV32 executable ELF")
    if ehsize != _ELF_HEADER.size or phentsize != _PROGRAM_HEADER.size or phnum == 0:
        raise ValueError("invalid or empty ELF program header table")
    if entry != MEMORY_BASE:
        raise ValueError(f"ELF entry must be 0x{MEMORY_BASE:08x}")
    if phoff + phnum * phentsize > len(elf):
        raise ValueError("ELF program header table is truncated")

    image = bytearray(MEMORY_SIZE)
    occupied = bytearray(MEMORY_SIZE)
    loaded = 0
    for index in range(phnum):
        (kind, offset, vaddr, paddr, filesz, memsz, _flags, _align) = (
            _PROGRAM_HEADER.unpack_from(elf, phoff + index * phentsize))
        if kind != 1:
            continue
        if paddr not in (0, vaddr):
            raise ValueError(f"PT_LOAD {index} physical/virtual address mismatch")
        if filesz > memsz or offset + filesz > len(elf):
            raise ValueError(f"PT_LOAD {index} has invalid file bounds")
        if vaddr < MEMORY_BASE or memsz > MEMORY_SIZE or vaddr - MEMORY_BASE > MEMORY_SIZE - memsz:
            raise ValueError(f"PT_LOAD {index} is outside the 256 KiB image")
        if vaddr < TOHOST + 4 and vaddr + memsz > TOHOST:
            raise ValueError(f"PT_LOAD {index} overlaps tohost MMIO")
        start = vaddr - MEMORY_BASE
        stop = start + memsz
        if any(occupied[start:stop]):
            raise ValueError(f"PT_LOAD {index} overlaps another segment")
        image[start:start + filesz] = elf[offset:offset + filesz]
        occupied[start:stop] = b"\x01" * memsz
        loaded += 1
    if loaded == 0 or not occupied[0]:
        raise ValueError("ELF has no PT_LOAD at the reset PC")
    return image


def write_hex_image(image: bytearray, path: Path) -> None:
    if len(image) != MEMORY_SIZE:
        raise ValueError("invalid memory image length")
    path.write_text("".join(f"{value:02x}\n" for value in image), encoding="ascii")
