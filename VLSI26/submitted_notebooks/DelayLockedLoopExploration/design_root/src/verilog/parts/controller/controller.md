---

# Digital Delay Locked Loop (DLL) Controller

---

## Signal Flow

```
Phase Detector → Controller → Delay Line → Clock Output
```

* **Phase Detector (PD)**
   * generates `up/down` signals
   * tells **direction**
* **Controller**
  * integrates error into a control word
  * decides **how much to adjust**
* **DCDL**
  * adjusts delay accordingly
  *  applies **physical delay**


Together, they form a **closed feedback system** that converges to phase alignment.

---



## 1. Controller System Context

The goal of a Delay Locked Loop (DLL) is to align the phase of an output clock with a reference clock. It does so by adjusting the delay through a digitally controlled delay line (DCDL). The controller forms the bridge that translates phase error into delay control updates. 

The controller converts **phase error → delay adjustment**

#### Inputs

* `up` → output clock is **late** → increase delay
* `down` → output clock is **early** → decrease delay

#### Output

* `ctrl[N-1:0]` → sets delay of DCDL



```
CLK_IN -------> +-------------------+      up[1:0], down[1:0]       +-------------------+
                |   Phase Detector  | ----------------------------> |    Controller     |
CLK_OUT  <----- |                   |                               |   THIS SECTION    |
                +-------------------+                               +---------+---------+
                                                                          |
                                                                          | ctrl[N-1:0]   
                                                                          v
                                                                   +-----------------------+
                                                                   |   Delay Line (DCDL)   |
                                                                   |                       |
                                                                   +-----------+-----------+
                                                                          |
                                                                          v
                                                                       CLK_OUT

                               Simple Delay Locked Loop Diagram
                                                                        
                                                                        
```



#### Core Behavior (Step-by-Step)

At every clock cycle:

1. **Read phase detector output**

   * `(up, down) ∈ { (1,0), (0,1), (0,0), (1,1) }`

2. **Interpret phase error**

   * `(1,0)` → output clock is **late** → increase delay
   * `(0,1)` → output clock is **early** → decrease delay
   * `(0,0)` or `(1,1)` → no valid correction → hold

3. **Update control word**

   The controller behaves like a simple digital accumulator (a counter):

   ` ctrl[k+1] = ctrl[k] + up - down `

   Equivalent interpretation:

   * `+1` when `up = 1`
   * `-1` when `down = 1`
   * `0` when both are equal

4. **Apply limits (saturation)**

  ` 0 ≤ ctrl ≤ 2N−1 `

---

#### Intuition

* `up` pushes the delay **forward**
* `down` pulls the delay **backward**
* The controller **accumulates corrections over time** until phase alignment is reached

---

#### Mathematical View 

The controller behaves like a **digital accumulator**:

` ctrl[k+1] = ctrl[k] + K * e[k] `

Where:

* ` e[k] ∈ {-1, 0, +1} ` from `up/down`
* ` K ` = step size (loop gain)

---

## 2. Controller Design Space

#### Why Controller Design Matters

Controller behavior determines:

* **Lock Time**

  * How fast the system converges

* **Stability**

  * Avoid oscillations or overshoot

* **Jitter**

  * Small fluctuations near lock

---

##### Key Trade-Offs

Different controllers optimize different goals:

* Fast acquisition  ↔  Low jitter
* Simple logic      ↔  Adaptive behavior
* Robustness        ↔  Responsiveness

---
No single controller is optimal.

This project allows:

* Direct comparison of architectures
* Understanding trade-offs in practice
* Testing under identical conditions
* Building intuition for real DLL design

This project explores **5 controller types**:

### 🔹 1. Saturating Controller

* Fixed ±1 step
* Simple and robust

### 🔹 2. Filtered Controller

* Updates only after repeated requests
* Reduces noise / chatter

### 🔹 3. Acquire / Track Controller

* Large steps → fast lock
* Small steps → low jitter

### 🔹 4. Coarse / Fine Controller

* Split control word:

  * Coarse → large jumps
  * Fine → precision tuning

### 🔹 5. Variable-Step Controller

* Step size increases with repeated error
* Adaptive behavior

---


## 3. Control Theory Background

DLL controllers behave as **discrete-time integrators** driven by a bang-bang phase detector. It is essentially a counter that keeps adjusting until the clocks line up. The feedback loop helps with the self correcting behavior. The latency that it takes to converge depends heavily on the granularity and the features of the controller. The corrections are constantly accumulated until the error is small enough. 


