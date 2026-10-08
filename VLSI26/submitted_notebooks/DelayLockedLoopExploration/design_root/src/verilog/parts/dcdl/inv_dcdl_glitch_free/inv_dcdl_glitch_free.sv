//**************************************************************************
// Glitch-free inv DCDL (all taps use 2 inverters)
//**************************************************************************
(* dont_touch = "true" *)
module inv_dcdl_glitch_free(
    input  logic clk, 
    input  logic rst_n, 
    input  logic A, 
    input  logic [1:0] Q,
    output logic Y
);


    logic tap0, tap1, tap2, tap3;

    logic s1, s2, s3, s4, s5, s6, s7, s8;

    // tap0 = 2 inv
    inverter a1 (.in(A),  .out(s1));
    inverter a2 (.in(s1), .out(tap0));

    // tap1 = 4 inv
    inverter b1 (.in(tap0), .out(s2));
    inverter b2 (.in(s2),   .out(tap1));

    // tap2 = 6 inv
    inverter c1 (.in(tap1), .out(s3));
    inverter c2 (.in(s3),   .out(tap2));

    // tap3 = 8 inv
    inverter d1 (.in(tap2), .out(s4));
    inverter d2 (.in(s4),   .out(tap3));

    logic [3:0] sel;

    always_comb begin
        sel = 4'b0000;
        sel[Q] = 1'b1;
    end


    logic [3:0] sel_reg;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            sel_reg <= 4'b0001;
        else
            sel_reg <= sel;
    end


    logic ntap0, ntap1, ntap2, ntap3;
    logic y0, y1, y2, y3;
    logic n01, n23;

    inverter inv_t0 (.in(tap0), .out(ntap0));
    inverter inv_t1 (.in(tap1), .out(ntap1));
    inverter inv_t2 (.in(tap2), .out(ntap2));
    inverter inv_t3 (.in(tap3), .out(ntap3));

    nand2 n0 (.a(ntap0), .b(sel_reg[0]), .out(y0));
    nand2 n1 (.a(ntap1), .b(sel_reg[1]), .out(y1));
    nand2 n2 (.a(ntap2), .b(sel_reg[2]), .out(y2));
    nand2 n3 (.a(ntap3), .b(sel_reg[3]), .out(y3));

    nand2 n4 (.a(y0), .b(y1), .out(n01));
    nand2 n5 (.a(y2), .b(y3), .out(n23));

    assign Y = ~(n01 | n23);


endmodule