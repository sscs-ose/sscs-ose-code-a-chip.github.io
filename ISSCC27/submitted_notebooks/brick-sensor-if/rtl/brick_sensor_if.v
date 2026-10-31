// brick_sensor_if.v -- Sensor-interface IP for the LEGO smart brick.
// Byte-wide register bus glues together:
//   - spi_master : burst-reads the on-brick IMU (ICM-42688-P/BMI270 style)
//   - can_framer : packs the samples into CAN 2.0A data frames for the brick bus
//
// Register map (addr[3:0]):
//   0x0  CTRL (W):  bit0=start SPI xfer (self-clearing), bit1=start CAN frame,
//                   bit2=clear done-stickies
//   0x1  STATUS (R): bit0=spi_busy, bit1=can_busy, bit2=spi_done(sticky,W1C),
//                    bit3=can_done(sticky,W1C)
//   0x2  SPI_CLKDIV (RW)   0x3  SPI_LEN bytes 1..8 (RW, low 4 bits)
//   0x4  CAN_ID[7:0] (RW)  0x5  CAN_ID[10:8] (RW)   0x6  CAN_DLC (RW, low 4 bits)
//   0x7  CAN_BITDIV (RW)
//   0x8-0xF  DATA_BUF[0..7] (RW): SPI RX lands here on done; CAN TX reads it.
// Reads return data one cycle after re_i.
module brick_sensor_if (
    input  wire       clk,
    input  wire       rst_n,
    // simple byte-wide register bus
    input  wire [3:0] addr_i,
    input  wire [7:0] wdata_i,
    input  wire       we_i,        // write strobe, 1 cycle
    input  wire       re_i,        // read strobe, 1 cycle
    output reg  [7:0] rdata_o,
    // SPI to IMU
    output wire       spi_sclk_o,
    output wire       spi_mosi_o,
    input  wire       spi_miso_i,
    output wire       spi_cs_n_o,
    // CAN to brick bus
    output wire       can_tx_o,
    output wire       can_busy_o
);

    // ---- registers ----
    reg [7:0]  spi_clkdiv;
    reg [3:0]  spi_len;      // 1..8
    reg [10:0] can_id;
    reg [3:0]  can_dlc;      // 0..8
    reg [7:0]  can_bitdiv;
    reg [7:0]  dbuf [0:7];
    reg        spi_done_st;
    reg        can_done_st;
    reg        spi_start;    // 1-cycle pulses to submodules
    reg        can_start;

    wire       spi_busy, spi_done_p;
    wire       can_busy, can_done_p;
    wire [63:0] spi_rx_word;
    wire [63:0] dbuf_word;
    integer i;

    assign dbuf_word   = {dbuf[7], dbuf[6], dbuf[5], dbuf[4], dbuf[3], dbuf[2], dbuf[1], dbuf[0]};
    assign can_busy_o = can_busy;

    spi_master u_spi (
        .clk      (clk),
        .rst_n    (rst_n),
        .start_i  (spi_start),
        .len_i    (spi_len == 4'd0 ? 4'd8 : spi_len),
        .clkdiv_i (spi_clkdiv),
        .tx_word_i(dbuf_word),
        .rx_word_o(spi_rx_word),
        .busy_o   (spi_busy),
        .done_o   (spi_done_p),
        .sclk_o   (spi_sclk_o),
        .mosi_o   (spi_mosi_o),
        .miso_i   (spi_miso_i),
        .cs_n_o   (spi_cs_n_o)
    );

    can_framer u_can (
        .clk     (clk),
        .rst_n   (rst_n),
        .start_i (can_start),
        .id_i    (can_id),
        .dlc_i   (can_dlc > 4'd8 ? 4'd8 : can_dlc),
        .data_i  (dbuf_word),
        .bitdiv_i(can_bitdiv),
        .tx_o    (can_tx_o),
        .busy_o  (can_busy),
        .done_o  (can_done_p)
    );

    // ---- register file ----
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            spi_clkdiv <= 8'd49;   // 1 MHz SCLK @ 100 MHz sysclk
            spi_len    <= 4'd8;
            can_id     <= 11'h100;
            can_dlc    <= 4'd8;
            can_bitdiv <= 8'd99;   // 1 Mbps @ 100 MHz sysclk
            spi_done_st <= 1'b0;
            can_done_st <= 1'b0;
            spi_start  <= 1'b0;
            can_start  <= 1'b0;
            for (i = 0; i < 8; i = i + 1) dbuf[i] <= 8'd0;
        end else begin
            spi_start <= 1'b0;
            can_start <= 1'b0;
            if (we_i) begin
                case (addr_i)
                    4'h0: begin
                        if (wdata_i[0] && !spi_busy) spi_start <= 1'b1;
                        if (wdata_i[1] && !can_busy) can_start <= 1'b1;
                        if (wdata_i[2]) begin
                            spi_done_st <= 1'b0;
                            can_done_st <= 1'b0;
                        end
                    end
                    4'h1: begin  // W1C on sticky bits
                        spi_done_st <= spi_done_st & ~wdata_i[2];
                        can_done_st <= can_done_st & ~wdata_i[3];
                    end
                    4'h2: spi_clkdiv <= wdata_i;
                    4'h3: spi_len    <= wdata_i[3:0];
                    4'h4: can_id[7:0]  <= wdata_i;
                    4'h5: can_id[10:8] <= wdata_i[2:0];
                    4'h6: can_dlc    <= wdata_i[3:0];
                    4'h7: can_bitdiv <= wdata_i;
                    default: dbuf[addr_i[2:0]] <= wdata_i;  // 0x8..0xF
                endcase
            end
            // submodule completion (wins over a same-cycle W1C clear)
            if (spi_done_p) begin
                for (i = 0; i < 8; i = i + 1)
                    dbuf[i] <= spi_rx_word[8*i +: 8];
                spi_done_st <= 1'b1;
            end
            if (can_done_p) can_done_st <= 1'b1;
        end
    end

    // ---- reads: data available one cycle after re_i ----
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rdata_o <= 8'd0;
        end else if (re_i) begin
            case (addr_i)
                4'h0: rdata_o <= 8'd0;
                4'h1: rdata_o <= {4'd0, can_done_st, spi_done_st, can_busy, spi_busy};
                4'h2: rdata_o <= spi_clkdiv;
                4'h3: rdata_o <= {4'd0, spi_len};
                4'h4: rdata_o <= can_id[7:0];
                4'h5: rdata_o <= {5'd0, can_id[10:8]};
                4'h6: rdata_o <= {4'd0, can_dlc};
                4'h7: rdata_o <= can_bitdiv;
                default: rdata_o <= dbuf[addr_i[2:0]];
            endcase
        end
    end

endmodule
