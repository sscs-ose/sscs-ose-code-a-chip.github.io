# Check the requested application before choosing a correction

A simulation can complete even when its circuit misses the required function. It can also fail to establish the prior state needed to exercise that function. Keep these outcomes separate.

| Declared history | Original POR | POR plus guard |
|---|---|---|
| Four benign 1.62 to 1.98 V supply cycles, TT/27 C | Preserves ordinary Q=1 write | Preserves ordinary Q=1 write |
| 1.35 V reset dip, TT/125 C | Prior Q=1 verified, reset-to-zero missed | Prior Q=1 verified, reset-to-zero missed |
| Benign 1.62 V trough, TT/-40 C | Cold release fails, prior Q=1 unestablished | Cold release fails, prior Q=1 unestablished |

The preserved cold setup failure cannot establish guard-specific storage failure. The hot reset miss is an exercised counterexample. Neither the original POR nor its guard meets both of these temperature requirements. The earlier finite 27 C/85 C successful histories remain evidence within their declared conditions.

After the normal pinned setup, use:

```bash
python reproduce_applicability.py
python applicability_consumer.py --history triangle
python applicability_consumer.py --history hot_shallow_reset --variant original
python applicability_consumer.py --history cold_storage
python applicability_consumer.py --kind window --corner fs --temp-C 27
```

The short reproduction command performs six new complete-circuit simulations and two fresh DC sweeps. A functional miss still exits normally if the simulation completed; an incomplete simulation exits with code 2. Raw decks, logs, source hashes and full-precision vectors remain in the new run directory. There is no saved-data substitute for failed fresh execution.

The whole post-write storage interval requires Q >= 1.44 V, reset-bar >= 0.8 times instantaneous DVDD, DVDD between 1.62 and 1.98 V and analog supply at least 3.135 V. Both a valid cold startup and a verified ordinary Q=1 write are prerequisites. The hot reset experiment uses the previous reset-to-zero contract instead. These are application and teaching assumptions, not upstream guarantees or characterized reset thresholds.

The isolated guard DC interface holds its POR input high and sweeps supply from 0.4 to 1.98 V. Five process corners and four listed temperatures were acquired in both directions. Every crossing is retained with a 1 mV bracket. Ten of twenty sampled conditions meet the two 1.35/1.62 V endpoint requirements; eight meet the additional sampled-band requirements. None of six resistor choices covers all three sampled TT temperatures. This is neither a yield estimate nor proof that another correction is impossible. Static DC results do not qualify complete POR/DFF action or hysteresis.

`python applicability_evidence.py` audits all 72 saved simulation records without SPICE. `python check_applicability.py` also checks corrupted-data fixtures, which are software tests rather than additional circuit evidence. These are optional saved studies. The main notebook explains their cold and hot limits beside the final controller choice. Its default execution makes six new latch simulations.

All added passives are ideal. The pinned schematic model defaults, zero diffusion/contact geometry and disabled gate-tunnelling selectors remain explicit. Source work is compared only for matched working applications, counting startup and every independent source. No energy ranking is assigned to the failed temperature pairs. Windows/Ubuntu agreement, when recorded in reproduction reports, does not establish independent-machine, silicon or physical reliability validation.
