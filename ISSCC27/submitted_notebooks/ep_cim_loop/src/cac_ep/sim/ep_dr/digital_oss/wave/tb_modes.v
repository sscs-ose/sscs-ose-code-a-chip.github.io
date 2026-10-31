// tb_modes.v — digital timing of the four operating modes (FORM, READ, SENSING, WRITE) for the notebook figures
//   Blocks (RTL, unchanged): global control  layout/blk_digital/rtl/glob_dig.v + glob_cells.v (hvl cell models, -DFUNCTIONAL)
//                            DATA            layout/blk_digital/rtl/data_blk.v
//                            row control     digital/rtl/row_ctrl.v + rowl.v
//                            column control  digital/col_blk/rtl/col_ctrl.v + coll.v
//   Wiring = chip netlist layout/top/net/chip_core.v, one half (free array, the *_f outputs of glob_dig):
//     pads SCK SDI SLD RST SEL_EN WP; SDI goes to every shift register; glob_dig gates SCK into the register clocks
//     (data_clk / row1_clk / col1_clk ...) with the clock-enable bits of the configuration register; col_ctrl lo = 0 (VSS).
//   Stimulus timing = real_circuit/gen_chip_deck3.py: SCK period 10 ns, SDI changes while SCK is low,
//     cfg(): SLD high, 12 bits shifted from CFG[11] (ts_col2) down to CFG[0] (m1), SLD low applies them;
//     token: SDI "1" then "0"s, row and column registers shifted together to min(r, c), then only the farther one;
//     program: SEL_EN +4 ns, WP +8 ns, 10 ns pulse; verify: SEL_EN +2 ns, WP +4 ns ... +30 ns; sensing slot 440 ns.
//   VCD markers: scen = 1 FORM, 2 READ, 3 SENSING, 4 WRITE (0 = not drawn), seg = step inside the scenario (names in dig_wave.py).
//   Each step ends with a check of the expected decoder outputs over all 106 rows and 64 columns.
//   Ends with "TB_MODES: PASS" or "TB_MODES: FAIL <n>".
`timescale 1ns / 1ps
module tb_modes;
    localparam NR = 106, NC = 64, NI = 49, ND = 52;
    localparam R_SEL = 3, C_SEL = 5;            // selected cell (row 3 = input 1, minus row; column 5 = hidden column)

    // pads
    reg SCK = 0, SDI = 0, SLD = 0, RST = 1, SEL_EN = 0, WP = 0;
    // figure markers
    reg [7:0] scen = 0, seg = 0;
    integer errs = 0, nchk = 0;

    // ---- global control
    wire data_clk_f, data_clk_n, row1_clk_f, row1_clk_n, row2_clk_f, row2_clk_n, col1_clk_f, col1_clk_n, col2_clk_f, col2_clk_n;
    wire rstb_f, rstb_n, READ_f, READ_n, READb_f, READb_n, PROG_f, PROG_n, VER_f, VER_n, SENSE_f, SENSE_n, WRANY_f, WRANY_n;
    wire dload_f, dload_n, pol_f, pol_n, rd_out_f, rd_out_n, rd_out_b_f, rd_out_b_n;
    glob_dig u_glob (.sck(SCK), .sdi(SDI), .sld(SLD), .rst(RST),
        .data_clk_f(data_clk_f), .data_clk_n(data_clk_n), .row1_clk_f(row1_clk_f), .row1_clk_n(row1_clk_n),
        .row2_clk_f(row2_clk_f), .row2_clk_n(row2_clk_n), .col1_clk_f(col1_clk_f), .col1_clk_n(col1_clk_n),
        .col2_clk_f(col2_clk_f), .col2_clk_n(col2_clk_n), .rstb_f(rstb_f), .rstb_n(rstb_n), .READ_f(READ_f), .READ_n(READ_n),
        .READb_f(READb_f), .READb_n(READb_n), .PROG_f(PROG_f), .PROG_n(PROG_n), .VER_f(VER_f), .VER_n(VER_n),
        .SENSE_f(SENSE_f), .SENSE_n(SENSE_n), .WRANY_f(WRANY_f), .WRANY_n(WRANY_n), .dload_f(dload_f), .dload_n(dload_n),
        .pol_f(pol_f), .pol_n(pol_n), .rd_out_f(rd_out_f), .rd_out_n(rd_out_n), .rd_out_b_f(rd_out_b_f), .rd_out_b_n(rd_out_b_n));

    // ---- DATA block
    wire [NI-1:0] ga, gb;
    wire [2:0] sp, spb, sm, smb;
    data_blk u_data (.sdi(SDI), .data_clk(data_clk_f), .dload(dload_f), .READ(READ_f), .rstb(rstb_f),
        .ga(ga), .gb(gb), .sp(sp), .spb(spb), .sm(sm), .smb(smb));

    // ---- row control
    wire [NR-1:0] wsel, wselb, rwz, rwzb, rsns, rsnsb, wlv, wlvb, wlw, wlwb, wl0, wl0b;
    row_ctrl u_row (.sdi(SDI), .row1_clk(row1_clk_f), .row2_clk(row2_clk_f), .rstb(rstb_f), .sel_en(SEL_EN),
        .PROG(PROG_f), .VER(VER_f), .SENSE(SENSE_f), .READb(READb_f), .WRANY(WRANY_f),
        .wsel(wsel), .wselb(wselb), .wz(rwz), .wzb(rwzb), .sns(rsns), .snsb(rsnsb),
        .wlv(wlv), .wlvb(wlvb), .wlw(wlw), .wlwb(wlwb), .wl0(wl0), .wl0b(wl0b));

    // ---- column control
    wire [NC-1:0] wvw, wvwb, cwz, cwzb, vfy, vfyb, sns1, sns1b, sns2, sns2b;
    col_ctrl u_col (.sdi(SDI), .col1_clk(col1_clk_f), .col2_clk(col2_clk_f), .rstb(rstb_f), .sel_en(SEL_EN),
        .PROG(PROG_f), .VER(VER_f), .SENSE(SENSE_f), .WRANY(WRANY_f), .lo(1'b0),
        .wvw(wvw), .wvwb(wvwb), .wz(cwz), .wzb(cwzb), .vfy(vfy), .vfyb(vfyb),
        .sns1(sns1), .sns1b(sns1b), .sns2(sns2), .sns2b(sns2b));

    // ---- internal registers, copied to the top so that one $dumpvars level holds everything the figures use
    wire [11:0] cfg_shift = u_glob.cq;          // configuration shift register
    wire [11:0] cfg_latch = u_glob.cfg;         // configuration latch (applied settings)
    wire [99:0] row_token = u_row.row1q;        // row token register (rows 0-99)
    wire [59:0] col_token = u_col.col1q;        // column token register (hidden columns 0-59)
    wire [ND-1:0] data_reg = u_data.q;          // DATA shift register
    wire [ND-1:0] data_lat = u_data.dl;         // DATA latches

    // ---- stimulus helpers (same timing as gen_chip_deck3.py)
    localparam TC = 10;
    task sbit(input b);                         // one bit on SDI, one SCK pulse
        begin SDI = b; #5 SCK = 1; #3 SCK = 0; #2; end
    endtask
    task shift_n(input b0, input integer n);    // b0 first, then n-1 zeros
        integer j;
        begin sbit(b0); for (j = 1; j < n; j = j + 1) sbit(1'b0); SDI = 0; end
    endtask
    // CFG bit k: 0 m1, 1 m0, 2 pv, 3 pol, 4 wu_en, 5 rd_out, 6 dload, 7 ts_data, 8 ts_row1, 9 ts_row2, 10 ts_col1, 11 ts_col2
    function [11:0] mk;
        input m1, m0, pv, pol, wu_en, dload, ts_data, ts_row1, ts_col1;
        mk = {1'b0, ts_col1, 1'b0, ts_row1, ts_data, dload, 1'b0, wu_en, pol, pv, m0, m1};
    endfunction
    task cfg(input [11:0] v);
        integer k;
        begin
            SLD = 1; #2;
            for (k = 11; k >= 0; k = k - 1) sbit(v[k]);
            SDI = 0; SLD = 0; #5;
        end
    endtask
    task shift_data(input [ND-1:0] v);          // last bit shifted = q[0] -> q[k] = v[k]
        integer k;
        begin for (k = ND - 1; k >= 0; k = k - 1) sbit(v[k]); SDI = 0; end
    endtask
    task rst_pulse;
        begin RST = 1; #10 RST = 0; #10; end
    endtask

    // ---- checks
    task ck(input ok, input [8*80:1] what);
        begin
            nchk = nchk + 1;
            if (ok !== 1'b1) begin errs = errs + 1; $display("  FAIL  t=%0d ns  scen %0d seg %0d  %0s", $time, scen, seg, what); end
        end
    endtask
    function [NR-1:0] oh_r; input integer r; oh_r = {{(NR-1){1'b0}}, 1'b1} << r; endfunction
    function [NC-1:0] oh_c; input integer c; oh_c = {{(NC-1){1'b0}}, 1'b1} << c; endfunction
    localparam [NR-1:0] R0 = {NR{1'b0}}, R1 = {NR{1'b1}};
    localparam [NC-1:0] C0 = {NC{1'b0}}, C1 = {NC{1'b1}};

    task ck_mode(input rd, input prog, input ver, input sense);
        begin
            ck(READ_f === rd && READb_f === ~rd, "mode decoder: read");
            ck(PROG_f === prog, "mode decoder: program");
            ck(VER_f === ver, "mode decoder: verify");
            ck(WRANY_f === (prog | ver), "mode decoder: program_or_verify");
            ck(SENSE_f === sense, "mode decoder: sense");
        end
    endtask
    task ck_tok(input integer r, input integer c);
        begin
            ck(row_token === ({{99{1'b0}}, 1'b1} << r), "row token position");
            ck(col_token === ({{59{1'b0}}, 1'b1} << c), "column token position");
        end
    endtask
    task ck_idle_lines;                         // write-type mode with select_enable low, or IDLE
        begin
            ck(wsel === R0 && rsns === R0 && wlw === R0, "no row selected");
            ck(cwz === C0 && vfy === C0 && sns1 === C0 && sns2 === C0, "no column selected");
        end
    endtask
    task ck_program(input integer r, input integer c);
        begin
            ck(wsel === oh_r(r), "row_to_write_bus only on the selected row");
            ck(rwz === ~oh_r(r), "row_to_0V on every other row");
            ck(wlw === oh_r(r), "wl_to_write_voltage only on the selected WL");
            ck(wl0 === ~oh_r(r) && wlv === R0, "wl_to_VSS on every other WL");
            ck(rsns === R0, "no row on the sense bus");
            ck(cwz === oh_c(c), "selected column to 0 V");
            ck(wvw === ~oh_c(c), "other columns to the write bus");
            ck(vfy === C0 && sns1 === C0 && sns2 === C0, "no column on verify or sense");
            ck(ga === {NI{1'b0}} && gb === {NI{1'b0}}, "input drivers off");
        end
    endtask
    task ck_verify(input integer r, input integer c);
        begin
            ck(wsel === oh_r(r) && rwz === ~oh_r(r), "verify: row to write bus, others 0 V");
            ck(wlv === oh_r(r) && wlw === R0 && wl0 === ~oh_r(r), "verify: selected WL to VDD, others VSS");
            ck(vfy === oh_c(c) && wvw === ~oh_c(c) && cwz === C0, "verify: column to verify bus, others write bus");
        end
    endtask
    task ck_read(input [ND-1:0] v);             // READ: every WL at VDD, inputs from the latches
        begin
            ck(wlv === R1 && wlw === R0 && wl0 === R0, "read: every WL to VDD");
            ck(wsel === R0 && rwz === R0, "read: no row to write bus or 0 V");
            ck(wvw === C0 && cwz === C0 && vfy === C0, "read: columns left to the clamps");
            ck(data_lat === v, "read: latches hold the expected input");
            ck(ga === v[NI-1:0] && gb === ~v[NI-1:0], "read: input-driver gates follow the latches");
        end
    endtask

    // ---- input images (bit 1 -> rows 2, 3; bit 2 -> rows 4, 5)
    localparam [ND-1:0] IMG_A = 52'h3_C3C3_C3C3_C3C3;   // bit 1 = 1, bit 2 = 0
    localparam [ND-1:0] IMG_B = 52'h9_6969_6969_6965;   // bit 1 = 0, bit 2 = 1

    initial begin
        $dumpfile("tb_modes.vcd");
        $dumpvars(1, tb_modes);
        // power-on reset (deck: RST high from 0 ns)
        #15 RST = 0; #5;

        // ================= FORM =================
        scen = 1;
        seg = 1; #20;                                                  // IDLE after reset
        ck_mode(0, 0, 0, 0); ck_idle_lines;
        ck(wl0 === R1, "IDLE: every WL to VSS");
        seg = 2; cfg(mk(0, 1, 0, 0, 0, 0, 0, 1, 1));                   // mode FORM, row + column token registers
        ck_mode(0, 1, 0, 0); ck_idle_lines;
        ck(rwz === R1 && wvw === C1, "FORM, select_enable low: rows 0 V, columns write bus");
        seg = 3; shift_n(1'b1, R_SEL + 1); #2;                         // row and column tokens -> 3
        ck_tok(R_SEL, R_SEL); ck_idle_lines;
        seg = 4; cfg(mk(0, 1, 0, 0, 0, 0, 0, 0, 1));                   // FORM, column register only
        ck_mode(0, 1, 0, 0);
        seg = 5; shift_n(1'b0, C_SEL - R_SEL); #2;                     // column token -> 5
        ck_tok(R_SEL, C_SEL); ck_idle_lines;
        seg = 6; #4 SEL_EN = 1; #4 WP = 1; #5;                         // program (forming) pulse 10 ns
        ck_program(R_SEL, C_SEL); ck(pol_f === 1'b0, "FORM: write buffer polarity SET");
        #5 WP = 0; #4 SEL_EN = 0; #8;
        ck_idle_lines;
        scen = 0; seg = 0;
        rst_pulse;

        // ---- (not drawn) previous image A in the latches
        cfg(mk(0, 0, 0, 0, 0, 0, 1, 0, 0));
        shift_data(IMG_A); #2;
        cfg(mk(0, 0, 0, 0, 0, 1, 0, 0, 0));
        ck(data_lat === IMG_A, "previous image in the latches");
        cfg(mk(0, 0, 0, 0, 0, 0, 0, 0, 0));                           // load off again before the reset:
        rst_pulse;                                                     // reset with load on would clear the latches (register -> 0 while open)

        // ================= READ =================
        scen = 2;
        seg = 1; #20;
        ck_mode(0, 0, 0, 0); ck(ga === {NI{1'b0}} && gb === {NI{1'b0}}, "IDLE: input drivers off");
        seg = 2; cfg(mk(1, 1, 0, 0, 0, 0, 1, 0, 0));                   // mode READ, DATA register, load off
        ck_mode(1, 0, 0, 0); ck_read(IMG_A);
        seg = 3; shift_data(IMG_B); #2;                                // 52 bits, latches closed
        ck(data_reg === IMG_B, "DATA register holds the new image");
        ck_read(IMG_A);
        seg = 4; cfg(mk(1, 1, 0, 0, 0, 1, 0, 0, 0));                   // READ, load on: every latch opens
        ck_mode(1, 0, 0, 0); ck_read(IMG_B);
        seg = 5; #40;                                                  // arrays settle
        ck_read(IMG_B);
        scen = 0; seg = 0; #1;

        // ================= SENSING (continues from READ) =================
        scen = 3;
        seg = 1; #20;
        seg = 2; cfg(mk(1, 1, 0, 0, 1, 1, 0, 1, 1));                   // READ + sensing, row + column token registers
        ck_mode(1, 0, 0, 1); ck_read(IMG_B); ck(rsns === R0 && sns1 === C0, "sensing, select_enable low: nothing on the sense buses");
        seg = 3; shift_n(1'b1, R_SEL + 1); #2;
        ck_tok(R_SEL, R_SEL);
        seg = 4; cfg(mk(1, 1, 0, 0, 1, 1, 0, 0, 1));                   // column register only
        seg = 5; shift_n(1'b0, C_SEL - R_SEL); #2;
        ck_tok(R_SEL, C_SEL); ck_read(IMG_B);
        seg = 6; SEL_EN = 1; #220;                                     // cell (3, 5) to the weight-update circuit
        ck(rsns === oh_r(R_SEL), "sense: only the selected row on the sense bus");
        ck(sns1 === oh_c(C_SEL) && sns2 === C0, "sense: only the selected column on sense bus 1");
        ck_read(IMG_B);
        #220 SEL_EN = 0; #2;
        seg = 7; shift_n(1'b0, 1); #2;                                 // column token one step -> 6
        ck_tok(R_SEL, C_SEL + 1); ck(rsns === R0 && sns1 === C0, "between cells: nothing on the sense buses");
        seg = 8; SEL_EN = 1; #220;                                     // cell (3, 6)
        ck(rsns === oh_r(R_SEL) && sns1 === oh_c(C_SEL + 1), "sense: next cell (3, 6)");
        ck_read(IMG_B);
        #220 SEL_EN = 0; #10;
        scen = 0; seg = 0;
        rst_pulse;

        // ================= WRITE =================
        scen = 4;
        seg = 1; #20;
        seg = 2; cfg(mk(1, 0, 0, 0, 0, 0, 0, 1, 1));                   // WRITE program (SET), row + column registers
        ck_mode(0, 1, 0, 0); ck_idle_lines;
        seg = 3; shift_n(1'b1, R_SEL + 1); #2;
        ck_tok(R_SEL, R_SEL);
        seg = 4; cfg(mk(1, 0, 0, 0, 0, 0, 0, 0, 1));
        seg = 5; shift_n(1'b0, C_SEL - R_SEL); #2;
        ck_tok(R_SEL, C_SEL); ck_idle_lines;
        seg = 6; #4 SEL_EN = 1; #4 WP = 1; #5;                         // SET pulse 10 ns
        ck_program(R_SEL, C_SEL); ck(pol_f === 1'b0, "WRITE: polarity SET");
        #5 WP = 0; #4 SEL_EN = 0; #8;
        seg = 7; cfg(mk(1, 0, 1, 0, 0, 0, 0, 0, 1));                   // WRITE verify
        ck_mode(0, 0, 1, 0); ck_tok(R_SEL, C_SEL);
        seg = 8; #2 SEL_EN = 1; #2 WP = 1; #20;                        // verify: read voltage on the write bus
        ck_verify(R_SEL, C_SEL);
        #6 WP = 0; #1 SEL_EN = 0; #9;
        ck_idle_lines;
        scen = 0; seg = 0; #10;

        if (errs == 0) $display("TB_MODES: PASS (%0d checks, end %0d ns)", nchk, $time);
        else           $display("TB_MODES: FAIL %0d of %0d checks", errs, nchk);
        $finish;
    end
endmodule
