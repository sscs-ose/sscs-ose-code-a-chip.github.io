// ---------------------------------------------------------------------------
// twiddle_gen : ROM-less on-the-fly twiddle generator (N4)
//
// Eliminates the 256-entry twiddle ROM by computing twiddles on-the-fly
// using iterated Montgomery multiplication. Stage roots/seeds are stored
// in an 8-entry constant table, and intermediate twiddles for each group
// are produced by running modular multiplication with the stage step factor.
// ---------------------------------------------------------------------------
module twiddle_gen #(
    parameter integer WIDTH  = 24,
    parameter integer LOGN   = 8,
    parameter [WIDTH-1:0] Q      = 24'd8380417,
    parameter [31:0]      QPRIME = 32'd4236238847
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire             init_stage,    // Asserted at start of a new stage
    input  wire [3:0]       stage_idx,     // Current stage 0..LOGN-1
    input  wire             step_valid,    // Pulse to step to the next twiddle factor
    input  wire [WIDTH-1:0] seed_in,       // Optional custom seed input (or internal if 0)
    output reg  [WIDTH-1:0] zeta_out,      // Current Montgomery twiddle factor
    output reg              ready          // High when zeta_out is valid
);

    // Stage seeds in Montgomery domain (for Dilithium Q=8380417)
    // Stage 0: zeta[1], Stage 1: zeta[2], Stage 2: zeta[4], Stage 3: zeta[8]...
    reg [WIDTH-1:0] stage_seeds [0:7];
    reg [WIDTH-1:0] stage_steps [0:7];

    initial begin
        stage_seeds[0] = 24'h0064f7; // zeta[1]
        stage_seeds[1] = 24'h581103; // zeta[2]
        stage_seeds[2] = 24'h039e44; // zeta[4]
        stage_seeds[3] = 24'h1bde2b; // zeta[8]
        stage_seeds[4] = 24'h299658; // zeta[16]
        stage_seeds[5] = 24'h741eb0; // zeta[32]
        stage_seeds[6] = 24'h534346; // zeta[64]
        stage_seeds[7] = 24'h4fb90e; // zeta[128]

        stage_steps[0] = 24'h3ffe00; // 1 in Montgomery domain
        stage_steps[1] = 24'h581103;
        stage_steps[2] = 24'h039e44;
        stage_steps[3] = 24'h1bde2b;
        stage_steps[4] = 24'h299658;
        stage_steps[5] = 24'h741eb0;
        stage_steps[6] = 24'h534346;
        stage_steps[7] = 24'h4fb90e;
    end

    // Internal Montgomery multiplier to advance zeta
    reg              mm_in_valid;
    reg  [WIDTH-1:0] mm_a, mm_b;
    wire [WIDTH-1:0] mm_result;
    wire             mm_out_valid;

    mod_mul #(.WIDTH(WIDTH), .Q(Q), .QPRIME(QPRIME)) u_mul (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(mm_in_valid),
        .a(mm_a),
        .b(mm_b),
        .result(mm_result),
        .out_valid(mm_out_valid)
    );

    localparam S_IDLE = 2'd0, S_WAIT = 2'd1;
    reg [1:0] state;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state       <= S_IDLE;
            zeta_out    <= {WIDTH{1'b0}};
            ready       <= 1'b0;
            mm_in_valid <= 1'b0;
            mm_a        <= {WIDTH{1'b0}};
            mm_b        <= {WIDTH{1'b0}};
        end else begin
            mm_in_valid <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (init_stage) begin
                        if (seed_in != {WIDTH{1'b0}})
                            zeta_out <= seed_in;
                        else if (stage_idx < 8)
                            zeta_out <= stage_seeds[stage_idx];
                        ready <= 1'b1;
                    end else if (step_valid && ready) begin
                        mm_a        <= zeta_out;
                        mm_b        <= (stage_idx < 8) ? stage_steps[stage_idx] : 24'h3ffe00;
                        mm_in_valid <= 1'b1;
                        ready       <= 1'b0;
                        state       <= S_WAIT;
                    end
                end

                S_WAIT: begin
                    if (mm_out_valid) begin
                        zeta_out <= mm_result;
                        ready    <= 1'b1;
                        state    <= S_IDLE;
                    end
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
