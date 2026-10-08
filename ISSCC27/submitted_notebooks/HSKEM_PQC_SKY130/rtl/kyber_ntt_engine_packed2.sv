// Packed-pair NTT engine, two lanes and two fused passes, for a single-port SRAM.
//
// Storage as in kyber_ntt_engine_packed: word w of one 24-bit x 128-word single-port SRAM holds the pair
// (a[2w], a[2w+1]). The partner of a[2w+h] is always a[2(w+L/2)+h], the same half of another word, and the
// twiddle of a butterfly depends on w only, so the two halves of a word pair form two independent butterfly
// streams with the same twiddle. This engine runs them side by side: one issue is a word butterfly, and two
// butterfly units (one per half) share the twiddle lookup. The register banks need no extra port, because
// both halves of a word are read and written together.
//
// With twice the compute rate, the SRAM port becomes the limit, so the layers are fused into two passes
// instead of three: forward {128,64,32} {16,8,4,2}, inverse {2,4,8,16} {32,64,128}. Each coefficient
// crosses the port twice per transform (512 accesses instead of 768). The four-layer pass works on groups
// of 16 words, the three-layer pass on groups of 8; two banks of 16 words work in ping-pong. As before, a
// pass starts loading only after the previous pass has been stored completely, and the inverse transform
// folds its scaling by 128^-1 = 3303 into the last layer (pre-scaled twiddle 1652 for the upper output,
// one extra "scale" issue for the lower one).
//
// External interface as kyber_ntt_engine_packed (16-bit data, one-cycle read latency, writes in pair
// order); we_pair writes a whole pair (wdata, wdata_odd) to word waddr[7:1] in one cycle, and rdata_pair
// returns the whole word addressed in the previous cycle.
//
// Stream mode (stream = 1 with start): the first pass takes its words from pair writes made while the
// transform runs, group by group and in slot order, instead of loading them; each arriving pair goes
// straight into its bank slot, so that pass only stores. For the inverse transform this is word order
// 0..127 (its first-pass groups are contiguous); for the forward transform group g (0..15) arrives as words
// g, g+64, g+32, g+96, g+16, g+80, g+48, g+112. A producer may thus start the transform before its data is
// complete and write one pair every second cycle. A slot is reused only after it has been stored; at that
// producer rate the store of a slot always precedes the next arrival in it (a simulation check reports any
// violation, and any word that arrives out of order).
//
// While a stream-mode transform runs, re = 1 reads word raddr[7:1] for an external user (rdata_pair in the
// next cycle) and takes the port in that cycle, ahead of a store. The decryption uses it to read u1-hat
// while its products stream into the inverse transform of the same store: the first pass stores a word
// only after the product that replaces it was computed from it. The SRAM model ntt_pair_sram comes from rtl/kyber_ntt_engine_packed.sv (or the macro binding).
// SPDX-License-Identifier: Apache-2.0

