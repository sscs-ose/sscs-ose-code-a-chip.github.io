// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: src/files.f
// Type: File list, compile order (primitives, frame chain, core, top level, Tiny Tapeout wrapper)
// Author: Paul Vincent Bezzina
// Description:
// =============================================================================
src/primitives/frame_buffer.sv
src/primitives/host_fifo.sv
src/primitives/uart_rx.sv
src/primitives/uart_tx.sv
src/core/frame_chain/first_counter.sv
src/core/frame_chain/header_counter.sv
src/core/frame_chain/start_router.sv
src/core/frame_chain/main_counter.sv
src/core/frame_chain/end_counter.sv
src/core/frame_chain/watchdog.sv
src/core/frame_chain/branch_unit.sv
src/core/frame_chain/crc_unit.sv
src/core/frame_chain/frame_chain.sv
src/core/line_codec.sv
src/core/entry_dispatch.sv
src/core/control_unit.sv
src/core/return_path.sv
src/core/emulator_channel.sv
src/top/protocol_emulator.sv
src/top/tt_um_vertrex_star_proem.sv
