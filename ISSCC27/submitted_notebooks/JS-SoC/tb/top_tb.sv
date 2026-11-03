`timescale 1ns/1ps

module cpu_tb;

    logic clk;
    logic rst;

    logic [7:0] bootloader_data;
    logic bootloader_write;
    logic bootloader_ready;

    logic tx;
    logic wave;
    logic wave1;
    logic wave2;

    top top1(
        .clk(clk),
        .rst(rst),
        .tx(tx),
        .bootloader_data(bootloader_data),
        .bootloader_write(bootloader_write),
        .bootloader_ready(bootloader_ready),
        .wave(wave),
        .wave1(wave1),
        .wave2(wave2)
    );

    always #1 clk = ~clk;

    task send_byte(input logic [7:0] data);
    begin
        wait(bootloader_ready == 1'b1);

        @(negedge clk);
        bootloader_data  = data;
        bootloader_write = 1'b1;

        @(negedge clk);
        bootloader_write = 1'b0;
        bootloader_data  = 8'h00;

        wait(bootloader_ready == 1'b0);
    end
    endtask

    task send_instruction(input logic [31:0] instruction);
    begin
        send_byte(instruction[31:24]);
        send_byte(instruction[23:16]);
        send_byte(instruction[15:8]);
        send_byte(instruction[7:0]);
    end
    endtask

    initial
    begin
        $dumpfile("results/build/js_soc.vcd");
        $dumpvars(0, cpu_tb);
        clk = 1'b0;

        rst = 1'b1;

        bootloader_data  = 8'h00;
        bootloader_write = 1'b0;

        #10;

        rst = 1'b0;

        wait(bootloader_ready == 1'b1);

        send_byte(8'd22);

        send_instruction(32'h40000537);
        send_instruction(32'h486925B7);
        send_instruction(32'h12158593);
        send_instruction(32'h00B52023);
        send_instruction(32'h00850513);
        send_instruction(32'h000A05B7);
        send_instruction(32'h00358593);
        send_instruction(32'h00B52023);
        send_instruction(32'h00450513);
        send_instruction(32'h0C0A05B7);
        send_instruction(32'h00658593);
        send_instruction(32'h00B52023);
        send_instruction(32'h0E0005B7);
        send_instruction(32'h00A58593);
        send_instruction(32'h00B52023);
        send_instruction(32'h00F00093);
        send_instruction(32'h01400113);
        send_instruction(32'h002081B3);
        send_instruction(32'h40118233);
        send_instruction(32'h004182B3);
        send_instruction(32'hFF628313);
        send_instruction(32'h00000063);

        wait(top1.bootloader1.hold == 1'b0);

        #60;

        $display("");
        $display("========================================");
        $display("       BOOTLOADER COMPLETE");
        $display("========================================");

        $display("COUNT      = %0d", top1.bootloader1.counter);
        $display("INSTR_CNT  = %0d", top1.bootloader1.instr_counter);
        $display("HOLD       = %b", top1.bootloader1.hold);
        $display("SEL        = %b", top1.bootloader1.sel);

        $display("");
        $display("IMEM CONTENT");
        $display("========================================");

        $display("IMEM[0]  = %08h", top1.imem1.ram[0]);
        $display("IMEM[1]  = %08h", top1.imem1.ram[1]);
        $display("IMEM[2]  = %08h", top1.imem1.ram[2]);
        $display("IMEM[3]  = %08h", top1.imem1.ram[3]);
        $display("IMEM[4]  = %08h", top1.imem1.ram[4]);
        $display("IMEM[5]  = %08h", top1.imem1.ram[5]);
        $display("IMEM[6]  = %08h", top1.imem1.ram[6]);
        $display("IMEM[7]  = %08h", top1.imem1.ram[7]);
        $display("IMEM[8]  = %08h", top1.imem1.ram[8]);
        $display("IMEM[9]  = %08h", top1.imem1.ram[9]);
        $display("IMEM[10] = %08h", top1.imem1.ram[10]);
        $display("IMEM[11] = %08h", top1.imem1.ram[11]);
        $display("IMEM[12] = %08h", top1.imem1.ram[12]);
        $display("IMEM[13] = %08h", top1.imem1.ram[13]);
        $display("IMEM[14] = %08h", top1.imem1.ram[14]);
        $display("IMEM[15] = %08h", top1.imem1.ram[15]);
        $display("IMEM[16] = %08h", top1.imem1.ram[16]);
        $display("IMEM[17] = %08h", top1.imem1.ram[17]);
        $display("IMEM[18] = %08h", top1.imem1.ram[18]);
        $display("IMEM[19] = %08h", top1.imem1.ram[19]);
        $display("IMEM[20] = %08h", top1.imem1.ram[20]);
        $display("IMEM[21] = %08h", top1.imem1.ram[21]);

        $display("========================================");

        $display("");
        $display("CPU REGISTER FILE");
        $display("========================================");

        $display("x0  = %08h", top1.core1.data.r1.register[0]);
        $display("x1  = %08h", top1.core1.data.r1.register[1]);
        $display("x2  = %08h", top1.core1.data.r1.register[2]);
        $display("x3  = %08h", top1.core1.data.r1.register[3]);
        $display("x4  = %08h", top1.core1.data.r1.register[4]);
        $display("x5  = %08h", top1.core1.data.r1.register[5]);
        $display("x6  = %08h", top1.core1.data.r1.register[6]);
        $display("x7  = %08h", top1.core1.data.r1.register[7]);

        $display("========================================");

        if (top1.bootloader1.hold !== 1'b0) $fatal(1, "FAIL: bootloader did not release CPU");
        if (top1.bootloader1.instr_counter !== 22) $fatal(1, "FAIL: instruction count mismatch");
        if (top1.imem1.ram[0] !== 32'h40000537) $fatal(1, "FAIL: IMEM[0]");
        if (top1.imem1.ram[21] !== 32'h00000063) $fatal(1, "FAIL: IMEM[21]");
        if (top1.core1.data.r1.register[1] !== 32'h0000000F) $fatal(1, "FAIL: x1");
        if (top1.core1.data.r1.register[2] !== 32'h00000014) $fatal(1, "FAIL: x2");
        if (top1.core1.data.r1.register[3] !== 32'h00000023) $fatal(1, "FAIL: x3");
        if (top1.core1.data.r1.register[4] !== 32'h00000014) $fatal(1, "FAIL: x4");
        if (top1.core1.data.r1.register[5] !== 32'h00000037) $fatal(1, "FAIL: x5");
        if (top1.core1.data.r1.register[6] !== 32'h0000002d) $fatal(1, "FAIL: x6");
        $display("SIMULATION PASS");

        $finish;
    end
endmodule
