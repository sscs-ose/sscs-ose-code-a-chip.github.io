(* dont_touch = "true" *)
module vernier_crossover_dcdl #(
    parameter STAGES = 16
)(
    input  logic A,
    input  logic [STAGES-1:0] Q,
    output logic Y
);

    (* keep = "true" *) logic [STAGES:0] slow_net;
    (* keep = "true" *) logic [STAGES:0] fast_net;
    (* keep = "true" *) logic [STAGES-1:0] mux_out;

    assign slow_net[0] = A;
    
    assign fast_net[0] = 1'b0; 

    genvar i;
    generate
        for (i = 0; i < STAGES; i++) begin : vdl_stage
            
            (* dont_touch = "true" *) sky130_fd_sc_hd__buf_1 slow_cell (
                .A(slow_net[i]),
                .X(slow_net[i+1])
            );

            (* dont_touch = "true" *) sky130_fd_sc_hd__mux2_1 cross_mux (
                .A0(fast_net[i]),
                .A1(slow_net[i]),
                .S(Q[i]),
                .X(mux_out[i])
            );

            (* dont_touch = "true" *) sky130_fd_sc_hd__buf_4 fast_cell (
                .A(mux_out[i]),
                .X(fast_net[i+1])
            );
            
        end
    endgenerate

    assign Y = fast_net[STAGES];

endmodule