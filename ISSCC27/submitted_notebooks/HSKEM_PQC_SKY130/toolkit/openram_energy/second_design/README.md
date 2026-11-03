# Second design: an 8 x 32 OpenRAM macro that is not one of HSKEM's

The tool's criterion "runs on a design other than HSKEM" is shown on two small SKY130 macros generated with the same OpenRAM
(`openram_config.py`: 8-bit words, 32 words, one read/write port, netlist only). HSKEM's eight macro types are all 12 to 24
bits wide and 128 to 768 words deep.

Generation (OpenRAM ffb5074, about 2 s each):

```
OPENRAM_HOME=<openram>/compiler OPENRAM_TECH=<openram>/technology PDK_ROOT=<pdk root> \
A2_OPENRAM_WORD_SIZE=8 A2_OPENRAM_NUM_WORDS=32 A2_OPENRAM_VERIFY=0 [A2_OPENRAM_WORDS_PER_ROW=1] \
A2_OPENRAM_OUTPUT_NAME=<name> A2_OPENRAM_OUTPUT=<dir> python3 <openram>/sram_compiler.py -n openram_config.py
```

Measurement (typical corner, 40 ns clock, three writes and three reads, about 80 s each):

```
SRAM_ENERGY_DELAY=1 run_openram_energy.sh <work dir> <dir>/<name>.sp
```

| Macro | Words per row | Write (pJ) | Read (pJ) | Idle (pJ) | clk to dout (ns) | Reads correct |
|---|---|---|---|---|---|---|
| sky130_sram_1rw_8x32_wpr1 | 1 (`openram_8x32_wpr1.log`) | 10.8, 11.8, 11.5 | 9.1, 9.5, 9.3 | 2.1, 3.1 | 1.50 | 3 of 3 |
| sky130_sram_1rw_8x32 | OpenRAM's choice (`openram_8x32_auto.log`) | 13.7, 15.6, 15.0 | 13.5, 13.6, 13.4 | 2.1, 3.3 | 1.71 | 2 of 3 |

The second macro is a finding of the tool's read check, not a failure of the tool. Its first read returns 2 where 3 was
written: bit 0 of word 6 is lost. Reading that word three times (`SRAM_ENERGY_READS=repeat`,
`energy_8x32_auto_tt_repeat.json`) returns 2 every time, so the write is what fails. A tighter tolerance (reltol 1e-4)
and six idle cycles before the first write give the same result. Word 5 is written two cycles later, and the macro places
more than one word on a row, so the likely cause is that this write disturbs word 6. The macro without column multiplexing
stores and returns every word.
