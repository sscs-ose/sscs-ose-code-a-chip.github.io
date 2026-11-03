### 6-bit: matched devices as drawn, before / after the end dummies

| pair | fingers | shortest diffusion, before -> after [um] | longest [um] | identical on both sides |
|---|---|---|---|---|
| Mi1 / Mi2 | 2 | 0.88 -> 0.88 | 2.65 | yes |
| Mn1 / Mn2 | 1 | 0.29 -> 0.29 | 0.73 | yes |
| Mp1 / Mp2 | 1 | 0.29 -> 0.73 | 0.73 | yes |
| Mr1 / Mr2 | 1 | 0.29 -> 0.29 | 0.73 | yes |
| Mr3 / Mr4 | 1 | 0.29 -> 0.29 | 0.73 | yes |
| Mon1 / Mon2 | 1 | 0.29 -> 0.29 | 0.29 | yes |
| Mop1 / Mop2 | 2 | 0.29 -> 0.29 | 0.73 | yes |
| Md1 / Md2 | 1 | 0.29 -> 0.29 | 3.24 | yes |
| Mdl1 / Mdl2 | 1 | 0.29 -> 0.29 | 0.73 | yes |
| top switch Mttn | 3 -> 4 | 0.29 -> 0.88 | 2.65 | - |
| top switch Mttp | 5 -> 4 | 0.29 -> 0.88 | 2.65 | - |

### Current with the drawn diffusion lengths / with the stress off (sa = sb = 0)

| block | device | saturation, before | after | triode (switch on), before | after |
|---|---|---|---|---|---|
| strongarm | Md1 | 0.931 | 0.931 | 0.990 | 0.990 |
| strongarm | Md2 | 0.931 | 0.931 | 0.990 | 0.990 |
| strongarm | Mdl1 | 0.853 | 0.853 | 0.979 | 0.979 |
| strongarm | Mdl2 | 0.853 | 0.853 | 0.979 | 0.979 |
| strongarm | Mi1 | 1.015 | 1.015 | 1.002 | 1.002 |
| strongarm | Mi2 | 1.015 | 1.015 | 1.002 | 1.002 |
| strongarm | Mn1 | 0.853 | 0.853 | 0.979 | 0.979 |
| strongarm | Mn2 | 0.853 | 0.853 | 0.979 | 0.979 |
| strongarm | Mon1 | 0.761 | 0.761 | 0.965 | 0.965 |
| strongarm | Mon2 | 0.761 | 0.761 | 0.965 | 0.965 |
| strongarm | Mop1 | 1.354 | 1.354 | 1.061 | 1.061 |
| strongarm | Mop2 | 1.354 | 1.354 | 1.061 | 1.061 |
| strongarm | Mp1 | 1.690 | 1.119 | 1.103 | 1.020 |
| strongarm | Mp2 | 1.690 | 1.119 | 1.103 | 1.020 |
| strongarm | Mr1 | 1.354 | 1.354 | 1.061 | 1.061 |
| strongarm | Mr2 | 1.354 | 1.354 | 1.061 | 1.061 |
| strongarm | Mr3 | 1.354 | 1.354 | 1.061 | 1.061 |
| strongarm | Mr4 | 1.354 | 1.354 | 1.061 | 1.061 |
| strongarm | Mt | 0.942 | 0.942 | 0.992 | 0.992 |
| topsw | Mttn | 0.963 | 1.007 | 0.992 | 1.002 |
| topsw | Mttp | 1.258 | 0.894 | 1.015 | 0.991 |

CDAC unit-cell switches: stand-alone fingers, sa = sb = 0.29 um in every cell (unchanged).

### Comparator as drawn, no mismatch (offset resolution 10 uV)

| netlist | systematic offset [uV] | delay at +1 mV [ps] | delay at -1 mV [ps] |
|---|---|---|---|
| schematic | +5 | 384 | 386 |
| before, stress off | +5 | 444 | 447 |
| before, with LOD | +5 | 443 | 446 |
| after, stress off | +5 | 520 | 522 |
| after, with LOD | +5 | 475 | 477 |
