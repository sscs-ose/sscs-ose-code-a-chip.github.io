### 4-bit: matched devices as drawn, before / after the end dummies

| pair | fingers | shortest diffusion, before -> after [um] | longest [um] | identical on both sides |
|---|---|---|---|---|
| Mi1 / Mi2 | 2 | 0.88 -> 0.88 | 2.65 | yes |
| Mn1 / Mn2 | 1 | 0.29 -> 0.29 | 0.73 | yes |
| Mp1 / Mp2 | 1 | 1.17 -> 1.61 | 1.95 | yes |
| Mr1 / Mr2 | 1 | 0.73 -> 0.73 | 2.83 | yes |
| Mr3 / Mr4 | 1 | 0.29 -> 0.29 | 3.27 | yes |
| Mon1 / Mon2 | 1 | 0.29 -> 0.29 | 0.29 | yes |
| Mop1 / Mop2 | 2 | 0.29 -> 0.29 | 3.27 | yes |
| Md1 / Md2 | 1 | 0.29 -> 0.29 | 3.24 | yes |
| Mdl1 / Mdl2 | 1 | 0.29 -> 0.29 | 0.73 | yes |
| top switch Mttn | 1 -> 1 | 0.29 -> 0.29 | 0.88 | - |
| top switch Mttp | 1 -> 1 | 0.29 -> 0.29 | 0.88 | - |

### Current with the drawn diffusion lengths / with the stress off (sa = sb = 0)

| block | device | saturation, before | after | triode (switch on), before | after |
|---|---|---|---|---|---|
| strongarm | Md1 | 0.932 | 0.932 | 0.990 | 0.990 |
| strongarm | Md2 | 0.932 | 0.932 | 0.990 | 0.990 |
| strongarm | Mdl1 | 0.854 | 0.854 | 0.979 | 0.979 |
| strongarm | Mdl2 | 0.854 | 0.854 | 0.979 | 0.979 |
| strongarm | Mi1 | 1.014 | 1.014 | 1.002 | 1.002 |
| strongarm | Mi2 | 1.014 | 1.014 | 1.002 | 1.002 |
| strongarm | Mn1 | 0.854 | 0.854 | 0.979 | 0.979 |
| strongarm | Mn2 | 0.854 | 0.854 | 0.979 | 0.979 |
| strongarm | Mon1 | 0.761 | 0.761 | 0.965 | 0.965 |
| strongarm | Mon2 | 0.761 | 0.761 | 0.965 | 0.965 |
| strongarm | Mop1 | 1.103 | 1.083 | 1.018 | 1.015 |
| strongarm | Mop2 | 1.103 | 1.083 | 1.018 | 1.015 |
| strongarm | Mp1 | 0.946 | 0.895 | 0.990 | 0.980 |
| strongarm | Mp2 | 0.946 | 0.895 | 0.990 | 0.980 |
| strongarm | Mr1 | 0.991 | 0.969 | 0.998 | 0.994 |
| strongarm | Mr2 | 0.991 | 0.969 | 0.998 | 0.994 |
| strongarm | Mr3 | 1.214 | 1.197 | 1.038 | 1.035 |
| strongarm | Mr4 | 1.214 | 1.197 | 1.038 | 1.035 |
| strongarm | Mt | 0.942 | 0.942 | 0.992 | 0.992 |
| topsw | Mttn | 0.915 | 0.950 | 0.981 | 0.989 |
| topsw | Mttp | 3.229 | 2.048 | 1.104 | 1.061 |

CDAC unit-cell switches: stand-alone fingers, sa = sb = 0.29 um in every cell (unchanged).

### Comparator as drawn, no mismatch (offset resolution 10 uV)

| netlist | systematic offset [uV] | delay at +1 mV [ps] | delay at -1 mV [ps] |
|---|---|---|---|
| schematic | +5 | 395 | 397 |
| before, stress off | +5 | 446 | 448 |
| before, with LOD | +5 | 418 | 420 |
| after, stress off | +5 | 522 | 525 |
| after, with LOD | +5 | 483 | 486 |
