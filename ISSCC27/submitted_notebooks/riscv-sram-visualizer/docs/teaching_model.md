# Manual SRAM teaching model

The student app uses `SRAMTeachingController` to construct one READ or WRITE
story. It executes the existing parser, processor, adapter, memory event engine
and 6T array once. It obtains address, row and column from `ADDRESS_DECODE`,
the access result from `SRAM_READ` or `SRAM_WRITE`, and before/after stored bits
from immutable array snapshots. No renderer recomputes address mapping or
performs a memory access. Previous, Next and Restart only change the index into
the recorded steps.

READ uses an explicit setup write of one at address 8, selects another row to
leave the target WL low, then executes `lw x5,8(x2)`.
WRITE uses `addi x1,x0,1` and `sw x1,8(x2)`. Both reach backend decoded cell
(0, 2). Both examples start with x2=0, so base plus offset gives address
0x08 (decimal 8).
The teaching model maps index 8 // 4 = 2, row 2 // 4 = 0, and column
2 % 4 = 2, the third column in zero-based indexing. Four-byte address slots
still represent separate single-bit cells, not 32-bit storage words.
Changing the operation constructs a fresh valid story. The guided
sequence contains processor request, architecture, decode, array, five 6T
schematic teaching states, five operation states, and summary. The read and
write branches never appear as consequences of the same instruction.

## 6T topology

M1/M2 are the PMOS/NMOS pull-up and pull-down of the left inverter, whose
output is Q. M3/M4 form the right inverter, whose output is Q_bar. Q drives
the gates of M3/M4, and Q_bar drives the gates of M1/M2. M5 connects BL to Q
and M6 connects BL_bar to Q_bar; both are NMOS access transistors gated by WL.
The pull-ups connect to VDD and pull-downs to GND. The SVG uses MOS channel
and insulated-gate symbols, PMOS gate bubbles, node dots and straight routing.
There is no storage capacitor.

## Educational periphery

`memory.periphery` records immutable binary phases. READ precharges both lines
to logical one with WL low, enables WL, represents a differential logical
outcome based on the actual stored bit, enables sensing, and presents the real
read result. WRITE enables a complementary driver, places value and complement
on BL/BL_bar, enables WL, then records the actual latch state after the backend
write. The `None` bit-line value before drive means unspecified, not zero.

The peripheral inset is a **schematic-style teaching abstraction**. Precharge
uses two PMOS pull-ups and a logical equalization path. Sensing uses a
differential NMOS input pair (S1/S2), diode-connected PMOS loads (P1/P2),
and a common NMOS tail switch (S3) controlled by SENSE_EN; DATA is taken at
one drain. Write driving uses two CMOS inverter branches (D1/D2 and D3/D4)
whose gates receive data and its complement. Driver enable is an educational
control state rather than a drawn transistor gate. This is not a complete
transistor netlist or PDK-verified sense amplifier; column mux, detailed
equalization, bias and output stage details remain unspecified.
Consequently it must not be used for circuit construction or electrical
prediction. Logical phases have no voltage magnitude or physical duration.
The legacy array leaves WL active after access, and the final phase records
WL=1 accordingly.
The existing waveform and 8T model remain in the advanced dashboard.

## Preview review

The SVG preview catalog is at [previews/teaching](previews/teaching/README.md).
Each export uses the same renderer as the notebook. Source processor artwork
is an original simple vector drawing; no uploaded reference image is copied.
