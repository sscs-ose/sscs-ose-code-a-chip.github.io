"""Rev C additions to the full-system testbench (sim/tb/tb_trustedge_spi.sv), behind `TRUSTEDGE_REVC`.

The testbench's trustedge_top has no entropy source (ENABLE_INTERNAL_ENTROPY = 0), so two entropy words are forced
at the collector's inputs:
  1. with the internal K handed over but no nonce, a binding at counter 4 is refused (0x09);
  2. the same counter 4 then binds once a nonce is ready, so the refused binding consumed nothing (C4);
  3. the forced nonce equals rev B's epoch {"SF21", 4}, so the testbench's recorded SF2 tag still applies;
  4. the binding consumed the nonce (the register is empty again).
The randomness of the nonce, the sealing counter and the receive lock are tested in tb/tb_revc_session.sv.

usage: py revc_tb_edit.py <root dir>
"""
import pathlib
import sys

p = pathlib.Path(sys.argv[1]) / "sim/tb/tb_trustedge_spi.sv"
lines = p.read_bytes().decode("ascii").splitlines(keepends=True)
assert not any("TRUSTEDGE_REVC" in l for l in lines), "already edited"


def find(text, start=0):
    for i in range(start, len(lines)):
        if text in lines[i]:
            return i
    raise SystemExit(f"anchor not found: {text!r}")


# after the K handoff is forced and before the successful binding at counter 4
i = find("force dut.c4_receiver_shared_secret =")
i = find(";", i + 1)                       # end of that force statement
block = """`ifdef TRUSTEDGE_REVC
        // Rev C: no epoch nonce yet, so the binding is refused and counter 4 stays unused
        spi_xfer_hsm_ext(8'h01, 8'h12, 8'h00, 32'd4, 8'd2,
                         {8'd2, 8'd3, 240'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h09 || dut.u_hsm_shell.transaction_counter_valid &&
            dut.u_hsm_shell.last_transaction_counter >= 32'd4) begin
            errors = errors + 1;
            $display("  FAIL revc-bind-without-nonce data=%064h", hsm_ext_data);
        end else
            $display("  PASS revc-bind-without-nonce refused, counter not consumed");
        // two entropy words through the real collector (the DRBG is idle): nonce = {"SF21", 4}
        force dut.entropy_ready = 1'b1;
        force dut.entropy_unhealthy = 1'b0;
        force dut.entropy_word_internal = 32'h53463231;
        force dut.entropy_word_valid = 1'b1;
        @(posedge clk); #1;
        force dut.entropy_word_internal = 32'd4;
        @(posedge clk); #1;
        force dut.entropy_word_valid = 1'b0;
        @(posedge clk); #1;
        if (dut.revc_nonce_words !== 2'd2 || dut.revc_epoch_nonce !== {32'h53463231, 32'd4}) begin
            errors = errors + 1;
            $display("  FAIL revc-nonce-collect words=%0d nonce=%016h", dut.revc_nonce_words, dut.revc_epoch_nonce);
        end
`endif
"""
lines[i + 1:i + 1] = [l + "\n" for l in block.rstrip("\n").split("\n")]

i = find("hsm_session_epoch = hsm_ext_data[135:72];")
block = """`ifdef TRUSTEDGE_REVC
        release dut.entropy_ready;
        release dut.entropy_unhealthy;
        release dut.entropy_word_internal;
        release dut.entropy_word_valid;
        if (dut.revc_nonce_words !== 2'd0) begin
            errors = errors + 1;
            $display("  FAIL revc-nonce-consumed words=%0d", dut.revc_nonce_words);
        end else
            $display("  PASS revc-bind with nonce at the same counter, nonce consumed");
`endif
"""
lines[i + 1:i + 1] = [l + "\n" for l in block.rstrip("\n").split("\n")]
p.write_bytes("".join(lines).encode("ascii"))
print("revc testbench edits applied")
