`default_nettype none
// PWM de 8 bits usando contador de 8 bits.
// Frecuencia PWM = CLK_FREQ / (PRESCALER * 256)
//
// Registros MMIO:
//   0x85 PWM_DUTY   (W)
//   0x86 PWM_CTRL   (W) - bit0=enable, bit1=invertidoo
//   0x87 PWM_PRE    (W) - prescaler (1-255, 0=sin prescaler=255)
//
// Ejemplo: CLK=27MHz, PRE=105 -> freq PWM = 27e6 / (105*256) = ~1 kHz

module pwm_8bit (
    input  wire       clk,
    input  wire       rst_n,

    // Bus MMIO
    input  wire [7:0] mmio_addr,
    input  wire [7:0] mmio_data_in,
    output reg  [7:0] mmio_data_out,
    input  wire       mmio_we,
    input  wire       mmio_re,

    // Pin de salida PWM
    output reg        pwm_out
);

    localparam ADDR_DUTY = 8'h85;
    localparam ADDR_CTRL = 8'h86;
    localparam ADDR_PRE  = 8'h87;

    reg [7:0] duty;         // Duty cycle: 0-255
    reg       enable;       // Habilitar salida
    reg       invert;       // Invertir polaridad
    reg [7:0] prescaler;    // Divisor de frecuencia
    reg [7:0] pre_cnt;      // Contador de prescaler
    reg [7:0] pwm_cnt;      // Contador PWM (0-255)

    // Escritura de registros de control
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            duty      <= 8'h00;
            enable    <= 1'b0;
            invert    <= 1'b0;
            prescaler <= 8'd105;   // ~1 kHz a 27 MHz por defecto
        end else if (mmio_we) begin
            case (mmio_addr)
                ADDR_DUTY: duty      <= mmio_data_in;
                ADDR_CTRL: begin
                    enable <= mmio_data_in[0];
                    invert <= mmio_data_in[1];
                end
                ADDR_PRE:  prescaler <= (mmio_data_in == 8'h00) ? 8'd255 : mmio_data_in;
                default: ;
            endcase
        end
    end

    // Lectura de registros
    always @(*) begin
        mmio_data_out = 8'h00;
        if (mmio_re) begin
            case (mmio_addr)
                ADDR_DUTY: mmio_data_out = duty;
                ADDR_CTRL: mmio_data_out = {6'b0, invert, enable};
                ADDR_PRE:  mmio_data_out = prescaler;
                default:   mmio_data_out = 8'h00;
            endcase
        end
    end

    // PWM
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pre_cnt <= 8'd0;
            pwm_cnt <= 8'd0;
            pwm_out <= 1'b0;
        end else if (!enable) begin
            pwm_out <= invert ? 1'b1 : 1'b0;  
            pre_cnt <= 8'd0;
            pwm_cnt <= 8'd0;
        end else begin
            // Prescaler
            if (pre_cnt >= prescaler - 1) begin
                pre_cnt <= 8'd0;
                // Contador PWM de 8 bits 
                pwm_cnt <= pwm_cnt + 8'd1;
                // Comparar: si contador < duty
                if (pwm_cnt < duty)
                    pwm_out <= invert ? 1'b0 : 1'b1;
                else
                    pwm_out <= invert ? 1'b1 : 1'b0;
            end else begin
                pre_cnt <= pre_cnt + 8'd1;
            end
        end
    end

endmodule

`default_nettype wire
