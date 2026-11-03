// Code your testbench here
// or browse Examples
`timescale 1ns/1ps

module karatsuba_multiplier_tb #(
    parameter int N = 8
);

    localparam int P_W = 2 * N;

    logic [N-1:0]   A, B;
    logic [P_W-1:0] P;

    logic [P_W-1:0] expected;

    int errors = 0;
    int tests  = 0;

    karatsuba_multiplier #(.N(N)) dut (
        .A(A),
        .B(B),
        .P(P)
    );

    assign expected = A * B;

    task automatic check(input string testname);
        tests++;
        if (P !== expected) begin
            errors++;
            $display("[FAIL] %s | t=%0t | A=%h B=%h | DUT=%h EXP=%h",
                     testname, $time, A, B, P, expected);
        end
    endtask

    task automatic run_random(int unsigned num_vectors);
        repeat (num_vectors) begin
            A = $urandom();
            B = $urandom();
            #(1ns);
            check("random");
        end
    endtask

    task automatic run_corners();
        logic [N-1:0] corners [5];
        corners[0] = '0;
        corners[1] = '0 + 1;
        corners[2] = '0 + 2;
        corners[3] = '1 - 1;
        corners[4] = '1;
        for (int i = 0; i < 5; i++) begin
            for (int j = 0; j < 5; j++) begin
                A = corners[i];
                B = corners[j];
                #(1ns);
                check($sformatf("corner[%0d][%0d]", i, j));
            end
        end
    endtask

    task automatic run_directed();
        A = '1;
        B = '1;
        #(1ns);
        check("max_x_max");

        A = {{(N/2){1'b1}}, {(N/2){1'b0}}};
        B = {{(N/2){1'b1}}, {(N/2){1'b0}}};
        #(1ns);
        check("half_split");

        A = '0 + (1 << (N/2));
        B = A;
        #(1ns);
        check("half_power");

        A = '1;
        B = '0 + 1;
        #(1ns);
        check("max_x_one");
    endtask

    task automatic run_patterns();
        logic [N-1:0] pats [4];
        pats[0] = '1 >> (N/2);
        pats[1] = '1 << (N/2);
        pats[2] = {{(N/2){1'b1}}, {(N/2){1'b0}}};
        pats[3] = {{(N/2){1'b0}}, {(N/2){1'b1}}};
        for (int i = 0; i < 4; i++) begin
            for (int j = 0; j < 4; j++) begin
                A = pats[i];
                B = pats[j];
                #(1ns);
                check($sformatf("pattern[%0d][%0d]", i, j));
            end
        end
    endtask

    initial begin
        $display("Karatsuba Multiplier TB: N = %0d bits", N);

        run_corners();
        run_directed();
        run_patterns();
        run_random(1000);

        $display("SUMMARY (N=%0d): %0d tests, %0d errors", N, tests, errors);
        if (errors == 0)
            $display("ALL TESTS PASSED");
        else
            $display("TESTS FAILED");

        if (errors != 0) $fatal(1, "Testbench finished with errors");
        $finish;
    end

    initial begin
        #(10us);
        $fatal(1, "WATCHDOG TIMEOUT");
    end

    initial begin
        $dumpfile($sformatf("karatsuba_multiplier_%0d_tb.vcd", N));
        $dumpvars(0, karatsuba_multiplier_tb);
    end

endmodule


module karatsuba_multiplier_tb_top;

    karatsuba_multiplier_tb #(.N(8))  tb8  ();
    karatsuba_multiplier_tb #(.N(16)) tb16 ();
    karatsuba_multiplier_tb #(.N(32)) tb32 ();

endmodule
