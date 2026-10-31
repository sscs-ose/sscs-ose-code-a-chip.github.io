"""Named designs of the restart. Each entry is a complete, reproducible design point."""
from shbench import Design, Switch

DESIGNS: dict[str, Design] = {}

def add(d: Design) -> Design:
    DESIGNS[d.name] = d
    return d

# Candidate F2 as released: two-stage driver, TG nfet 3x5 um / pfet 6x5 um, Cs 1 pF
F2 = add(Design("f2"))
# F2 driver with the half-width gate of the F2 width ladder
add(Design("f2_half", switch=Switch(wn=2.5, wp=2.5)))

# R3 sampling-network study: bootstrapped NMOS switch (design-study record)
AB_IC = (("xsw.t", "{v0}+{vdd}"), ("xsw.g", "{v0}+{vdd}"), ("xsw.bt", "{v0}"), ("xsw.x", "{v0}"),
         ("xsw.z1", "{vdd}"), ("xsw.z2", "2*{vdd}"))


def boot(ws: float = 2.5, ms: int = 2, cb: str = "0.4p") -> Switch:
    return Switch(kind="sub", subckt_file="sw_bootab.spice", subckt_name="sw_bootab",
                  subckt_params=(("WS", ws), ("MS", ms), ("CB", cb), ("CZ", "50f")), ic=AB_IC)


FC17 = dict(driver_file="driver_drv_fc17.spice", driver_subckt="drv_fc17")
add(Design("f2_boot5", switch=boot()))
add(Design("f2_boot2", switch=boot(ws=2, ms=1, cb="0.2p")))
add(Design("fc17_boot5", switch=boot(), **FC17))
add(Design("fc17_boot2", switch=boot(ws=2, ms=1, cb="0.2p"), **FC17))

# R3 driver iteration 2 (design-study record): native-threshold folded-cascode driver
NF16A = dict(driver_file="driver_drv_nf16a.spice", driver_subckt="drv_nf16a")
add(Design("nf16a_boot5", switch=boot(), **NF16A))
add(Design("nf16a_boot2", switch=boot(ws=2, ms=1, cb="0.2p"), **NF16A))

# R3 final bounded refinement of the A family (design-study record): drv_Q1
Q1 = dict(driver_file="driver_drv_Q1.spice", driver_subckt="drv_Q1")
add(Design("q1_boot5", switch=boot(), **Q1))
add(Design("q1_boot2", switch=boot(ws=2, ms=1, cb="0.2p"), **Q1))

# switch isolation: behavioural reference driver (sw_drv_ideal.spice) with the selected switch
add(Design("ideal_boot2", driver_file="sw_drv_ideal.spice", driver_subckt="drv_ideal",
           switch=boot(ws=2, ms=1, cb="0.2p")))
