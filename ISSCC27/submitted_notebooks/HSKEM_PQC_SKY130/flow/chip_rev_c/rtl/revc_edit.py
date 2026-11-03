"""Rev C edits of the HSKEM-2 chip root, every one behind `TRUSTEDGE_REVC` (with the define off the logic is rev B's).

C1a  fresh public epoch per binding: trustedge_top collects 64 bits from the health-gated entropy source while the
     DRBG is idle (so no word that becomes public ever seeds the DRBG); a binding takes this nonce as its epoch and
     is refused while no nonce is ready.
C1b  the send counter of FRAME_SEAL must advance by exactly one per sealed frame (1 after each binding).
C4   a refused binding no longer consumes its transaction counter; the grant/consume pulses follow the binding's own
     result (also when an HMAC is in flight); per-key receive counts (accepted, rejected) are returned with every
     secure frame, and RECV_FAIL_LIMIT rejected tags lock the receive path until the next binding or zeroisation.

usage: py revc_edit.py <root dir>      (edits rtl/hsm/hsm_shell.sv and rtl/trustedge_top.v in place)
"""
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])


class Src:
    def __init__(self, path):
        self.path = path
        self.lines = path.read_bytes().decode("ascii").splitlines(keepends=True)

    def find(self, text, start=0, exact=False):
        for i in range(start, len(self.lines)):
            s = self.lines[i].strip()
            if (s == text) if exact else (text in s):
                return i
        raise SystemExit(f"{self.path.name}: anchor not found after line {start + 1}: {text!r}")

    def count(self, text):
        return sum(text in l for l in self.lines)

    def insert_after(self, i, block):
        self.lines[i + 1:i + 1] = [l + "\n" for l in block.split("\n")]

    def insert_before(self, i, block):
        self.lines[i:i] = [l + "\n" for l in block.split("\n")]

    def replace_line(self, i, block):
        self.lines[i:i + 1] = [l + "\n" for l in block.split("\n")]

    def save(self):
        self.path.write_text("".join(self.lines), encoding="ascii", newline="")


IFC, ELSE, END = "`ifdef TRUSTEDGE_REVC", "`else", "`endif"

# ---------------------------------------------------------------- hsm_shell.sv
h = Src(root / "rtl/hsm/hsm_shell.sv")
assert h.count("TRUSTEDGE_REVC") == 0, "already edited"

i = h.find("input  wire [255:0] hmac_rsp_digest", exact=True)
h.insert_after(i, f"""{IFC}
    ,
    // Rev C: a fresh public epoch for every binding, from entropy words that never reach the DRBG.
    input  wire         epoch_nonce_valid,
    input  wire [63:0]  epoch_nonce,
    output reg          epoch_nonce_consume
{END}""")

i = h.find("reg [63:0]  session_epoch;", exact=True)
h.insert_after(i, f"""{IFC}
    // Rev C: receive counts of the bound key (frames accepted and tags rejected) and a lock after RECV_FAIL_LIMIT
    // rejected tags, so that one binding allows only a bounded number of online tag guesses.
`ifdef REVC_FAIL_LIMIT
    localparam [15:0] RECV_FAIL_LIMIT = `REVC_FAIL_LIMIT;   // smaller limit for the bounded formal proof
`else
    localparam [15:0] RECV_FAIL_LIMIT = 16'd16;
`endif
    localparam [7:0]  RESULT_COUNTER_SKIPPED = 8'h0C;
    reg [15:0]  recv_ok_count;
    reg [15:0]  recv_fail_count;
    reg         recv_locked;
{END}""")

# the binding's own success, including the HMAC/provisioning interlock of the command decoder and the nonce
i = h.find("wire ext_bind_success = ext_cmd_valid && ext_header_valid &&", exact=True)
j = h.find("ext_mlkem_sender_key == ext_mlkem_receiver_key));", i)
h.insert_after(j, f"""{IFC}
    // Rev C: grant and consume only for a binding the decoder executes: no HMAC or provisioning in flight and a
    // fresh epoch nonce ready, exactly the conditions of the SUB_MLKEM_SESSION_BIND branch below.
    wire ext_bind_ok = ext_bind_success && epoch_nonce_valid &&
                       !(hmac_busy || hmac_pending != HMAC_NONE ||
                         prov_hmac_busy || prov_state != PROV_IDLE);
    wire recv_tag_ok = (hmac_digest[255:128] == hmac_supplied_tag);
{ELSE}
    wire ext_bind_ok = ext_bind_success;
{END}""")

