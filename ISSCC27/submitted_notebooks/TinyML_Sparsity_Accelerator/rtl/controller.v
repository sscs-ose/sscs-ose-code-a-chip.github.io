`timescale 1ns / 1ps

module controller #(
    parameter TILE_SIZE = 16
)(
    input  wire clk,
    input  wire rst_n,
    input  wire tile_valid,
    input  wire is_zero,
    input  wire use_sparse,
    
    output wire [$clog2(TILE_SIZE)-1:0] rd_addr,
    output reg  [$clog2(TILE_SIZE+1)-1:0] zero_count,
    output reg  mode_latched,  // 0: Dense, 1: Sparse
    output wire mac_en,
    output reg  acc_en,        // Delayed by 1 cycle to match MAC pipeline latency
    output reg  acc_clr,
    output reg  done
);

    localparam S_IDLE  = 3'b000,
               S_SCAN  = 3'b001,
               S_EVAL  = 3'b010,
               S_COMP  = 3'b011,
               S_DRAIN = 3'b100;

    reg [2:0] state, next_state;
    reg [$clog2(TILE_SIZE)-1:0] ptr;

    // Combinational read address directly tracking pointer during SCAN and COMP
    assign rd_addr = ptr;

    // Combinational MAC enable: active in S_COMP whenever operand is not zero (or dense mode)
    assign mac_en = (state == S_COMP) && (!mode_latched || !is_zero);

    // FSM State Register
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) state <= S_IDLE;
        else        state <= next_state;
    end

    // Next State Logic
    always @(*) begin
        case (state)
            S_IDLE:  next_state = tile_valid ? S_SCAN : S_IDLE;
            S_SCAN:  next_state = (ptr == TILE_SIZE - 1) ? S_EVAL : S_SCAN;
            S_EVAL:  next_state = S_COMP;
            S_COMP:  next_state = (ptr == TILE_SIZE - 1) ? S_DRAIN : S_COMP;
            S_DRAIN: next_state = S_IDLE;
            default: next_state = S_IDLE;
        endcase
    end

    // Sequential Datapath & Control Registers
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ptr          <= 0;
            zero_count   <= 0;
            mode_latched <= 0;
            acc_en       <= 0;
            acc_clr      <= 0;
            done         <= 0;
        end else begin
            // Default single-cycle pulse resets
            acc_clr <= 1'b0;
            done    <= 1'b0;

            // Pipeline delay: acc_en matches MAC output latency (1 cycle)
            acc_en  <= mac_en;

            case (state)
                S_IDLE: begin
                    ptr        <= 0;
                    zero_count <= 0;
                    if (tile_valid) begin
                        acc_clr <= 1'b1; // Clear accumulator for new tile
                    end
                end

                S_SCAN: begin
                    // Count zeros combinationally matching rd_addr = ptr
                    if (is_zero) begin
                        zero_count <= zero_count + 1'b1;
                    end
                    if (ptr == TILE_SIZE - 1) begin
                        ptr <= 0;
                    end else begin
                        ptr <= ptr + 1'b1;
                    end
                end

                S_EVAL: begin
                    // Latch mode from cost estimator
                    mode_latched <= use_sparse;
                    ptr          <= 0;
                end

                S_COMP: begin
                    if (ptr == TILE_SIZE - 1) begin
                        ptr <= 0;
                    end else begin
                        ptr <= ptr + 1'b1;
                    end
                end

                S_DRAIN: begin
                    // Final product settles into accumulator at the end of this cycle
                    done <= 1'b1; // Pulse done signal
                end

                default: begin
                    ptr <= 0;
                end
            endcase
        end
    end

endmodule
