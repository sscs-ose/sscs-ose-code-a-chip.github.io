"""report.py - tables and netlists generated from a design dict, so nothing about a design is typed by hand.
SPDX-License-Identifier: Apache-2.0"""
from __future__ import annotations
import vga_flow as vf


def _g(p, grp):
    W, nf = p[f"W_{grp}"], vf.nf_of(p, grp)
    return W, nf, W / nf


def device_rows(p):
    """[device(s), role, fingers x finger width = total W, L, copies] - the layout input."""
    rows = []
    for devs, role, grp in (("M2, M3", "input pair", "in"), ("M6–M9", "steering", "st"), ("M1, M4", "PMOS mirror", "mir")):
        W, nf, wf = _g(p, grp)
        rows.append([devs, role, f"{nf} × {wf:g} = {W:g}", f"{p[f'L_{grp}']:g}", "1"])
    mode = vf.bias_mode(p)
    if mode == "unit":
        Wu, Lu, nu_ = p.get("W_u", vf.W_F), p["L_u"], vf.nf_of(p, "u")
        u_ = f"{nu_} × {Wu/nu_:g} = {Wu:g}"
        rows.append(["M5", "tail (unit copies)", u_, f"{Lu:g}", str(p["m_tail"])])
        if p.get("m_sink"):
            rows.append(["M10, M11", "keep-alive sinks (unit copies)", u_, f"{Lu:g}", str(p["m_sink"])])
        rows.append(["M12", "reference diode (unit)", u_, f"{Lu:g}", "1"])
    else:
        W, nf, wf = _g(p, "tail")
        rows.append(["M5", "tail", f"{nf} × {wf:g} = {W:g}", f"{p['L_tail']:g}", "1"])
        if mode == "legacy":
            rows.append(["M10, M11", "keep-alive sinks", f"1 × {p['W_k']:g}", f"{p['L_k']:g}", "1"])
            rows.append(["M12", "reference diode", f"1 × {p['W_ref']:g}", f"{p['L_ref']:g}", "1"])
    return rows


def bias_rows(p):
    rows = [["V_DD", f"{p['vdd']:g} V"], ["input common mode", f"{p['vin_cm']:.2f} V"],
            ["steering common mode", f"{p['vctrl_cm']:.2f} V"]]
    if vf.bias_mode(p) == "voltage":
        rows.append(["tail gate V_bias", f"{p['vbias']:.2f} V"])
    else:
        rows.append(["reference current I_ref (into the iref pin)", f"{p['iref']*1e6:.3g} µA"])
    return rows


def subckt(p, name="vga_core"):
    """LVS netlist of the core: pins vdd gnd vin_p vin_n iref|vbias vctrl_p vctrl_n v_out. Every transistor carries
    the same W/nf/m and junction geometry as the SPICE netlist the flow verified, so this file simulates exactly
    like the flow's own netlist (vga_flow.subckt_instance) and is the LVS reference for the layout."""
    mode = vf.bias_mode(p)
    bias_pin = "iref" if mode != "voltage" else "vbias"
    n, pf = "sky130_fd_pr__nfet_01v8", "sky130_fd_pr__pfet_01v8"
    def fet(nm, d, g, s, b, model, W, L, nf=1, m=1):
        return (f"X{nm} {d} {g} {s} {b} {model} L={L:g} W={W:g} nf={int(nf)} {vf._geom(W, nf)}"
                + (f" m={int(m)}" if int(m) != 1 else ""))
    L = [f".subckt {name} vdd gnd vin_p vin_n {bias_pin} vctrl_p vctrl_n v_out"]
    W, nf, _ = _g(p, "mir")
    L += [fet("M1", "net4", "net4", "vdd", "vdd", pf, W, p["L_mir"], nf), fet("M4", "v_out", "net4", "vdd", "vdd", pf, W, p["L_mir"], nf)]
    W, nf, _ = _g(p, "in")
    L += [fet("M2", "net2", "vin_p", "net5", "gnd", n, W, p["L_in"], nf), fet("M3", "net3", "vin_n", "net5", "gnd", n, W, p["L_in"], nf)]
    W, nf, _ = _g(p, "st")
    L += [fet("M6", "net4", "vctrl_p", "net2", "gnd", n, W, p["L_st"], nf), fet("M7", "vdd", "vctrl_n", "net2", "gnd", n, W, p["L_st"], nf),
          fet("M8", "vdd", "vctrl_n", "net3", "gnd", n, W, p["L_st"], nf), fet("M9", "v_out", "vctrl_p", "net3", "gnd", n, W, p["L_st"], nf)]
    if mode == "unit":
        Wu, Lu, nu_ = p.get("W_u", vf.W_F), p["L_u"], vf.nf_of(p, "u")
        L += [fet("M5", "net5", bias_pin, "gnd", "gnd", n, Wu, Lu, nu_, p["m_tail"])]
        if p.get("m_sink"):
            L += [fet("M10", "net4", bias_pin, "gnd", "gnd", n, Wu, Lu, nu_, p["m_sink"]),
                  fet("M11", "v_out", bias_pin, "gnd", "gnd", n, Wu, Lu, nu_, p["m_sink"])]
        L += [fet("M12", bias_pin, bias_pin, "gnd", "gnd", n, Wu, Lu, nu_)]
    else:
        W, nf, _ = _g(p, "tail")
        L += [fet("M5", "net5", bias_pin, "gnd", "gnd", n, W, p["L_tail"], nf)]
    L += [".ends"]
    return "\n".join(L) + "\n"


def sizes(p):
    """The layout generator's input (layout/vga_core_12t_sizes.json) for design p: per device type, finger count,
    length, copies and total width (every finger W_F wide), the bias, the pins and the internal nets to label."""
    nu_ = vf.nf_of(p, "u")
    devs = (("M1", "pfet_01v8", p["nf_mir"], p["L_mir"], 1), ("M4", "pfet_01v8", p["nf_mir"], p["L_mir"], 1),
            ("M2", "nfet_01v8", p["nf_in"], p["L_in"], 1), ("M3", "nfet_01v8", p["nf_in"], p["L_in"], 1),
            ("M6", "nfet_01v8", p["nf_st"], p["L_st"], 1), ("M7", "nfet_01v8", p["nf_st"], p["L_st"], 1),
            ("M8", "nfet_01v8", p["nf_st"], p["L_st"], 1), ("M9", "nfet_01v8", p["nf_st"], p["L_st"], 1),
            ("M5", "nfet_01v8", nu_, p["L_u"], p["m_tail"]), ("M10", "nfet_01v8", nu_, p["L_u"], p["m_sink"]),
            ("M11", "nfet_01v8", nu_, p["L_u"], p["m_sink"]), ("M12", "nfet_01v8", nu_, p["L_u"], 1))
    return dict(pins=["vdd", "gnd", "vin_p", "vin_n", "iref", "vctrl_p", "vctrl_n", "v_out"], finger_width_um=vf.W_F,
                devices={d: dict(type=t, nf=int(nf), L_um=float(L), m=int(m), W_total_um=float(nf * vf.W_F))
                         for d, t, nf, L, m in devs},
                bias=dict(iref_A=p["iref"], vin_cm_V=p["vin_cm"], vctrl_cm_V=p["vctrl_cm"], vdd_V=p["vdd"]),
                internal_net_labels=["net2", "net3", "net4", "net5"])
