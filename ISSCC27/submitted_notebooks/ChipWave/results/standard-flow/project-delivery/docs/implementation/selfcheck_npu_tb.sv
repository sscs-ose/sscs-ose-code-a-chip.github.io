`timescale 1ns/1ps
module selfcheck_npu_tb;
    logic clk, rst_n, req_valid, req_ready, rsp_valid, rsp_ready, kill;
    logic [31:0] req_a, req_b, rsp_data;
    int checked;
    logic [31:0] rng;
    nebula_npu_dot4 dut (.*);
    task automatic tick;
        #2; clk=1; #2; clk=0; #2;
    endtask
    function automatic logic [31:0] random_word();
        rng = rng * 32'd1664525 + 32'd1013904223;
        return rng;
    endfunction
    task automatic check_dot(input logic [31:0] a,b);
        int av, bv, expected;
        begin
            expected=0;
            for (int lane=0;lane<4;lane++) begin
                av=int'(a[8*lane+:8]); bv=int'(b[8*lane+:8]);
                if (av>=128) av-=256;
                if (bv>=128) bv-=256;
                expected+=av*bv;
            end
            #1;
            if (!req_ready || rsp_valid) $fatal(1,"not idle");
            req_a=a; req_b=b; req_valid=1; rsp_ready=1;
            tick();
            if (req_ready || rsp_valid) $fatal(1,"early response n");
            tick();
            if (req_ready || rsp_valid) $fatal(1,"early response n+1");
            tick();
            if (req_ready || !rsp_valid || rsp_data !== 32'(expected))
                $fatal(1,"dot n+2 a=%h b=%h expected=%h actual=%h",a,b,expected,rsp_data);
            rsp_ready=0;
            repeat (3) begin
                req_a=~req_a; req_b=~req_b;
                tick();
                if (req_ready || !rsp_valid || rsp_data !== 32'(expected)) $fatal(1,"backpressure");
            end
            rsp_ready=1;
            tick();
            if (!req_ready || rsp_valid) $fatal(1,"accepted on consumption edge");
            req_valid=0;
            checked++;
        end
    endtask
    initial begin
        clk=0; rst_n=0; kill=0; req_valid=0; rsp_ready=0; req_a=0; req_b=0; rng=32'hbada55; checked=0;
        #1;
        if (req_ready || rsp_valid || rsp_data!=0) $fatal(1,"reset outputs");
        tick(); rst_n=1;
        for (int a=0;a<256;a++)
            for (int b=0;b<256;b++) check_dot({4{8'(a)}},{4{8'(b)}});
        repeat (2000) check_dot(random_word(),random_word());
        for (int reset_mode=0;reset_mode<2;reset_mode++) begin
            for (int age=0;age<5;age++) begin
                req_a=32'h80808080;req_b=32'h80808080;req_valid=1;rsp_ready=0;
                if (age>0) repeat (age) tick();
                rsp_ready=1;
                if (reset_mode==1) rst_n=0;
                else kill=1;
                #1;
                if (req_ready || rsp_valid) $fatal(1,"cancel handshake");
                tick(); req_valid=0; kill=0; rst_n=1; #1;
                if (!req_ready || rsp_valid) $fatal(1,"cancel recovery");
                repeat (4) begin tick(); if (rsp_valid) $fatal(1,"stale response"); end
                check_dot(32'h7f0180ff,32'h80807fff);
            end
        end
        $display("SELFCHECK_NPU_PASS dots=%0d cancellations=10",checked);
        $finish;
    end
endmodule
