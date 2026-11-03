# Documents

Every document is a PDF here, built from its LaTeX source in [latex/](latex/) by
`bash scripts/docs.sh` (all of them) or `bash scripts/docs.sh line_codec` (one).

| Document | Read it for |
| --- | --- |
| [protocol_emulator_design.pdf](protocol_emulator_design.pdf) | The design reference: every block, the host protocol, protocol recipes with exact bytes, the test list, implementation results, limits and files. Start here. |
| [protocol_emulator_isa.pdf](protocol_emulator_isa.pdf) | The instruction set (v0.7.1): every instruction and field, the return messages, example programs and the version history. |
| [standards_guide.pdf](standards_guide.pdf) | Tested receive and transmit programs for sixteen standards, from RS-485 to RC5 infrared, and what the host still has to do for each. |
| [line_codec.pdf](line_codec.pdf) | The line codec, signal by signal: tick sources, decoders, the transmit state machine, I2C conditions, the output stage. |
| [branch_unit.pdf](branch_unit.pdf) | The branch unit: how the two BRANCH rules decide, their timing, and what the frame chain does with the result. |
| [verification_report.pdf](verification_report.pdf) | The sign-off of v0.7.1: lint, synthesis, place and route at three corners, gate level, coverage, sigrok, formal, and the two bugs found. |
| [toolchain_guide.pdf](toolchain_guide.pdf) | How to run everything yourself, from first principles: YAML, the C++ and cocotb tests, lint, coverage, sigrok, formal proofs, the ASIC flow, timing, Tiny Tapeout and GitHub Actions. |
| [info.md](info.md) | The Tiny Tapeout datasheet page. |

| Folder or file | Content |
| --- | --- |
| `latex/` | The LaTeX source of every PDF |
| `images/` | `protocol_emulator_architecture.png` (the whole chip) and `layout_full.png` (the routed layout); more layout pictures are in [../gds/](../gds/README.md) |
| `diagram/` | `make_diagram.py`, which draws the architecture picture, and its fonts |
| `architecture_datasheet.png` | A smaller copy of the architecture picture for `info.md`; Tiny Tapeout needs it next to `info.md` and limits image size |
