
# Wrøngm
This Repo is an attempt to automate the design of Analog Circuits especially Dynamic amplifiers

## Team

| Name | Qualification | IEEE Member | SSCS Member |
|:--|:--|:--:|:--:|
| Nithin P | B.Tech, VTU | No | No |
| Pramoda S R | B.Tech, VTU | No | No |
| Praveen Venkatachala | PhD, Oregon State University | Yes | Yes |

- This work is Licensed under **Apache 2.0**

## Setup.exe
Install the requirements
```bash
pip install -r requirements.txt
```

---

## Overview

This project processes differential amplifier simulation data to help select optimal transistor dimensions and operating points based on a target swing, transconductance (`gm`) value and other analog design constraints.

---

## Key Steps

### 1. **Data Acquisition & Unzipping**
```python
gmid_file_id = '1Gd_mxW6A0DBHGzFmbQJ1NT2dvuKrFsCy'
gdown.download(f'https://drive.google.com/uc?id={gmid_file_id}', output_zip, quiet=False)
```
- Downloads a ZIP file from Google Drive containing pre-characterized transistor data for **gm/id design methodology**.
- The data is then unzipped into a local folder (`./gmid_Data`).

---

### 2. **Data Extraction & Processing**
```python
def get_data(data: list, key: str) -> pd.DataFrame:
    ...
```
- Parses raw data files for different transistor types (e.g., `LV_NMOS`, `HV_PMOS`).
- Constructs a DataFrame containing device characteristics like `gm`, `id`, `Vth`, `gds`, `Cgg`, `Cgs`, `Cgd`.

Additional derived metrics include:
- **gm/id**: Transconductance to current ratio (used for analog design).
- **gm/gds**: Transconductance to output conductance (amplifier gain).
- **ft**: Unity-gain frequency.

---

### 3. **Visualization with Plotly**
```python
plot_interactive(df, 'Vgs', 'gm/id', ...)
```
- Uses **Plotly** to plot various device performance metrics, making it easy to visually select the right device operating point.
- Interactive graphs cover:
  - `gm/id` vs `Vgs` and `Vov`
  - `gm/gds` vs `gm/id`
  - `id/W` vs `gm/id`
  - Frequency (`ft`) vs `gm/id`
  - Capacitance ratios: `Cgd/Cgg`, `Cgs/Cgg`

---

### 4. **Parameter Optimization**
```python
result = minimize(objective_function, x0, method='L-BFGS-B', bounds=bounds)
```
- Performs constrained optimization to find device settings that meet target values:
  - Target `gm/id = 15`
  - Target `gm/gds ≥ 120`
- Uses a **weighted error function** to prioritize `gm/gds` (since gain is more critical in analog design).
- Finds the closest actual datapoint to the optimized values and reports that.

---

###  **Output: Design Recommendation**
```python
print("Closest Matching Row:\n", closest_row[[...]])
```
- Final output prints the **best-fit device configuration** based on the user's design goals.