### Key Concepts

---

#### • Binary phase error (`up/down`)

* Only the **direction** of error matters, not the amount
* Implemented using a **bang-bang phase detector**

```id="a1"
Late  → up = 1 → increase delay
Early → down = 1 → decrease delay
```

---

#### • Loop gain (set by step size)

* **Step size** = how big each correction is
* **Loop gain** = how strongly the system reacts to error

> “If the clock is wrong, how big of a correction do we make?”

* Large step size:

  * Faster correction
  * More overshoot / jitter

* Small step size:

  * Slower correction
  * Smoother behavior

```id="a2"
High gain:   32 → 36 → 40 → overshoot
Low gain:    32 → 33 → 34 → smooth approach
```

---

#### • Digital (Quantized) control

* Everything is **digital**
* `ctrl` changes in **discrete steps** (no continuous values)
* Updates happen **once per clock cycle**

```id="a3"
ctrl: 32 → 33 → 34 → 35   (step-by-step)
```

---

#### • Limit cycles (steady-state oscillation)

* The system **never becomes perfectly still**
* Near lock, it keeps correcting back and forth

```id="a4"
ctrl: 32 ↔ 33 ↔ 32 ↔ 33
```

* These small oscillations appear as **jitter**

---

#### • Stability depends on update behavior

* Large / frequent updates:

  * Fast response
  * More oscillation

* Small / infrequent updates:

  * Slower response
  * More stable

```id="a5"
Fast:   big jumps → oscillation
Slow:   small steps → stable
```

---



## 4. Controller Design Space

Different controller architectures trade off:

* Speed vs stability
* Resolution vs complexity
* Noise immunity vs responsiveness

### Categories

* Fixed-step (baseline)
* Filtered (noise suppression)
* Multi-mode (coarse/fine or acquire/track)
* Adaptive (variable step)

---

## 5. Controller Implementations

This project implements five controller architectures:

#### Internal Controller Architecture (Generic)

```
           +-----------------------+
UP  -----> |                       |
DOWN ----> |   Control Logic       | ---> ctrl[N-1:0]
           | (state / arithmetic)  |
CLK ------>|                       |
RST ------>|                       |
           +-----------------------+
```


### Conceptual Waveform

```
clk_in:   ─┐ ─┐ ─┐ ─┐ ─┐ ─┐ ─┐
           └─┘ └─┘ └─┘ └─┘ └─┘

up:        1   1   1   0   0
down:      0   0   0   1   1

ctrl:     32  33  34  34  33  32
```

---

### 5.1 Saturating Up/Down Controller

**Baseline implementation**


```
          +------------------+
UP -----> |                  |
DOWN ---> |  +1 / -1 Logic   |
          |  (Adder/Sub)     |
          +--------+---------+
                   |
                   v
            +-------------+
            | Saturation  |
            |  Clamp      |
            +------+------+ 
                   |
                   v
                 ctrl
```

* ±1 step per cycle
* Hard saturation at bounds
* Simple and robust

✔ Industry baseline
✖ Slow convergence near lock



---

** Saturation Behavior **

```
ctrl:   ... 60 61 62 63 63 63 63
                 ↑  ↑
              saturates at MAX
```


---

### 5.2 Filtered Controller

```
UP -----> +-------------+         +------------------+
          | UP Counter  |-------> |                  |
          +-------------+         |                  |
                                  |   Update Logic   | ---> ctrl
DOWN ---> +-------------+         | (only on threshold)
          | DOWN Counter|-------> |                  |
          +-------------+         +------------------+
```


* Requires repeated requests before update
* Reduces jitter and chatter

✔ Stable near lock
✖ Slower response

** Filtered Controller Behavior **

```
up:        1 1 1 1    0
counter:   1 2 3 4 -> trigger
ctrl:     32      33
```

✔ Update only after threshold reached


---

### 5.3 Acquire / Track Controller

```
                +----------------------+
UP/DOWN ------> |   Step Selection     |
                | (Acquire / Track)    |
                +----------+-----------+
                           |
                           v
                     +-----------+
                     | Adder     |
                     | (+/- step)|
                     +-----+-----+
                           |
                           v
                         ctrl

          +------------------------------+
          | Quiet Counter (mode switch)  |
          +------------------------------+
```

* Dual-mode operation:

  * **Acquire**: large steps (fast lock)
  * **Track**: small steps (low jitter)

