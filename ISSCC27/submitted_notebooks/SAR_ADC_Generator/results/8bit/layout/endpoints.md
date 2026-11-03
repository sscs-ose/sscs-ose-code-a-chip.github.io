| case | offset [LSB] | gain error [LSB] |
|---|---|---|
| schematic | -0.859 | -0.531 |
| unit-cell CDAC | -0.859 | -0.719 |
| full core from layout | -0.609 | -0.750 |
| unit-cell CDAC, top-plate to pg/ng coupling (4.28 fF) removed | -0.953 | -0.562 |

Transition levels from ramps of 32 points per LSB around the first and last transition (resolution 1/32 LSB).

Cause of the post-layout gain error: removing only the extracted top-plate-to-control-line (pg/ng) capacitors brings the gain back to the schematic's value within one 1/32-LSB step (build/diag/gainfix).
