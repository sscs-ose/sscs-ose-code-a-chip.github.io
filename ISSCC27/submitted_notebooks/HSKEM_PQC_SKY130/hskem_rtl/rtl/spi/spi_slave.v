// ============================================================================

// spi_slave.v  -  SPI Mode-0 slave (bit) + trustedge_frame

// ============================================================================

module spi_slave #(

    parameter integer MAX_PAYLOAD = 64

) (

    input  wire        clk,

    input  wire        rst_n,

    input  wire        cs_n,

    input  wire        sck,

    input  wire        mosi,

    output reg         miso,

    output wire        irq,

    input  wire        enrolled,

    input  wire        session_valid,

    input  wire        ota_pending,
    input  wire        ota_ok_seen,
    input  wire        ota_deny_seen,
    input  wire [7:0]  verify_fail_count,

    output wire        frame_valid,

    output wire [7:0]  frame_cmd,

    output wire [15:0] frame_pl_len,

    output wire [7:0]  frame_pl [0:MAX_PAYLOAD-1],

    output wire        crc_error,

    output wire        reset_pulse,

    input  wire        ext_tx_load,

    input  wire [7:0]  ext_tx_len,

    input  wire [7:0]  ext_tx_buf [0:39]

);

    // SPI pins are asynchronous to clk. Preserve the two-stage synchronizers
    // so implementation tools do not retime them into ordinary logic.
    (* ASYNC_REG = "TRUE" *) reg cs_s1, cs_s2;
    (* ASYNC_REG = "TRUE" *) reg sck_s1, sck_s2;
    (* ASYNC_REG = "TRUE" *) reg mosi_s1, mosi_s2;
    reg sck_prev;

    always @(posedge clk or negedge rst_n) begin

        if (!rst_n) begin

            cs_s1 <= 1'b1; cs_s2 <= 1'b1;
            sck_s1 <= 1'b0; sck_s2 <= 1'b0; sck_prev <= 1'b0;
            mosi_s1 <= 1'b0; mosi_s2 <= 1'b0;

        end else begin

            cs_s1    <= cs_n;
            cs_s2    <= cs_s1;

            sck_s1   <= sck;
            sck_s2   <= sck_s1;

            sck_prev <= sck_s2;

            mosi_s1  <= mosi;
            mosi_s2  <= mosi_s1;

        end

    end



    wire cs_active = !cs_s2;

    wire sck_rise  = sck_s2 & !sck_prev;

    wire sck_fall  = !sck_s2 & sck_prev;



    reg [7:0] rx_sh;

    reg [2:0] rx_bc;

    reg       rx_byte_valid;

    reg [7:0] rx_byte;



    always @(posedge clk or negedge rst_n) begin

        if (!rst_n) begin

            rx_sh <= 8'h00; rx_bc <= 3'd0;

            rx_byte_valid <= 1'b0; rx_byte <= 8'h00;

        end else begin

            rx_byte_valid <= 1'b0;

            if (!cs_active) begin

                rx_sh <= 8'h00; rx_bc <= 3'd0;

            end else if (sck_rise) begin

                rx_sh <= {rx_sh[6:0], mosi_s2};

                if (rx_bc == 3'd7) begin

                    rx_byte       <= {rx_sh[6:0], mosi_s2};

                    rx_byte_valid <= 1'b1;

                    rx_bc         <= 3'd0;

                end else

                    rx_bc <= rx_bc + 3'd1;

            end

        end

    end



    wire       tx_byte_valid;

    wire [7:0] tx_byte;

    reg        tx_ready;



    trustedge_frame #(.MAX_PAYLOAD(MAX_PAYLOAD)) u_frame (

        .clk(clk), .rst_n(rst_n),

        .rx_byte_valid(rx_byte_valid), .rx_byte(rx_byte),

        .tx_byte_valid(tx_byte_valid), .tx_byte(tx_byte),

        .tx_byte_ready(tx_ready),

        .enrolled(enrolled), .session_valid(session_valid), .ota_pending(ota_pending),
        .ota_ok_seen(ota_ok_seen), .ota_deny_seen(ota_deny_seen),
        .verify_fail_count(verify_fail_count),
        .cs_active(cs_active),

        .frame_valid(frame_valid), .frame_cmd(frame_cmd),

        .frame_pl_len(frame_pl_len), .frame_pl(frame_pl),

        .crc_error(crc_error), .reset_pulse(reset_pulse), .irq(irq),

        .ext_tx_load(ext_tx_load), .ext_tx_len(ext_tx_len), .ext_tx_buf(ext_tx_buf)

    );



    reg [7:0] tx_sh;

    reg [2:0] tx_bc;

    reg       tx_busy;



    always @(posedge clk or negedge rst_n) begin

        if (!rst_n) begin

            miso <= 1'b0; tx_busy <= 1'b0; tx_bc <= 3'd0;

            tx_ready <= 1'b1;

        end else begin

            tx_ready <= cs_active && !tx_busy && !tx_byte_valid && (rx_bc == 3'd0) && !sck_s2;

            if (!cs_active) begin

                miso <= 1'b0; tx_busy <= 1'b0; tx_bc <= 3'd0;

            end else begin

                if (!tx_busy && tx_byte_valid) begin

                    tx_sh   <= tx_byte;

                    tx_busy <= 1'b1;

                    tx_bc   <= 3'd0;

                    miso    <= tx_byte[7];

                end else if (tx_busy && sck_fall) begin

                    if (tx_bc == 3'd7) begin

                        tx_busy <= 1'b0;

                        miso    <= 1'b0;

                    end else begin

                        tx_bc <= tx_bc + 3'd1;

                        tx_sh <= {tx_sh[6:0], 1'b0};

                        miso  <= tx_sh[6];

                    end

                end

            end

        end

    end



endmodule

