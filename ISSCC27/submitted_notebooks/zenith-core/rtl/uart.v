`default_nettype none
// UART TX
// 8N1, baud rate configurable con registros

module uart_tx #(
    parameter CLK_FREQ  = 27_000_000,
    parameter BAUD_RATE = 115200
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] data_in,      // Byte a enviar
    input  wire       tx_start,     // Pulso de 1 ciclo para iniciar
    output reg        tx_busy,      // 1 mientras transmite
    output reg        tx            // Pin serial siempre tira 1 sinoi se usa
);

    localparam BAUD_DIV = CLK_FREQ / BAUD_RATE;

    localparam ST_IDLE  = 2'd0;
    localparam ST_START = 2'd1;
    localparam ST_DATA  = 2'd2;
    localparam ST_STOP  = 2'd3;

    reg [1:0]  state;
    reg [2:0]  bit_idx;
    reg [7:0]  shift_reg;
    reg [15:0] baud_cnt;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state     <= ST_IDLE;
            tx        <= 1'b1;
            tx_busy   <= 1'b0;
            bit_idx   <= 3'd0;
            shift_reg <= 8'h00;
            baud_cnt  <= 16'd0;
        end else begin
            case (state)
                ST_IDLE: begin
                    tx      <= 1'b1;
                    tx_busy <= 1'b0;
                    if (tx_start) begin
                        shift_reg <= data_in;
                        tx_busy   <= 1'b1;
                        baud_cnt  <= 16'd0;
                        state     <= ST_START;
                    end
                end

                ST_START: begin
                    tx <= 1'b0;                         // start bit
                    if (baud_cnt < BAUD_DIV - 1) begin
                        baud_cnt <= baud_cnt + 1;
                    end else begin
                        baud_cnt <= 16'd0;
                        bit_idx  <= 3'd0;
                        state    <= ST_DATA;
                    end
                end

                ST_DATA: begin
                    tx <= shift_reg[0];                 // LSB primero
                    if (baud_cnt < BAUD_DIV - 1) begin
                        baud_cnt <= baud_cnt + 1;
                    end else begin
                        baud_cnt  <= 16'd0;
                        shift_reg <= {1'b0, shift_reg[7:1]};
                        if (bit_idx == 3'd7) begin
                            state <= ST_STOP;
                        end else begin
                            bit_idx <= bit_idx + 1;
                        end
                    end
                end

                ST_STOP: begin
                    tx <= 1'b1;                         // stop bit
                    if (baud_cnt < BAUD_DIV - 1) begin
                        baud_cnt <= baud_cnt + 1;
                    end else begin
                        baud_cnt <= 16'd0;
                        state    <= ST_IDLE;
                    end
                end

                default: state <= ST_IDLE;
            endcase
        end
    end

endmodule


// UART RX 
// Receptor para programar la instruction mem

module uart_rx #(
    parameter CLK_FREQ  = 27_000_000,
    parameter BAUD_RATE = 115200
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       rx,
    output reg  [7:0] data_out,
    output reg        data_valid
);
    // usa CLK_FRE en MHz: CYCLE = CLK_FRE * 1000000 / BAUD_RATE
    // se recibe en CLK_FREQ en Hz
    localparam CYCLE     = CLK_FREQ / BAUD_RATE;
    localparam HALF_CYCLE = CYCLE / 2;

    localparam S_IDLE     = 3'd0;
    localparam S_START    = 3'd1;
    localparam S_REC_BYTE = 3'd2;
    localparam S_STOP     = 3'd3;
    localparam S_DATA     = 3'd4;

    reg [2:0]  state;
    reg [2:0]  next_state;

    reg        rx_d0, rx_d1;
    wire       rx_negedge = rx_d1 & ~rx_d0;  // flanco de bajada

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rx_d0 <= 1'b1; rx_d1 <= 1'b1; end
        else        begin rx_d0 <= rx;   rx_d1 <= rx_d0; end
    end

    reg [7:0]  rx_bits;
    reg [15:0] cycle_cnt;
    reg [2:0]  bit_cnt;

    // maquina de estados
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) state <= S_IDLE;
        else        state <= next_state;
    end

    always @(*) begin
        case (state)
            S_IDLE:
                next_state = rx_negedge ? S_START : S_IDLE;
            S_START:
                next_state = (cycle_cnt == CYCLE - 1) ? S_REC_BYTE : S_START;
            S_REC_BYTE:
                next_state = (cycle_cnt == CYCLE - 1 && bit_cnt == 3'd7) ? S_STOP : S_REC_BYTE;
            S_STOP:
                
                next_state = (cycle_cnt == HALF_CYCLE - 1) ? S_DATA : S_STOP;
            S_DATA:
                next_state = S_IDLE; 
            default:
                next_state = S_IDLE;
        endcase
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            data_valid <= 1'b0;
        else if (state == S_STOP && next_state != state)
            data_valid <= 1'b1;
        else if (state == S_DATA)
            data_valid <= 1'b0;
        else
            data_valid <= 1'b0;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            data_out <= 8'd0;
        else if (state == S_STOP && next_state != state)
            data_out <= rx_bits;
    end

    // Contador de bits
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            bit_cnt <= 3'd0;
        else if (state == S_REC_BYTE) begin
            if (cycle_cnt == CYCLE - 1)
                bit_cnt <= bit_cnt + 3'd1;
        end else
            bit_cnt <= 3'd0;
    end

    // Contador de baud
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            cycle_cnt <= 16'd0;
        else if ((state == S_REC_BYTE && cycle_cnt == CYCLE - 1) ||
                 next_state != state)
            cycle_cnt <= 16'd0;
        else
            cycle_cnt <= cycle_cnt + 16'd1;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            rx_bits <= 8'd0;
        else if (state == S_REC_BYTE && cycle_cnt == HALF_CYCLE - 1)
            rx_bits[bit_cnt] <= rx_d0; 
    end

endmodule

// Registros:
//   0x83 UART_TX   (W) - escribe byte para transmitir
//   0x84 UART_STAT (R) - bit0 = ocupado

module uart_mmio #(
    parameter CLK_FREQ  = 27_000_000,
    parameter BAUD_RATE = 115200
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire [7:0]  mmio_addr,
    input  wire [7:0]  mmio_data_in,
    output reg  [7:0]  mmio_data_out,
    input  wire        mmio_we,
    input  wire        mmio_re,

    // Pines fisico
    output wire        uart_tx_pin
);

    localparam ADDR_TX   = 8'h83;
    localparam ADDR_STAT = 8'h84;

    reg [7:0] tx_data;
    reg       tx_start;
    wire      tx_busy;

    uart_tx #(
        .CLK_FREQ  (CLK_FREQ),
        .BAUD_RATE (BAUD_RATE)
    ) u_tx (
        .clk      (clk),
        .rst_n    (rst_n),
        .data_in  (tx_data),
        .tx_start (tx_start),
        .tx_busy  (tx_busy),
        .tx       (uart_tx_pin)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tx_data  <= 8'h00;
            tx_start <= 1'b0;
        end else begin
            tx_start <= 1'b0;
            if (mmio_we && mmio_addr == ADDR_TX && !tx_busy) begin
                tx_data  <= mmio_data_in;
                tx_start <= 1'b1;
            end
        end
    end

    always @(*) begin
        mmio_data_out = 8'h00;
        if (mmio_re && mmio_addr == ADDR_STAT)
            mmio_data_out = {7'b0, tx_busy};
    end

endmodule

`default_nettype wire