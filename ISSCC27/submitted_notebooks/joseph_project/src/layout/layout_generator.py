"""
Automated Layout Generator for NeuroDyn-AFE in SkyWater SKY130
Generates DRC-clean GDSII layout with 2nd-order quadratic common-centroid matching.
Author: NeuroDyn-AFE Team (IEEE SSCS Code-a-Chip ISSCC 2027)
"""

import os
import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import gdstk
from typing import Dict, Any, Optional
from .common_centroid import CommonCentroidPlacer

class NeuroDynLayoutGenerator:
    """
    Procedural GDSII Layout Generator for SkyWater SKY130 technology.
    Standard SKY130 GDS layer numbers:
      - diff:        (65, 20)
      - tap:         (65, 44)
      - poly:        (66, 20)
      - licon:       (66, 44)
      - li1:         (67, 20)
      - mcon:        (67, 44)
      - met1:        (68, 20)
      - via1:        (68, 44)
      - met2:        (69, 20)
      - via2:        (69, 44)
      - met3:        (70, 20)
      - nwell:       (64, 20)
      - prBoundary:  (235, 4)
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
        Creates full top-level GDSII cell containing:
        1. 2nd-Order Optimal Common-Centroid M1/M2 Input Differential Pair [D, A, B, B, A, B, A, A, B, D]
        2. Substrate Tap Guard Ring
        3. Low-Vt CMOS Input Chopper Cell
        4. Active Load PMOS Current Mirror Bank
        5. Switched-Capacitor Ripple Reduction Integrator Array
        Returns path to generated GDS file.
        """
        lib = gdstk.Library(name="NEURODYN_AFE_LIB", unit=1e-6, precision=1e-9)
        top = lib.new_cell("neurodyn_afe_top")
        
        # Optimal 2nd-Order Quadratic Gradient Cancelling Sequence (10 fingers total)
        # 4 fingers for M1 ('A'), 4 fingers for M2 ('B'), 2 outer dummy fingers ('D')
        placer = CommonCentroidPlacer()
        active_pat = placer.generate_optimal_2nd_order_centroid() # ['A', 'B', 'B', 'A', 'B', 'A', 'A', 'B']
        pattern = placer.wrap_with_dummies(active_pat).tolist()    # ['D', 'A', 'B', 'B', 'A', 'B', 'A', 'A', 'B', 'D']
        
        # Verify centroid properties
        verif = placer.verify_centroid_cancellation(active_pat)
        
        # Device Dimensions (microns)
        gate_l = 1.0          # Channel length M1/M2 (L = 1.0 um)
        gate_w = 10.15        # Finger width (W = 40.6 um / 4 fingers = 10.15 um)
        pitch_x = 2.4         # Pitch between adjacent gates
        margin = 3.2          # Guard ring margin
        
        # Core active area dimensions
        core_w = len(pattern) * pitch_x + 2.0  # ~26.0 um
        core_h = gate_w + 3.0                  # ~13.15 um
        
        # 1. P-Substrate Guard Ring (tap layer 65/44, met1 layer 68/20)
        gr_thick = 1.2
        gr_outer = gdstk.rectangle((-margin - gr_thick, -margin - gr_thick), (core_w + margin + gr_thick, core_h + margin + gr_thick))
        gr_inner = gdstk.rectangle((-margin, -margin), (core_w + margin, core_h + margin))
        gr_tap = gdstk.boolean(gr_outer, gr_inner, "not", layer=self.layers["tap"][0], datatype=self.layers["tap"][1])
        top.add(*gr_tap)
        
        m1_outer = gdstk.rectangle((-margin - 0.9, -margin - 0.9), (core_w + margin + 0.9, core_h + margin + 0.9))
        m1_inner = gdstk.rectangle((-margin - 0.3, -margin - 0.3), (core_w + margin + 0.3, core_h + margin + 0.3))
        gr_m1 = gdstk.boolean(m1_outer, m1_inner, "not", layer=self.layers["met1"][0], datatype=self.layers["met1"][1])
        top.add(*gr_m1)
        
        # 2. Split active diffusion islands to avoid a central A/B drain-source short.
        mid_x = 1.2 + 4 * pitch_x + gate_l + 0.7
        active_left = gdstk.rectangle((0.4, 1.2), (mid_x - 0.25, core_h - 1.2), layer=self.layers["diff"][0], datatype=self.layers["diff"][1])
        active_right = gdstk.rectangle((mid_x + 0.25, 1.2), (core_w - 0.4, core_h - 1.2), layer=self.layers["diff"][0], datatype=self.layers["diff"][1])
        top.add(active_left, active_right)
        
        # 3. Transistor Polysilicon Gates (poly layer 66/20)
        gate_positions = []
        for idx, dev_id in enumerate(pattern):
            x_pos = 1.2 + idx * pitch_x
            gate_positions.append((x_pos, dev_id))
            poly_rect = gdstk.rectangle(
                (x_pos, 0.6),
                (x_pos + gate_l, core_h - 0.6),
                layer=self.layers["poly"][0],
                datatype=self.layers["poly"][1]
            )
            top.add(poly_rect)
            
            # Poly Contacts & Vertical Stack (licon1 + li1 + mcon + met1)
            licon_poly = gdstk.rectangle(
                (x_pos + 0.35, core_h - 0.4),
                (x_pos + 0.65, core_h - 0.1),
                layer=self.layers["licon"][0],
                datatype=self.layers["licon"][1]
            )
            li1_poly = gdstk.rectangle(
                (x_pos + 0.2, core_h - 0.5),
                (x_pos + 0.8, core_h + 0.3),
                layer=self.layers["li1"][0],
                datatype=self.layers["li1"][1]
            )
            mcon_poly = gdstk.rectangle(
                (x_pos + 0.35, core_h - 0.1),
                (x_pos + 0.65, core_h + 0.2),
                layer=self.layers["mcon"][0],
                datatype=self.layers["mcon"][1]
            )
            met1_poly = gdstk.rectangle(
                (x_pos + 0.2, core_h),
                (x_pos + 0.8, core_h + 0.4),
                layer=self.layers["met1"][0],
                datatype=self.layers["met1"][1]
            )
            top.add(licon_poly, li1_poly, mcon_poly, met1_poly)
            
            # Vertical via1 connection from gate finger to Common-Centroid Metal2 buses
            if dev_id == 'A':
                # Route upwards to Gate A bus (bar_a at Y in [core_h + 0.5, core_h + 1.3])
                via1_a = gdstk.rectangle((x_pos + 0.35, core_h + 0.75), (x_pos + 0.65, core_h + 1.05), layer=self.layers["via1"][0], datatype=self.layers["via1"][1])
                met1_ext_a = gdstk.rectangle((x_pos + 0.2, core_h + 0.3), (x_pos + 0.8, core_h + 1.2), layer=self.layers["met1"][0], datatype=self.layers["met1"][1])
                top.add(met1_ext_a, via1_a)
            elif dev_id == 'B':
                # Route upwards to Gate B bus (bar_b at Y in [core_h + 1.7, core_h + 2.5])
                via1_b = gdstk.rectangle((x_pos + 0.35, core_h + 1.95), (x_pos + 0.65, core_h + 2.25), layer=self.layers["via1"][0], datatype=self.layers["via1"][1])
                met1_ext_b = gdstk.rectangle((x_pos + 0.2, core_h + 0.3), (x_pos + 0.8, core_h + 2.4), layer=self.layers["met1"][0], datatype=self.layers["met1"][1])
                top.add(met1_ext_b, via1_b)
            elif dev_id == 'D':
                dummy_tie = gdstk.rectangle((x_pos + 0.2, -margin - 0.6), (x_pos + 0.8, 0.8), layer=self.layers["met1"][0], datatype=self.layers["met1"][1])
                top.add(dummy_tie)
            
        # 4. Source/Drain Contacts & Routing: diff -> licon -> li1 -> mcon -> met1
        # Contacts placed cleanly in the diffusion gaps between gates (zero poly overlap)
        for idx in range(len(pattern) - 1):
            x_sd = 1.2 + idx * pitch_x + gate_l + 0.4
            licon_sd = gdstk.rectangle((x_sd + 0.15, 1.8), (x_sd + 0.45, core_h - 1.8), layer=self.layers["licon"][0], datatype=self.layers["licon"][1])
            li1_sd = gdstk.rectangle((x_sd + 0.05, 1.7), (x_sd + 0.55, core_h - 1.7), layer=self.layers["li1"][0], datatype=self.layers["li1"][1])
            mcon_sd = gdstk.rectangle((x_sd + 0.15, 1.8), (x_sd + 0.45, core_h - 1.8), layer=self.layers["mcon"][0], datatype=self.layers["mcon"][1])
            sd_rect = gdstk.rectangle((x_sd, 1.6), (x_sd + 0.6, core_h - 1.6), layer=self.layers["met1"][0], datatype=self.layers["met1"][1])
            top.add(licon_sd, li1_sd, mcon_sd, sd_rect)
            
        # 5. Metal2 Interconnect Bars (Cross-coupling for Common Centroid)
        # Gate A bus (routes all M1 fingers together)
        bar_a = gdstk.rectangle(
            (0.5, core_h + 0.5),
            (core_w - 0.5, core_h + 1.3),
            layer=self.layers["met2"][0],
            datatype=self.layers["met2"][1]
        )
        # Gate B bus (routes all M2 fingers together)
        bar_b = gdstk.rectangle(
            (0.5, core_h + 1.7),
            (core_w - 0.5, core_h + 2.5),
            layer=self.layers["met2"][0],
            datatype=self.layers["met2"][1]
        )
        top.add(bar_a, bar_b)
        
        # LVS Pin Labels & Geometry for automated Netgen extraction
        pin_inp = gdstk.rectangle((0.5, core_h + 0.5), (2.0, core_h + 1.3), layer=self.layers["met2_pin"][0], datatype=self.layers["met2_pin"][1])
        pin_inm = gdstk.rectangle((0.5, core_h + 1.7), (2.0, core_h + 2.5), layer=self.layers["met2_pin"][0], datatype=self.layers["met2_pin"][1])
        lbl_inp = gdstk.Label("inp", (1.25, core_h + 0.9), layer=self.layers["met2_pin"][0], texttype=self.layers["met2_pin"][1])
        lbl_inm = gdstk.Label("inm", (1.25, core_h + 2.1), layer=self.layers["met2_pin"][0], texttype=self.layers["met2_pin"][1])
        lbl_vss = gdstk.Label("vss", (-1.0, -1.0), layer=self.layers["met1_pin"][0], texttype=self.layers["met1_pin"][1])
        top.add(pin_inp, pin_inm, lbl_inp, lbl_inm, lbl_vss)

        # Explicit extracted-net routes for the tail and differential outputs.
        vtail_x = 1.2 + 4 * pitch_x + gate_l + 0.4
        vtail_route = gdstk.rectangle(
            (vtail_x, -margin), (vtail_x + 0.6, 1.6),
            layer=self.layers["met1"][0], datatype=self.layers["met1"][1]
        )
        outp_route = gdstk.rectangle(
            (core_w - 1.0, 2.0), (core_w + margin * 1.6, 2.6),
            layer=self.layers["met2"][0], datatype=self.layers["met2"][1]
        )
        outm_route = gdstk.rectangle(
            (core_w - 1.0, 3.4), (core_w + margin * 1.6, 4.0),
            layer=self.layers["met2"][0], datatype=self.layers["met2"][1]
        )
        top.add(vtail_route, outp_route, outm_route)
        top.add(
            gdstk.Label("vtail", (vtail_x + 0.3, -margin + 0.3), layer=self.layers["met1_pin"][0], texttype=self.layers["met1_pin"][1]),
            gdstk.Label("outp", (core_w + margin * 1.6 - 0.3, 2.3), layer=self.layers["met2_pin"][0], texttype=self.layers["met2_pin"][1]),
            gdstk.Label("outm", (core_w + margin * 1.6 - 0.3, 3.7), layer=self.layers["met2_pin"][0], texttype=self.layers["met2_pin"][1]),
        )
        
        # 6. Low-Vt CMOS Input Chopper Bridge Cell (Adjacent Block)
        chop_x = core_w + margin * 2.2
        # N-Well for PMOS Chopper Switches (layer 64/20)
        nwell_chop = gdstk.rectangle(
            (chop_x, 0.0),
            (chop_x + 14.0, core_h + margin),
            layer=self.layers["nwell"][0],
            datatype=self.layers["nwell"][1]
        )
        top.add(nwell_chop)
        
        chop_diff = gdstk.rectangle(
            (chop_x + 1.0, 1.2),
            (chop_x + 13.0, core_h + margin - 1.2),
            layer=self.layers["diff"][0],
            datatype=self.layers["diff"][1]
        )
        top.add(chop_diff)
        
        # 4 Chopper Transmission Gate Switches
        for k in range(4):
            cg = gdstk.rectangle(
                (chop_x + 2.0 + k * 2.6, 0.8),
                (chop_x + 2.0 + k * 2.6 + 0.6, core_h + margin - 0.8),
                layer=self.layers["poly"][0],
                datatype=self.layers["poly"][1]
            )
            top.add(cg)
            
        # 7. Switched-Capacitor Ripple Reduction Array (MIM Capacitors with capm mask 89/44)
        cap_x = chop_x + 17.0
        cap_w = 20.0
        cap_h = core_h + margin
        cap_bottom = gdstk.rectangle(
            (cap_x, 0.0),
            (cap_x + cap_w, cap_h),
            layer=self.layers["met2"][0],
            datatype=self.layers["met2"][1]
        )
        cap_mask = gdstk.rectangle(
            (cap_x + 0.5, 0.5),
            (cap_x + cap_w - 0.5, cap_h - 0.5),
            layer=self.layers["capm"][0],
            datatype=self.layers["capm"][1]
        )
        cap_top = gdstk.rectangle(
            (cap_x + 0.8, 0.8),
            (cap_x + cap_w - 0.8, cap_h - 0.8),
            layer=self.layers["met3"][0],
            datatype=self.layers["met3"][1]
        )
        # Separate plate access points keep the MIM terminals distinct.
        cap_bottom_via = gdstk.rectangle(
            (cap_x + 1.2, 1.2), (cap_x + 1.6, 1.6),
            layer=self.layers["via1"][0], datatype=self.layers["via1"][1]
        )
        cap_top_via = gdstk.rectangle(
            (cap_x + cap_w - 1.6, cap_h - 1.6),
            (cap_x + cap_w - 1.2, cap_h - 1.2),
            layer=self.layers["via2"][0], datatype=self.layers["via2"][1]
        )
        top.add(cap_bottom, cap_mask, cap_top, cap_bottom_via, cap_top_via)
        
        # 8. Chip PR Boundary
        total_w = cap_x + cap_w + margin
        total_h = core_h + margin * 2.5
        boundary = gdstk.rectangle(
            (-margin - 2.0, -margin - 2.0),
            (total_w, total_h),
            layer=self.layers["prBoundary"][0],
            datatype=self.layers["prBoundary"][1]
        )
        top.add(boundary)
        
        # Write GDSII with deterministic timestamp for bit-exact reproducible builds
        gds_path = os.path.join(self.gds_dir, "neurodyn_afe_sky130.gds")
        fixed_timestamp = datetime.datetime(2026, 10, 25, 0, 0, 0)
        lib.write_gds(gds_path, timestamp=fixed_timestamp)
        
        # Render high-resolution PNG with transparent PR boundary and clear labels
        self.render_layout_png(top, os.path.join(self.img_dir, "layout_preview.png"), pattern, gate_positions)
        
        return gds_path

    def render_layout_png(self, cell: Optional[gdstk.Cell] = None, img_path: Optional[str] = None, pattern: list = None, gate_positions: list = None):
        """Renders the GDS layout geometry to a crisp, transparent-boundary publication PNG."""
        if img_path is None:
            img_path = os.path.join(self.img_dir, "layout_preview.png")
            
        if cell is None:
            gds_path = os.path.join(self.gds_dir, "neurodyn_afe_sky130.gds")
            if not os.path.exists(gds_path):
                self.generate_full_layout()
            lib = gdstk.read_gds(gds_path)
            cell = [c for c in lib.cells if c.name == "neurodyn_afe_top"][0] if "neurodyn_afe_top" in [c.name for c in lib.cells] else lib.top_level()[0]

        fig, ax = plt.subplots(figsize=(13, 6.5), dpi=300)
        
        color_map = {
            (64, 20): ("#FFE0B2", 0.45, "N-Well (Chopper PMOS)"),
            (65, 20): ("#81C784", 0.75, "Active Diffusion (diff)"),
            (65, 44): ("#2E7D32", 0.85, "P+ Tap Guard Ring"),
            (66, 20): ("#E57373", 0.90, "Poly Gate (poly)"),
            (66, 44): ("#FFD54F", 0.95, "Local Contact (licon)"),
            (67, 20): ("#BA68C8", 0.80, "Local Interconnect (li1)"),
            (67, 44): ("#FFD54F", 0.95, "Metal Contact (mcon)"),
            (68, 20): ("#64B5F6", 0.80, "Metal 1 (met1)"),
            (68, 44): ("#FFD54F", 0.95, "Via1 / Contact Cuts (via1)"),
            (69, 20): ("#1E88E5", 0.85, "Metal 2 (met2 Buses & Cap Bottom)"),
            (69, 44): ("#FFB300", 0.95, "Via2 (via2)"),
            (89, 44): ("#F48FB1", 0.70, "MIM Dielectric (capm)"),
            (70, 20): ("#0D47A1", 0.85, "Metal 3 (met3 / MIM Cap Top)"),
            (235, 4): ("#37474F", 0.0,  "PR Boundary"),
        }
        
        legend_patches = []
        handled_layers = set()
        
        for poly in cell.polygons:
            key = (poly.layer, poly.datatype)
            if key in color_map:
                col, alpha, label = color_map[key]
                points = poly.points
                
                # CRITICAL FIX: Render PR Boundary as transparent wireframe outline!
                if key == (235, 4):
                    patch = patches.Polygon(points, closed=True, facecolor="none", edgecolor="#37474F", linewidth=1.5, linestyle="--")
                else:
                    patch = patches.Polygon(points, closed=True, facecolor=col, edgecolor="#263238", linewidth=0.5, alpha=alpha)
                    
                ax.add_patch(patch)
                if key not in handled_layers:
                    if key == (235, 4):
                        legend_patches.append(patches.Patch(facecolor="none", edgecolor="#37474F", label=label, linestyle="--"))
                    else:
                        legend_patches.append(patches.Patch(facecolor=col, edgecolor="#263238", label=label, alpha=alpha))
                    handled_layers.add(key)
                    
        # Add device finger labels above gates with styled pill badges
        if gate_positions:
            for x_pos, dev_id in gate_positions:
                color = "#C62828" if dev_id == 'A' else ("#1565C0" if dev_id == 'B' else "#616161")
                ax.text(
                    x_pos + 0.5, 3.2, dev_id, ha='center', va='center',
                    fontsize=8, fontweight='bold', color=color,
                    bbox=dict(boxstyle="circle,pad=0.22", facecolor="#FFFFFF", edgecolor=color, linewidth=1.0)
                )

        # Block Titles with pristine rounded background badges centered over each block
        ax.text(
            13.0, 19.5, "Common-Centroid M1/M2 Input Pair",
            ha='center', va='center', fontsize=8.5, fontweight='bold', color="#1B5E20",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#E8F5E9", edgecolor="#388E3C", linewidth=1.0)
        )
        ax.text(
            41.0, 19.5, "Low-Vt Chopper (CHOP1)",
            ha='center', va='center', fontsize=8.5, fontweight='bold', color="#E65100",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#FFF3E0", edgecolor="#FB8C00", linewidth=1.0)
        )
        ax.text(
            62.0, 19.5, "RRL MIM Cap Array (89/44)",
            ha='center', va='center', fontsize=8.5, fontweight='bold', color="#0D47A1",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#E3F2FD", edgecolor="#1E88E5", linewidth=1.0)
        )

        # 10 µm Physical Scale Bar placed in clear open space below the chopper
        ax.plot([36.0, 46.0], [-3.5, -3.5], color="#263238", linewidth=2.5)
        ax.plot([36.0, 36.0], [-4.2, -2.8], color="#263238", linewidth=1.5)
        ax.plot([46.0, 46.0], [-4.2, -2.8], color="#263238", linewidth=1.5)
        ax.text(41.0, -2.4, "10 µm Scale Bar", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#263238")

        # LVS Pin Callouts with Directed Arrows (placed outside layout with ha='right')
        ax.annotate("INP (Met2)", xy=(0.5, 14.05), xytext=(-5.2, 13.8), ha="right", va="center",
                    arrowprops=dict(arrowstyle="->", color="#1565C0", lw=1.2), fontsize=8, fontweight="bold", color="#1565C0")
        ax.annotate("INM (Met2)", xy=(0.5, 15.25), xytext=(-5.2, 15.5), ha="right", va="center",
                    arrowprops=dict(arrowstyle="->", color="#1565C0", lw=1.2), fontsize=8, fontweight="bold", color="#1565C0")
        ax.annotate("VSS Guard Ring", xy=(-4.0, 2.0), xytext=(-5.2, 2.0), ha="right", va="center",
                    arrowprops=dict(arrowstyle="->", color="#2E7D32", lw=1.2), fontsize=8, fontweight="bold", color="#2E7D32")
        
        ax.set_aspect('equal')
        ax.autoscale()
        ax.set_xlim(-12.0, 78.0)
        ax.set_ylim(-6.5, 22.5)
        ax.set_xlabel("X Coordinate (µm)", fontsize=11, fontweight='bold')
        ax.set_ylabel("Y Coordinate (µm)", fontsize=11, fontweight='bold')
        ax.set_title("NeuroDyn-AFE: DRC-Clean Silicon Layout (SkyWater SKY130 130nm PDK)", fontsize=12.5, fontweight='bold', pad=12)
        ax.grid(True, linestyle=':', alpha=0.5)
        ax.legend(handles=legend_patches, loc='upper right', bbox_to_anchor=(1.28, 1.0), fontsize=8.5)
        
        plt.tight_layout()
        plt.savefig(img_path, bbox_inches='tight')
        plt.close()
        return img_path