module kyber_ntt_engine_packed2 #(
    parameter bit EXTRA_STAGE = 1'b1          // 1: three-stage butterfly units (shorter clock period)
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire        inverse,
    output reg         busy,
    output reg         done,
    input  wire [7:0]  waddr,
    input  wire [15:0] wdata,
    input  wire        we,
    output wire [15:0] rdata,
    input  wire [7:0]  raddr,
    input  wire        we_pair,               // with we: write the pair (wdata, wdata_odd) at once
    input  wire [11:0] wdata_odd,
    output wire [23:0] rdata_pair,
    input  wire        stream,                // with start: the first pass arrives by pair writes
    input  wire        re                     // while busy (stream mode): read raddr for an external user
);
    localparam [12:0] Q13 = 13'd3329;
    localparam [4:0]  N_GROUPS = 5'd24;          // 16 groups of 8 words + 8 groups of 16 words

    // ------------------------------------------------------------- group sequence -> pass, group
    // forward: pass 0 (3 layers) groups 0..15, pass 1 (4 layers) groups 16..23
    // inverse: pass 0 (4 layers) groups 0..7,  pass 1 (3 layers + scaling) groups 8..23
    reg inv_q;

    function automatic pass_of(input [4:0] seq, input inv);
        pass_of = inv ? (seq >= 5'd8) : (seq >= 5'd16);
    endfunction
    function automatic [4:0] first_of(input p, input inv);
        first_of = !p ? 5'd0 : inv ? 5'd8 : 5'd16;
    endfunction
    // four-layer pass: forward pass 1, inverse pass 0
    function automatic quad_pass(input p, input inv);
        quad_pass = inv ? !p : p;
    endfunction
    // word distance of slot bit k in pass p (the word distance of layer k of the pass)
    function automatic [6:0] wdist(input p, input [1:0] k, input inv);
        if (!inv) wdist = p ? (7'd8 >> k) : (7'd64 >> k);         // {16,8,4,2} / {128,64,32}
        else      wdist = p ? (7'd16 << k) : (7'd1 << k);         // {32,64,128} / {2,4,8,16}
    endfunction
    // base word of group g of pass p: the group index fills the bit positions not used by the pass
    function automatic [6:0] base_of(input p, input [4:0] g, input inv);
        base_of = quad_pass(p, inv) ? {g[2:0], 4'b0000} : {3'b000, g[3:0]};
    endfunction
    function automatic [6:0] word_of(input p, input [4:0] g, input [3:0] s, input inv);
        word_of = base_of(p, g, inv) | (s[0] ? wdist(p, 2'd0, inv) : 7'd0)
                                     | (s[1] ? wdist(p, 2'd1, inv) : 7'd0)
                                     | (s[2] ? wdist(p, 2'd2, inv) : 7'd0)
                                     | (s[3] ? wdist(p, 2'd3, inv) : 7'd0);
    endfunction

    // ------------------------------------------------------------------- register banks
    reg [11:0] bank  [0:1][0:15][0:1];            // [bank][slot][half]
    reg        valid [0:1][0:15];                 // both halves of a slot move together
    reg        occ   [0:1][0:15];                 // a slot holds a word that is not yet stored
    reg        stream_q;

    // --------------------------------------------------------------------- SRAM port
    reg  [4:0]  load_seq, comp_seq, store_seq;  // next group to load / compute / store
    reg  [3:0]  load_slot, store_slot;
    reg  [4:0]  op;                             // word butterfly within the computing group
    reg         ld_pend;                        // a read issued last cycle lands in the bank now
    reg         ld_pend_bank;
    reg  [3:0]  ld_pend_slot;

    wire       lp = pass_of(load_seq, inv_q);
    wire       cp = pass_of(comp_seq, inv_q);
    wire       sp = pass_of(store_seq, inv_q);
    wire [4:0] l_words = quad_pass(lp, inv_q) ? 5'd16 : 5'd8;
    wire [4:0] s_words = quad_pass(sp, inv_q) ? 5'd16 : 5'd8;
    wire [4:0] l_group = load_seq  - first_of(lp, inv_q);
    wire [4:0] c_group = comp_seq  - first_of(cp, inv_q);
    wire [4:0] s_group = store_seq - first_of(sp, inv_q);
    wire       s_bank  = store_seq[0];
    wire       l_bank  = load_seq[0];
    wire       c_bank  = comp_seq[0];

    // a store sends the next slot of the oldest fully issued group once it is final; an external read
    // during a stream-mode transform has the port first
    wire ext_rd_busy = busy && stream_q && re;
    wire store_ok = busy && !ext_rd_busy && (store_seq < comp_seq) && valid[s_bank][store_slot];
    // a load needs its bank free (group seq-2 stored) and the previous pass stored completely; in stream
    // mode the first pass is not loaded but arrives by pair writes
    wire load_ok  = busy && !store_ok && !ext_rd_busy && (load_seq < N_GROUPS) && !(stream_q && !lp) &&
                    (store_seq + 5'd1 >= load_seq) && (store_seq >= first_of(lp, inv_q));
    wire s_arrive = busy && stream_q && !lp && we && we_pair && (load_seq < N_GROUPS);

    reg  [11:0] hold_lo_full;                   // external writes: the even coefficient of a pair
    reg         rd_half_q;

    wire        ext_wr  = !busy && we && (waddr[0] || we_pair);
    wire        sram_ce = store_ok || load_ok || ext_wr || (!busy && !we) || ext_rd_busy;
    wire        sram_we = store_ok || ext_wr;
    wire [6:0]  sram_addr = store_ok ? word_of(sp, s_group, store_slot, inv_q) :
                            load_ok  ? word_of(lp, l_group, load_slot, inv_q) :
                            ext_wr   ? waddr[7:1] : raddr[7:1];
    wire [23:0] sram_wdata = store_ok ? {bank[s_bank][store_slot][1], bank[s_bank][store_slot][0]}
                                      : we_pair ? {wdata_odd, wdata[11:0]} : {wdata[11:0], hold_lo_full};
    wire [23:0] sram_rdata;

    ntt_pair_sram u_sram (.clk(clk), .ce(sram_ce), .we(sram_we), .addr(sram_addr),
                          .wdata(sram_wdata), .rdata(sram_rdata));
    assign rdata = {4'd0, rd_half_q ? sram_rdata[23:12] : sram_rdata[11:0]};
    assign rdata_pair = sram_rdata;

    // ------------------------------------------------------------- operation decode
    wire       quad   = quad_pass(cp, inv_q);
    wire [4:0] n_ops  = quad ? 5'd31 : (inv_q ? 5'd15 : 5'd11);  // last operation index
    wire       is_scale = !quad && inv_q && (op >= 5'd12);
    wire [1:0] layer  = is_scale ? 2'd2 : quad ? op[4:3] : op[3:2];
    wire [2:0] pair_i = quad ? op[2:0] : {1'b0, op[1:0]};
    // the lower slot of the pair: the pair index with a zero inserted at the layer's bit position
    reg  [3:0] slot_a;
    always @* begin
        if (is_scale)  slot_a = {2'b00, op[1:0]};                  // words without the 64 bit
        else case (layer)
            2'd0:    slot_a = {pair_i, 1'b0};
            2'd1:    slot_a = {pair_i[2:1], 1'b0, pair_i[0]};
            2'd2:    slot_a = {pair_i[2], 1'b0, pair_i[1:0]};
            default: slot_a = {1'b0, pair_i};
        endcase
    end
    wire [3:0] slot_b = slot_a | (4'd1 << layer);
    wire [6:0] w_lo   = word_of(cp, c_group, slot_a, inv_q);
    // global layer: forward m = log2(128/L), inverse m = log2(L/2)
    wire [2:0] m_fwd  = cp ? (3'd3 + layer) : {1'b0, layer};
    wire [2:0] m_inv  = cp ? (3'd4 + layer) : {1'b0, layer};
    // zeta index: forward 128/L + (w >> log2 L); inverse 256/L - 1 - (w >> log2 L)
    wire [6:0] zidx_f = (7'd1 << m_fwd) + (w_lo >> (3'd7 - m_fwd));
    wire [6:0] zidx_i = (7'd1 << (3'd6 - m_inv)) - 7'd1 + (7'd1 << (3'd6 - m_inv)) - (w_lo >> (m_inv + 3'd1));
    wire [15:0] zeta_w = kyber_pkg::kyber_zeta(inv_q ? zidx_i : zidx_f);
    wire       last_inv_layer = inv_q && cp && (layer == 2'd2) && !is_scale;
    wire [11:0] zeta  = is_scale ? 12'd3303 : last_inv_layer ? 12'd1652 : zeta_w[11:0];

    wire comp_started = (load_seq > comp_seq) || ((load_seq == comp_seq) && (load_slot != 4'd0));
    wire issue = busy && (comp_seq < N_GROUPS) && comp_started &&
                 valid[c_bank][slot_a] && (is_scale || valid[c_bank][slot_b]);

    // ---------------------------------------------------------------- butterfly units, one per half
    reg         s1_v, s1_inv, s1_scale, s1_bank;
    reg  [3:0]  s1_sa, s1_sb;
    reg         s2_v, s2_inv, s2_scale, s2_bank;
    reg  [3:0]  s2_sa, s2_sb;
    wire        wb_v     = EXTRA_STAGE ? s2_v     : s1_v;
    wire        wb_inv   = EXTRA_STAGE ? s2_inv   : s1_inv;
    wire        wb_scale = EXTRA_STAGE ? s2_scale : s1_scale;
    wire        wb_bank  = EXTRA_STAGE ? s2_bank  : s1_bank;
    wire [3:0]  wb_sa    = EXTRA_STAGE ? s2_sa    : s1_sa;
    wire [3:0]  wb_sb    = EXTRA_STAGE ? s2_sb    : s1_sb;
    wire [11:0] opa    [0:1];
    wire [11:0] opb    [0:1];
    wire [11:0] sum_ab [0:1];
    wire [11:0] m_in   [0:1];
    wire [11:0] out_lo [0:1];
    wire [11:0] out_hi [0:1];
    reg  [11:0] s1_x   [0:1];
    reg  [23:0] s1_prod[0:1];
    reg  [11:0] s2_x   [0:1];
    reg  [11:0] s2_r   [0:1];
    wire [11:0] s1_r   [0:1];

    genvar gh;
    generate for (gh = 0; gh < 2; gh = gh + 1) begin : g_lane
        assign opa[gh] = bank[c_bank][slot_a][gh];
        assign opb[gh] = bank[c_bank][slot_b][gh];
        wire [12:0] sum_w  = {1'b0, opa[gh]} + opb[gh];
        assign sum_ab[gh]  = (sum_w >= Q13) ? (sum_w - Q13) : sum_w[11:0];
        wire [12:0] dif_w  = {1'b0, opb[gh]} + Q13 - opa[gh];
        wire [11:0] dif_ba = (dif_w >= Q13) ? (dif_w - Q13) : dif_w[11:0];
        assign m_in[gh]    = is_scale ? opa[gh] : inv_q ? dif_ba : opb[gh];
        barrett_reduce_1c u_red (.a(s1_prod[gh]), .r(s1_r[gh]));
        wire [11:0] wb_x   = EXTRA_STAGE ? s2_x[gh] : s1_x[gh];
        wire [11:0] wb_r   = EXTRA_STAGE ? s2_r[gh] : s1_r[gh];
        wire [12:0] f_sum_w = {1'b0, wb_x} + wb_r;
        wire [11:0] f_sum   = (f_sum_w >= Q13) ? (f_sum_w - Q13) : f_sum_w[11:0];
        wire [12:0] f_dif_w = {1'b0, wb_x} + Q13 - wb_r;
        wire [11:0] f_dif   = (f_dif_w >= Q13) ? (f_dif_w - Q13) : f_dif_w[11:0];
        assign out_lo[gh] = wb_scale ? wb_r : wb_inv ? wb_x : f_sum;
        assign out_hi[gh] = wb_inv ? wb_r : f_dif;
        always @(posedge clk) begin
            if (issue) begin
                s1_x[gh]    <= inv_q ? sum_ab[gh] : opa[gh];
                s1_prod[gh] <= m_in[gh] * zeta;
            end
            s2_x[gh] <= s1_x[gh]; s2_r[gh] <= s1_r[gh];
        end
    end endgenerate

    // ----------------------------------------------------------------------- control
    integer b, s, h;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0; done <= 1'b0; inv_q <= 1'b0;
            load_seq <= 5'd0; comp_seq <= 5'd0; store_seq <= 5'd0;
            load_slot <= 4'd0; store_slot <= 4'd0; op <= 5'd0;
            ld_pend <= 1'b0; ld_pend_bank <= 1'b0; ld_pend_slot <= 4'd0; stream_q <= 1'b0;
            s1_v <= 1'b0; s2_v <= 1'b0; hold_lo_full <= 12'd0; rd_half_q <= 1'b0;
            s1_inv <= 1'b0; s1_scale <= 1'b0; s1_bank <= 1'b0; s1_sa <= 4'd0; s1_sb <= 4'd0;
            s2_inv <= 1'b0; s2_scale <= 1'b0; s2_bank <= 1'b0; s2_sa <= 4'd0; s2_sb <= 4'd0;
            for (b = 0; b < 2; b = b + 1)
                for (s = 0; s < 16; s = s + 1) begin
                    valid[b][s] <= 1'b0; occ[b][s] <= 1'b0;
                    for (h = 0; h < 2; h = h + 1) bank[b][s][h] <= 12'd0;
                end
        end else begin
            done <= 1'b0;
            rd_half_q <= raddr[0];
            if (!busy && we && !waddr[0]) hold_lo_full <= wdata[11:0];

            if (!busy) begin
                if (start) begin
                    busy <= 1'b1; inv_q <= inverse; stream_q <= stream;
                    load_seq <= 5'd0; comp_seq <= 5'd0; store_seq <= 5'd0;
                    load_slot <= 4'd0; store_slot <= 4'd0; op <= 5'd0;
                end
            end else begin
                // ---- loads: the read issued last cycle lands in its bank
                if (ld_pend) begin
                    bank[ld_pend_bank][ld_pend_slot][0] <= sram_rdata[11:0];
                    bank[ld_pend_bank][ld_pend_slot][1] <= sram_rdata[23:12];
                    valid[ld_pend_bank][ld_pend_slot] <= 1'b1;
                    occ[ld_pend_bank][ld_pend_slot] <= 1'b1;
                end
                // ---- stream mode: an arriving pair takes the next slot of the first pass directly
                if (s_arrive) begin
                    bank[l_bank][load_slot][0] <= wdata[11:0];
                    bank[l_bank][load_slot][1] <= wdata_odd;
                    valid[l_bank][load_slot] <= 1'b1;
                    occ[l_bank][load_slot] <= 1'b1;
                    if ({1'b0, load_slot} == l_words - 5'd1) begin
                        load_slot <= 4'd0; load_seq <= load_seq + 5'd1;
                    end else
                        load_slot <= load_slot + 4'd1;
                end
                ld_pend <= load_ok;
                ld_pend_bank <= l_bank; ld_pend_slot <= load_slot;
                if (load_ok) begin
                    if ({1'b0, load_slot} == l_words - 5'd1) begin
                        load_slot <= 4'd0; load_seq <= load_seq + 5'd1;
                    end else
                        load_slot <= load_slot + 4'd1;
                end
                // ---- stores
                if (store_ok) begin
                    valid[s_bank][store_slot] <= 1'b0;
                    occ[s_bank][store_slot] <= 1'b0;
                    if ({1'b0, store_slot} == s_words - 5'd1) begin
                        store_slot <= 4'd0; store_seq <= store_seq + 5'd1;
                        if (store_seq == N_GROUPS - 5'd1) begin
                            busy <= 1'b0; done <= 1'b1;
                        end
                    end else
                        store_slot <= store_slot + 4'd1;
                end
                // ---- butterfly units: issue (both halves of one word butterfly)
                s1_v <= issue;
                if (issue) begin
                    valid[c_bank][slot_a] <= 1'b0;
                    if (!is_scale) valid[c_bank][slot_b] <= 1'b0;
                    s1_inv <= inv_q; s1_scale <= is_scale; s1_bank <= c_bank;
                    s1_sa <= slot_a; s1_sb <= slot_b;
                    if (op == n_ops) begin
                        op <= 5'd0; comp_seq <= comp_seq + 5'd1;
                    end else
                        op <= op + 5'd1;
                end
                // ---- optional third stage
                s2_v <= s1_v;
                s2_inv <= s1_inv; s2_scale <= s1_scale; s2_bank <= s1_bank;
                s2_sa <= s1_sa; s2_sb <= s1_sb;
                // ---- butterfly units: write back
                if (wb_v) begin
                    bank[wb_bank][wb_sa][0] <= out_lo[0];
                    bank[wb_bank][wb_sa][1] <= out_lo[1];
                    valid[wb_bank][wb_sa] <= 1'b1;
                    if (!wb_scale) begin
                        bank[wb_bank][wb_sb][0] <= out_hi[0];
                        bank[wb_bank][wb_sb][1] <= out_hi[1];
                        valid[wb_bank][wb_sb] <= 1'b1;
                    end
                end
            end
        end
    end
`ifndef SYNTHESIS
    // stream mode: a pair must arrive at the expected word and in a slot whose previous word is stored
    always @(posedge clk) if (rst_n && s_arrive) begin
        if (occ[l_bank][load_slot])
            $display("NTT_STREAM_VIOLATION t=%0t slot %0d of bank %0d not yet stored", $time, load_slot, l_bank);
        if (waddr[7:1] != word_of(lp, l_group, load_slot, inv_q))
            $display("NTT_STREAM_VIOLATION t=%0t word %0d arrived, %0d expected", $time, waddr[7:1],
                     word_of(lp, l_group, load_slot, inv_q));
    end
`endif
endmodule
