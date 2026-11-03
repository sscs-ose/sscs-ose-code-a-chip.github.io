#!/usr/bin/env python3
"""Preflight the public TT load-transient deck without requiring ngspice."""

from pathlib import Path


def require(text: str, fragment: str, path: Path) -> None:
    if fragment not in text:
        raise SystemExit(f"{path.name}: missing required deck fragment: {fragment}")


def main() -> int:
    bench = Path(__file__).with_name("tb_load_tran_tt.spi")
    circuit = bench.parent.parent / "circuit.spi"
    deck = bench.read_text(encoding="utf-8")
    design = circuit.read_text(encoding="utf-8")

    for fragment in (
        '.lib "/opt/sky130/continuous/sky130.lib.spice" tt',
        ".include \"/app/circuit.spi\"",
        "ILOAD vout vss PULSE(1m 25m 20u 200n 200n 20u 100u)",
        "XLDO vin vout vss vref ibias fb_div gate_drive gate ldo_ota5",
        "RFBTOP vout fb_div 300k",
        "RFBBOT fb_div vss 600k",
        "VLOOP gate_drive gate 0",
        "RESR vout vcap 50m",
        "COUT vcap vss 1u",
        ".tran 25n 70u",
    ):
        require(deck, fragment, bench)
    require(design, ".subckt ldo_ota5 vin vout vss vref ibias fb gate_drive gate", circuit)
    require(design, ".ends ldo_ota5", circuit)
    print("PASS public TT load-transient deck preflight")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
