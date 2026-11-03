// Packed-pair, layer-fused NTT engine for a single-port SRAM.
//
// ML-KEM's NTT stops at len = 2, so bit 0 of a coefficient index is never a butterfly distance. The
// engine therefore stores the pair (a[2w], a[2w+1]) in word w of one 24-bit x 128-word single-port SRAM
// (12 bits per coefficient suffice, q < 2^12): in every layer the partner of a[2w+h] is a[2(w+L/2)+h],
// the same half of another word, so one port access moves two coefficients without conflict.
//
// Layers are fused in passes: a pass loads a group of words into a register bank, runs its layers there
// and stores the group back. Forward passes {128,64,32} {16,8} {4,2}; inverse passes {2,4} {8,16}
// {32,64,128}. Each coefficient crosses the SRAM port three times per transform (768 accesses instead of
// several thousand). Two banks of 8 words work in ping-pong: while one group computes, the other bank
// stores the previous group and loads the next. A pass starts loading only after the previous pass has
// been stored completely (a barrier that costs about ten cycles and removes any word-level tracking).
//
// One butterfly unit, pipelined: multiply | Barrett reduction (| add/subtract with EXTRA_STAGE),
// issuing one operation per cycle in a fixed order; a valid bit per buffered coefficient holds an
// operation until its operands are written back. The inverse transform folds its scaling by
// 128^-1 = 3303 into the last layer: the upper output uses the pre-scaled twiddle 1729 * 3303 = 1652,
// the lower output costs one extra "scale" issue.
//
// External interface as kyber_ntt_engine (16-bit data, one-cycle read latency). External writes are
// expected in pair order (index 2w, then 2w+1), as every user of the engine writes sequentially; the
// even coefficient is held until its partner arrives. The model golden/packed_ntt_model.py describes
// the same schedule cycle by cycle.
// SPDX-License-Identifier: Apache-2.0

