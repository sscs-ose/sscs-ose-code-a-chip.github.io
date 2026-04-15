`timescale 1ps/1ps

//**************************************************************************
// Module      : dll_controller_updown_filtered
// Author      : Mythri Muralikannan
// Description : Filtered up/down DLL controller
//**************************************************************************

module controller #(
    parameter integer CTRL_BITS   = 6,
    parameter integer INIT_CTRL   = 32,
    parameter integer FILTER_LEN  = 4
)(
    input  wire                 clk_in,
    input  wire                 rst,
    input  wire                 up,
    input  wire                 down,
    output reg  [CTRL_BITS-1:0] ctrl
);

    localparam integer MAX_CTRL = (1 << CTRL_BITS) - 1;
    localparam [CTRL_BITS-1:0] ZERO_CTRL = {CTRL_BITS{1'b0}};
    localparam [CTRL_BITS-1:0] MAX_CTRL_VEC = MAX_CTRL[CTRL_BITS-1:0];

    localparam integer CNT_BITS = (FILTER_LEN <= 1) ? 1 : $clog2(FILTER_LEN + 1);

    reg [CNT_BITS-1:0] up_count;
    reg [CNT_BITS-1:0] down_count;

    always @(posedge clk_in or posedge rst) begin
        if (rst) begin
            up_count   <= {CNT_BITS{1'b0}};
            down_count <= {CNT_BITS{1'b0}};

            if (INIT_CTRL < 0)
                ctrl <= ZERO_CTRL;
            else if (INIT_CTRL > MAX_CTRL)
                ctrl <= MAX_CTRL_VEC;
            else
                ctrl <= INIT_CTRL[CTRL_BITS-1:0];
        end else begin
            case ({up, down})
                2'b10: begin
                    down_count <= {CNT_BITS{1'b0}};
                    if (up_count < FILTER_LEN)
                        up_count <= up_count + 1'b1;

                    if (up_count == FILTER_LEN - 1) begin
                        if (ctrl < MAX_CTRL_VEC)
                            ctrl <= ctrl + 1'b1;
                        up_count <= {CNT_BITS{1'b0}};
                    end
                end

                2'b01: begin
                    up_count <= {CNT_BITS{1'b0}};
                    if (down_count < FILTER_LEN)
                        down_count <= down_count + 1'b1;

                    if (down_count == FILTER_LEN - 1) begin
                        if (ctrl > ZERO_CTRL)
                            ctrl <= ctrl - 1'b1;
                        down_count <= {CNT_BITS{1'b0}};
                    end
                end

                default: begin
                    up_count   <= {CNT_BITS{1'b0}};
                    down_count <= {CNT_BITS{1'b0}};
                    ctrl       <= ctrl;
                end
            endcase
        end
    end

endmodule