### 8-bit: matched devices as drawn, before / after the end dummies

| pair | fingers | shortest diffusion, before -> after [um] | longest [um] | identical on both sides |
|---|---|---|---|---|
| Mi1 / Mi2 | 14 | 0.88 -> 0.88 | 16.81 | yes |
| Mn1 / Mn2 | 9 | 0.29 -> 0.73 | 4.25 | yes |
| Mp1 / Mp2 | 9 | 0.29 -> 0.73 | 4.25 | yes |
| Mr1 / Mr2 | 1 | 0.29 -> 0.29 | 0.73 | yes |
| Mr3 / Mr4 | 1 | 0.29 -> 0.29 | 0.73 | yes |
| Mon1 / Mon2 | 1 | 0.29 -> 0.29 | 0.29 | yes |
| Mop1 / Mop2 | 2 | 0.29 -> 0.29 | 0.73 | yes |
| Md1 / Md2 | 1 | 0.29 -> 0.29 | 17.40 | yes |
| Mdl1 / Mdl2 | 1 | 0.29 -> 0.29 | 4.69 | yes |
| top switch Mttn | 24 -> 24 | 0.29 -> 0.88 | 14.45 | - |
| top switch Mttp | 48 -> 24 | 0.29 -> 0.88 | 14.45 | - |

### Current with the drawn diffusion lengths / with the stress off (sa = sb = 0)

| block | device | saturation, before | after | triode (switch on), before | after |
|---|---|---|---|---|---|
| strongarm | Md1 | 0.943 | 0.943 | 0.991 | 0.991 |
| strongarm | Md2 | 0.943 | 0.943 | 0.991 | 0.991 |
| strongarm | Mdl1 | 0.918 | 0.920 | 0.988 | 0.988 |
| strongarm | Mdl2 | 0.918 | 0.920 | 0.988 | 0.988 |
| strongarm | Mi1 | 1.070 | 1.070 | 1.011 | 1.011 |
| strongarm | Mi2 | 1.070 | 1.070 | 1.011 | 1.011 |
| strongarm | Mn1 | 1.036 | 1.055 | 1.005 | 1.008 |
| strongarm | Mn2 | 1.036 | 1.055 | 1.005 | 1.008 |
| strongarm | Mon1 | 0.761 | 0.761 | 0.965 | 0.965 |
| strongarm | Mon2 | 0.761 | 0.761 | 0.965 | 0.965 |
| strongarm | Mop1 | 1.354 | 1.354 | 1.061 | 1.061 |
| strongarm | Mop2 | 1.354 | 1.354 | 1.061 | 1.061 |
| strongarm | Mp1 | 0.965 | 0.860 | 0.993 | 0.976 |
| strongarm | Mp2 | 0.965 | 0.860 | 0.993 | 0.976 |
| strongarm | Mr1 | 1.354 | 1.354 | 1.061 | 1.061 |
| strongarm | Mr2 | 1.354 | 1.354 | 1.061 | 1.061 |
| strongarm | Mr3 | 1.354 | 1.354 | 1.061 | 1.061 |
| strongarm | Mr4 | 1.354 | 1.354 | 1.061 | 1.061 |
| strongarm | Mt | 1.080 | 1.080 | 1.011 | 1.011 |
| topsw | Mttn | 1.029 | 1.035 | 1.006 | 1.008 |
| topsw | Mttp | 0.615 | 0.606 | 0.960 | 0.960 |

CDAC unit-cell switches: stand-alone fingers, sa = sb = 0.29 um in every cell (unchanged).

### Comparator as drawn, no mismatch (offset resolution 10 uV)

| netlist | systematic offset [uV] | delay at +1 mV [ps] | delay at -1 mV [ps] |
|---|---|---|---|
| schematic | +5 | 185 | 186 |
| before, stress off | +5 | 184 | 185 |
| before, with LOD | +5 | 161 | 161 |
| after, stress off | +5 | 195 | 196 |
| after, with LOD | +5 | 168 | 169 |
