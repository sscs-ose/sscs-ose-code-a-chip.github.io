`default_nettype none
// Primer micro de 8 bits, arquitectura RISC-V (reducida xd)
// Mapa de memoria de datos
//   0x00-0x7F : RAM 128 bytes
//   0x80      : GPIO_OUT
//   0x81      : GPIO_IN
//   0x82      : GPIO_DIR
//   0x83      : UART_TX (W)
//   0x84      : UART_STAT (R)
//   0x85      : PWM_DUTY
//   0x86      : PWM_CTRL
//   0x87      : PWM_PRESCALER

module microrv8_system #(
    parameter CLK_FREQ  = 27_000_000,
    parameter BAUD_RATE = 115200
) (
    input  wire        clk,
    input  wire        rst_n,      

    // GPIOs Fisicos
    input  wire [7:0]  gpio_in,
    output wire [7:0]  gpio_out,
    output wire [7:0]  gpio_dir,

    // UART Fisico
    input  wire        uart_rx_pin,
    output wire        uart_tx_pin,

    // PWM Fisico
    output wire        pwm_pin,

    // Debug 
    output wire [7:0]  debug_pc,
    output wire [7:0]  debug_state,
    output wire [15:0] debug_instr,

    // Estado del loader (1 mientras carga un programa via UART)
    output wire        loader_active
);

    wire loader_loading;
    wire cpu_rst_n = rst_n & ~loader_loading;
    assign loader_active = loader_loading;

    // Bus CPU - Instruction Memory

    wire [8:0]  cpu_pc;
    wire [15:0] cpu_instr;

    // Bus CPU - Data Memory

    wire [7:0]  cpu_mem_addr;
    wire [7:0]  cpu_mem_wdata;
    wire [7:0]  cpu_mem_rdata;
    wire        cpu_mem_we;
    wire        cpu_mem_re;

    // Bus MMIO (data_memory -> a gpios)

    wire [7:0]  mmio_addr;
    wire [7:0]  mmio_data_wr;
    wire        mmio_we;
    wire        mmio_re;

    // Mux de lectura MMIO
    wire [7:0]  gpio_mmio_rd;
    wire [7:0]  uart_mmio_rd;
    wire [7:0]  pwm_mmio_rd;

    reg  [7:0]  mmio_data_rd;
    always @(*) begin
        case (mmio_addr)
            8'h80, 8'h81, 8'h82: mmio_data_rd = gpio_mmio_rd;
            8'h83, 8'h84:        mmio_data_rd = uart_mmio_rd;
            8'h85, 8'h86, 8'h87: mmio_data_rd = pwm_mmio_rd;
            default:             mmio_data_rd = 8'h00;
        endcase
    end

    // GPIO directo desde CPU (opcode OUT = 110)
    wire [7:0] cpu_gpio_direct;

    // Loader
    wire [8:0]  ldr_wr_addr;
    wire [15:0] ldr_wr_data;
    wire        ldr_wr_en;

    // Instancias

    cpu_core cpu (
        .clk            (clk),
        .rst_n          (cpu_rst_n),
        .pc_out         (cpu_pc),
        .instruction_in (cpu_instr),
        .mem_addr       (cpu_mem_addr),
        .mem_wdata      (cpu_mem_wdata),
        .mem_rdata      (cpu_mem_rdata),
        .mem_we         (cpu_mem_we),
        .mem_re         (cpu_mem_re),
        .gpio_out       (cpu_gpio_direct),
        .debug_pc       (debug_pc),
        .debug_state    (debug_state),
        .debug_instr    (debug_instr)
    );

    instruction_memory imem (
        .clk      (clk),
        .addr     (cpu_pc),
        .data_out (cpu_instr),
        .wr_addr  (ldr_wr_addr),
        .wr_data  (ldr_wr_data),
        .wr_en    (ldr_wr_en)
    );

    data_memory dmem (
        .clk          (clk),
        .rst_n        (rst_n),
        .addr         (cpu_mem_addr),
        .data_in      (cpu_mem_wdata),
        .we           (cpu_mem_we),
        .re           (cpu_mem_re),
        .data_out     (cpu_mem_rdata),
        .mmio_addr    (mmio_addr),
        .mmio_data_wr (mmio_data_wr),
        .mmio_data_rd (mmio_data_rd),
        .mmio_we      (mmio_we),
        .mmio_re      (mmio_re)
    );

    wire [7:0] gpio_out_mmio;
    wire [7:0] gpio_dir_int;

    gpio_8bit gpio (
        .clk          (clk),
        .rst_n        (rst_n),
        .mmio_addr    (mmio_addr),
        .mmio_data_in (mmio_data_wr),
        .mmio_data_out(gpio_mmio_rd),
        .mmio_we      (mmio_we),
        .mmio_re      (mmio_re),
        .gpio_in      (gpio_in),
        .gpio_out     (gpio_out_mmio),
        .gpio_dir     (gpio_dir_int)
    );
    assign gpio_dir = gpio_dir_int;

    assign gpio_out = gpio_out_mmio | cpu_gpio_direct;

    uart_mmio #(
        .CLK_FREQ  (CLK_FREQ),
        .BAUD_RATE (BAUD_RATE)
    ) uart (
        .clk          (clk),
        .rst_n        (rst_n),
        .mmio_addr    (mmio_addr),
        .mmio_data_in (mmio_data_wr),
        .mmio_data_out(uart_mmio_rd),
        .mmio_we      (mmio_we),
        .mmio_re      (mmio_re),
        .uart_tx_pin  (uart_tx_pin)
    );

    pwm_8bit pwm (
        .clk          (clk),
        .rst_n        (rst_n),
        .mmio_addr    (mmio_addr),
        .mmio_data_in (mmio_data_wr),
        .mmio_data_out(pwm_mmio_rd),
        .mmio_we      (mmio_we),
        .mmio_re      (mmio_re),
        .pwm_out      (pwm_pin)
    );

    uart_loader #(
        .CLK_FREQ  (CLK_FREQ),
        .BAUD_RATE (BAUD_RATE)
    ) loader (
        .clk      (clk),
        .rst_n    (rst_n),
        .rx       (uart_rx_pin),
        .wr_addr  (ldr_wr_addr),
        .wr_data  (ldr_wr_data),
        .wr_en    (ldr_wr_en),
        .loading  (loader_loading),
        .load_done()
    );

    wire _cpu_out_suppress = &{cpu_gpio_direct[7:0]}; 

endmodule

`default_nettype wire