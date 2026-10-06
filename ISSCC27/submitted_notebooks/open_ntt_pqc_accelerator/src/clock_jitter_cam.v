// ---------------------------------------------------------------------------
// clock_jitter_cam.v: Randomized Clock Jitter & Power Camouflage Unit (N10)
//
// Countermeasure against Correlation Power Analysis (CPA) and Correlation
// Electromagnetic Analysis (CEMA) attacks in physical silicon.
//
// Architectural Features:
// 1. Time-Domain Desynchronization: Modulates internal clock edges across
//    discrete delay phase states driven by on-chip physical entropy (TRNG/LFSR),
//    preventing trace alignment by external side-channel oscilloscopes.
// 2. Dynamic Power Equalization (Camouflage): During idle cycles or low-power
//    butterfly steps, pseudo-random dummy capacitive toggles are activated to
//    flatten the global current consumption profile (dI/dt).
// ---------------------------------------------------------------------------
`timescale 1ns / 1ps

module clock_jitter_cam #(
    parameter integer DUMMY_LANES = 8
) (
    input  wire        clk_in,          // Raw system clock input
    input  wire        rst_n,           // Active-low reset
    input  wire        enable_jitter,   // 1 = Active clock phase desynchronization
    input  wire        enable_camou,    // 1 = Active power profile flattening
    input  wire [7:0]  entropy_seed,    // From Hardware TRNG (src/trng.v)
    input  wire        datapath_busy,   // 1 when NTT butterfly engine is active

    output wire        clk_jittered,    // Desynchronized internal core clock
    output reg  [1:0]  phase_state,     // Current selected phase delay tap
    output reg  [7:0]  dummy_toggles    // Dummy capacitive switching nets
);

    // 1. Pseudo-random phase selector updated on clock edges
    reg [7:0] jitter_lfsr;
    always @(posedge clk_in or negedge rst_n) begin
        if (!rst_n) begin
            jitter_lfsr <= 8'h5A;
            phase_state <= 2'b00;
        end else begin
            // Non-linear feedback polynomial combined with physical TRNG seed
            jitter_lfsr <= {jitter_lfsr[6:0], jitter_lfsr[7] ^ jitter_lfsr[5] ^ jitter_lfsr[4] ^ jitter_lfsr[3]} ^ entropy_seed;
            if (enable_jitter) begin
                phase_state <= jitter_lfsr[1:0];
            end else begin
                phase_state <= 2'b00;
            end
        end
    end

    // 2. Behavioral model of 4-tap delay line for sky130 standard cell buffers
    // In sky130, each tap represents ~250ps delay introduced by buffer chains
    reg clk_dly1, clk_dly2, clk_dly3;
    always @(*) begin
        clk_dly1 <= #0.2 clk_in;
        clk_dly2 <= #0.4 clk_in;
        clk_dly3 <= #0.6 clk_in;
    end

    reg clk_mux;
    always @(*) begin
        case (phase_state)
            2'b00:   clk_mux = clk_in;
            2'b01:   clk_mux = clk_dly1;
            2'b10:   clk_mux = clk_dly2;
            2'b11:   clk_mux = clk_dly3;
            default: clk_mux = clk_in;
        endcase
    end

    assign clk_jittered = enable_jitter ? clk_mux : clk_in;

    // 3. Dummy Power Equalization (Power Camouflage)
    // When the primary datapath is idle or sparsely loaded, toggle dummy loads
    // to maintain a stationary mean power consumption profile
    always @(posedge clk_in or negedge rst_n) begin
        if (!rst_n) begin
            dummy_toggles <= 8'h00;
        end else if (enable_camou) begin
            if (!datapath_busy) begin
                // Invert dummy registers to mimic busy arithmetic switching
                dummy_toggles <= ~dummy_toggles ^ jitter_lfsr;
            end else begin
                // Complementary switching
                dummy_toggles <= dummy_toggles ^ {4'b0, jitter_lfsr[3:0]};
            end
        end else begin
            dummy_toggles <= 8'h00;
        end
    end

endmodule
