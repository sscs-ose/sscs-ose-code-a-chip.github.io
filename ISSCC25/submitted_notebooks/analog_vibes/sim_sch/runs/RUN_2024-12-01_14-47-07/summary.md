
# CACE Summary for ota

**netlist source**: schematic

|      Parameter       |         Tool         |     Result      | Min Limit  |  Min Value   | Typ Target |  Typ Value   | Max Limit  |  Max Value   |  Status  |
| :------------------- | :------------------- | :-------------- | ---------: | -----------: | ---------: | -----------: | ---------: | -----------: | :------: |
| DC gain              | ngspice              | A0                   |             any |          ​ |          any |          ​ |          any |          ​ |  Cancel 🟧   |
| Unity Gain Frequency | ngspice              | UGF                  |             any |          ​ |          any |          ​ |          any |          ​ |  Cancel 🟧   |
| Phase Margin         | ngspice              | PM                   |             any |          ​ |          any |          ​ |          any |          ​ |  Cancel 🟧   |
| DC CMRR              | ngspice              | CMRR_DC              |             any |          ​ |          any |          ​ |          any |          ​ |  Cancel 🟧   |
| DC PSRR              | ngspice              | PSRR_DC              |             any |          ​ |          any |          ​ |          any |          ​ |  Cancel 🟧   |
| HD2 at 0.8V(p-p), 1kHz | ngspice              | HD2                  |             any |  32.874 dB |          any |  47.843 dB |          any |  65.088 dB |   Pass ✅    |
| HD3 at 0.8V(p-p), 1kHz | ngspice              | HD3                  |             any |  38.746 dB |          any |  53.906 dB |          any |  76.419 dB |   Pass ✅    |
| Noise:Vin(rms) (1kHz to 1MHz) | ngspice              | vin_noi_rms          |             any |          ​ |          any |          ​ |          any |          ​ |  Cancel 🟧   |
| Rise Slew Rate       | ngspice              | rise_slew            |             any |          ​ |          any |          ​ |          any |          ​ |   Skip 🟧    |
| Fall Slew Rate       | ngspice              | fall_slew            |             any |          ​ |          any |          ​ |          any |          ​ |   Skip 🟧    |
| Total Static Power   | ngspice              | power_tot            |             any |          ​ |          any |          ​ |          any |          ​ |   Skip 🟧    |
| Power - OTA Core     | ngspice              | power_ota_core       |             any |          ​ |          any |          ​ |          any |          ​ |   Skip 🟧    |
| Power - OTA Bias     | ngspice              | power_ota_bias       |             any |          ​ |          any |          ​ |          any |          ​ |   Skip 🟧    |

