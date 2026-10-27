`timescale 1ns / 1ps

module controller #(
    parameter TILE_SIZE = 16
)(
    input  wire clk,
    input  wire rst_n,
    input  wire tile_valid,
    input  wire is_zero,
    input  wire use_sparse,
    
    output reg  [$clog2(TILE_SIZE)-1:0] rd_addr,
    output reg  [$clog2(TILE_SIZE+1)-1:0] zero_count,
    output reg  mode_latched,  // 0: Dense, 1: Sparse
    output reg  mac_en,
    output reg  acc_en,        // now delayed by 1 cycle (pipelined)
    output reg  acc_clr,
    output reg  done
);

    localparam S_IDLE  = 2'b00,
               S_SCAN  = 2'b01,
               S_EVAL  = 2'b10,
               S_COMP  = 2'b11;

    reg [1:0] state, next_state;
    reg [$clog2(TILE_SIZE)-1:0] ptr;

    // ---------------------------------------------------------
    // BUG FIX #1: Pipeline register to delay acc_en by 1 cycle
    // The MAC is a registered multiplier, so its product (prod)
    // is only valid 1 cycle AFTER mac_en is asserted.
    // acc_en must therefore be delayed to match.
    // ---------------------------------------------------------
    reg mac_en_internal;    // immediate MAC enable (drives mac_en)
    reg acc_en_internal;    // immediate ACC enable (gets delayed)
    reg done_internal;      // immediate done (gets delayed)

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            acc_en <= 1'b0;
            done   <= 1'b0;
        end else begin
            acc_en <= acc_en_internal;  // 1-cycle delay
            done   <= done_internal;    // 1-cycle delay to align with final accumulation
        end
    end

    always @(*) begin
        mac_en = mac_en_internal;
    end

    // FSM State Register
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) state <= S_IDLE;
        else state <= next_state;
    end

    // Next State Logic
    always @(*) begin
        case (state)
            S_IDLE: next_state = tile_valid ? S_SCAN : S_IDLE;
            S_SCAN: next_state = (ptr == TILE_SIZE - 1) ? S_EVAL : S_SCAN;
            S_EVAL: next_state = S_COMP;
            S_COMP: next_state = (ptr == TILE_SIZE - 1) ? S_IDLE : S_COMP;
            default: next_state = S_IDLE;
        endcase
    end

    // Counter & Control Signals
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ptr            <= 0;
            zero_count     <= 0;
            mode_latched   <= 0;
            rd_addr        <= 0;
            mac_en_internal <= 0;
            acc_en_internal <= 0;
            acc_clr        <= 0;
            done_internal  <= 0;
        end else begin
            mac_en_internal <= 0;
            acc_en_internal <= 0;
            acc_clr         <= 0;
            done_internal   <= 0;

            case (state)
                S_IDLE: begin
                    ptr        <= 0;
                    zero_count <= 0;
                    if (tile_valid) acc_clr <= 1'b1;
                end

                S_SCAN: begin
                    if (is_zero) zero_count <= zero_count + 1'b1;
                    if (ptr == TILE_SIZE - 1) begin
                        ptr <= 0;
                    end else begin
                        ptr <= ptr + 1'b1;
                    end
                    rd_addr <= ptr;
                end

                S_EVAL: begin
                    mode_latched <= use_sparse;
                    // -------------------------------------------------
                    // BUG FIX #2: Start ptr at 1 instead of 0.
                    // rd_addr is set to 0 here, so element [0] is
                    // already presented to MAC on the first S_COMP
                    // cycle. ptr=1 ensures the NEXT cycle advances
                    // rd_addr to 1, avoiding a double-read of [0].
                    // -------------------------------------------------
                    ptr          <= 1;       // was 0 — caused double-read
                    rd_addr      <= 0;
                end

                S_COMP: begin
                    rd_addr <= ptr;
                    
                    // Execution Decision Logic
                    if (!mode_latched) begin
                        // DENSE MODE: Compute all operands unconditionally
                        mac_en_internal <= 1'b1;
                        acc_en_internal <= 1'b1;
                    end else begin
                        // SPARSE MODE: Skip zero-valued operands
                        if (!is_zero) begin
                            mac_en_internal <= 1'b1;
                            acc_en_internal <= 1'b1;
                        end
                    end

                    if (ptr == TILE_SIZE - 1) begin
                        done_internal <= 1'b1;
                        ptr  <= 0;
                    end else begin
                        ptr <= ptr + 1'b1;
                    end
                end
            endcase
        end
    end

endmodule
