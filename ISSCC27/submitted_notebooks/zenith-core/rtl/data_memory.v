`default_nettype none
//   0x00 - 0x7F : RAM de 128 bytes
//   0x80 - 0xFF : Memory-Mapped I/O
//     0x80 : GPIO_OUT   (W) - pines de salida
//     0x81 : GPIO_IN    (R) - pines de entrada
//     0x82 : GPIO_DIR   (W) - dirección de pines
//     0x83 : UART_TX    (W) - byte a transmitir
//     0x84 : UART_STAT  (R) - bit0 = tx_busy
//     0x85 : PWM_DUTY   (W) - duty cycle (0-255)
//     0x86 : PWM_CTRL   (W) - bit0 = enable
//     0x87 : reservado


module data_memory (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [7:0]  addr,
    input  wire [7:0]  data_in,
    input  wire        we,
    input  wire        re,
    output reg  [7:0]  data_out,

    output reg  [7:0]  mmio_addr,
    output reg  [7:0]  mmio_data_wr,   // dato hacia periférico
    input  wire [7:0]  mmio_data_rd,   // dato desde periférico
    output reg         mmio_we,
    output reg         mmio_re
);


    reg [7:0] ram [0:127];

    wire is_mmio = addr[7];             

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            data_out     <= 8'h00;
            mmio_addr    <= 8'h00;
            mmio_data_wr <= 8'h00;
            mmio_we      <= 1'b0;
            mmio_re      <= 1'b0;
            for (i = 0; i < 128; i = i + 1)
                ram[i] <= 8'h00;
        end else begin

            mmio_we <= 1'b0;
            mmio_re <= 1'b0;

            if (we) begin
                if (!is_mmio) begin
                    // Escribir RAM
                    ram[addr[6:0]] <= data_in;
                end else begin
                    // mmio
                    mmio_addr    <= addr;
                    mmio_data_wr <= data_in;
                    mmio_we      <= 1'b1;
                end
            end

            if (re) begin
                if (!is_mmio) begin
                    // Leer RAM
                    data_out <= ram[addr[6:0]];
                end else begin
                    // Leer mmio para el siguiente ciclo 
                    mmio_addr <= addr;
                    mmio_re   <= 1'b1;
                    data_out  <= mmio_data_rd;
                end
            end
        end
    end

endmodule

`default_nettype wire
