(* dont_touch = "true" *)
module inv_dcdl_glitchless #(
    parameter int STAGES = 64,
    parameter int CTRL_BITS = $clog2(STAGES)  
)(
    input  logic                 clk,   // Reference clock
    input  logic                 rst,   // Active-high reset
    input  logic                 A,     // Input to be delayed
    input  logic [CTRL_BITS-1:0] Q,     // Binary control word
    output logic                 Y      // Delayed output
);

    logic [STAGES-1:0] taps;
    logic [STAGES-1:0] chain_mid; // Intermediate nodes for the segment pairs

    genvar i;
    generate
        for (i = 0; i < STAGES; i++) begin : delay_chain
            if (i == 0) begin
                // First stage connects to input A
                inverter inv_a (.in(A),            .out(chain_mid[i]));
                inverter inv_b (.in(chain_mid[i]), .out(taps[i]));
            end else begin
                // Subsequent stages connect to the previous tap
                inverter inv_a (.in(taps[i-1]),    .out(chain_mid[i]));
                inverter inv_b (.in(chain_mid[i]), .out(taps[i]));
            end
        end
    endgenerate

    logic [STAGES-1:0] sel_one_hot;
    logic [STAGES-1:0] sel_reg;

    always_comb begin
        sel_one_hot = '0;
        sel_one_hot[Q] = 1'b1;
    end

    // Switching on the negedge ensures the MUX is stable before 
    // the next posedge of clk (assuming clk == A) arrives.
    always_ff @(negedge clk or posedge rst) begin
        if (rst)
            sel_reg <= {{STAGES-1{1'b0}}, 1'b1}; // Default to Stage 0
        else
            sel_reg <= sel_one_hot;
    end

    // -----------------------------------------------------------------
    // 3. Gated Reduction Tree
    // -----------------------------------------------------------------
    // We use an AND-OR structure. Every tap is "masked" by its 
    // corresponding one-hot select bit.
    // -----------------------------------------------------------------
    logic [STAGES-1:0] gated_taps;

    generate
        for (i = 0; i < STAGES; i++) begin : tap_gating
            // Using logic operators; synthesis will map this to 
            // standard cells (e.g., sky130_fd_sc_hd__and2)
            assign gated_taps[i] = taps[i] & sel_reg[i];
        end
    endgenerate

    // Behavioral OR-reduction. 
    // The tool will synthesize this into a balanced log2 tree of OR gates.
    assign Y = |gated_taps;

endmodule