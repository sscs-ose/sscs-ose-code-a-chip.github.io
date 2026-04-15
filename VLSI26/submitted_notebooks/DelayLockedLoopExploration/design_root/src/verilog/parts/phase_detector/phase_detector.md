
---

# 📘 Digital Phase Detector (DLL / PLL) TODO: FIX AI GENERATED RN

---

## Signal Flow

```
Phase Detector → Controller → Delay Line → Clock Output
```

* **Phase Detector (PD)**

  * compares `clk_in` and `clk_out`
  * generates `up/down`
  * tells **direction of error**

* **Controller**

  * integrates error into control word

* **DCDL**

  * applies **physical delay**

Together, they form a **closed feedback system** that converges to phase alignment.

---

## 1. Phase Detector System Context

The goal of a phase detector is to determine the **relative timing between two clocks**.

It converts:

> **phase difference → directional control signal**

---

### Inputs

* `clk_in` → reference clock
* `clk_out` → feedback clock

---

### Outputs

* `up` → reference leads → **speed up loop**
* `down` → feedback leads → **slow down loop**

---

```
CLK_IN -------> +-------------------+      up, down       +-------------------+
                |   Phase Detector  | ------------------> |    Controller     |
CLK_OUT  <----- |   THIS SECTION    |                     |                   |
                +-------------------+                     +---------+---------+
                                                                  |
                                                                  v
                                                           Delay Line (DCDL)
                                                                  |
                                                                  v
                                                               CLK_OUT
```

---

### Core Behavior (Step-by-Step)

1. Detect rising edges
2. Compare arrival time
3. Output direction

---

### Mathematical View

```
e[k] ∈ { -1, 0, +1 }
```

---

## 2. Phase Detector Design Space

---

### Trade-Offs

* Simplicity ↔ Accuracy
* Area ↔ Robustness
* Speed ↔ Stability

---

### Implemented Types

* Behavioral
* Edge-order
* Single FF
* PFD
* XOR

---

## 3. Control Theory Background

---

### Key Concepts

* Binary error (up/down)
* Bang-bang operation
* Quantized decisions
* Limit cycles → jitter

---

## 4. Phase Detector Behavior

---

```
clk_in:   ─┐ ─┐ ─┐
           └─┘ └─┘

clk_out:    ─┐ ─┐
             └─┘

up/down toggling near lock
```

---

## 5. Phase Detector Implementations

---

### Generic Architecture

```
            +----------------------+
CLK_IN  --->|                      |
CLK_OUT --->|   Phase Detection    | ---> up
RST    --->|                      | ---> down
            +----------------------+
```

---

## 5.1 Behavioral Timestamp Detector

* Uses `$time` to compare edges

---

### Circuit (Conceptual)

```
clk_in  ----> [ Time Capture ] ----\
                                   >---- [ Compare ] ---> up/down
clk_out ----> [ Time Capture ] ----/
```

---

### Behavior

```
if t_in > t_out → up
if t_out > t_in → down
```

---

### Notes

✔ Ideal
✖ Not synthesizable

---

## 5.2 Edge-Order Detector

* First edge wins

---

### Circuit

```
          +-------------------+
clk_in -->| Set UP latch      |
          |                   |----> up
clk_out ->| Reset UP latch    |
          +-------------------+

          +-------------------+
clk_out ->| Set DOWN latch    |
          |                   |----> down
clk_in -->| Reset DOWN latch  |
          +-------------------+
```

---

### Behavior

```
First edge sets output
Second edge clears it
```

---

### Notes

✔ Simple
✖ Race conditions

---

## 5.3 Single Flip-Flop Detector

* Samples feedback

---

### Circuit

```
             +--------+
clk_out ---->|   D    |
             |  FF    |----> Q
clk_in ----->|  CLK   |
             +--------+

Q → up/down logic
```

---

### Behavior

```
clk_out = 0 → up
clk_out = 1 → down
```

---

### Notes

✔ Very small
✖ Biased

---

## 5.4 Phase-Frequency Detector (PFD)

* Two flip-flops + reset

---

### Circuit

```
          +--------+         +--------+
clk_in -->|  D=1   |         |        |
          |  FF    |----+--->|        |
          |        |    |    |        |
          +--------+    |    |        |
                        |    |        |
                        v    v        |
                     +------------+   |
                     | AND (UP&DN)|---+
                     +------------+
                        |
                        v
                     reset

clk_out --> +--------+
            |  D=1   |
            |  FF    |
            +--------+

Outputs:
UP = Q1
DOWN = Q2
```

---

### Behavior

```
UP pulse width ∝ phase difference
DOWN pulse width ∝ phase difference
```

---

### Notes

✔ Industry standard
✔ Detects frequency

---

## 5.5 Sampled XOR Detector

* XOR + sampling

---

### Circuit

```
clk_in ----\
            XOR ----> [ DFF ] ---> decision → up/down
clk_out ---/            ^
                        |
                      clk_in
```

---

### Behavior

```
XOR = 1 → mismatch
Sample clk_out → decide direction
```

---

### Notes

✔ Simple
✖ Weak near lock

---

## 6. Design Trade-Off Matrix

| Detector   | Accuracy | Complexity | Freq Detect | Use      |
| ---------- | -------- | ---------- | ----------- | -------- |
| Behavioral | Ideal    | Low        | No          | Sim      |
| Edge-order | Medium   | Low        | No          | Rare     |
| Single FF  | Low      | Very Low   | No          | Basic    |
| PFD        | High     | Medium     | Yes         | Standard |
| XOR        | Medium   | Low        | No          | Limited  |

---

## 7. Mode Behavior & State

* Edge-order → latch-based
* PFD → FF + reset
* FF → sampled

---

## 8. Parameterization & Tuning

* Clock timing
* Sampling edges
* Reset logic

---

## 9. Non-Idealities

* Quantization
* Limit cycles
* Metastability

---

## 10. Boundary Conditions

* Simultaneous edges
* Near-equal timing
* Reset handling

---

## 11. Verification Strategy

* Reset behavior
* Direction correctness
* Stability

---

## 12. Timing Considerations

* Edge-triggered
* Async clocks
* Reset critical

---

## 13. Integration with Controller

```
PD → Controller → DCDL
```

---

## 14. Stability & Loop Behavior

* Weak PD → jitter
* Strong PD → stable

---

## 15. Selection Guide

| Use Case   | Detector   |
| ---------- | ---------- |
| Simulation | Behavioral |
| Simple     | FF         |
| Moderate   | Edge       |
| Production | PFD        |

---

## 16. Industry Practices

* PFD → standard
* Others → limited

---

## 17. Limitations

* Jitter
* Bias
* Metastability

---

## 18. Future Work

* Hybrid PDs
* Adaptive detection

---

## ✅ Summary

The phase detector determines:

> **which direction the loop should correct**

It is critical for:

* stability
* jitter
* correct lock

---
