"""
opentcad.gui.app — Streamlit front-end for the whole pipeline.

Launch from the repo root:
    streamlit run opentcad/gui/app.py

Three stacked sections walk you through the pipeline in order:

    1. Structure   — build the initial cross-section (layers, regions,
                     contacts). Renders a live preview of the stack.
    2. Recipe      — append deposit / etch / oxidize steps and run them
                     against the substrate. Renders the topography state
                     after each step.
    3. Device      — configure PhysicsConfig, mesh the current state,
                     and run iv_sweep or cv_sweep. Renders IV / CV.

Session state carries the built objects between sections so navigating
tabs doesn't re-run the whole pipeline.
"""
from __future__ import annotations

import io
from dataclasses import asdict

import numpy as np
import streamlit as st

from opentcad.device.physics import PhysicsConfig
from opentcad.device.models import (
    Auger, Boltzmann, Canali, ConstantMobility, FermiDirac, Klaassen,
    Lombardi, NoBGN, Radiative, SRH, Slotboom,
)
from opentcad.geometry.formats import Material, MATERIAL_NAMES
from opentcad.geometry.structure import Structure
from opentcad.materials.database import load_material
from opentcad.process.topography import (
    Recipe, extract_surface_polyline,
    initial_state_from_structure, simulate, topography_to_meshfield,
)
from opentcad.process.topography.simulator import (
    _apply_deposit, _apply_etch, _apply_oxidize,
)

from opentcad.gui.plots import (
    plot_cv, plot_iv, plot_meshfield, plot_structure_stack,
    plot_topography_polylines,
)


st.set_page_config(page_title="OpenTCAD", layout="wide",
                   page_icon="🔬")


# ---------------------------------------------------------------------------
# Session state initialization.
# ---------------------------------------------------------------------------
#: Demo geometry constants — matched to examples/02_nmos_idvg.py so the
#: GUI walkthrough reproduces the Phase 0 exit result exactly.
DEMO_L_GATE_UM = 1.0
DEMO_W_SD_UM = 0.5
DEMO_H_BODY_UM = 0.5
DEMO_T_OX_UM = 0.005
DEMO_SD_DEPTH_UM = 0.1
DEMO_N_A = 1e17
DEMO_N_D = 1e20
DEMO_WIDTH_UM = 2.0 * DEMO_W_SD_UM + DEMO_L_GATE_UM   # = 2.0 um
DEMO_VDS = 0.05


def _seed_nmos_structure() -> "Structure":
    """Build the same NMOS as examples/02_nmos_idvg.py — 2 µm wide,
    p-body Na=1e17, 5 nm gate oxide, n+ S/D at 1e20 punched through the
    oxide by 100 nm."""
    w = DEMO_WIDTH_UM
    top_of_si = DEMO_H_BODY_UM
    top_of_ox = DEMO_H_BODY_UM + DEMO_T_OX_UM
    return (Structure(width_um=w, name="nmos_demo")
            .add_substrate("p_body", DEMO_H_BODY_UM, Material.SI,
                           doping_Na=DEMO_N_A)
            .add_layer("oxide", DEMO_T_OX_UM, Material.SIO2)
            .add_region("source", 0.0, DEMO_W_SD_UM,
                        top_of_si - DEMO_SD_DEPTH_UM, top_of_ox,
                        Material.SI, doping_Nd=DEMO_N_D)
            .add_region("drain", w - DEMO_W_SD_UM, w,
                        top_of_si - DEMO_SD_DEPTH_UM, top_of_ox,
                        Material.SI, doping_Nd=DEMO_N_D)
            .add_contact("source", 0.0, DEMO_W_SD_UM, "oxide", surface="top")
            .add_contact("drain",  w - DEMO_W_SD_UM, w, "oxide", surface="top")
            .add_contact("gate",   DEMO_W_SD_UM, DEMO_W_SD_UM + DEMO_L_GATE_UM,
                         "oxide", surface="top")
            .add_contact("body",   0.0, w, "p_body", surface="bottom"))


