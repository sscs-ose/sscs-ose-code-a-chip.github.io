
# CACE Summary for ota

**netlist source**: schematic

|      Parameter       |         Tool         |     Result      | Min Limit  |  Min Value   | Typ Target |  Typ Value   | Max Limit  |  Max Value   |  Status  |
| :------------------- | :------------------- | :-------------- | ---------: | -----------: | ---------: | -----------: | ---------: | -----------: | :------: |
| DC gain              | ngspice              | A0                   |             any |          ​ |          any |          ​ |          any |          ​ |  Cancel 🟧   |
| Unity Gain Frequency | ngspice              | UGF                  |             any |          ​ |          any |          ​ |          any |          ​ |  Cancel 🟧   |
| Phase Margin         | ngspice              | PM                   |             any |          ​ |          any |          ​ |          any |          ​ |  Cancel 🟧   |
| DC CMRR              | ngspice              | CMRR_DC              |             any |          ​ |          any |          ​ |          any |          ​ |  Cancel 🟧   |
| DC PSRR              | ngspice              | PSRR_DC              |             any |          ​ |          any |          ​ |          any |          ​ |  Cancel 🟧   |
| HD2 at 0.8V(p-p), 1kHz | ngspice              | HD2                  |             any |          ​ |          any |          ​ |          any |          ​ |  Cancel 🟧   |
| HD3 at 0.8V(p-p), 1kHz | ngspice              | HD3                  |             any |          ​ |          any |          ​ |          any |          ​ |  Cancel 🟧   |
| Noise:Vin(rms) (1kHz to 1MHz) | ngspice              | vin_noi_rms          |             any |          ​ |          any |          ​ |          any |          ​ |   Skip 🟧    |
| Rise Slew Rate       | ngspice              | rise_slew            |             any |          ​ |          any |          ​ |          any |          ​ |   Skip 🟧    |
| Fall Slew Rate       | ngspice              | fall_slew            |             any |          ​ |          any |          ​ |          any |          ​ |   Skip 🟧    |
| Total Static Power   | ngspice              | power_tot            |             any |          ​ |          any |          ​ |          any |          ​ |   Skip 🟧    |

