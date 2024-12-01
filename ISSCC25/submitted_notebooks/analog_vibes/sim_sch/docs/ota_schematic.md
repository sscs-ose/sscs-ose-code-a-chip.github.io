
# CACE Summary for ota

**netlist source**: schematic

|      Parameter       |         Tool         |     Result      | Min Limit  |  Min Value   | Typ Target |  Typ Value   | Max Limit  |  Max Value   |  Status  |
| :------------------- | :------------------- | :-------------- | ---------: | -----------: | ---------: | -----------: | ---------: | -----------: | :------: |
| DC gain              | ngspice              | A0                   |             any |  40.062 dB |          any |  44.987 dB |          any |  52.226 dB |   Pass ✅    |
| Unity Gain Frequency | ngspice              | UGF                  |             any | 417097.000 Hz |          any | 826089.000 Hz |          any | 2059780.000 Hz |   Pass ✅    |
| Phase Margin         | ngspice              | PM                   |             any |   86.774 ° |          any |   89.349 ° |          any |   90.115 ° |   Pass ✅    |
| DC CMRR              | ngspice              | CMRR_DC              |             any | -84.205 dB |          any | -55.444 dB |          any | -41.906 dB |   Pass ✅    |
| DC PSRR              | ngspice              | PSRR_DC              |             any | -68.171 dB |          any | -51.774 dB |          any | -48.202 dB |   Pass ✅    |
| HD2 at 0.8V(p-p), 1kHz | ngspice              | HD2                  |             any |  32.874 dB |          any |  47.843 dB |          any |  65.088 dB |   Pass ✅    |
| HD3 at 0.8V(p-p), 1kHz | ngspice              | HD3                  |             any |  38.746 dB |          any |  53.906 dB |          any |  76.419 dB |   Pass ✅    |
| Noise:Vin(rms) (1kHz to 1MHz) | ngspice              | vin_noi_rms          |             any | 45.164 uVrms |          any | 57.088 uVrms |          any | 77.765 uVrms |   Pass ✅    |
| Rise Slew Rate       | ngspice              | rise_slew            |             any | 3.273 V/us |          any | 4.498 V/us |          any | 7.482 V/us |   Pass ✅    |
| Fall Slew Rate       | ngspice              | fall_slew            |             any | 2.147 V/us |          any | 3.240 V/us |          any | 5.228 V/us |   Pass ✅    |
| Total Static Power   | ngspice              | power_tot            |             any | 169.306 uW |          any | 183.448 uW |          any | 198.997 uW |   Pass ✅    |
| Power - OTA Core     | ngspice              | power_ota_core       |             any | 101.369 uW |          any | 111.447 uW |          any | 122.915 uW |   Pass ✅    |
| Power - OTA Bias     | ngspice              | power_ota_bias       |             any |  67.924 uW |          any |  72.003 uW |          any |  76.082 uW |   Pass ✅    |


## Plots
