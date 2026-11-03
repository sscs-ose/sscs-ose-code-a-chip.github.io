#!/usr/bin/env python3
"""Check the public LC-VCO supply-pushing deck pair before simulation."""

from __future__ import annotations

from pathlib import Path


BENCHES = Path(__file__).resolve().parent
COMMON_LINES = (
    '.lib "/opt/sky130/continuous/sky130.lib.spice" tt',
    '.include "/app/circuit.spi"',
    ".temp 27",
    "IREF iref vss 50u",
    "XVCO vss iref vctrl vdd outp outn lc_vco_2ghz",
    "CLOADP outp vss 10f",
    "CLOADN outn vss 10f",
    ".ic v(outp)=0.61 v(outn)=0.59",
    ".tran 5p 160n uic",
    ".end",
)


def check_deck(name: str, supply: str) -> None:
    text = (BENCHES / name).read_text()
    for required in COMMON_LINES + (f"VDD vdd vss {supply}",):
        if required not in text:
            raise SystemExit(f"{name}: missing {required!r}")


def main() -> None:
    check_deck("tb_supply_pushing_tt_1p62v_27c.spi", "1.62")
    check_deck("tb_supply_pushing_tt_1p98v_27c.spi", "1.98")
    print("public supply-pushing benches: 2/2 structurally valid")


if __name__ == "__main__":
    main()