def _init_state():
    """Seed session state with a demo-ready NMOS. Two clicks — Build
    MeshField, then Run device solve — produce the Phase 0 exit Id-Vgs
    curve at Vds = 50 mV, on/off > 10¹⁰. All device-analysis parameters
    are pre-populated to match — sweep Vgs from 0 to 1.5 V, hold drain
    at 50 mV, measure drain current.

    Also seeds a demo Recipe (30 nm blanket + 100 nm masked RIE) so the
    Recipe section has something to show without typing."""
    ss = st.session_state
    if "structure" not in ss:
        ss.structure = _seed_nmos_structure()
    if "recipe_steps" not in ss:
        # Left empty on purpose. ViennaLS advection callbacks are
        # unstable on Streamlit's non-main script-runner thread on
        # macOS — clicking "Run recipe" from the browser will segfault
        # the server. Use the Python API (examples/04, 05) for
        # topography demos; the GUI demonstrates the Structure DSL
        # + DEVSIM path only.
        ss.recipe_steps = []
    if "topography_state" not in ss:
        ss.topography_state = None
    if "meshfield" not in ss:
        ss.meshfield = None
    if "device_result" not in ss:
        ss.device_result = None    # {"kind": "iv"|"cv", "V":..., "I|C":...}
    # Analysis defaults — match examples/02_nmos_idvg.py.
    ss.setdefault("iv_v_start", 0.0)
    ss.setdefault("iv_v_end",   1.5)
    ss.setdefault("iv_v_step",  0.1)
    ss.setdefault("iv_terminal_a",   "gate")     # sweep target
    ss.setdefault("iv_terminal_b",   "source")   # reference at 0 V
    ss.setdefault("iv_measure",      "drain")    # read current here
    ss.setdefault("iv_hold_drain_v", DEMO_VDS)   # 50 mV
    ss.setdefault("mesh_size_um",    0.03)


_init_state()


# ---------------------------------------------------------------------------
# Sidebar — global state summary.
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Pipeline state")
    ss = st.session_state
    s = ss.structure
    st.markdown(
        f"**Structure**  \n"
        f"{len(s._layers)} layers, {len(s._regions)} regions, "
        f"{len(s._contacts)} contacts  \n"
        f"width = {s.width_um:.3f} µm, total height = "
        f"{s.total_height_um:.3f} µm")

    st.markdown(f"**Recipe**  \n{len(ss.recipe_steps)} step(s)")

    if ss.topography_state is not None:
        st.markdown(
            f"**Topography state**  \n"
            f"{len(ss.topography_state.layers)} LS layers, "
            f"grid={ss.topography_state.grid_delta_um:.4f} µm")
    else:
        st.markdown("**Topography state**  _(not simulated)_")

    if ss.meshfield is not None:
        st.markdown(
            f"**MeshField**  \n"
            f"{ss.meshfield.n_cells} triangles, "
            f"{ss.meshfield.n_points} nodes")
    else:
        st.markdown("**MeshField**  _(not built)_")

    st.divider()
    if st.button("Reset entire pipeline", type="secondary",
                 use_container_width=True):
        for k in ("structure", "recipe_steps", "topography_state",
                  "meshfield", "device_result"):
            if k in ss:
                del ss[k]
        st.rerun()

    st.caption("OpenTCAD Streamlit UI")


# ---------------------------------------------------------------------------
# 1. Structure builder
# ---------------------------------------------------------------------------
st.title("OpenTCAD")
st.caption(
    "Process → device pipeline. Build a structure, run a process recipe, "
    "hand the result to DEVSIM.")

st.header("1. Structure")

col1, col2 = st.columns([1, 1.2])

