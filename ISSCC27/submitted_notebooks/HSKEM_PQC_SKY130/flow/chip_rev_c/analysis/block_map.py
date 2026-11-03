"""Which block of the design owns each part of the die: reads the signed-off DEF (read only) and writes, on a square
grid, the block that holds the most named cells in each tile, then the block of each SRAM macro. Buffers and clock cells added by the flow carry no
block name and are left out. Only tile positions and block names are written, never instance names.

usage: block_map.py <6_final.def> <out.csv.gz>
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import collections
import gzip
import re
import sys

TILE_UM = 20
COMP = re.compile(r"^\s*-\s+(\S+)\s+(\S+)\s.*(?:PLACED|FIXED)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)")
BLOCKS = ("g_qualification_puf_vault", "u_hsm_shell", "u_shared_mlkem_sponge", "u_mlkem512_decaps_partial",
          "u_security_hmac", "u_mlkem512_kpke_partial", "u_c2_shake_drbg", "u_bridge", "u_mlkem512_encaps_partial",
          "u_spi", "u_shared_ntt", "u_puf", "u_c3_pk_pair_sram")


def block_of(name: str) -> str | None:
    for b in BLOCKS:
        if b in name:
            return b
    return None


def main() -> None:
    tiles: dict = collections.defaultdict(collections.Counter)
    in_comp, seen, macros = False, collections.Counter(), []
    with open(sys.argv[1], errors="replace") as f:
        for ln in f:
            if ln.startswith("COMPONENTS"):
                in_comp = True
            elif ln.startswith("END COMPONENTS"):
                break
            elif in_comp and (m := COMP.match(ln)):
                b = block_of(m[1].replace("\\", ""))
                if "sky130_sram" in m[2]:
                    macros.append((int(m[3]) / 1000, int(m[4]) / 1000, b))
                if b:
                    seen[b] += 1
                    tiles[(int(m[3]) // (TILE_UM * 1000), int(m[4]) // (TILE_UM * 1000))][b] += 1
    with gzip.GzipFile(sys.argv[2], "wb", mtime=0) as g:
        g.write(f"tile_um,{TILE_UM}\nix,iy,block\n".encode())
        for (ix, iy), c in sorted(tiles.items()):
            g.write(f"{ix},{iy},{c.most_common(1)[0][0]}\n".encode())
        for x, y, b in macros:
            g.write(f"macro:{x},{y},{b}\n".encode())
    print(len(tiles), "tiles;", dict(seen))


if __name__ == "__main__":
    main()