module kyber_ntt_engine_packed #(
    parameter bit EXTRA_STAGE = 1'b1          // 1: three-stage butterfly unit (shorter clock period)
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
    input  wire [7:0]  raddr
);
    localparam [12:0] Q13 = 13'd3329;
    localparam [6:0]  N_GROUPS = 7'd80;          // 16 + 32 + 32 groups per transform

    // ------------------------------------------------------------- group sequence -> pass, group
    // forward: pass 0 (3 layers) groups 0..15, pass 1 groups 16..47, pass 2 groups 48..79
    // inverse: pass 0 groups 0..31, pass 1 groups 32..63, pass 2 (3 layers + scaling) groups 64..79
    reg inv_q;

    function automatic [1:0] pass_of(input [6:0] seq, input inv);
        if (!inv) pass_of = (seq < 7'd16) ? 2'd0 : (seq < 7'd48) ? 2'd1 : 2'd2;
        else      pass_of = (seq < 7'd32) ? 2'd0 : (seq < 7'd64) ? 2'd1 : 2'd2;
    endfunction
    function automatic [6:0] first_of(input [1:0] p, input inv);
        if (!inv) first_of = (p == 2'd0) ? 7'd0 : (p == 2'd1) ? 7'd16 : 7'd48;
        else      first_of = (p == 2'd0) ? 7'd0 : (p == 2'd1) ? 7'd32 : 7'd64;
    endfunction
    // three-layer pass: forward pass 0, inverse pass 2
    function automatic big_pass(input [1:0] p, input inv);
        big_pass = inv ? (p == 2'd2) : (p == 2'd0);
    endfunction
    // word distance of slot bit k in pass p (the word distance of layer k of the pass)
    function automatic [6:0] wdist(input [1:0] p, input [1:0] k, input inv);
        if (!inv) case (p)
            2'd0:    wdist = 7'd64 >> k;               // layers 128, 64, 32
            2'd1:    wdist = 7'd8  >> k;               // layers 16, 8
            default: wdist = 7'd2  >> k;               // layers 4, 2
        endcase else case (p)
            2'd0:    wdist = 7'd1  << k;               // layers 2, 4
            2'd1:    wdist = 7'd4  << k;               // layers 8, 16
            default: wdist = 7'd16 << k;               // layers 32, 64, 128
        endcase
    endfunction
    // base word of group g of pass p: the group index fills the bit positions not used by the pass
    function automatic [6:0] base_of(input [1:0] p, input [6:0] g, input inv);
        if (!inv) case (p)
            2'd0:    base_of = g;                                    // bits 6:4 are slot bits
            2'd1:    base_of = {g[4:2], 2'b00, g[1:0]};              // bits 3:2
            default: base_of = {g[4:0], 2'b00};                      // bits 1:0
        endcase else case (p)
            2'd0:    base_of = {g[4:0], 2'b00};
            2'd1:    base_of = {g[4:2], 2'b00, g[1:0]};
            default: base_of = g;
        endcase
    endfunction
    function automatic [6:0] word_of(input [1:0] p, input [6:0] g, input [2:0] s, input inv);
        word_of = base_of(p, g, inv) | (s[0] ? wdist(p, 2'd0, inv) : 7'd0)
                                     | (s[1] ? wdist(p, 2'd1, inv) : 7'd0)
                                     | (s[2] ? wdist(p, 2'd2, inv) : 7'd0);
    endfunction

    // ------------------------------------------------------------------- register banks
    reg [11:0] bank  [0:1][0:7][0:1];             // [bank][slot][half]
    reg        valid [0:1][0:7][0:1];

    // --------------------------------------------------------------------- SRAM port
    reg  [6:0]  load_seq, comp_seq, store_seq;  // next group to load / compute / store
    reg  [2:0]  load_slot, store_slot;
    reg  [4:0]  op;                             // operation within the computing group
    reg         ld_pend;                        // a read issued last cycle lands in the bank now
    reg         ld_pend_bank;
    reg  [2:0]  ld_pend_slot;

    wire [1:0] lp = pass_of(load_seq, inv_q);
    wire [1:0] cp = pass_of(comp_seq, inv_q);
    wire [1:0] sp = pass_of(store_seq, inv_q);
    wire [3:0] l_words = big_pass(lp, inv_q) ? 4'd8 : 4'd4;
    wire [3:0] s_words = big_pass(sp, inv_q) ? 4'd8 : 4'd4;
    wire [6:0] l_group = load_seq  - first_of(lp, inv_q);
    wire [6:0] c_group = comp_seq  - first_of(cp, inv_q);
    wire [6:0] s_group = store_seq - first_of(sp, inv_q);
    wire       s_bank  = store_seq[0];
    wire       l_bank  = load_seq[0];
    wire       c_bank  = comp_seq[0];

    // a store sends the next slot of the oldest fully issued group once both halves are final
    wire store_ok = busy && (store_seq < comp_seq) &&
                    valid[s_bank][store_slot][0] && valid[s_bank][store_slot][1];
    // a load needs its bank free (group seq-2 stored) and the previous pass stored completely
    wire load_ok  = busy && !store_ok && (load_seq < N_GROUPS) &&
                    (store_seq + 7'd1 >= load_seq) && (store_seq >= first_of(lp, inv_q));

    reg  [11:0] hold_lo_full;                   // external writes: the even coefficient of a pair
    reg         rd_half_q;

    wire        ext_wr  = !busy && we && waddr[0];
    wire        sram_ce = store_ok || load_ok || ext_wr || (!busy && !we);
    wire        sram_we = store_ok || ext_wr;
    wire [6:0]  sram_addr = store_ok ? word_of(sp, s_group, store_slot, inv_q) :
                            load_ok  ? word_of(lp, l_group, load_slot, inv_q) :
                            ext_wr   ? waddr[7:1] : raddr[7:1];
    wire [23:0] sram_wdata = store_ok ? {bank[s_bank][store_slot][1], bank[s_bank][store_slot][0]}
                                      : {wdata[11:0], hold_lo_full};
    wire [23:0] sram_rdata;

    ntt_pair_sram u_sram (.clk(clk), .ce(sram_ce), .we(sram_we), .addr(sram_addr),
                          .wdata(sram_wdata), .rdata(sram_rdata));
    assign rdata = {4'd0, rd_half_q ? sram_rdata[23:12] : sram_rdata[11:0]};

    // ------------------------------------------------------------- operation decode
    wire       big    = big_pass(cp, inv_q);
    wire [4:0] n_ops  = big ? (inv_q ? 5'd31 : 5'd23) : 5'd7;    // last operation index
    wire       is_scale = big && inv_q && (op >= 5'd24);
    wire [1:0] layer  = is_scale ? 2'd2 : big ? op[4:3] : {1'b0, op[2]};
    wire [1:0] pair_i = big ? op[2:1] : {1'b0, op[1]};
    wire       half   = op[0];
    // the lower slot of the pair: the pair index with a zero inserted at the layer's bit position
    reg  [2:0] slot_a;
    always @* begin
        if (is_scale)          slot_a = {1'b0, op[2:1]};           // words without the 64 bit
        else if (big) case (layer)
            2'd0:    slot_a = {pair_i, 1'b0};
            2'd1:    slot_a = {pair_i[1], 1'b0, pair_i[0]};
            default: slot_a = {1'b0, pair_i};
        endcase else case (layer)
            2'd0:    slot_a = {1'b0, pair_i[0], 1'b0};
            default: slot_a = {2'b00, pair_i[0]};
        endcase
    end
    wire [2:0] slot_b = slot_a | (3'd1 << layer);
    wire [6:0] w_lo   = word_of(cp, c_group, slot_a, inv_q);
    // global layer: forward m = log2(128/L), inverse m = log2(L/2)
    wire [2:0] m_fwd  = (cp == 2'd0) ? {1'b0, layer} : (cp == 2'd1) ? (3'd3 + layer) : (3'd5 + layer);
    wire [2:0] m_inv  = (cp == 2'd0) ? {1'b0, layer} : (cp == 2'd1) ? (3'd2 + layer) : (3'd4 + layer);
    // zeta index: forward 128/L + (w >> log2 L); inverse 256/L - 1 - (w >> log2 L)
    wire [6:0] zidx_f = (7'd1 << m_fwd) + (w_lo >> (3'd7 - m_fwd));
    wire [6:0] zidx_i = (7'd1 << (3'd6 - m_inv)) - 7'd1 + (7'd1 << (3'd6 - m_inv)) - (w_lo >> (m_inv + 3'd1));
    wire [15:0] zeta_w = kyber_pkg::kyber_zeta(inv_q ? zidx_i : zidx_f);
    wire       last_inv_layer = inv_q && (cp == 2'd2) && (layer == 2'd2) && !is_scale;
    wire [11:0] zeta  = is_scale ? 12'd3303 : last_inv_layer ? 12'd1652 : zeta_w[11:0];

    wire [11:0] opa = bank[c_bank][slot_a][half];
    wire [11:0] opb = bank[c_bank][slot_b][half];
    wire comp_started = (load_seq > comp_seq) || ((load_seq == comp_seq) && (load_slot != 3'd0));
    wire issue = busy && (comp_seq < N_GROUPS) && comp_started &&
                 valid[c_bank][slot_a][half] && (is_scale || valid[c_bank][slot_b][half]);

    // ---------------------------------------------------------------- butterfly unit
    wire [12:0] sum_w  = {1'b0, opa} + opb;
    wire [11:0] sum_ab = (sum_w >= Q13) ? (sum_w - Q13) : sum_w[11:0];
    wire [12:0] dif_w  = {1'b0, opb} + Q13 - opa;
    wire [11:0] dif_ba = (dif_w >= Q13) ? (dif_w - Q13) : dif_w[11:0];
    wire [11:0] m_in   = is_scale ? opa : inv_q ? dif_ba : opb;

    // stage 1 registers
    reg        s1_v, s1_inv, s1_scale, s1_bank, s1_half;
    reg [2:0]  s1_sa, s1_sb;
    reg [11:0] s1_x;
    reg [23:0] s1_prod;
    // stage 2 (Barrett) and optional stage 3 registers
    wire [11:0] s1_r;
    barrett_reduce_1c u_red (.a(s1_prod), .r(s1_r));
    reg        s2_v, s2_inv, s2_scale, s2_bank, s2_half;
    reg [2:0]  s2_sa, s2_sb;
    reg [11:0] s2_x, s2_r;

    wire        wb_v     = EXTRA_STAGE ? s2_v     : s1_v;
    wire        wb_inv   = EXTRA_STAGE ? s2_inv   : s1_inv;
    wire        wb_scale = EXTRA_STAGE ? s2_scale : s1_scale;
    wire        wb_bank  = EXTRA_STAGE ? s2_bank  : s1_bank;
    wire        wb_half  = EXTRA_STAGE ? s2_half  : s1_half;
    wire [2:0]  wb_sa    = EXTRA_STAGE ? s2_sa    : s1_sa;
    wire [2:0]  wb_sb    = EXTRA_STAGE ? s2_sb    : s1_sb;
    wire [11:0] wb_x     = EXTRA_STAGE ? s2_x     : s1_x;
    wire [11:0] wb_r     = EXTRA_STAGE ? s2_r     : s1_r;
    wire [12:0] f_sum_w  = {1'b0, wb_x} + wb_r;
    wire [11:0] f_sum    = (f_sum_w >= Q13) ? (f_sum_w - Q13) : f_sum_w[11:0];
    wire [12:0] f_dif_w  = {1'b0, wb_x} + Q13 - wb_r;
    wire [11:0] f_dif    = (f_dif_w >= Q13) ? (f_dif_w - Q13) : f_dif_w[11:0];
    wire [11:0] out_lo   = wb_scale ? wb_r : wb_inv ? wb_x : f_sum;
    wire [11:0] out_hi   = wb_inv ? wb_r : f_dif;

    // ----------------------------------------------------------------------- control
    integer b, s, h;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0; done <= 1'b0; inv_q <= 1'b0;
            load_seq <= 7'd0; comp_seq <= 7'd0; store_seq <= 7'd0;
            load_slot <= 3'd0; store_slot <= 3'd0; op <= 5'd0;
            ld_pend <= 1'b0; ld_pend_bank <= 1'b0; ld_pend_slot <= 3'd0;
            s1_v <= 1'b0; s2_v <= 1'b0; hold_lo_full <= 12'd0; rd_half_q <= 1'b0;
            for (b = 0; b < 2; b = b + 1)
                for (s = 0; s < 8; s = s + 1)
                    for (h = 0; h < 2; h = h + 1) begin
                        valid[b][s][h] <= 1'b0; bank[b][s][h] <= 12'd0;
                    end
        end else begin
            done <= 1'b0;
            rd_half_q <= raddr[0];
            if (!busy && we && !waddr[0]) hold_lo_full <= wdata[11:0];

            if (!busy) begin
                if (start) begin
                    busy <= 1'b1; inv_q <= inverse;
                    load_seq <= 7'd0; comp_seq <= 7'd0; store_seq <= 7'd0;
                    load_slot <= 3'd0; store_slot <= 3'd0; op <= 5'd0;
                end
            end else begin
                // ---- loads: the read issued last cycle lands in its bank
                if (ld_pend) begin
                    bank[ld_pend_bank][ld_pend_slot][0] <= sram_rdata[11:0];
                    bank[ld_pend_bank][ld_pend_slot][1] <= sram_rdata[23:12];
                    valid[ld_pend_bank][ld_pend_slot][0] <= 1'b1;
                    valid[ld_pend_bank][ld_pend_slot][1] <= 1'b1;
                end
                ld_pend <= load_ok;
                ld_pend_bank <= l_bank; ld_pend_slot <= load_slot;
                if (load_ok) begin
                    if ({1'b0, load_slot} == l_words - 4'd1) begin
                        load_slot <= 3'd0; load_seq <= load_seq + 7'd1;
                    end else
                        load_slot <= load_slot + 3'd1;
                end
                // ---- stores
                if (store_ok) begin
                    valid[s_bank][store_slot][0] <= 1'b0;
                    valid[s_bank][store_slot][1] <= 1'b0;
                    if ({1'b0, store_slot} == s_words - 4'd1) begin
                        store_slot <= 3'd0; store_seq <= store_seq + 7'd1;
                        if (store_seq == N_GROUPS - 7'd1) begin
                            busy <= 1'b0; done <= 1'b1;
                        end
                    end else
                        store_slot <= store_slot + 3'd1;
                end
                // ---- butterfly unit: issue
                s1_v <= issue;
                if (issue) begin
                    valid[c_bank][slot_a][half] <= 1'b0;
                    if (!is_scale) valid[c_bank][slot_b][half] <= 1'b0;
                    s1_inv <= inv_q; s1_scale <= is_scale; s1_bank <= c_bank; s1_half <= half;
                    s1_sa <= slot_a; s1_sb <= slot_b;
                    s1_x <= inv_q ? sum_ab : opa;
                    s1_prod <= m_in * zeta;
                    if (op == n_ops) begin
                        op <= 5'd0; comp_seq <= comp_seq + 7'd1;
                    end else
                        op <= op + 5'd1;
                end
                // ---- optional third stage
                s2_v <= s1_v;
                s2_inv <= s1_inv; s2_scale <= s1_scale; s2_bank <= s1_bank; s2_half <= s1_half;
                s2_sa <= s1_sa; s2_sb <= s1_sb; s2_x <= s1_x; s2_r <= s1_r;
                // ---- butterfly unit: write back
                if (wb_v) begin
                    bank[wb_bank][wb_sa][wb_half] <= out_lo;
                    valid[wb_bank][wb_sa][wb_half] <= 1'b1;
                    if (!wb_scale) begin
                        bank[wb_bank][wb_sb][wb_half] <= out_hi;
                        valid[wb_bank][wb_sb][wb_half] <= 1'b1;
                    end
                end
            end
        end
    end
endmodule

// The coefficient store: 128 words x 24 bit, one port, chip enable. Simulation model; the
// physical binding to the OpenRAM macro sky130_sram_1rw_24x128 is rtl/ntt_pair_sram_macro.sv.
`ifndef NTT_PAIR_SRAM_MACRO
module ntt_pair_sram (
    input  wire        clk,
    input  wire        ce,
    input  wire        we,
    input  wire [6:0]  addr,
    input  wire [23:0] wdata,
    output reg  [23:0] rdata
);
    reg [23:0] mem [0:127];
    always @(posedge clk) begin
        if (ce) begin
            if (we) mem[addr] <= wdata;
            else    rdata <= mem[addr];
        end
    end
endmodule
`endif