with col1:
    with st.form("structure_form", clear_on_submit=False):
        st.subheader("Substrate + layers")

        new_width = st.number_input(
            "Structure width [µm]", min_value=0.05, max_value=100.0,
            value=float(ss.structure.width_um), step=0.1)

        st.markdown("**Add layer**")
        layer_col1, layer_col2 = st.columns(2)
        with layer_col1:
            layer_name = st.text_input("Name", value="oxide")
            layer_material = st.selectbox(
                "Material",
                [m.name for m in Material if m != Material.VACUUM],
                index=1)  # SIO2
        with layer_col2:
            layer_thickness = st.number_input(
                "Thickness [µm]", min_value=0.001, max_value=10.0,
                value=0.005, step=0.001, format="%.4f")
            doping_kind = st.selectbox("Doping", ["none", "N (Nd)", "P (Na)"])
            doping_conc = st.number_input(
                "Doping conc. [cm⁻³]", min_value=0.0, value=1e17,
                format="%.2e", disabled=(doping_kind == "none"))

        add_layer = st.form_submit_button(
            "Add layer to top of stack", type="primary")

    if add_layer:
        try:
            if new_width != ss.structure.width_um:
                # Rebuild structure with new width (keeps layers/contacts).
                new_s = Structure(width_um=new_width, name=ss.structure.name)
                for L in ss.structure._layers:
                    new_s._layers.append(L)
                for r in ss.structure._regions:
                    new_s._regions.append(r)
                for c in ss.structure._contacts:
                    new_s._contacts.append(c)
                ss.structure = new_s

            kw = {}
            if doping_kind == "N (Nd)":
                kw["doping_Nd"] = float(doping_conc)
            elif doping_kind == "P (Na)":
                kw["doping_Na"] = float(doping_conc)
            mat = Material[layer_material]
            if not ss.structure._layers:
                ss.structure.add_substrate(layer_name, float(layer_thickness),
                                            mat, **kw)
            else:
                ss.structure.add_layer(layer_name, float(layer_thickness),
                                        mat, **kw)
            # Invalidate downstream state.
            ss.topography_state = None; ss.meshfield = None
            ss.device_result = None
            st.rerun()
        except Exception as e:
            st.error(f"Could not add layer: {e}")

    # Existing-layer list with delete buttons.
    st.subheader("Current stack (top → bottom)")
    if not ss.structure._layers:
        st.info("No layers yet. Add a substrate above.")
    else:
        for idx, layer in reversed(list(enumerate(ss.structure._layers))):
            c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
            c1.write(f"**{layer.name}**")
            c2.write(MATERIAL_NAMES.get(layer.material, layer.material.name))
            dop = ""
            if layer.doping_Nd:
                dop = f"Nd={layer.doping_Nd:.1e}"
            elif layer.doping_Na:
                dop = f"Na={layer.doping_Na:.1e}"
            c3.write(f"{layer.thickness_um*1000:.1f} nm {dop}")
            if c4.button("✕", key=f"del_layer_{idx}",
                          help="Remove this layer"):
                del ss.structure._layers[idx]
                ss.topography_state = None; ss.meshfield = None
                ss.device_result = None
                st.rerun()

    with st.expander("Add contact"):
        with st.form("contact_form", clear_on_submit=True):
            c_name = st.text_input("Contact name", value="anode")
            c_x_start = st.number_input(
                "x_start [µm]", min_value=0.0,
                max_value=float(ss.structure.width_um), value=0.0)
            c_x_end = st.number_input(
                "x_end [µm]", min_value=0.0,
                max_value=float(ss.structure.width_um),
                value=float(ss.structure.width_um))
            layer_names = [L.name for L in ss.structure._layers]
            c_layer = st.selectbox("On layer", layer_names or ["(none)"])
            c_surface = st.selectbox("Surface", ["top", "bottom"])
            c_ctype = st.selectbox("Type",
                                   ["ohmic", "schottky", "metal_on_insulator"])
            c_wf = st.number_input("Work function [eV]",
                                   value=4.5, step=0.1,
                                   disabled=(c_ctype != "schottky"))
            c_vfb = st.number_input(
                "flat_band_shift_V", value=0.0, step=0.1,
                disabled=(c_ctype != "metal_on_insulator"))
            add_contact = st.form_submit_button("Add contact")
        if add_contact and layer_names:
            try:
                ss.structure.add_contact(
                    c_name, float(c_x_start), float(c_x_end), c_layer,
                    surface=c_surface,
                    contact_type=("metal_on_insulator"
                                  if c_ctype == "metal_on_insulator"
                                  else c_ctype),
                    work_function_eV=(float(c_wf) if c_ctype == "schottky"
                                       else None),
                    flat_band_shift_V=(float(c_vfb)
                                         if c_ctype == "metal_on_insulator"
                                         else 0.0),
                )
                ss.meshfield = None; ss.device_result = None
                st.rerun()
            except Exception as e:
                st.error(f"Could not add contact: {e}")

        for idx, c in enumerate(ss.structure._contacts):
            cc1, cc2 = st.columns([5, 1])
            cc1.write(f"**{c.name}** ({c.contact_type}, {c.surface}, "
                       f"x=[{c.x_start:.3f}, {c.x_end:.3f}], "
                       f"on `{c.layer_name}`)")
            if cc2.button("✕", key=f"del_contact_{idx}"):
                del ss.structure._contacts[idx]
                ss.meshfield = None; ss.device_result = None
                st.rerun()

