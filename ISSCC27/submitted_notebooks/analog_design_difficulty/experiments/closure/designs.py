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
# selected and frozen 2026-10-31, superseded 2026-11-01: its switch terminal voltages leave the documented
# compact-model validity domain (completed A3 check; docs/restart/SWITCH_REDESIGN_DECISION.md)
add(Design("q1_boot2", switch=boot(ws=2, ms=1, cb="0.2p"), **Q1))

# switch isolation: behavioural reference driver (sw_drv_ideal.spice) with the selected switch
add(Design("ideal_boot2", driver_file="sw_drv_ideal.spice", driver_subckt="drv_ideal",
           switch=boot(ws=2, ms=1, cb="0.2p")))

# Bootstrap compact-model-domain investigation (docs/restart/BOOTSTRAP_MODEL_DOMAIN_HANDOFF.md): helper-circuit
# variants of the selected switch (same main switch W 2 um, CB 0.2 pF, same driver drv_Q1).
def bootv(subckt: str, ws: float = 2, ms: int = 1, cb: str = "0.2p", extra: tuple = ()) -> Switch:
    return Switch(kind="sub", subckt_file=f"{subckt}.spice", subckt_name=subckt,
                  subckt_params=(("WS", ws), ("MS", ms), ("CB", cb), ("CZ", "50f")) + extra, ic=AB_IC)


add(Design("q1_bootac2", switch=bootv("sw_bootac"), **Q1))
# investigation only: weaker bottom-plate device; reduced boost ratio (CB 65 fF) to test the main-switch turn-on mechanism
add(Design("q1_bootac2_w042", switch=bootv("sw_bootac", extra=(("WBC", 0.42),)), **Q1))
add(Design("q1_boot2_cb65", switch=bootv("sw_bootab", cb="0.065p"), **Q1))

# Switch redesign study, Workstream N (docs/restart/SWITCH_REDESIGN_DECISION.md): native thick-oxide NMOS switch
# without bootstrap, W = 4 um fingers x m, same driver drv_Q1 and Cs 1 pF.
def nvt(ms: int, ws: float = 4) -> Switch:
    return Switch(kind="sub", subckt_file="sw_nvt.spice", subckt_name="sw_nvt",
                  subckt_params=(("WS", ws), ("MS", ms)))


for _m in (1, 2, 4, 8):
    add(Design(f"q1_nvt{_m}", switch=nvt(_m), **Q1))

# the selected design: drv_Q1 + one native thick-oxide NMOS switch (W 4 um, L 0.5 um), Cs 1 pF
SELECTED = "q1_nvt1"
