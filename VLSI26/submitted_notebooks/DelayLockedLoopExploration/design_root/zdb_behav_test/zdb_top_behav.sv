`timescale 1ns/1ps

module zdb_top #(
    parameter integer CTRL_BITS        = 6,
    parameter integer INIT_CTRL        = (1 << (CTRL_BITS-1)),

    parameter integer DELAY_PS         = 100,
    parameter integer UPDATE_DIV_BITS  = 4,
    parameter integer RESET_DELAY_PS   = 0,
    parameter integer LOCK_COUNT_MAX   = 32
)(
    input  wire clk_in,
    input  wire rst,

    output wire clk_out,
    output wire locked,
    output wire [CTRL_BITS-1:0] ctrl_dbg
);

    wire up, down;
    wire [CTRL_BITS-1:0] ctrl;
    wire clk_delayed;

    dcdl #(
        .CTRL_BITS(CTRL_BITS),
        .DELAY_PS (DELAY_PS)
    ) u_dcdl (
        .clk_in  (clk_in),
        .ctrl    (ctrl),
        .clk_out (clk_delayed)
    );

    assign clk_out = clk_delayed;

    pfd #(
        .RESET_DELAY_PS(RESET_DELAY_PS)
    ) u_pfd (
        .clk_ref (clk_in),
        .clk_fb  (clk_out),
        .rst_n   (~rst),
        .up      (up),
        .down    (down)
    );

    // require UPDATE_DIV_BITS >= 1
    reg [UPDATE_DIV_BITS-1:0] update_div;

    always @(posedge clk_in or posedge rst) begin
        if (rst)
            update_div <= 0;
        else
            update_div <= update_div + 1;
    end

    wire update_en = (update_div == 0);

    controller #(
        .CTRL_BITS (CTRL_BITS),
        .INIT_CTRL (INIT_CTRL)
    ) u_ctrl (
        .clk_in    (clk_in),
        .rst       (rst),
        .up        (up),
        .down      (down),
        .update_en (update_en),
        .ctrl      (ctrl)
    );

    reg [$clog2(LOCK_COUNT_MAX+1)-1:0] lock_cnt;
    reg locked_r;

    always @(posedge clk_in or posedge rst) begin
        if (rst) begin
            lock_cnt <= 0;
            locked_r <= 0;
        end else begin
            if (~(up | down)) begin
                if (lock_cnt < LOCK_COUNT_MAX)
                    lock_cnt <= lock_cnt + 1;
            end else begin
                lock_cnt <= 0;
            end

            locked_r <= (lock_cnt >= LOCK_COUNT_MAX);
        end
    end

    assign locked   = locked_r;
    assign ctrl_dbg = ctrl;

endmodule