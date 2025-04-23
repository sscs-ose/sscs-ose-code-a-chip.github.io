
# Wrøngm
This Repo is an attempt to automate the design of Analog Circuits especially Dynamic amplifiers

## Team

| Name | Qualification | IEEE Member | SSCS Member |
|:--|:--|:--:|:--:|
| Nithin P | B.Tech, VTU | No | No |
| Pramoda S R | B.Tech, VTU | No | No |
| Praveen Kumar Venkatacahala (Team Lead) | PhD, Oregon State University | Yes | Yes |

- This work is Licensed under **Apache 2.0**


<h2>Introduction</h2>

<p>
Dynamic amplifiers such as <b>Ring Amplifiers</b>, <b>Inverter-Based Amplifiers</b>, and <b>Zero-Crossing Detector Amplifiers</b> have emerged as popular alternatives to small-signal settling-based amplifiers.
</p>


<p>
Unlike conventional OTAs (Operational Transconductance Amplifiers), where settling occurs in the small-signal and Islew domain<b></b>, dynamic amplifiers demonstrate <b>multiple stages of settling</b>, including:
</p>

<ul>
  <li><b>RC Settling</b></li>
  <li><b>Large Signal Settling</b></li>
  <li><b>Small Signal Settling</b></li>
</ul>

<p>
These mechanisms make dynamic amplifiers well-suited for high-performance, fast-settling analog circuits.
</p>


<!-- Figures 1, 2, and 3 side by side with individual captions -->
<div style="display: flex; justify-content: space-around; align-items: center; margin-top: 20px;">
    <div style="text-align: center;">
        <!-- Make sure the correct file path for Inverter-Based Amplifier is used -->
        <img src="https://i.ibb.co/S4TT2hg0/Fig1.jpg" width="280" alt="Inverter-Based Amplifier">
        <div><b>Figure 1:</b> Inverter-Based Amplifier [2]</div>
    </div>
    <div style="text-align: center;">
        <!-- Use the correct image path for the Ring Amplifier -->
        <img src="https://i.ibb.co/6Rn5zDvL/Fig2.png" width="370" alt="Ring Amplifier">
        <div><b>Figure 2:</b> Ring Amplifier [2]</div>
    </div>
    <div style="text-align: center;">
        <!-- Use the provided path for Zero-Crossing Detector Amplifier -->
        <img src="https://i.ibb.co/qM53KSN4/Fig3.png" width="370" alt="Zero-Crossing Detector Amplifier">
        <div><b>Figure 3:</b> Zero-Crossing Detector Amplifier [3]</div>
    </div>
</div>

---

  <h3> Error Behavior</h3>
<p>
The dynamic behavior of amplifiers can be better understood by analyzing the <b>dynamic error over time</b>. Traditional OTAs exhibit a <b>single-pole dynamic error response</b>, resulting in a uniform exponential decay slope.
</p>

<p style="text-align: center;">
    <!-- Make sure the path to the image is correct -->
    <img src="https://i.ibb.co/Bpt8gvF/Fig4.png" width="45%" alt="Dynamic Error in Traditional OTA">
</p>

<p style="text-align: center;">
    <b>Figure 4:</b> Dynamic Error in Traditional OTA (Single Pole Response)
</p>

<p>
In contrast, <b>dynamic amplifiers</b> exhibit a mix of <b>non-linear (fast)</b> and <b>linear (slow)</b> settling phases. This results in a two-phase error decay:
</p>

<ul>
  <li><b>Fast decay</b> during the non-linear (large signal) settling phase</li>
  <li><b>Slow decay</b> during the linear (small signal) settling phase</li>
</ul>

<p>
This behavior allows dynamic amplifiers to reachfinal valuey quickly, followed bysmall signal stageg for precise settling.
</p>

<p style="text-align: center;">
  <img src="https://i.ibb.co/d0rP5pr0/Fig5.png" width="45%">
</p>

<p style="text-align: center;">
  <b>Figure 5:</b> Dynamic Error in Dynamic Amplifier (Two-Phase Settling Behavior)
</p>

<hr>

## Understanding Dynamic Amplifiers

Let us consider two widely known types of dynamic amplifier:

1. **Inverter-Based Amplifier**  

### Inverter-Based Amplifier (IBA)

<p style="text-align: center;">
    <img src="https://i.ibb.co/S4TT2hg0/Fig1.jpg" alt="IBA Schematic" width="450"/>
</p>

<p style="text-align: center;"><strong>Figure 6:</strong> Schematic of the Inverter-Based Amplifier (IBA).</p>

Figure 6. shows the transient characterisitics of the IBA, which illustrate the small-signal transconductance gm.  
For large signal positive step inputs, the amplifier exhibits a **non-linear, signal-dependent large-signal Gm**.

Initially, the load capacitor is charged with a **high current** (a function of the large-signal Gm), followed by a **small-signal current** as the signal settles.  
This initial **non-linear settling behavior** significantly improves the speed of the IBA.

In general dynamic amplifiers such as IBA and RAMP(Ring Amplifier) have a large signal and small signal settling with fast RC phase or fast gmC phase.
<p style="text-align: center;">
    <img src="https://i.ibb.co/zHGKxKKC/Fig7.png" alt="IBA Transient Response" width="450"/>
</p>

<p style="text-align: center;"><strong>Figure 7:</strong> Transient Response of the Inverter-Based Amplifier.</p>

<!--
### Ring Amplifiers
Figure 7 illustrates the schematic of the RAMP.

<p style="text-align: center;">
    <img src="https://i.ibb.co/vxSTsvtx/Fig8.png" alt="Ring Amplifier Schematic" width="500"/>
</p>

<p style="text-align: center;"><strong>Figure 7:</strong> Schematic of the Ring Amplifier (RAMP). </p>


- When a large step input is applied to the Ring Amplifier, the output undergoes different phases of settling:

---

#### 1. RC Settling Phase

During this phase:

- The **input of the third stage** experiences a **rail-to-rail swing**.
- This swing leads to a **large Vov** for the **third-stage PMOS**, causing an **impulse current** to be pushed into the load capacitor.
- In this region, **VGS** is relatively constant, while **VDS** is changing.
- The output current is primarily determined by the **Ron** of the PMOS transistor.

---

#### 2. Large-Signal Settling Phase

In this phase:

- As the feedback from the output reaches the gate(VGP) potential of the PMOS, **VGS** begins to change.
- Meanwhile, **VDS** has nearly settled to its final value.
- The output current now becomes a function of the **large-signal transconductance Gm** of the amplifier.

---

#### 3. Small-Signal Settling Phase

Finally:

- As the output voltage Vout approaches its final value Vout_final, the amplifier transitions into **small-signal operation**.
- This final phase completes the remaining portion of the settling behavior with small signal linearity.

---

<p style="text-align: center;">
    <img src="https://i.ibb.co/990HCnSz/Fig9.png" alt="Ring Amplifier Schematic" width="500"/>
</p>
<p style="text-align: center;"><strong>Figure 8:</strong> RAMP transient response[2].</p>

This multi-phase settling behavior highlights the **non-linear nature** of dynamic amplifiers and explains why small-signal models alone are insufficient to fully describe their performance.

-->
 
## Setup.exe
**Pramod pls take care of this. Just mention all the dependencies judges need to take care of and guidlines**
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