i = h.find("mlkem_bind_consume_pulse   <= 1'b0;", exact=True)
h.insert_after(i, f"""{IFC}
            epoch_nonce_consume        <= 1'b0;
{END}""")

i = h.find("session_grant_pulse      <= hmac_attest_success || ext_bind_success;", exact=True)
h.replace_line(i, "            session_grant_pulse      <= hmac_attest_success || ext_bind_ok;")
i = h.find("mlkem_bind_consume_pulse <= ext_bind_success;", exact=True)
h.replace_line(i, f"""            mlkem_bind_consume_pulse <= ext_bind_ok;
{IFC}
            epoch_nonce_consume      <= ext_bind_ok;
{END}""")

# every place that closes the session also clears the receive counts and the lock
k, n_clear = 0, 0
while True:
    try:
        i = h.find("session_epoch", k)
    except SystemExit:
        break
    m = re.match(r"(\s*)session_epoch\s*<= 64'd0;", h.lines[i])
    if m:
        ind = m.group(1)
        h.insert_after(i, f"""{IFC}
{ind}recv_ok_count   <= 16'd0;
{ind}recv_fail_count <= 16'd0;
{ind}recv_locked     <= 1'b0;
{END}""")
        n_clear += 1
        k = i + 5
    else:
        k = i + 1
assert n_clear == 6, n_clear

# SUB_MLKEM_SESSION_BIND: the counter advances only on success; the epoch is the nonce
b = h.find("SUB_MLKEM_SESSION_BIND: begin", exact=True)
i = h.find("last_transaction_counter <= ext_counter;", b)
assert "transaction_counter_valid<= 1'b1;" in h.lines[i + 1]
h.insert_before(i, "`ifndef TRUSTEDGE_REVC")
h.insert_after(i + 2, END)
i = h.find("result_now = RESULT_POLICY_DENIED;", i)
h.insert_after(i, f"""{IFC}
                                end else if (!epoch_nonce_valid) begin
                                    // no fresh epoch yet: refuse, and keep the counter unused
                                    result_now = RESULT_POLICY_DENIED;
{END}""")
i = h.find("end else begin", i + 4, exact=True)
h.insert_after(i, f"""{IFC}
                                    last_transaction_counter <= ext_counter;
                                    transaction_counter_valid<= 1'b1;
                                    recv_ok_count   <= 16'd0;
                                    recv_fail_count <= 16'd0;
                                    recv_locked     <= 1'b0;
{END}""")
i = h.find("session_epoch        <= {32'h53463231, ext_counter};", i, exact=True)
h.replace_line(i, f"""{IFC}
                                    session_epoch        <= epoch_nonce;
{ELSE}
                                    session_epoch        <= {{32'h53463231, ext_counter}};
{END}""")
i = h.find("ext_resp_now[135:72] = {32'h53463231, ext_counter};", i, exact=True)
h.replace_line(i, f"""{IFC}
                                    ext_resp_now[135:72] = epoch_nonce;
{ELSE}
                                    ext_resp_now[135:72] = {{32'h53463231, ext_counter}};
{END}""")

# SUB_MLKEM_FRAME_SEAL: exactly one more than the last sealed counter
b = h.find("SUB_MLKEM_FRAME_SEAL: begin", exact=True)
i = h.find("ext_counter <= last_seal_counter) begin", b)
i = h.find("replay_seen <= 1'b1;", i)
h.insert_after(i, f"""{IFC}
                            end else if (ext_counter != (seal_counter_valid ?
                                                         last_seal_counter + 32'd1 : 32'd1)) begin
                                // Rev C: the send counter advances by exactly one per sealed frame
                                result_now = RESULT_COUNTER_SKIPPED;
{END}""")

