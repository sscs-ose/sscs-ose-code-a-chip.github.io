`timescale 1ns/1ps
module reset_waveform_tb;
    integration_smoke_tb smoke();
    initial begin
        $dumpfile("reports/verification/reset-waveform.vcd");
        $dumpvars(1, smoke);
    end
endmodule
