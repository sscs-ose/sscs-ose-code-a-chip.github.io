module controller #(
    parameter integer CTRL_BITS = 6,
    parameter integer INIT_CTRL = 4
)(
    input  wire                 clk_in,
    input  wire                 rst,
    input  wire                 up,
    input  wire                 down,
    input  wire                 update_en,
    output reg  [CTRL_BITS-1:0] ctrl
);

    localparam integer MAX_CTRL = (1 << CTRL_BITS) - 1;

    localparam [CTRL_BITS-1:0] MAX_CTRL_VEC = MAX_CTRL[CTRL_BITS-1:0];
    localparam [CTRL_BITS-1:0] ZERO_CTRL    = {CTRL_BITS{1'b0}};

    localparam [CTRL_BITS-1:0] INIT_CLAMPED =
        (INIT_CTRL > MAX_CTRL) ? MAX_CTRL_VEC :
                                 INIT_CTRL[CTRL_BITS-1:0];

    always @(posedge clk_in or posedge rst) begin
        if (rst) begin
            ctrl <= INIT_CLAMPED;
        end
        else if (update_en) begin
            case ({up, down})
                2'b10: if (ctrl != MAX_CTRL_VEC)
                    ctrl <= ctrl + 1'b1;

                2'b01: if (ctrl != ZERO_CTRL)
                    ctrl <= ctrl - 1'b1;

                2'b11: if (ctrl != MAX_CTRL_VEC)
                    ctrl <= ctrl + 1'b1;

                default: ;
            endcase
        end
    end

endmodule