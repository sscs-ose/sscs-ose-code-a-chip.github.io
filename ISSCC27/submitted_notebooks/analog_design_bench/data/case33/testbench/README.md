# Public development diagnostics

Run these files from this directory with `ngspice -b <file>`. They use the
declared nominal supply, temperature, interface, and electrical definitions.
They are diagnostics, not the complete hidden PVT or mismatch sweep.

- `tb_nominal.spi`: closed-loop 0.9 V differential rise/fall accuracy and
  settling.
- `tb_loop_nominal.spi`: return-ratio loop gain, unity crossing, phase margin,
  output common mode, and power against the 5 mW PVT limit.
- `tb_noise_nominal.spi`: closed-loop differential output noise from 10 Hz to
  10 GHz under the supplied SKY130 compact model.
- `tb_range_nominal.spi`: nominal 3 dB-compression differential output swing
  from the slope of one DC transfer sweep; the required minimum is 1.8 V.
- `tb_cmfb_nominal.spi`: common-mode static error and recovery after the
  specified 50 uA-per-output disturbance.
- `tb_mismatch_nominal.spi`: one fixed-seed local-mismatch common-mode, VDD,
  and VSS feedthrough diagnostic at 10 Hz. Final signoff uses the published
  20 fixed-seed sample set.

Use `closed_loop_differential_gain_db` from the nominal-TT
`tb_loop_nominal.spi` run as the common numerator. At 10 Hz, compute CMRR as
`closed_loop_differential_gain_db - mc_closed_cm_10_db`; compute PSRR+ and
PSRR- by replacing the second term with
`mc_closed_vdd_10_db` and `mc_closed_vss_10_db`, respectively.