✔ Widely used in industry
✔ Balanced performance


Acquire → Track Transition

```
mode:     A   A   A   A   T   T   T
step:     4   4   4   4   1   1   1

ctrl:    32 36 40 44 45 46 47
```

✔ Large jumps → fine tuning


---

### 5.4 Coarse / Fine Controller


```
                 +-------------------+
UP/DOWN -------> |   Mode Select     |
                 | (Coarse / Fine)   |
                 +----+---------+----+
                      |         |
                      v         v
                +---------+  +---------+
                | Coarse  |  |  Fine   |
                | Counter |  | Counter |
                +----+----+  +----+----+
                     \          /
                      \        /
                       v      v
                    {coarse, fine}
                          |
                          v
                        ctrl
```


* Splits control word:

  * Coarse bits → large adjustments
  * Fine bits → precise tuning

✔ High resolution
✔ Efficient hardware scaling


** Coarse / Fine Behavior **

```
coarse:   3   4   5   5   5
fine:     0   0   0   1   2

ctrl:    24  32  40  41  42
```

✔ Two-stage resolution

---

### 5.5 Variable-Step Controller


```
UP/DOWN -----> +----------------------+
               | Direction Tracker    |
               +----------+-----------+
                          |
                          v
               +----------------------+
               | Step Size Generator  |
               | (based on history)   |
               +----------+-----------+
                          |
                          v
                    +-----------+
                    | Adder     |
                    | (+/- step)|
                    +-----+-----+
                          |
                          v
                        ctrl
```

* Step size adapts based on persistence of error
* Nonlinear control behavior

✔ Fast convergence
✖ Requires careful tuning

```
same_dir_count: 1 2 3 4 5 6
step size:      1 1 2 2 4 4

ctrl:          32 33 34 36 38 42
```

✔ Adaptive acceleration

---

## 6. Design Trade-Off Matrix

| Controller Type | Lock Speed | Jitter   | Complexity | Industry Use |
| --------------- | ---------- | -------- | ---------- | ------------ |
| Saturating      | Low        | Medium   | Low        | Common       |
| Filtered        | Low        | Low      | Medium     | Moderate     |
| Acquire/Track   | High       | Low      | Medium     | Very Common  |
| Coarse/Fine     | High       | Very Low | High       | Very Common  |
| Variable-Step   | Very High  | Medium   | High       | Specialized  |

---
## !!!!!! TODO: ADD SOME NUMBERS AND DIAGRAMS HERE TO SHOW CONVERGENCE  !!!!!!!!!!

## 7. Design, Tuning & Practical Considerations

Designing a DLL controller requires careful tuning of parameters that directly impact **lock speed, stability, and jitter**. Because the system is fully digital and operates with discrete updates, small parameter changes can significantly affect loop behavior.

---

### 🔷 Key Parameters

* **`CTRL_BITS` (Resolution)**

  * Determines the number of discrete delay steps:
    ` Range = [0, 2^N - 1] `
  * More bits → finer delay control → lower jitter
  * Fewer bits → faster convergence but coarser resolution

---

* **`INIT_CTRL` (Startup Bias)**

  * Initial value of the control word after reset
  * Ideally chosen near the expected lock point
  * Poor choice → longer lock time or saturation at startup

---

* **Step Size (Loop Gain)**

  * Determines how much `ctrl` changes per update
  * Large step:

    * Faster lock
    * Higher overshoot and jitter
   
  * Small step:

    * Slower lock
    * Smoother steady-state behavior

---

* **Thresholds (Mode Switching / Adaptive Logic)**

  * Used in:

    * Acquire/Track controllers
    * Variable-step controllers
      
  * Define when the controller:

    * switches modes
    * increases/decreases step size
      
  * Poor tuning → premature switching or instability

---

* **Filter Length (Filtered Controllers)**

  * Number of consecutive `up/down` signals required before update
  * Larger value:

    * Better noise immunity
    * Slower response
      
  * Smaller value:

    * Faster response
    * More sensitive to noise

---

## 8. Digital Effects, Non-Idealities & Stability

Because DLL controllers are fully digital, they exhibit behaviors that differ from ideal continuous systems.

---

### 🔷 Quantization Effects

* Control updates happen in **discrete steps**
* The system cannot settle exactly at the ideal point
* Result: small oscillations around lock

---

### 🔷 Limit Cycles (Steady-State Oscillation)