with col2:
    st.subheader("Preview")
    if ss.structure._layers:
        st.pyplot(plot_structure_stack(ss.structure), clear_figure=True)
    else:
        st.info("Add a layer to see the preview.")


# ---------------------------------------------------------------------------
# 2. Recipe (topography)
# ---------------------------------------------------------------------------
st.header("2. Recipe (topography)")

col1, col2 = st.columns([1, 1.2])

with col1:
    step_type = st.selectbox("Step type", ["deposit", "etch", "oxidize"])

    with st.form(f"recipe_form_{step_type}", clear_on_submit=False):
        step_dict = {"type": step_type}
        if step_type == "deposit":
            step_dict["material"] = st.selectbox(
                "Material",
                [m.name for m in Material if m != Material.VACUUM],
                index=1)
            step_dict["thickness_um"] = st.number_input(
                "Thickness [µm]", min_value=0.001, max_value=5.0,
                value=0.03, step=0.001, format="%.4f")

        elif step_type == "etch":
            step_dict["depth_um"] = st.number_input(
                "Depth [µm]", min_value=0.001, max_value=5.0,
                value=0.05, step=0.001, format="%.4f")
            step_dict["model"] = st.selectbox("Model",
                                              ["isotropic", "directional"])
            masked = st.checkbox("Masked (window)")
            if masked:
                w1, w2 = st.columns(2)
                step_dict["x0"] = w1.number_input(
                    "window x0 [µm]", min_value=0.0,
                    max_value=float(ss.structure.width_um),
                    value=float(ss.structure.width_um) * 0.35, step=0.05)
                step_dict["x1"] = w2.number_input(
                    "window x1 [µm]", min_value=0.0,
                    max_value=float(ss.structure.width_um),
                    value=float(ss.structure.width_um) * 0.65, step=0.05)
            else:
                step_dict["x0"] = step_dict["x1"] = None
            if step_dict["model"] == "directional":
                step_dict["sidewall_ratio"] = st.slider(
                    "Sidewall ratio (0=pure RIE, 1=isotropic)",
                    min_value=0.0, max_value=1.0, value=0.0, step=0.05)

        else:   # oxidize
            step_dict["temperature_C"] = st.number_input(
                "Temperature [°C]", min_value=600, max_value=1300, value=1000)
            step_dict["time_s"] = st.number_input(
                "Time [s]", min_value=1, max_value=100000, value=1800)
            step_dict["ambient"] = st.selectbox("Ambient", ["dry", "wet"])
            masked = st.checkbox("LOCOS mask")
            if masked:
                w1, w2 = st.columns(2)
                step_dict["x0"] = w1.number_input(
                    "window x0 [µm]", min_value=0.0,
                    max_value=float(ss.structure.width_um),
                    value=float(ss.structure.width_um) * 0.35, step=0.05,
                    key="ox_x0")
                step_dict["x1"] = w2.number_input(
                    "window x1 [µm]", min_value=0.0,
                    max_value=float(ss.structure.width_um),
                    value=float(ss.structure.width_um) * 0.65, step=0.05,
                    key="ox_x1")
                step_dict["bird_beak_length_um"] = st.number_input(
                    "Bird's beak length [µm]", min_value=0.0,
                    max_value=1.0, value=0.03, step=0.005, format="%.4f")
            else:
                step_dict["x0"] = step_dict["x1"] = None
                step_dict["bird_beak_length_um"] = 0.0

        add_step = st.form_submit_button("Append step to recipe",
                                          type="primary")
    if add_step:
        ss.recipe_steps.append(step_dict)
        ss.topography_state = None
        ss.meshfield = None
        ss.device_result = None
        st.rerun()

    st.subheader("Current recipe")
    if not ss.recipe_steps:
        st.info("No steps yet.")
    for i, s in enumerate(ss.recipe_steps):
        sc1, sc2 = st.columns([5, 1])
        if s["type"] == "deposit":
            _fmt_step = (f"deposit {s['thickness_um']*1000:.1f} nm "
                          f"{s['material']} (conformal)")
        elif s["type"] == "etch":
            _fmt_step = f"etch {s['depth_um']*1000:.1f} nm ({s['model']})"
            if s.get("x0") is not None:
                _fmt_step += f" window=[{s['x0']:.3f}, {s['x1']:.3f}]"
            if s["model"] == "directional" and s.get("sidewall_ratio") is not None:
                _fmt_step += f" sw={s['sidewall_ratio']:.2f}"
        else:
            _fmt_step = (f"oxidize {s['temperature_C']}°C "
                          f"{s['time_s']//60}min {s['ambient']}")
            if s.get("x0") is not None:
                _fmt_step += f" window=[{s['x0']:.3f}, {s['x1']:.3f}]"
                if s.get("bird_beak_length_um", 0):
                    _fmt_step += (f" beak="
                                    f"{s['bird_beak_length_um']*1000:.0f}nm")
        sc1.write(f"**{i+1}.** {_fmt_step}")
        if sc2.button("✕", key=f"del_step_{i}"):
            del ss.recipe_steps[i]
            ss.topography_state = None; ss.meshfield = None
            ss.device_result = None
            st.rerun()

    st.divider()
    grid_delta = st.number_input(
        "Level-set grid Δ [µm]", min_value=0.001, max_value=0.05,
        value=0.005, step=0.001, format="%.4f",
        help="Finer grid = sharper edges, slower simulation.")

    if st.button("▶ Run recipe", type="primary",
                 disabled=(not ss.recipe_steps and
                            not ss.structure._layers)):
        try:
            with st.spinner("Simulating topography…"):
                state = initial_state_from_structure(
                    ss.structure, grid_delta_um=float(grid_delta))
                for s in ss.recipe_steps:
                    if s["type"] == "deposit":
                        from opentcad.process.topography.recipe import Deposit
                        _apply_deposit(state, Deposit(
                            material=Material[s["material"]],
                            thickness_um=float(s["thickness_um"])))
                    elif s["type"] == "etch":
                        from opentcad.process.topography.recipe import Etch
                        _apply_etch(state, Etch(
                            depth_um=float(s["depth_um"]),
                            model=s["model"],
                            window_x_um=((float(s["x0"]), float(s["x1"]))
                                          if s.get("x0") is not None
                                          else None),
                            sidewall_ratio=float(
                                s.get("sidewall_ratio", 0.0)),
                        ))
                    else:
                        from opentcad.process.topography.recipe import Oxidize
                        _apply_oxidize(state, Oxidize(
                            temperature_C=float(s["temperature_C"]),
                            time_s=float(s["time_s"]),
                            ambient=s["ambient"],
                            window_x_um=((float(s["x0"]), float(s["x1"]))
                                          if s.get("x0") is not None
                                          else None),
                            bird_beak_length_um=float(
                                s.get("bird_beak_length_um", 0.0)),
                        ))
                ss.topography_state = state
                ss.meshfield = None; ss.device_result = None
            st.success(f"Ran {len(ss.recipe_steps)} step(s).")
        except Exception as e:
            st.error(f"Recipe failed: {e}")

