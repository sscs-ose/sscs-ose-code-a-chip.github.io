`default_nettype none
`timescale 1ns / 1ps

module tb_fibo;

    localparam CLK_FREQ  = 1_000_000;
    localparam BAUD_RATE = 9600;
    localparam CLK_HALF  = 500;
    localparam N         = 14;
    localparam N_INSTR   = 12;

    reg clk, rst_n;

    wire [7:0]  gpio_out, gpio_dir;
    wire        uart_tx_pin, pwm_pin;
    wire [7:0]  debug_pc, debug_state;
    wire [15:0] debug_instr;

    microrv8_system #(
        .CLK_FREQ  (CLK_FREQ),
        .BAUD_RATE (BAUD_RATE)
    ) dut (
        .clk         (clk),
        .rst_n       (rst_n),
        .gpio_in     (8'h00),
        .gpio_out    (gpio_out),
        .gpio_dir    (gpio_dir),
        .uart_rx_pin (1'b1),
        .uart_tx_pin (uart_tx_pin),
        .pwm_pin     (pwm_pin),
        .debug_pc    (debug_pc),
        .debug_state (debug_state),
        .debug_instr (debug_instr)
    );

    initial clk = 0;
    always #(CLK_HALF) clk = ~clk;

    reg [7:0] expected [0:N-1];
    reg [7:0] seen     [0:N-1];
    integer   n_out;
    integer   errors;
    integer   k;
    integer   fd;
    reg [1023:0] hexfile;

    always @(posedge clk) begin
        if (rst_n && debug_state[2:0] == 3'd5 && debug_instr[15:13] == 3'b110) begin
            if (n_out < N) seen[n_out] = gpio_out;
            n_out = n_out + 1;
            $display("[%0t] OUT #%0d  gpio = %0d (0x%02X)  pc=%0d",
                     $time, n_out, gpio_out, gpio_out, debug_pc);
        end
    end

    initial begin
        $dumpfile("tb_fibo.vcd");
        $dumpvars(0, tb_fibo);
        $timeformat(-9, 1, " ns", 12);

        expected[0]  = 0;   expected[1]  = 1;   expected[2]  = 1;
        expected[3]  = 2;   expected[4]  = 3;   expected[5]  = 5;
        expected[6]  = 8;   expected[7]  = 13;  expected[8]  = 21;
        expected[9]  = 34;  expected[10] = 55;  expected[11] = 89;
        expected[12] = 144; expected[13] = 233;

        n_out  = 0;
        errors = 0;
        rst_n  = 0;
        repeat (10) @(posedge clk);

        if (!$value$plusargs("HEX=%s", hexfile))
            hexfile = "../programs/fibo.hex";
        fd = $fopen(hexfile, "r");
        if (fd == 0) begin
            hexfile = "programs/fibo.hex";
            fd = $fopen(hexfile, "r");
        end
        if (fd == 0) begin
            $display("ERROR: no se encontro fibo.hex");
            $finish;
        end
        $fclose(fd);
        $readmemh(hexfile, dut.imem.rom, 0, N_INSTR - 1);
        $display("Programa cargado desde: %0s", hexfile);
        for (k = 0; k < N_INSTR; k = k + 1)
            $display("  ROM[%0d] = %04h", k, dut.imem.rom[k]);

        $display("Fibonacci");
        rst_n = 1;
        $display("[%0t] Reset liberado", $time);

        repeat (1500) @(posedge clk);

        $display("");
        $display("=== Resultados ===");
        $display("Instrucciones OUT ejecutadas: %0d (esperadas %0d)", n_out, N);
        if (n_out != N) errors = errors + 1;

        for (k = 0; k < N; k = k + 1)
            if (seen[k] !== expected[k]) begin
                $display("FAIL: OUT #%0d = %0d, esperado %0d", k + 1, seen[k], expected[k]);
                errors = errors + 1;
            end

        if (gpio_out !== 8'd233) begin
            $display("FAIL: gpio final = %0d, esperado 233", gpio_out);
            errors = errors + 1;
        end

        if (debug_pc !== 8'd11) begin
            $display("FAIL: el PC debia quedar en 11 (done), esta en %0d", debug_pc);
            errors = errors + 1;
        end

        if (errors == 0)
            $display("RESULTADO: PASS  (secuencia 0 1 1 2 3 5 ... 233, PC en done)");
        else
            $display("RESULTADO: FAIL  (%0d errores)", errors);
        $display("=== Fin ===");
        $finish;
    end

    initial begin
        #50_000_000;
        $display("TIMEOUT");
        $finish;
    end

endmodule

`default_nettype wire