```id="limit"
ctrl: 32 ↔ 33 ↔ 32 ↔ 33
```

* The loop continuously toggles near the correct delay
* This appears as **jitter** in the output clock

---

### 🔷 Bang-Bang Control Behavior

* Phase detector only provides **direction**, not magnitude
* Leads to:

  * oscillatory behavior near lock
  * nonlinear loop dynamics

---

### 🔷 Metastability & Sampling Effects

* Phase detector decisions depend on clock sampling
* Near alignment:

  * signals may be ambiguous
  * incorrect `up/down` decisions can occur

---

### 🔷 Stability vs Update Dynamics

* Large / frequent updates:

  * Fast convergence
  * Increased oscillation

* Small / infrequent updates:

  * Slower convergence
  * Improved stability

---

## 9. Boundary Conditions & Saturation

Controllers must enforce strict limits to ensure safe operation:

---

### 🔷 Required Behaviors

* No overflow above maximum value
* No underflow below zero
* Proper clamping at boundaries
* Stable behavior when saturated

---

### 🔷 Edge Case Handling

* Recovery from `ctrl = 0` or `ctrl = MAX`
* No wrap-around (prevents instability)
* Consistent behavior under persistent `up` or `down`

---

## 10. Verification Strategy

A **unified testbench** is used to validate all controller implementations under consistent conditions.

---

### 🔷 Philosophy

* Behavior-based (not cycle-exact)
* Architecture-independent
* Focused on correctness and robustness

---

### 🔷 Core Behaviors Verified

* Reset initialization (`INIT_CTRL`)
* Monotonic response:

  * `up` → nondecreasing
  * `down` → nonincreasing
* Saturation at bounds
* Stability under idle conditions
* Recovery from extreme values
* Alternating input robustness

---

### 🔷 Example Guarantees

* No overflow or underflow
* No runaway behavior
* Correct response to persistent inputs
* Stable operation across all controller types

✔ Reusable across all designs

---

## 11. Timing & Implementation Considerations

---

### 🔷 Clocking

* Fully synchronous operation (`clk_in`)
* Updates occur **once per clock cycle**

---

### 🔷 Reset Behavior

* Asynchronous reset supported
* Initializes controller to `INIT_CTRL`

---

### 🔷 Latency

* One-cycle update latency:

  * phase error → control update → delay adjustment

---

### 🔷 Synthesizability

* All designs are:

  * RTL-compliant
  * Fully synthesizable
  * Scalable with parameterization

---

## 12. Integration with Delay Line (DCDL)

The controller directly drives the delay line via `ctrl[N-1:0]`.

---

### 🔷 Key Considerations

* **Control word → delay mapping**

  * Each increment corresponds to a delay step

* **Resolution matching**

  * `CTRL_BITS` must align with DCDL granularity

* **Dynamic range**

  * Coarse/fine architectures improve range and precision

---

## 13. Stability & Loop Behavior in Practice

---

### 🔷 Observed Behaviors

* High-gain (large step):

  * Fast lock
  * Overshoot and oscillation

* Low-gain (small step):

  * Slower lock
  * Reduced jitter

---

### 🔷 Bandwidth Intuition

* Step size effectively controls **loop bandwidth**
* Trade-off:

  * Fast response vs smooth steady-state

---

## 14. Controller Selection Guide

| Use Case        | Recommended Controller |
| --------------- | ---------------------- |
| Simple system   | Saturating             |
| Low jitter      | Filtered               |
| Balanced design | Acquire/Track          |
| High resolution | Coarse/Fine            |
| Fastest lock    | Variable-Step          |

---

## 15. Industry Practices

---

### 🔷 Common Architectures

* **Acquire + Track**

  * Standard in ASIC designs
  * Balances speed and stability

* **Coarse + Fine**

  * Used in high-resolution DLLs
  * Improves precision and range

---

### 🔷 Hybrid Designs

* Combine multiple techniques:

  * e.g., coarse + fine + filtered

---

### 🔷 Less Common

* Pure variable-step controllers

  * Typically research-oriented
  * Require careful tuning

---

## 16. Limitations & Failure Modes

---

### 🔷 Common Issues

* Limit-cycle oscillation near lock
* Slow convergence (filtered designs)
* Sensitivity to noisy phase detector
* Incorrect parameter tuning

---

## 17. Future Extensions

---

* Hybrid controllers (filtered + adaptive)
* Dynamic threshold tuning
* Calibration-assisted control

---





