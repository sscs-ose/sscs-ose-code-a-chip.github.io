"""TRUSTEDGE_T3_CRC_SERIAL: slow-corner timing of the SPI bridge.

The bridge builds a response and its CRC-16 in one clock cycle: up to 37 chained byte updates between the state registers
and ext_tx_buf (about 53 ns at the slow corner). With the define on, a task only writes the payload bytes and raises crc_go;
a serial engine then updates the CRC one byte per cycle from ext_tx_buf, writes the two CRC bytes (at ext_tx_len-2 and -1)
and raises ext_tx_load. The response reaches the frame layer len+1 cycles later; its bytes and its CRC are unchanged.
SPDX-License-Identifier: Apache-2.0
"""
import re


def edit_bridge(s: str) -> str:
    tasks, n = re.subn(r"            crc_acc = 16'hFFFF;\n.*?ext_tx_buf\[\d+\]\s*= crc_acc\[7:0\];\n",
                       "`ifdef TRUSTEDGE_T3_CRC_SERIAL\n            crc_go <= 1'b1;\n`else\n\\g<0>`endif\n", s, flags=re.S)
    assert n == 7, n
    # a build task's CRC block is now optional; the caller's load strobe goes through the engine
    s = tasks
    k = s.count("ext_tx_load <= 1'b1;")
    assert k == 17, k
    s = s.replace("ext_tx_load <= 1'b1;", "`ifdef TRUSTEDGE_T3_CRC_SERIAL\ntx_req <= 1'b1;\n`else\next_tx_load <= 1'b1;\n`endif")
    s = s.replace("    reg [15:0] crc_acc;\n", """    reg [15:0] crc_acc;
`ifdef TRUSTEDGE_T3_CRC_SERIAL
    reg        crc_go, crc_busy, crc_fin, tx_req;
    reg [15:0] crc_s;
    reg [5:0]  crc_i;
`endif
""", 1)
    a = "            ext_tx_load  <= 1'b0;\n            ext_tx_len   <= 8'd0;\n"
    assert s.count(a) == 1
    s = s.replace(a, a + """`ifdef TRUSTEDGE_T3_CRC_SERIAL
            crc_go <= 1'b0; crc_busy <= 1'b0; crc_fin <= 1'b0; tx_req <= 1'b0; crc_s <= 16'd0; crc_i <= 6'd0;
`endif
""")
    b = "            ext_tx_load <= 1'b0;\n\n            if (frame_valid) begin\n"
    assert s.count(b) == 1
    s = s.replace(b, """            ext_tx_load <= 1'b0;
`ifdef TRUSTEDGE_T3_CRC_SERIAL
            tx_req <= 1'b0;
            if (tx_req && !crc_go) ext_tx_load <= 1'b1;      // a response without a CRC to compute passes straight through
            if (crc_busy) begin
                crc_s <= crc16_byte(crc_s, ext_tx_buf[crc_i]);
                crc_i <= crc_i + 6'd1;
                if ({2'b00, crc_i} + 8'd3 == ext_tx_len) begin crc_busy <= 1'b0; crc_fin <= 1'b1; end
            end
            if (crc_fin) begin
                ext_tx_buf[ext_tx_len - 8'd2] = crc_s[15:8];
                ext_tx_buf[ext_tx_len - 8'd1] = crc_s[7:0];
                ext_tx_load <= 1'b1;
                crc_fin <= 1'b0;
            end
            if (crc_go) begin crc_s <= 16'hFFFF; crc_i <= 6'd1; crc_busy <= 1'b1; crc_go <= 1'b0; end
`endif

            if (frame_valid) begin
""")
    return s
