`timescale 1ns / 1ps

module pixel_addr_gen #(
    parameter PIXEL_SCALE = 1 // 1: 640x480 native, 4: 160x120 (4x pixel replication)
)(
    input  wire [15:0] H_count,
    input  wire [15:0] V_count,
    input  wire        video_on,
    output wire [20:0] pixel_addr
);

    generate
        if (PIXEL_SCALE == 4) begin : g_scale4
            // 160x120 Framebuffer with 4x hardware pixel replication to 640x480
            // H_scaled in [0, 159], V_scaled in [0, 119]
            wire [13:0] h_scaled = H_count[15:2];
            wire [13:0] v_scaled = V_count[15:2];

            // Address = (V_scaled * 160 + H_scaled) * 4
            // 160 * 4 = 640 = 512 + 128 = (1 << 9) + (1 << 7)
            wire [20:0] v_term = {v_scaled[11:0], 9'd0} + {v_scaled[13:0], 7'd0};
            wire [20:0] h_term = {5'd0, h_scaled[13:0], 2'd0};

            assign pixel_addr = video_on ? (v_term + h_term) : 21'd0;
        end else begin : g_scale1
            // Native 640x480 Framebuffer: (V_count * 640 + H_count) * 4
            wire [20:0] v_term_11 = {V_count[9:0], 11'd0};
            wire [20:0] v_term_9  = {V_count[11:0], 9'd0};
            wire [20:0] h_term_2  = {3'd0, H_count[15:0], 2'd0};

            assign pixel_addr = video_on ? (v_term_11 + v_term_9 + h_term_2) : 21'd0;
        end
    endgenerate

endmodule