with col2:
    st.subheader("Topography preview")
    state = ss.topography_state
    if state is None:
        st.info("Run the recipe to see the topography stack.")
    else:
        polylines = []
        for L in state.layers:
            nodes, _ = extract_surface_polyline(L.level_set)
            pts = np.asarray(nodes)
            if pts.size == 0:
                continue
            xs = pts[:, 0]; ys = pts[:, 1]
            xmin = state.bounds_um[0]; xmax = state.bounds_um[1]
            keep = (xs >= xmin - 1e-7) & (xs <= xmax + 1e-7)
            order = np.argsort(xs[keep])
            polylines.append((L.material,
                              xs[keep][order].copy(),
                              ys[keep][order].copy()))
        st.pyplot(plot_topography_polylines(
            state.bounds_um, polylines,
            title=f"After {len(ss.recipe_steps)} step(s)"),
                  clear_figure=True)


# ---------------------------------------------------------------------------
# 3. Device solver
# ---------------------------------------------------------------------------
st.header("3. Device")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("Meshing")
    mesh_source = st.radio(
        "Mesh source",
        ["From Structure (skip topography)", "From topography state"],
        index=0, horizontal=False)
    mesh_size_um = st.number_input(
        "Mesh size [µm]", min_value=0.005, max_value=0.5,
        step=0.005, format="%.4f", key="mesh_size_um")
    if st.button("Build MeshField", type="secondary"):
        try:
            with st.spinner("Meshing…"):
                if mesh_source.startswith("From topography"):
                    if ss.topography_state is None:
                        st.error("No topography state. Run the recipe first "
                                  "or switch to 'From Structure'.")
                        st.stop()
                    ss.meshfield = topography_to_meshfield(
                        ss.topography_state, mesh_size_um=float(mesh_size_um))
                else:
                    ss.meshfield = ss.structure.to_meshfield(
                        mesh_size_um=float(mesh_size_um))
                ss.device_result = None
            st.success(f"MeshField: {ss.meshfield.n_cells} triangles.")
        except Exception as e:
            st.error(f"Meshing failed: {e}")

    st.divider()
    st.subheader("Physics")
    mobility_choice = st.selectbox(
        "Mobility",
        ["Constant", "Klaassen",
         "Klaassen + Canali",
         "Klaassen + Canali + Lombardi"])
    recomb_srh = st.checkbox("SRH", value=True)
    recomb_aug = st.checkbox("Auger", value=False)
    recomb_rad = st.checkbox("Radiative", value=False)
    bgn_choice = st.selectbox("Bandgap narrowing", ["None", "Slotboom"])
    stat_choice = st.selectbox("Statistics", ["Boltzmann", "Fermi-Dirac"])

    st.divider()
    st.subheader("Analysis")
    analysis_kind = st.selectbox("Kind", ["iv_sweep", "cv_sweep"])
    contact_names = [c.name for c in ss.structure._contacts]
    if len(contact_names) < 2:
        st.warning("Need at least two named contacts on the structure.")
    else:
        def _default_idx(name: str, fallback: int) -> int:
            return contact_names.index(name) if name in contact_names else fallback

        cA = st.selectbox("Terminal A (swept)", contact_names,
                          index=_default_idx(ss.get("iv_terminal_a", contact_names[0]), 0),
                          help="Contact whose voltage is ramped from V start → V end.")
        cB = st.selectbox("Terminal B (reference, held at 0 V)", contact_names,
                          index=_default_idx(ss.get("iv_terminal_b", contact_names[-1]),
                                              len(contact_names) - 1),
                          help="Reference contact held at 0 V throughout the sweep.")
        cMeas = st.selectbox("Measure current at", contact_names,
                              index=_default_idx(ss.get("iv_measure", cA),
                                                  _default_idx(cA, 0)),
                              help="Which contact to read current from. "
                                   "For NMOS Id-Vgs: sweep gate, measure drain.")
        c1c, c2c, c3c = st.columns(3)
        v_start = c1c.number_input("V start [V]", step=0.05, key="iv_v_start")
        v_end   = c2c.number_input("V end [V]",   step=0.05, key="iv_v_end")
        v_step  = c3c.number_input("V step [V]",  min_value=0.001,
                                    step=0.005, format="%.3f", key="iv_v_step")

        # Hold-contact rows: any contact other than A, B, or measure can
        # be pre-biased to a fixed DC voltage before the sweep starts.
        # This is what makes MOSFET Id-Vgs at fixed Vds possible.
        other_contacts = [c for c in contact_names if c not in {cA, cB}]
        st.markdown("**Hold at fixed bias** (optional)")
        holds: dict[str, float] = {}
        if other_contacts:
            for name in other_contacts:
                default_v = 0.0
                if name == "drain":
                    default_v = float(ss.get("iv_hold_drain_v", 0.0))
                v = st.number_input(f"{name} [V]", value=default_v,
                                    step=0.01, format="%.3f",
                                    key=f"hold_{name}")
                if v != 0.0:
                    holds[name] = float(v)

        if st.button("▶ Run device solve", type="primary",
                     disabled=(ss.meshfield is None)):
            try:
                from opentcad.device.solver import DeviceSolver
                mobility = {
                    "Constant": ConstantMobility(),
                    "Klaassen": Klaassen(),
                    "Klaassen + Canali": Canali(base=Klaassen()),
                    "Klaassen + Canali + Lombardi":
                        Lombardi(base=Canali(base=Klaassen())),
                }[mobility_choice]
                recomb = []
                if recomb_srh: recomb.append(SRH())
                if recomb_aug: recomb.append(Auger())
                if recomb_rad: recomb.append(Radiative())
                bgn = Slotboom() if bgn_choice == "Slotboom" else NoBGN()
                stats = (FermiDirac() if stat_choice == "Fermi-Dirac"
                          else Boltzmann())
                cfg = PhysicsConfig(mobility=mobility, recombination=recomb,
                                    bgn=bgn, statistics=stats)

                # Load material params for every unique material in the
                # MeshField.
                mats_present = {Material(int(mid)) for mid in
                                np.unique(ss.meshfield.material_ids)}
                mat_params = {}
                for m in mats_present:
                    name = MATERIAL_NAMES.get(m, m.name)
                    try:
                        mat_params[name] = load_material(
                            "Si" if m == Material.SI else
                            "SiO2" if m == Material.SIO2 else name)
                    except Exception:
                        pass

                import devsim as ds
                # DEVSIM keeps a global device table. If the user clicks
                # Run twice, or if a prior solve raised mid-flight,
                # stale devices accumulate and can segfault on shutdown.
                # Clear them before creating a fresh solver.
                for stale in list(ds.get_device_list()):
                    try:
                        ds.delete_device(device=stale)
                    except Exception:
                        pass

                solver = None
                try:
                    with st.spinner("Running device solve…"):
                        solver = DeviceSolver(ss.meshfield, mat_params,
                                               physics=cfg)
                        if analysis_kind == "iv_sweep":
                            V, I = solver.iv_sweep(
                                cA, cB, v_start=float(v_start),
                                v_end=float(v_end), v_step=float(v_step),
                                hold_contacts=holds or None,
                                measure_contact=cMeas)
                            ss.device_result = {"kind": "iv", "V": V, "I": I,
                                                 "A": cA, "B": cB,
                                                 "measure": cMeas,
                                                 "holds": dict(holds)}
                        else:
                            V, C = solver.cv_sweep(
                                cA, cB, v_start=float(v_start),
                                v_end=float(v_end), v_step=float(v_step))
                            ss.device_result = {"kind": "cv", "V": V, "C": C,
                                                 "A": cA, "B": cB}
                    st.success("Done.")
                finally:
                    # Always drop the DEVSIM device, even on error. If
                    # we leave it in the global table, the atexit
                    # teardown can segfault on macOS.
                    if solver is not None:
                        try:
                            ds.delete_device(device=solver._device_name)
                        except Exception:
                            pass
            except Exception as e:
                st.error(f"Device solve failed: {e}")

