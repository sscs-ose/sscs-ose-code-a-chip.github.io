// tb_brick_sensor_if.v -- cocotb testbench. MISO is looped back to MOSI so the
// SPI master test verifies full-duplex shifting without an external slave model.
`timescale 1ns/1ps
module tb_brick_sensor_if;
    reg        clk;
    reg        rst_n;
    reg  [3:0] addr;
    reg  [7:0] wdata;
    reg        we;
    reg        re;
    wire [7:0] rdata;
    wire       spi_sclk_o, spi_mosi_o, spi_cs_n_o;
    wire       spi_miso_i;
    wire       can_tx_o, can_busy_o;

    assign spi_miso_i = spi_mosi_o;  // loopback

    brick_sensor_if dut (
        .clk        (clk),
        .rst_n      (rst_n),
        .addr_i     (addr),
        .wdata_i    (wdata),
        .we_i       (we),
        .re_i       (re),
        .rdata_o    (rdata),
        .spi_sclk_o (spi_sclk_o),
        .spi_mosi_o (spi_mosi_o),
        .spi_miso_i (spi_miso_i),
        .spi_cs_n_o (spi_cs_n_o),
        .can_tx_o   (can_tx_o),
        .can_busy_o (can_busy_o)
    );

    // NOTE: clk is driven by cocotb's Clock (see test_sensor_if.py).
    // Do NOT generate it here -- two drivers cause intermittent failures.

    initial begin
        $dumpfile("dump.vcd");
        $dumpvars(0, tb_brick_sensor_if);
    end
endmodule
