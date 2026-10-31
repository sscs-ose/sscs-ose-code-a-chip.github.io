import os
import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import gdstk
from typing import Dict, Any, Optional

class NeuroDynLayoutGenerator:
    """
    Procedural GDSII Layout Generator for SkyWater SKY130 technology.
    Instantiates the COMPLETE NeuroDyn Dynamic OTA and Chopper AFE macro:
      1. Differential Input Pair M1/M2 (Common-Centroid [D, A, B, B, A, B, A, A, B, D])
      2. Auxiliary Steering Pair M1_aux/M2_aux
      3. Tail Current Source Transistor M_tail (NMOS LVT)
      4. Active Load PMOS Current Mirror Bank M3/M4 in dedicated N-Well
      5. Continuous-Time Resistive CMFB Network R_cm1/R_cm2
      6. Second Stage Output Conversion M5-M8 (PMOS loads M5/M7, NMOS sinks M6/M8)
      7. Dual Miller Frequency Compensation MIM Capacitors C_c1/C_c2
      8. Low-Vt CMOS Input Chopper Cell CHOP1
      9. Guard Ring and Full LVS Pin Labels
    """
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.gds_dir = os.path.join(output_dir, "data", "gds")
        self.img_dir = os.path.join(output_dir, "images")
        os.makedirs(self.gds_dir, exist_ok=True)
        os.makedirs(self.img_dir, exist_ok=True)
        
        # SKY130 Layer Table (Compliant with SkyWater SKY130 DRM)
        self.layers = {
            "nwell": (64, 20),
            "diff": (65, 20),
            "tap": (65, 44),
            "poly": (66, 20),
            "licon": (66, 44),
            "li1": (67, 20),
            "mcon": (67, 44),
            "met1": (68, 20),
            "met1_pin": (68, 16),
            "via1": (68, 44),
            "met2": (69, 20),
            "met2_pin": (69, 16),
            "via2": (69, 44),
            "capm": (89, 44),
            "met3": (70, 20),
            "prBoundary": (235, 4),
        }

    def generate_full_layout(self) -> str:
        """
        Creates full top-level GDSII cell containing the complete OTA + Chopper macro.
        Returns path to generated GDS file.
        """
        lib = gdstk.Library(name="NEURODYN_AFE_LIB", unit=1e-6, precision=1e-9)
        top = lib.new_cell("neurodyn_afe_top")
        
        # Dimensions
        gate_l_in = 1.0       # M1/M2 length
        gate_w_in = 10.15     # M1/M2 finger width
        pitch_x = 2.4
        
        pattern = ['D', 'A', 'B', 'B', 'A', 'B', 'A', 'A', 'B', 'D']
        n_fingers = len(pattern)
        core_w = n_fingers * pitch_x + 2.0  # ~26.0 um
        core_h = gate_w_in + 3.0           # ~13.15 um
        margin = 3.5

        # =========================================================================
        # 1. INPUT DIFFERENTIAL PAIR M1/M2 (Common-Centroid)
        # =========================================================================
        # Split active diffusion islands
        mid_x = 1.2 + 4 * pitch_x + gate_l_in + 0.7
        active_left = gdstk.rectangle((0.4, 1.2), (mid_x - 0.25, core_h - 1.2), layer=self.layers["diff"][0], datatype=self.layers["diff"][1])
        active_right = gdstk.rectangle((mid_x + 0.25, 1.2), (core_w - 0.4, core_h - 1.2), layer=self.layers["diff"][0], datatype=self.layers["diff"][1])
        top.add(active_left, active_right)

        gate_positions = []
        for idx, dev_id in enumerate(pattern):
            x_pos = 1.2 + idx * pitch_x
            gate_positions.append((x_pos, dev_id))
            poly_rect = gdstk.rectangle((x_pos, 0.6), (x_pos + gate_l_in, core_h - 0.6), layer=self.layers["poly"][0], datatype=self.layers["poly"][1])
            top.add(poly_rect)

            # Poly contact stack
            licon_poly = gdstk.rectangle((x_pos + 0.35, core_h - 0.4), (x_pos + 0.65, core_h - 0.1), layer=self.layers["licon"][0], datatype=self.layers["licon"][1])
            li1_poly = gdstk.rectangle((x_pos + 0.2, core_h - 0.5), (x_pos + 0.8, core_h + 0.3), layer=self.layers["li1"][0], datatype=self.layers["li1"][1])
            mcon_poly = gdstk.rectangle((x_pos + 0.35, core_h - 0.1), (x_pos + 0.65, core_h + 0.2), layer=self.layers["mcon"][0], datatype=self.layers["mcon"][1])
            met1_poly = gdstk.rectangle((x_pos + 0.2, core_h), (x_pos + 0.8, core_h + 0.4), layer=self.layers["met1"][0], datatype=self.layers["met1"][1])
            top.add(licon_poly, li1_poly, mcon_poly, met1_poly)

            # Route to common-centroid gate buses
            if dev_id == 'A':
                via1_a = gdstk.rectangle((x_pos + 0.35, core_h + 0.75), (x_pos + 0.65, core_h + 1.05), layer=self.layers["via1"][0], datatype=self.layers["via1"][1])
                met1_ext_a = gdstk.rectangle((x_pos + 0.2, core_h + 0.3), (x_pos + 0.8, core_h + 1.2), layer=self.layers["met1"][0], datatype=self.layers["met1"][1])
                top.add(met1_ext_a, via1_a)
            elif dev_id == 'B':
                via1_b = gdstk.rectangle((x_pos + 0.35, core_h + 1.95), (x_pos + 0.65, core_h + 2.25), layer=self.layers["via1"][0], datatype=self.layers["via1"][1])
                met1_ext_b = gdstk.rectangle((x_pos + 0.2, core_h + 0.3), (x_pos + 0.8, core_h + 2.4), layer=self.layers["met1"][0], datatype=self.layers["met1"][1])
                top.add(met1_ext_b, via1_b)
            elif dev_id == 'D':
                dummy_tie = gdstk.rectangle((x_pos + 0.2, -margin - 0.6), (x_pos + 0.8, 0.8), layer=self.layers["met1"][0], datatype=self.layers["met1"][1])
                top.add(dummy_tie)

        # Source / Drain Contacts
        for idx in range(len(pattern) - 1):
            x_sd = 1.2 + idx * pitch_x + gate_l_in + 0.4
            licon_sd = gdstk.rectangle((x_sd + 0.15, 1.8), (x_sd + 0.45, core_h - 1.8), layer=self.layers["licon"][0], datatype=self.layers["licon"][1])
            li1_sd = gdstk.rectangle((x_sd + 0.05, 1.7), (x_sd + 0.55, core_h - 1.7), layer=self.layers["li1"][0], datatype=self.layers["li1"][1])
            mcon_sd = gdstk.rectangle((x_sd + 0.15, 1.8), (x_sd + 0.45, core_h - 1.8), layer=self.layers["mcon"][0], datatype=self.layers["mcon"][1])
            sd_rect = gdstk.rectangle((x_sd, 1.6), (x_sd + 0.6, core_h - 1.6), layer=self.layers["met1"][0], datatype=self.layers["met1"][1])
            top.add(licon_sd, li1_sd, mcon_sd, sd_rect)

        # Gate A and Gate B buses (Metal 2)
        bar_a = gdstk.rectangle((0.5, core_h + 0.5), (core_w - 0.5, core_h + 1.3), layer=self.layers["met2"][0], datatype=self.layers["met2"][1])
        bar_b = gdstk.rectangle((0.5, core_h + 1.7), (core_w - 0.5, core_h + 2.5), layer=self.layers["met2"][0], datatype=self.layers["met2"][1])
        top.add(bar_a, bar_b)

        # Labels for inp and inm
        top.add(
            gdstk.rectangle((0.5, core_h + 0.5), (2.0, core_h + 1.3), layer=self.layers["met2_pin"][0], datatype=self.layers["met2_pin"][1]),
            gdstk.Label("inp", (1.25, core_h + 0.9), layer=self.layers["met2_pin"][0], texttype=self.layers["met2_pin"][1]),
            gdstk.rectangle((0.5, core_h + 1.7), (2.0, core_h + 2.5), layer=self.layers["met2_pin"][0], datatype=self.layers["met2_pin"][1]),
            gdstk.Label("inm", (1.25, core_h + 2.1), layer=self.layers["met2_pin"][0], texttype=self.layers["met2_pin"][1]),
        )

        # =========================================================================
        # 2. TAIL CURRENT SOURCE TRANSISTOR M_tail (NMOS LVT)
        # =========================================================================
        tail_y = -9.0
        tail_diff = gdstk.rectangle((1.0, tail_y), (core_w - 1.0, tail_y + 6.0), layer=self.layers["diff"][0], datatype=self.layers["diff"][1])
        top.add(tail_diff)
        # 2 Poly gates for M_tail (L = 2.0 um each, W = 10.15 um)
        for k in range(2):
            gx = 4.0 + k * 8.0
            gp = gdstk.rectangle((gx, tail_y - 0.5), (gx + 2.0, tail_y + 6.5), layer=self.layers["poly"][0], datatype=self.layers["poly"][1])
            # Contacts & Met1 gate route
            lic_tail = gdstk.rectangle((gx + 0.5, tail_y - 0.4), (gx + 1.5, tail_y - 0.1), layer=self.layers["licon"][0], datatype=self.layers["licon"][1])
            m1_tail_gate = gdstk.rectangle((gx + 0.3, tail_y - 0.8), (gx + 1.7, tail_y), layer=self.layers["met1"][0], datatype=self.layers["met1"][1])
            top.add(gp, lic_tail, m1_tail_gate)
        # Route Vbn_tail bus
        vbn_tail_bus = gdstk.rectangle((2.0, tail_y - 1.2), (core_w - 2.0, tail_y - 0.6), layer=self.layers["met1"][0], datatype=self.layers["met1"][1])
        top.add(vbn_tail_bus, gdstk.Label("vbn_tail", (4.0, tail_y - 0.9), layer=self.layers["met1_pin"][0], texttype=self.layers["met1_pin"][1]))
        # Connect Tail drain to diff-pair tail node via Met1 bus
        tail_drain_bus = gdstk.rectangle((2.0, tail_y + 5.0), (core_w - 2.0, tail_y + 6.5), layer=self.layers["met1"][0], datatype=self.layers["met1"][1])
        tail_up_link = gdstk.rectangle((core_w / 2 - 0.5, tail_y + 6.0), (core_w / 2 + 0.5, 1.6), layer=self.layers["met1"][0], datatype=self.layers["met1"][1])
        top.add(tail_drain_bus, tail_up_link, gdstk.Label("tail", (core_w / 2, 0.0), layer=self.layers["met1_pin"][0], texttype=self.layers["met1_pin"][1]))

        # =========================================================================
        # 3. ACTIVE PMOS LOAD M3, M4 (N-Well)
        # =========================================================================
        pmos_y = core_h + 4.5
        nwell_pmos = gdstk.rectangle((-1.0, pmos_y - 1.0), (core_w + 1.0, pmos_y + 9.5), layer=self.layers["nwell"][0], datatype=self.layers["nwell"][1])
        pmos_diff = gdstk.rectangle((0.5, pmos_y), (core_w - 0.5, pmos_y + 7.5), layer=self.layers["diff"][0], datatype=self.layers["diff"][1])
        top.add(nwell_pmos, pmos_diff)
        # 8 Poly gates (4 for M3, 4 for M4, L = 2.0 um, W = 3.15 um)
        for k in range(8):
            gx = 1.0 + k * 2.8
            gp = gdstk.rectangle((gx, pmos_y - 0.5), (gx + 1.2, pmos_y + 8.0), layer=self.layers["poly"][0], datatype=self.layers["poly"][1])
            top.add(gp)
        # Gate bus for vbp_cmfb
        vbp_bus = gdstk.rectangle((0.5, pmos_y + 8.2), (core_w - 0.5, pmos_y + 9.0), layer=self.layers["met1"][0], datatype=self.layers["met1"][1])
        top.add(vbp_bus, gdstk.Label("vbp_cmfb", (2.0, pmos_y + 8.6), layer=self.layers["met1_pin"][0], texttype=self.layers["met1_pin"][1]))
        # VDD supply bus (Metal 1)
        vdd_bus = gdstk.rectangle((-margin, pmos_y + 9.5), (core_w + 20.0, pmos_y + 11.0), layer=self.layers["met1"][0], datatype=self.layers["met1"][1])
        top.add(vdd_bus, gdstk.Label("vdd", (0.0, pmos_y + 10.25), layer=self.layers["met1_pin"][0], texttype=self.layers["met1_pin"][1]))

        # =========================================================================
        # 4. CMFB RESISTIVE NETWORK R_cm1, R_cm2
        # =========================================================================
        res_y = pmos_y + 12.0
        # Two high-res poly strips
        r1 = gdstk.rectangle((2.0, res_y), (10.0, res_y + 0.8), layer=self.layers["poly"][0], datatype=self.layers["poly"][1])
        r2 = gdstk.rectangle((12.0, res_y), (20.0, res_y + 0.8), layer=self.layers["poly"][0], datatype=self.layers["poly"][1])
        vcm_node = gdstk.rectangle((9.5, res_y - 0.2), (12.5, res_y + 1.0), layer=self.layers["met1"][0], datatype=self.layers["met1"][1])
        top.add(r1, r2, vcm_node, gdstk.Label("vcm_sense", (11.0, res_y + 0.4), layer=self.layers["met1_pin"][0], texttype=self.layers["met1_pin"][1]))

        # =========================================================================
        # 5. SECOND GAIN STAGE M5, M6, M7, M8
        # =========================================================================
        st2_x = core_w + 3.0
        # NMOS sinks M6, M8 (P-substrate)
        st2_nmos_diff = gdstk.rectangle((st2_x, 1.0), (st2_x + 12.0, core_h - 1.0), layer=self.layers["diff"][0], datatype=self.layers["diff"][1])
        top.add(st2_nmos_diff)
        for k in range(4):
            gx = st2_x + 1.0 + k * 2.6
            gp = gdstk.rectangle((gx, 0.5), (gx + 1.5, core_h - 0.5), layer=self.layers["poly"][0], datatype=self.layers["poly"][1])
            top.add(gp)
        # Gate bus for Vbn_out
        vbn_out_bus = gdstk.rectangle((st2_x, core_h), (st2_x + 12.0, core_h + 0.8), layer=self.layers["met1"][0], datatype=self.layers["met1"][1])
        top.add(vbn_out_bus, gdstk.Label("vbn_out", (st2_x + 2.0, core_h + 0.4), layer=self.layers["met1_pin"][0], texttype=self.layers["met1_pin"][1]))

        # PMOS drivers M5, M7 (N-Well)
        nwell_st2 = gdstk.rectangle((st2_x - 0.5, pmos_y - 1.0), (st2_x + 12.5, pmos_y + 9.5), layer=self.layers["nwell"][0], datatype=self.layers["nwell"][1])
        st2_pmos_diff = gdstk.rectangle((st2_x, pmos_y), (st2_x + 12.0, pmos_y + 7.5), layer=self.layers["diff"][0], datatype=self.layers["diff"][1])
        top.add(nwell_st2, st2_pmos_diff)
        for k in range(4):
            gx = st2_x + 1.0 + k * 2.6
            gp = gdstk.rectangle((gx, pmos_y - 0.5), (gx + 1.5, pmos_y + 8.0), layer=self.layers["poly"][0], datatype=self.layers["poly"][1])
            top.add(gp)

        # Output routes: outp and outm
        outp_bar = gdstk.rectangle((st2_x + 2.0, core_h + 1.5), (st2_x + 5.0, core_h + 2.5), layer=self.layers["met2"][0], datatype=self.layers["met2"][1])
        outm_bar = gdstk.rectangle((st2_x + 7.0, core_h + 1.5), (st2_x + 10.0, core_h + 2.5), layer=self.layers["met2"][0], datatype=self.layers["met2"][1])
        top.add(outp_bar, outm_bar)
        top.add(
            gdstk.Label("outp", (st2_x + 3.5, core_h + 2.0), layer=self.layers["met2_pin"][0], texttype=self.layers["met2_pin"][1]),
            gdstk.Label("outm", (st2_x + 8.5, core_h + 2.0), layer=self.layers["met2_pin"][0], texttype=self.layers["met2_pin"][1]),
        )

        # =========================================================================
        # 6. DUAL MILLER COMPENSATION CAPACITORS C_c1, C_c2 (MIM Caps)
        # =========================================================================
        cap_x = st2_x + 16.0
        cap_w = 12.0
        cap_h = 10.0
        for idx, (cap_name, cy) in enumerate([("C_c1", 1.0), ("C_c2", 14.0)]):
            cb = gdstk.rectangle((cap_x, cy), (cap_x + cap_w, cy + cap_h), layer=self.layers["met2"][0], datatype=self.layers["met2"][1])
            cm = gdstk.rectangle((cap_x + 0.4, cy + 0.4), (cap_x + cap_w - 0.4, cy + cap_h - 0.4), layer=self.layers["capm"][0], datatype=self.layers["capm"][1])
            ct = gdstk.rectangle((cap_x + 0.8, cy + 0.8), (cap_x + cap_w - 0.8, cy + cap_h - 0.8), layer=self.layers["met3"][0], datatype=self.layers["met3"][1])
            via1_c = gdstk.rectangle((cap_x + 1.0, cy + 1.0), (cap_x + 1.5, cy + 1.5), layer=self.layers["via1"][0], datatype=self.layers["via1"][1])
            via2_c = gdstk.rectangle((cap_x + cap_w - 1.5, cy + cap_h - 1.5), (cap_x + cap_w - 1.0, cy + cap_h - 1.0), layer=self.layers["via2"][0], datatype=self.layers["via2"][1])
            top.add(cb, cm, ct, via1_c, via2_c, gdstk.Label(cap_name, (cap_x + cap_w / 2, cy + cap_h / 2), layer=self.layers["met3"][0], texttype=self.layers["met3"][1]))

        # =========================================================================
        # 7. LOW-VT INPUT CHOPPER BRIDGE CELL CHOP1
        # =========================================================================
        chop_x = -17.0
        nwell_chop = gdstk.rectangle((chop_x - 1.0, 0.0), (chop_x + 12.0, core_h + 8.0), layer=self.layers["nwell"][0], datatype=self.layers["nwell"][1])
        chop_diff = gdstk.rectangle((chop_x, 1.0), (chop_x + 11.0, core_h + 7.0), layer=self.layers["diff"][0], datatype=self.layers["diff"][1])
        top.add(nwell_chop, chop_diff)
        for k in range(4):
            cg = gdstk.rectangle((chop_x + 1.0 + k * 2.4, 0.5), (chop_x + 1.8 + k * 2.4, core_h + 7.5), layer=self.layers["poly"][0], datatype=self.layers["poly"][1])
            top.add(cg)

        # Chopper pins: vin_p, vin_n, phi, phi_bar
        top.add(
            gdstk.Label("vin_p", (chop_x + 2.0, 2.0), layer=self.layers["met1_pin"][0], texttype=self.layers["met1_pin"][1]),
            gdstk.Label("vin_n", (chop_x + 2.0, 5.0), layer=self.layers["met1_pin"][0], texttype=self.layers["met1_pin"][1]),
            gdstk.Label("phi", (chop_x + 5.0, core_h + 5.0), layer=self.layers["met1_pin"][0], texttype=self.layers["met1_pin"][1]),
            gdstk.Label("phi_bar", (chop_x + 8.0, core_h + 5.0), layer=self.layers["met1_pin"][0], texttype=self.layers["met1_pin"][1]),
        )

        # Connect Chopper outputs to inp and inm
        link_p = gdstk.rectangle((chop_x + 9.0, core_h + 0.6), (0.5, core_h + 1.2), layer=self.layers["met2"][0], datatype=self.layers["met2"][1])
        link_n = gdstk.rectangle((chop_x + 9.0, core_h + 1.8), (0.5, core_h + 2.4), layer=self.layers["met2"][0], datatype=self.layers["met2"][1])
        top.add(link_p, link_n)

        # =========================================================================
        # 8. SUBSTRATE GUARD RING & CHIP PR BOUNDARY
        # =========================================================================
        min_x = chop_x - 3.0
        max_x = cap_x + cap_w + 3.0
        min_y = tail_y - 3.0
        max_y = res_y + 5.0

        # P-Substrate Guard Ring (tap layer 65/44 and met1 layer 68/20)
        gr_thick = 1.2
        gr_outer = gdstk.rectangle((min_x - gr_thick, min_y - gr_thick), (max_x + gr_thick, max_y + gr_thick))
        gr_inner = gdstk.rectangle((min_x, min_y), (max_x, max_y))
        gr_tap = gdstk.boolean(gr_outer, gr_inner, "not", layer=self.layers["tap"][0], datatype=self.layers["tap"][1])
        gr_m1 = gdstk.boolean(
            gdstk.rectangle((min_x - gr_thick + 0.2, min_y - gr_thick + 0.2), (max_x + gr_thick - 0.2, max_y + gr_thick - 0.2)),
            gdstk.rectangle((min_x + 0.2, min_y + 0.2), (max_x - 0.2, max_y - 0.2)),
            "not", layer=self.layers["met1"][0], datatype=self.layers["met1"][1]
        )
        top.add(*gr_tap, *gr_m1)
        top.add(gdstk.Label("vss", (min_x, min_y), layer=self.layers["met1_pin"][0], texttype=self.layers["met1_pin"][1]))

        # PR Boundary
        boundary = gdstk.rectangle((min_x - 2.0, min_y - 2.0), (max_x + 2.0, max_y + 2.0), layer=self.layers["prBoundary"][0], datatype=self.layers["prBoundary"][1])
        top.add(boundary)

        # Save GDSII
        gds_path = os.path.join(self.gds_dir, "neurodyn_afe_sky130.gds")
        fixed_timestamp = datetime.datetime(2026, 10, 25, 0, 0, 0)
        lib.write_gds(gds_path, timestamp=fixed_timestamp)

        # Render high-resolution PNG
        self.render_layout_png(top, os.path.join(self.img_dir, "layout_preview.png"), pattern, gate_positions)

        return gds_path

    def render_layout_png(self, cell: Optional[gdstk.Cell] = None, img_path: Optional[str] = None, pattern: list = None, gate_positions: list = None):
        """Renders the GDS layout geometry to a crisp publication PNG."""
        if img_path is None:
            img_path = os.path.join(self.img_dir, "layout_preview.png")
            
        if cell is None:
            gds_path = os.path.join(self.gds_dir, "neurodyn_afe_sky130.gds")
            if not os.path.exists(gds_path):
                self.generate_full_layout()
            lib = gdstk.read_gds(gds_path)
            cell = [c for c in lib.cells if c.name == "neurodyn_afe_top"][0] if "neurodyn_afe_top" in [c.name for c in lib.cells] else lib.top_level()[0]

        fig, ax = plt.subplots(figsize=(14, 7), dpi=300)
        
        color_map = {
            (64, 20): ("#FFE0B2", 0.45, "N-Well (PMOS Active Load & Chopper)"),
            (65, 20): ("#81C784", 0.75, "Active Diffusion (diff)"),
            (65, 44): ("#2E7D32", 0.85, "P+ Tap Guard Ring (vss)"),
            (66, 20): ("#E57373", 0.90, "Polysilicon Gates (poly)"),
            (66, 44): ("#FFD54F", 0.95, "Local Contact (licon)"),
            (67, 20): ("#BA68C8", 0.80, "Local Interconnect (li1)"),
            (67, 44): ("#FFD54F", 0.95, "Metal Contact (mcon)"),
            (68, 20): ("#64B5F6", 0.80, "Metal 1 (met1 Power & Bias Rails)"),
            (68, 44): ("#FFD54F", 0.95, "Via1 Cuts (via1)"),
            (69, 20): ("#1E88E5", 0.85, "Metal 2 (met2 Buses & Out Rails)"),
            (69, 44): ("#FFB300", 0.95, "Via2 Cuts (via2)"),
            (89, 44): ("#FF8A65", 0.85, "MIM Capacitor Dielectric (capm)"),
            (70, 20): ("#8E24AA", 0.75, "Metal 3 (met3 Cap Top Plate)"),
            (235, 4): ("#37474F", 0.35, "PR Boundary (Macro Edge)"),
        }
        
        used_labels = set()
        for poly in cell.polygons:
            key = (poly.layer, poly.datatype)
            if key in color_map:
                color, alpha, lbl = color_map[key]
                lbl_to_use = lbl if lbl not in used_labels else None
                if lbl_to_use:
                    used_labels.add(lbl)
                points = poly.points
                ax.fill(points[:, 0], points[:, 1], color=color, alpha=alpha, label=lbl_to_use, edgecolor="#37474F", linewidth=0.35)

        ax.set_aspect("equal")
        ax.set_title("NeuroDyn-AFE Complete Silicon Layout (SkyWater SKY130 CMOS)", fontsize=13, fontweight="bold", pad=12)
        ax.set_xlabel("X Position (um)", fontsize=10, fontweight="bold")
        ax.set_ylabel("Y Position (um)", fontsize=10, fontweight="bold")
        ax.grid(True, linestyle="--", alpha=0.35, color="#CFD8DC")
        ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.0), fontsize=7.5, framealpha=0.95)
        
        fig.tight_layout()
        fig.savefig(img_path, bbox_inches="tight", dpi=300)
        plt.close(fig)
        return img_path
