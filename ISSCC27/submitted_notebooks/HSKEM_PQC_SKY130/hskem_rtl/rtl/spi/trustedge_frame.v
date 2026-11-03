// ============================================================================
// trustedge_frame.v  -  Xu ly khung giao thuc TrustEdge (byte interface)
// ============================================================================
module trustedge_frame #(
    parameter integer MAX_PAYLOAD = 64
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        rx_byte_valid,
    input  wire [7:0]  rx_byte,
    output reg         tx_byte_valid,
    output reg  [7:0]  tx_byte,
    input  wire        tx_byte_ready,
    input  wire        enrolled,
    input  wire        session_valid,
    input  wire        ota_pending,
    input  wire        ota_ok_seen,
    input  wire        ota_deny_seen,
    input  wire [7:0]  verify_fail_count,
    input  wire        cs_active,
    output reg         frame_valid,
    output reg  [7:0]  frame_cmd,
    output reg  [15:0] frame_pl_len,
    output reg  [7:0]  frame_pl [0:MAX_PAYLOAD-1],
    output reg         crc_error,
    output reg         reset_pulse,
    output reg         irq,
    input  wire        ext_tx_load,
    input  wire [7:0]  ext_tx_len,
    input  wire [7:0]  ext_tx_buf [0:39]
);
    localparam [7:0] SOF            = 8'hA5;
    localparam [7:0] CMD_STATUS     = 8'hF0;
    localparam [7:0] CMD_RESET      = 8'hFF;
    localparam [7:0] STATUS_RSP_LEN = 8'd10;

    localparam [2:0] RX_IDLE=0, RX_CMD=1, RX_LEN0=2, RX_LEN1=3,
                     RX_DATA=4, RX_CRC0=5, RX_CRC1=6, RX_DROP=7;

    reg [2:0]  rx_st;
    reg [7:0]  cmd_r;
    reg [15:0] len_r, data_cnt;
    reg [7:0]  payload [0:MAX_PAYLOAD-1];
    reg [7:0]  crc0_r;
    reg [15:0] crc_acc;

    reg [7:0]  tx_buf [0:39];
    reg [7:0]  tx_len;
    reg [7:0]  tx_idx;
    reg        tx_busy;
    reg        tx_load;
    reg        tx_ready_d;

    integer    pi_rx;
    integer    pi_tx;

    function automatic [15:0] crc16_byte;
        input [15:0] c;
        input [7:0]  d;
        integer i;
        reg [15:0] x;
        begin
            x = c ^ {d, 8'h00};
            for (i = 0; i < 8; i = i + 1) begin
                if (x[15])
                    x = {x[14:0], 1'b0} ^ 16'h1021;
                else
                    x = {x[14:0], 1'b0};
            end
            crc16_byte = x;
        end
    endfunction

    reg [15:0] crc_expect;
    reg [7:0]  status_byte_r;
    reg [15:0] status_crc_r;

    // --- RX FSM (khong ghi tx_buf) ---
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rx_st        <= RX_IDLE;
            frame_valid  <= 1'b0;
            crc_error    <= 1'b0;
            reset_pulse  <= 1'b0;
            frame_cmd    <= 8'h00;
            frame_pl_len <= 16'd0;
            tx_load      <= 1'b0;
            irq          <= 1'b0;
        end else begin
            frame_valid <= 1'b0;
            crc_error   <= 1'b0;
            reset_pulse <= 1'b0;
            tx_load     <= 1'b0;
            irq         <= 1'b0;

            if (!cs_active) begin
                rx_st    <= RX_IDLE;
                data_cnt <= 16'd0;
            end else if (rx_byte_valid) begin
                case (rx_st)
                    RX_IDLE: begin
                        if (rx_byte == SOF)
                            rx_st <= RX_CMD;
                    end
                    RX_CMD: begin
                        cmd_r   <= rx_byte;
                        crc_acc <= crc16_byte(16'hFFFF, rx_byte);
                        rx_st   <= RX_LEN0;
                    end
                    RX_LEN0: begin
                        len_r[15:8] <= rx_byte;
                        crc_acc     <= crc16_byte(crc_acc, rx_byte);
                        rx_st       <= RX_LEN1;
                    end
                    RX_LEN1: begin
                        len_r[7:0] <= rx_byte;
                        data_cnt   <= 16'd0;
                        crc_acc    <= crc16_byte(crc_acc, rx_byte);
                        // Reject an oversized frame before accepting any
                        // payload byte.  Stay in RX_DROP until CS is released
                        // so an embedded SOF byte cannot resynchronize and
                        // reach the command bridge inside the same malformed
                        // transaction.
                        if ({len_r[15:8], rx_byte} > MAX_PAYLOAD)
                            rx_st <= RX_DROP;
                        else if ({len_r[15:8], rx_byte} == 16'd0)
                            rx_st <= RX_CRC0;
                        else
                            rx_st <= RX_DATA;
                    end
                    RX_DATA: begin
                        if (data_cnt < MAX_PAYLOAD)
                            payload[data_cnt[7:0]] <= rx_byte;
                        crc_acc  <= crc16_byte(crc_acc, rx_byte);
                        data_cnt <= data_cnt + 16'd1;
                        if (data_cnt + 16'd1 >= len_r)
                            rx_st <= RX_CRC0;
                    end
                    RX_CRC0: begin
                        crc0_r <= rx_byte;
                        rx_st  <= RX_CRC1;
                    end
                    RX_CRC1: begin
                        crc_expect = {crc0_r, rx_byte};
                        if (crc_acc !== crc_expect) begin
                            crc_error <= 1'b1;
                        end else begin
                            frame_valid  <= 1'b1;
                            frame_cmd    <= cmd_r;
                            frame_pl_len <= len_r;
                            for (pi_rx = 0; pi_rx < MAX_PAYLOAD; pi_rx = pi_rx + 1) begin
                                if (pi_rx < len_r)
                                    frame_pl[pi_rx] <= payload[pi_rx];
                            end
                            if (cmd_r == CMD_RESET)
                                reset_pulse <= 1'b1;
                            if (cmd_r == CMD_STATUS && !tx_busy) begin
                                tx_load <= 1'b1;
                                irq     <= 1'b1;
                            end
                        end
                        rx_st <= RX_IDLE;
                    end
                    RX_DROP: begin
                        rx_st <= RX_DROP;
                    end
                    default: rx_st <= RX_IDLE;
                endcase
            end
        end
    end

    // --- TX: driver duy nhat cho tx_buf ---
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tx_byte_valid <= 1'b0;
            tx_byte       <= 8'h00;
            tx_busy       <= 1'b0;
            tx_idx        <= 8'd0;
            tx_len        <= 8'd0;
            tx_ready_d    <= 1'b0;
        end else begin
            tx_byte_valid <= 1'b0;
            tx_ready_d    <= tx_byte_ready;

            if (!cs_active) begin
                tx_busy <= 1'b0;
                tx_idx  <= 8'd0;
                tx_ready_d <= 1'b0;
            end else if (ext_tx_load && !tx_busy) begin
                for (pi_tx = 0; pi_tx < 40; pi_tx = pi_tx + 1)
                    tx_buf[pi_tx] <= ext_tx_buf[pi_tx];
                tx_busy <= 1'b1;
                tx_idx  <= 8'd0;
                tx_len  <= ext_tx_len;
                tx_ready_d <= 1'b0;
            end else if (tx_load && !tx_busy) begin
                status_byte_r = {3'b0, ota_deny_seen, ota_ok_seen,
                                 ota_pending, session_valid, enrolled};
                status_crc_r  = 16'hFFFF;
                status_crc_r  = crc16_byte(status_crc_r, CMD_STATUS);
                status_crc_r  = crc16_byte(status_crc_r, 8'd0);
                status_crc_r  = crc16_byte(status_crc_r, 8'd4);
                status_crc_r  = crc16_byte(status_crc_r, status_byte_r);
                status_crc_r  = crc16_byte(status_crc_r, verify_fail_count);
                status_crc_r  = crc16_byte(status_crc_r, 8'd0);
                status_crc_r  = crc16_byte(status_crc_r, 8'd0);
                tx_buf[0]  <= SOF;
                tx_buf[1]  <= CMD_STATUS;
                tx_buf[2]  <= 8'd0;
                tx_buf[3]  <= 8'd4;
                tx_buf[4]  <= status_byte_r;
                tx_buf[5]  <= verify_fail_count;
                tx_buf[6]  <= 8'd0;
                tx_buf[7]  <= 8'd0;
                tx_buf[8]  <= status_crc_r[15:8];
                tx_buf[9]  <= status_crc_r[7:0];
                tx_busy    <= 1'b1;
                tx_idx     <= 8'd0;
                tx_len     <= STATUS_RSP_LEN;
                tx_ready_d <= 1'b0;
            end else if (tx_busy && tx_byte_ready && !tx_ready_d) begin
                tx_byte       <= tx_buf[tx_idx];
                tx_byte_valid <= 1'b1;
                if (tx_idx + 8'd1 >= tx_len) begin
                    tx_busy <= 1'b0;
                    tx_idx  <= 8'd0;
                end else begin
                    tx_idx <= tx_idx + 8'd1;
                end
            end
        end
    end

endmodule
