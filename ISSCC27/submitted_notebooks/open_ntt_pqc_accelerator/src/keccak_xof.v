// ---------------------------------------------------------------------------
// keccak_xof : High-Throughput SHAKE-128 / Keccak-f[1600] XOF Accelerator (N9)
//
// Accelerates seed expansion and matrix generation (SampleNTT) for ML-KEM/Kyber
// and ML-DSA/Dilithium.
//
// Specifications:
// - Keccak-f[1600] permutation state: 25 lanes x 64-bit = 1600 bits.
// - SHAKE-128 rate r = 1344 bits (168 bytes, 21 lanes). Capacity c = 256 bits.
// - Domain separator: 0x1F (for SHAKE-128) with standard 10*1 padding.
// - Round-based iterative permutation (24 cycles per permutation block).
// - Squeeze engine directly streams 24-bit coefficients to OpenNTT Coeff RAM.
// ---------------------------------------------------------------------------
`timescale 1ns / 1ps

module keccak_xof #(
    parameter integer OUT_WIDTH = 24
) (
    input  wire                 clk,
    input  wire                 rst_n,

    // Control
    input  wire                 start_absorb,  // Initialize sponge & begin absorbing
    input  wire                 absorb_valid,  // 64-bit word input valid
    input  wire [63:0]          absorb_data,   // Input message / seed stream
    input  wire                 absorb_last,   // Last word of input message
    output reg                  absorb_ready,  // Ready to accept next 64-bit word

    // Permutation status
    output reg                  perm_busy,

    // Squeeze stream to Coeff RAM / SampleNTT
    input  wire                 squeeze_req,   // Request next 24-bit coefficient
    output reg  [OUT_WIDTH-1:0] squeeze_data,  // Rejection-sampled / formatted coefficient
    output reg                  squeeze_valid  // Data valid pulse
);

    // 25 x 64-bit state registers: lane[x + 5*y]
    reg [63:0] state [0:24];

    // Round counter: 0 to 23
    reg [4:0] round_cnt;
    reg [2:0] xof_state;

    localparam S_IDLE    = 3'd0;
    localparam S_ABSORB  = 3'd1;
    localparam S_PAD     = 3'd2;
    localparam S_PERM    = 3'd3;
    localparam S_SQUEEZE = 3'd4;

    reg [4:0] absorb_idx; // Lane index (0 to 20 for rate=21 lanes)
    reg [4:0] squeeze_idx;

    // Keccak-f Round Constants RC[i]
    function [63:0] get_rc;
        input [4:0] r;
        case (r)
            5'd0:  get_rc = 64'h0000000000000001;
            5'd1:  get_rc = 64'h0000000000008082;
            5'd2:  get_rc = 64'h800000000000808a;
            5'd3:  get_rc = 64'h8000000080008000;
            5'd4:  get_rc = 64'h000000000000808b;
            5'd5:  get_rc = 64'h0000000080000001;
            5'd6:  get_rc = 64'h8000000080008081;
            5'd7:  get_rc = 64'h8000000000008009;
            5'd8:  get_rc = 64'h000000000000008a;
            5'd9:  get_rc = 64'h0000000000000088;
            5'd10: get_rc = 64'h0000000080008009;
            5'd11: get_rc = 64'h000000008000000a;
            5'd12: get_rc = 64'h000000008000808b;
            5'd13: get_rc = 64'h800000000000008b;
            5'd14: get_rc = 64'h8000000000008089;
            5'd15: get_rc = 64'h8000000000008003;
            5'd16: get_rc = 64'h8000000000008002;
            5'd17: get_rc = 64'h8000000000000080;
            5'd18: get_rc = 64'h000000000000800a;
            5'd19: get_rc = 64'h800000008000000a;
            5'd20: get_rc = 64'h8000000080008081;
            5'd21: get_rc = 64'h8000000000008080;
            5'd22: get_rc = 64'h0000000080000001;
            5'd23: get_rc = 64'h8000000080008008;
            default: get_rc = 64'h0;
        endcase
    endfunction

    // Rotation helper
    function [63:0] rotl64;
        input [63:0] val;
        input [5:0] shift;
        begin
            if (shift == 0)
                rotl64 = val;
            else
                rotl64 = (val << shift) | (val >> (64 - shift));
        end
    endfunction

    // 1-round combinational Keccak step
    reg [63:0] C [0:4];
    reg [63:0] D [0:4];
    reg [63:0] B [0:24];
    integer i, j, x, y;

    // FSM and round engine
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            xof_state     <= S_IDLE;
            round_cnt     <= 5'd0;
            absorb_idx    <= 5'd0;
            squeeze_idx   <= 5'd0;
            absorb_ready  <= 1'b0;
            perm_busy     <= 1'b0;
            squeeze_data  <= {OUT_WIDTH{1'b0}};
            squeeze_valid <= 1'b0;
            for (i = 0; i < 25; i = i + 1)
                state[i] <= 64'd0;
        end else begin
            squeeze_valid <= 1'b0;

            case (xof_state)
                S_IDLE: begin
                    perm_busy <= 1'b0;
                    if (start_absorb) begin
                        for (i = 0; i < 25; i = i + 1)
                            state[i] <= 64'd0;
                        absorb_idx   <= 5'd0;
                        absorb_ready <= 1'b1;
                        xof_state    <= S_ABSORB;
                    end
                end

                S_ABSORB: begin
                    if (absorb_valid && absorb_ready) begin
                        state[absorb_idx] <= state[absorb_idx] ^ absorb_data;
                        if (absorb_last || absorb_idx == 5'd20) begin
                            absorb_ready <= 1'b0;
                            xof_state    <= S_PAD;
                        end else begin
                            absorb_idx <= absorb_idx + 1'b1;
                        end
                    end
                end

                S_PAD: begin
                    // SHAKE-128 standard pad10*1: domain separator 0x1F and 0x80 on rate boundary
                    state[absorb_idx] <= state[absorb_idx] ^ 64'h000000000000001f;
                    state[20]         <= state[20] ^ 64'h8000000000000000;
                    round_cnt         <= 5'd0;
                    perm_busy         <= 1'b1;
                    xof_state         <= S_PERM;
                end

                S_PERM: begin
                    // Execute 1 round of Keccak-f[1600]
                    // 1. Theta step
                    C[0] = state[0] ^ state[5]  ^ state[10] ^ state[15] ^ state[20];
                    C[1] = state[1] ^ state[6]  ^ state[11] ^ state[16] ^ state[21];
                    C[2] = state[2] ^ state[7]  ^ state[12] ^ state[17] ^ state[22];
                    C[3] = state[3] ^ state[8]  ^ state[13] ^ state[18] ^ state[23];
                    C[4] = state[4] ^ state[9]  ^ state[14] ^ state[19] ^ state[24];

                    D[0] = C[4] ^ rotl64(C[1], 6'd1);
                    D[1] = C[0] ^ rotl64(C[2], 6'd1);
                    D[2] = C[1] ^ rotl64(C[3], 6'd1);
                    D[3] = C[2] ^ rotl64(C[4], 6'd1);
                    D[4] = C[3] ^ rotl64(C[0], 6'd1);

                    // 2. Rho & Pi step combined into B
                    B[0]  = state[0]  ^ D[0];
                    B[1]  = rotl64(state[6]  ^ D[1], 6'd44);
                    B[2]  = rotl64(state[12] ^ D[2], 6'd43);
                    B[3]  = rotl64(state[18] ^ D[3], 6'd21);
                    B[4]  = rotl64(state[24] ^ D[4], 6'd14);

                    B[5]  = rotl64(state[3]  ^ D[3], 6'd28);
                    B[6]  = rotl64(state[9]  ^ D[4], 6'd20);
                    B[7]  = rotl64(state[10] ^ D[0], 6'd3);
                    B[8]  = rotl64(state[16] ^ D[1], 6'd45);
                    B[9]  = rotl64(state[22] ^ D[2], 6'd61);

                    B[10] = rotl64(state[1]  ^ D[1], 6'd1);
                    B[11] = rotl64(state[7]  ^ D[2], 6'd6);
                    B[12] = rotl64(state[13] ^ D[3], 6'd25);
                    B[13] = rotl64(state[19] ^ D[4], 6'd8);
                    B[14] = rotl64(state[20] ^ D[0], 6'd18);

                    B[15] = rotl64(state[4]  ^ D[4], 6'd27);
                    B[16] = rotl64(state[5]  ^ D[0], 6'd36);
                    B[17] = rotl64(state[11] ^ D[1], 6'd10);
                    B[18] = rotl64(state[17] ^ D[2], 6'd15);
                    B[19] = rotl64(state[23] ^ D[3], 6'd56);

                    B[20] = rotl64(state[2]  ^ D[2], 6'd62);
                    B[21] = rotl64(state[8]  ^ D[3], 6'd55);
                    B[22] = rotl64(state[14] ^ D[4], 6'd39);
                    B[23] = rotl64(state[15] ^ D[0], 6'd41);
                    B[24] = rotl64(state[21] ^ D[1], 6'd2);

                    // 3. Chi step & Iota step
                    for (y = 0; y < 5; y = y + 1) begin
                        for (x = 0; x < 5; x = x + 1) begin
                            state[x + 5*y] <= B[x + 5*y] ^ ((~B[((x+1)%5) + 5*y]) & B[((x+2)%5) + 5*y]);
                        end
                    end
                    state[0] <= (B[0] ^ ((~B[1]) & B[2])) ^ get_rc(round_cnt);

                    if (round_cnt == 5'd23) begin
                        perm_busy   <= 1'b0;
                        squeeze_idx <= 5'd0;
                        xof_state   <= S_SQUEEZE;
                    end else begin
                        round_cnt <= round_cnt + 1'b1;
                    end
                end

                S_SQUEEZE: begin
                    if (squeeze_req) begin
                        // Extract 24-bit word from rate lanes
                        squeeze_data  <= state[squeeze_idx][OUT_WIDTH-1:0];
                        squeeze_valid <= 1'b1;
                        if (squeeze_idx == 5'd20) begin
                            squeeze_idx <= 5'd0;
                            round_cnt   <= 5'd0;
                            perm_busy   <= 1'b1;
                            xof_state   <= S_PERM; // Re-permute for continuous squeezing
                        end else begin
                            squeeze_idx <= squeeze_idx + 1'b1;
                        end
                    end
                end

                default: xof_state <= S_IDLE;
            endcase
        end
    end

endmodule
