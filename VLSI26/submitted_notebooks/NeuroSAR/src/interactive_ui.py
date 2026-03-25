"""
NeuroSAR interactive UI — ipywidgets-based sliders for real-time
exploration of the PINN surrogate in Jupyter notebooks.
"""

from typing import Dict, Optional

import numpy as np
import torch
import ipywidgets as widgets
from IPython.display import display, HTML

from src.config import DESIGN
from src.pinn_model import NeuroSARNet, predict_full_conversion
from src.physics import metastability_dwell, enob_proxy, walden_fom
from src.plotting import (
    plot_conversion_summary,
    plot_fom_heatmap,
)
from src.utils import to_tensor


# =========================================================================
# Slider definitions
# =========================================================================

def _make_sliders() -> Dict[str, widgets.FloatSlider]:
    """Create ipywidgets sliders for each design parameter."""
    D = DESIGN
    style = {"description_width": "140px"}
    layout = widgets.Layout(width="450px")

    sliders = {
        "vin": widgets.FloatSlider(
            value=0.9, min=D.vin_range[0], max=D.vin_range[1], step=0.01,
            description="V_in (V):", style=style, layout=layout,
            continuous_update=False,
        ),
        "cu": widgets.FloatLogSlider(
            value=10e-15, base=10, min=-15, max=-13, step=0.1,
            description="C_unit (F):", style=style, layout=layout,
            continuous_update=False,
        ),
        "cload": widgets.FloatLogSlider(
            value=100e-15, base=10, min=-14, max=-12, step=0.1,
            description="C_load (F):", style=style, layout=layout,
            continuous_update=False,
        ),
        "gm": widgets.FloatLogSlider(
            value=500e-6, base=10, min=-4.3, max=-2.7, step=0.05,
            description="g_m (S):", style=style, layout=layout,
            continuous_update=False,
        ),
        "tau": widgets.FloatLogSlider(
            value=100e-12, base=10, min=-11, max=-9.3, step=0.1,
            description="τ_regen (s):", style=style, layout=layout,
            continuous_update=False,
        ),
        "vos": widgets.FloatSlider(
            value=0.0, min=-10e-3, max=10e-3, step=0.5e-3,
            description="V_os (V):", style=style, layout=layout,
            continuous_update=False,
            readout_format=".1e",
        ),
        "temp": widgets.FloatSlider(
            value=300.0, min=250.0, max=400.0, step=5.0,
            description="Temp (K):", style=style, layout=layout,
            continuous_update=False,
        ),
        "fs": widgets.FloatLogSlider(
            value=50e6, base=10, min=6, max=8.3, step=0.1,
            description="f_s (Hz):", style=style, layout=layout,
            continuous_update=False,
        ),
    }
    return sliders


# =========================================================================
# Output display area
# =========================================================================

class InteractiveDashboard:
    """
    Full interactive dashboard for NeuroSAR exploration.

    Usage in a notebook cell:
        dashboard = InteractiveDashboard(model)
        dashboard.show()
    """

    def __init__(
        self,
        model: NeuroSARNet,
        device: Optional[torch.device] = None,
    ):
        self.model = model
        self.device = device or next(model.parameters()).device
        self.model.eval()

        self.sliders = _make_sliders()
        self.output = widgets.Output(layout=widgets.Layout(width="100%"))
        self.metrics_html = widgets.HTML(value="")

        # Observe slider changes
        for s in self.sliders.values():
            s.observe(self._on_change, names="value")

    def _get_params(self) -> torch.Tensor:
        """Build parameter tensor from current slider values."""
        s = self.sliders
        params = [
            s["vin"].value,
            1.8,  # vref fixed
            s["cu"].value,
            s["cload"].value,
            s["gm"].value,
            s["tau"].value,
            s["vos"].value,
            s["temp"].value,
            s["fs"].value,
        ]
        return to_tensor([params], device=self.device)

    @torch.no_grad()
    def _compute(self) -> Dict:
        """Run PINN inference and compute FoMs."""
        params = self._get_params()
        t_local = torch.linspace(0, 1, DESIGN.n_time_steps, device=self.device)
        result = predict_full_conversion(self.model, params, t_local, DESIGN.n_bits)

        # FoMs
        vdac = result["vdac"][0]
        residues = vdac - 0.9  # approx Vref/2
        gm = params[0, 4]
        cl = params[0, 3]
        t_meta = metastability_dwell(residues, gm.unsqueeze(0), cl.unsqueeze(0))
        max_meta = t_meta.max().item()

        energy = result["energy"][0].item()
        settling_err = torch.abs(result["vdiff"][0, -1, -1])
        enob_val = enob_proxy(settling_err.unsqueeze(0), DESIGN.n_bits).item()

        fs = params[0, 8]
        fom = walden_fom(
            to_tensor([energy], device=self.device),
            fs.unsqueeze(0),
            to_tensor([enob_val], device=self.device),
        ).item()

        return {
            "result": result,
            "energy": energy,
            "max_meta": max_meta,
            "enob": enob_val,
            "walden_fom": fom,
        }

    def _on_change(self, change=None):
        """Callback for slider updates."""
        self.update()

    def update(self):
        """Recompute and redraw everything."""
        comp = self._compute()
        result = comp["result"]

        # Metrics
        self.metrics_html.value = f"""
        <div style="background: #f8f9fa; padding: 12px; border-radius: 8px;
                    font-family: monospace; font-size: 14px; margin: 8px 0;">
            <b>Figures of Merit</b><br>
            Energy/conv: <b>{comp['energy']:.3e} J</b> &nbsp;|&nbsp;
            Max metastability: <b>{comp['max_meta']:.3e} s</b> &nbsp;|&nbsp;
            ENOB proxy: <b>{comp['enob']:.2f} bits</b> &nbsp;|&nbsp;
            Walden FoM: <b>{comp['walden_fom']:.3e} J/step</b>
        </div>
        """

        # Waveforms
        vdac  = result["vdac"][0].cpu().numpy()
        vdiff = result["vdiff"][0].cpu().numpy()
        vcomp = result["vcomp"][0].cpu().numpy()
        t_local = np.linspace(0, 1, DESIGN.n_time_steps)

        fig = plot_conversion_summary(vdac, vdiff, vcomp, t_local,
                                       title="PINN Predicted Waveforms")

        self.output.clear_output(wait=True)
        with self.output:
            fig.show()

    def show(self):
        """Display the interactive dashboard."""
        title = widgets.HTML(
            "<h2 style='color: #1f77b4; font-family: sans-serif;'>"
            "NeuroSAR Interactive Explorer</h2>"
            "<p style='color: #666;'>Adjust design parameters and observe "
            "real-time SAR ADC waveform predictions from the PINN surrogate.</p>"
        )

        slider_box = widgets.VBox(list(self.sliders.values()))
        controls = widgets.VBox([title, slider_box, self.metrics_html])
        layout = widgets.VBox([controls, self.output])

        display(layout)
        self.update()  # Initial render
