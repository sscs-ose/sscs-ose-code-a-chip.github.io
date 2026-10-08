"""A bounded, declared circuit family; no proprietary or altered device models."""

from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Design:
    name: str
    input_device: str = "nfet_01v8"
    input_w: float = 2.0
    tail_w: float = 5.0
    latch_n_w: float = 1.0
    latch_p_w: float = 2.0
    reset_w: float = 1.0
    trim_l: float = 1.0
    trim_bits: int = 3

    @property
    def max_code(self) -> int:
        return (1 << self.trim_bits) - 1

    @property
    def transistor_count(self) -> int:
        return 11 + 4 * self.trim_bits

    @property
    def gate_area_um2(self) -> float:
        core = 0.15 * (
            2 * self.input_w + self.tail_w + 2 * self.latch_n_w
            + 2 * self.latch_p_w + 4 * self.reset_w
        )
        return core + 2 * self.max_code * (0.42 * self.trim_l + 0.15)

    def report(self) -> dict:
        return {
            **asdict(self), "max_code": self.max_code,
            "transistor_count": self.transistor_count,
            "gate_area_proxy_um2": self.gate_area_um2,
        }


DESIGNS = {design.name: design for design in (
    Design("baseline"),
    Design("svt_fast_4b", input_w=4, tail_w=10, latch_n_w=2, latch_p_w=3,
           reset_w=1.5, trim_bits=4),
    Design("lvt_base_3b", input_device="nfet_01v8_lvt"),
    Design("lvt_fine_3b", input_device="nfet_01v8_lvt", trim_l=2),
    Design("lvt_balanced_4b", input_device="nfet_01v8_lvt", input_w=3, tail_w=7,
           trim_bits=4),
    Design("lvt_fine_4b", input_device="nfet_01v8_lvt", input_w=3, tail_w=7,
           trim_l=2, trim_bits=4),
    Design("lvt_fast_4b", input_device="nfet_01v8_lvt", input_w=4, tail_w=10,
           latch_n_w=2, latch_p_w=3, reset_w=1.5, trim_bits=4),
    Design("lvt_fast_fine_4b", input_device="nfet_01v8_lvt", input_w=4, tail_w=10,
           latch_n_w=2, latch_p_w=3, reset_w=1.5, trim_l=2, trim_bits=4),
    Design("lvt_wide_5b", input_device="nfet_01v8_lvt", input_w=7, tail_w=12,
           latch_n_w=2, latch_p_w=3, reset_w=1.5, trim_bits=5),
)}


def get_design(name: str) -> Design:
    if name not in DESIGNS:
        raise ValueError(f"Unknown circuit design: {name}")
    return DESIGNS[name]


def controls(design: Design) -> list[str]:
    return [f"t{side}{bit}" for side in ("p", "n") for bit in range(design.trim_bits)]


def circuit_text(design: Design) -> str:
    if design.name == "baseline":
        return (ROOT / "circuits" / "strongarm.spice").read_text(encoding="utf-8")
    lines = [
        f"* Comparator Atlas declared design: {design.name}",
        "* Generated physical transistor netlist. Gate-area proxy is not layout area.",
        ".subckt atlas vinp vinn clk vdd vss qp qn " + " ".join(controls(design)),
        "+ params: pair_skew=0",
    ]

    def mos(name: str, nodes: str, device: str, width: str | float, length: float = 0.15) -> None:
        width_text = width if isinstance(width, str) else f"{width:.12g}"
        lines.extend((
            f"{name} {nodes} sky130_fd_pr__{device}",
            f"+ w={{{width_text}}} l={length:.12g}",
            f"+ ad={{0.29*({width_text})}} as={{0.29*({width_text})}}",
            f"+ pd={{2*(0.29+({width_text}))}} ps={{2*(0.29+({width_text}))}}",
        ))

    mos("Xinp", "xp vinp tail vss", design.input_device, f"{design.input_w:g}*(1+pair_skew)")
    mos("Xinn", "xn vinn tail vss", design.input_device, f"{design.input_w:g}*(1-pair_skew)")
    mos("Xtail", "tail clk vss vss", "nfet_01v8", design.tail_w)
    mos("Xln", "qn qp xp vss", "nfet_01v8", design.latch_n_w)
    mos("Xlp", "qp qn xn vss", "nfet_01v8", design.latch_n_w)
    mos("Xpn", "qn qp vdd vdd", "pfet_01v8", design.latch_p_w)
    mos("Xpp", "qp qn vdd vdd", "pfet_01v8", design.latch_p_w)
    for node in ("xp", "xn", "qp", "qn"):
        mos(f"Xr{node}", f"{node} clk vdd vdd", "pfet_01v8", design.reset_w)
    for side, input_node, drain in (("p", "vinp", "xp"), ("n", "vinn", "xn")):
        for bit in range(design.trim_bits):
            weight = 1 << bit
            mos(f"Xt{side}{bit}", f"{drain} {input_node} s{side}{bit} vss",
                design.input_device, 0.42 * weight, design.trim_l)
            mos(f"Xs{side}{bit}", f"s{side}{bit} t{side}{bit} tail vss",
                "nfet_01v8", float(weight))
    lines.append(".ends atlas")
    return "\n".join(lines) + "\n"