with col2:
    if ss.meshfield is not None:
        st.subheader("MeshField")
        st.pyplot(plot_meshfield(ss.meshfield), clear_figure=True)
        # VTU download
        buf = io.BytesIO()
        ss.meshfield.grid.save("gui_export.vtu")
        with open("gui_export.vtu", "rb") as f:
            st.download_button("Download MeshField as VTU",
                                data=f.read(),
                                file_name=f"{ss.structure.name}.vtu",
                                mime="application/octet-stream")
    else:
        st.info("Build a MeshField to see the mesh and enable device solves.")

    result = ss.device_result
    if result is not None:
        st.subheader("Result")
        if result["kind"] == "iv":
            hold_bits = ", ".join(f"V_{n}={v*1000:.0f} mV"
                                  for n, v in (result.get("holds") or {}).items())
            hold_suffix = f"  |  {hold_bits}" if hold_bits else ""
            title = (f"I_{result.get('measure', result['A'])} vs "
                     f"V_{result['A']}  ({result['B']} = 0 V){hold_suffix}")
            fig = plot_iv(result["V"], result["I"], title=title)
        else:
            fig = plot_cv(result["V"], result["C"],
                           title=f"CV: {result['A']} → {result['B']}")
        st.pyplot(fig, clear_figure=True)
