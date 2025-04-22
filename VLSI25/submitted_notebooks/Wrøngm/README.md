
# Wrøngm
This Repo is an attempt to automate the design of Analog Circuits especially Dynamic amplifiers

## Team

| Name | Qualification | IEEE Member | SSCS Member |
|:--|:--|:--:|:--:|
| Nithin P | B.Tech, VTU | No | No |
| Pramoda S R | B.Tech, VTU | No | No |
| Praveen Kumar Venkatacahala (Team Lead) | PhD, Oregon State University | Yes | Yes |
 
## Setup.exe
**Pramod pls take care of this%%
Clone the repo and make sure to pull to get latest scripts
```bash
git clone https://www.github.com/chennakeshavadasa/RAMPA.git
cd RAMPA
git pull origin main
```

Create virtual environment for better isolation
```bash
python -m venv venv
venv\Scripts\activate
```

Install the requirements
```bash
pip install -r requirements.txt
```

---

## Overview

This project processes differential amplifier simulation data to help select optimal transistor dimensions and operating points based on a target swing, transconductance (`gm`) value and other analog design constraints.

---

## Key Steps

### 1. **Data Parsing and Preprocessing**

Simulation files contain measurements for different transistor widths across various lengths. The parser:

- Detects width headers and appends them to each corresponding row.
- Filters out alternate redundant values.
- Outputs clean, numeric DataFrames for each file.

```python
def get_data(file_path: str) -> pd.DataFrame:
    ...
    for line in file:
        entry = line.strip().split()
        if len(entry) == 24:
            current_width = float(entry[1])
            entry = entry[2:]
        entry.insert(0, current_width)
        filtered_entry = [val for i, val in enumerate(entry) if i < 3 or i % 2 == 0]
        new_data.append(filtered_entry)

    return pd.DataFrame(new_data, columns=columns).astype(float)
```

All parsed files are merged and exported to a single CSV:

```python
df = pd.concat(dfs, ignore_index=True)
df = df[cols]
df.to_csv('Combined_Data.csv', index=False)
```

---

### 2. **Filtering Data Based on Design Constraints**

To find viable transistor operating points:

- Limit gate voltage (`V(V1)`) to a specific design window.
- Ensure the source voltage (`V(S)`) is above 0.1V to keep the tail MOS in saturation.
- From each length group, select the row with the highest `V(D1)` for optimal output swing.

```python
filtered_df = df[(df["V(V1)"] >= V1_min) & (df["V(V1)"] <= V1_max)]
valid_data = filtered_df[filtered_df["V(S)"] >= 0.1]

best_per_length = (
    valid_data.groupby("Length", group_keys=False)
    .apply(lambda x: x.loc[x["V(D1)"].idxmax()])
)
```

---

### 3. **Selecting the Best Transistor Sizing**

Among the filtered candidates, the best one is chosen by minimizing the absolute difference between the target and actual gm:

```python
best_per_length["gm_diff"] = abs(best_per_length["gm"] - Gm1)
best_final_row = best_per_length.loc[best_per_length["gm_diff"].idxmin()].copy()
```

---

### 4. **Computing gm/ID Ratios**

The gm/ID ratio is a critical figure of merit for analog design, indicating efficiency of transconductance generation.

- **Input Pair**: Calculated from selected operating point.
- **PMOS Mirror**: Fixed value assumed from designer’s strategy.
- **NMOS Tail**: Derived from the selected `V(S)`.

```python
gm_id_ip_pair = best_final_row["gm"] / best_final_row["IDS"]
gm_id_P = 5  # Assumed for PMOS
gm_id_N = 2 / best_final_row["V(S)"]
```

---

### 5. **Result Summary**

The script prints the chosen transistor dimensions and gm/ID values in SI units:

```python
print(f"Input Pair: Width = {format_si(W_input, unit='m')}, Length = {format_si(L_input, unit='m')}")
print(f"gm/id of Input Pair: gm/id = {gm_id_ip_pair}")
print(f"PMOS Current Mirror: gm/id = {gm_id_P:.2f} (Choose Length ≥ 2µm)")
print(f"NMOS Tail Transistor: gm/id = {gm_id_N:.2f} (Choose Length ≥ 2µm)")
```
