# NeuroSAR Model Card

## Model Description
Physics-informed neural network (PINN) surrogate for SAR ADC transient dynamics.

## Architecture
- Type: Multi-head MLP with Fourier feature encoding
- Parameters: 249,858
- Activation: tanh (smooth second derivatives for physics residuals)
- Output heads: vdac, vdiff(t), vcomp(t), energy

## Training Data
- Source: Synthetic transient generator (analytical physics models)
- Samples: 2,000
- Design space: 9 parameters (Vin, Vref, Cu, Cload, gm, τ, Vos, T, fs)

## Performance
- Best validation loss: 0.0000e+00
- Physics residuals embedded: KCL, charge conservation, comparator ODE

## Intended Use
- Educational exploration of SAR ADC design trade-offs
- Interactive design-space navigation via Jupyter notebooks
- Demonstration of physics-informed ML for circuit design

## Limitations
- Trained on analytical models, not transistor-level SPICE
- ENOB proxy is simplified (no full FFT-based SNDR)
- Comparator model is first-order (no noise, no kickback)

## License
Apache 2.0