# SUB_SECURE_FRAME: refuse while the receive path is locked
b = h.find("SUB_SECURE_FRAME: begin", exact=True)
i = h.find("result_now = RESULT_COUNTER_EXHAUSTED;", b)
h.insert_after(i, f"""{IFC}
                            end else if (recv_locked) begin
                                result_now = RESULT_LOCKED;
{END}""")

# HMAC_SECURE result: count, lock, and report the counts after this frame
b = h.find("end else if (hmac_pending == HMAC_SECURE) begin", exact=True)
i = h.find("result_now = RESULT_AUTH_FAILED;", b)
h.insert_after(i, f"""{IFC}
                        if (recv_fail_count != 16'hFFFF)
                            recv_fail_count <= recv_fail_count + 16'd1;
                        if (recv_fail_count + 16'd1 >= RECV_FAIL_LIMIT)
                            recv_locked     <= 1'b1;
{END}""")
i = h.find("ext_resp_now[199:136] = hmac_payload;", i)
h.insert_after(i, f"""{IFC}
                        if (recv_ok_count != 16'hFFFF)
                            recv_ok_count   <= recv_ok_count + 16'd1;
{END}""")
i = h.find("end", i + 4, exact=True)
h.insert_after(i, f"""{IFC}
                    ext_len_now = 8'd20;
                    ext_resp_now[135:120] = (recv_tag_ok && recv_ok_count != 16'hFFFF) ?
                                            recv_ok_count + 16'd1 : recv_ok_count;
                    ext_resp_now[119:104] = (!recv_tag_ok && recv_fail_count != 16'hFFFF) ?
                                            recv_fail_count + 16'd1 : recv_fail_count;
                    ext_resp_now[103:96]  = {{7'd0, recv_locked ||
                                             (!recv_tag_ok && recv_fail_count + 16'd1 >= RECV_FAIL_LIMIT)}};
{END}""")
h.save()

# -------------------------------------------------------------- trustedge_top.v
t = Src(root / "rtl/trustedge_top.v")
assert t.count("TRUSTEDGE_REVC") == 0, "already edited"
i = t.find("hsm_shell #(", exact=True)
t.insert_before(i, f"""{IFC}
    // Rev C: the epoch nonce of the next binding.  Two 32-bit words of the health-gated entropy source are taken
    // only while the DRBG is idle (it collects its words only while busy), so no word that becomes a public epoch
    // ever enters the DRBG; a binding consumes the nonce and the register refills.  Zeroisation clears it.
    reg  [63:0] revc_epoch_nonce;
    reg  [1:0]  revc_nonce_words;
    wire        revc_epoch_nonce_consume;
    wire        revc_epoch_nonce_valid = (revc_nonce_words == 2'd2);
    always @(posedge clk or negedge core_rst_n_security) begin
        if (!core_rst_n_security) begin
            revc_epoch_nonce <= 64'd0;
            revc_nonce_words <= 2'd0;
        end else if (revc_epoch_nonce_consume || hsm_zeroize_pulse) begin
            revc_epoch_nonce <= 64'd0;
            revc_nonce_words <= 2'd0;
        end else if (!revc_epoch_nonce_valid && !c2_drbg_busy && entropy_word_valid &&
                     entropy_ready && !entropy_unhealthy) begin
            revc_epoch_nonce <= {{revc_epoch_nonce[31:0], entropy_word_internal}};
            revc_nonce_words <= revc_nonce_words + 2'd1;
        end
    end
{END}""")
i = t.find(".hmac_rsp_digest(security_hmac_digest)", i)
t.insert_after(i, f"""{IFC}
        ,
        .epoch_nonce_valid(revc_epoch_nonce_valid),
        .epoch_nonce(revc_epoch_nonce),
        .epoch_nonce_consume(revc_epoch_nonce_consume)
{END}""")
t.save()
print("revc edits applied:", h.count("TRUSTEDGE_REVC"), "blocks in hsm_shell.sv,",
      t.count("TRUSTEDGE_REVC"), "in trustedge_top.v")
