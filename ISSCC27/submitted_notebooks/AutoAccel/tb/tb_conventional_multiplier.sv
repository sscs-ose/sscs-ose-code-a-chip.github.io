`timescale 1ns / 1ps

module tb_conventional_multiplier;

    parameter int N = 8;
    parameter int NUM_RANDOM_TESTS = 100;

    logic [N-1:0] A;
    logic [N-1:0] B;
    logic [2*N-1:0] P;

    int pass_cnt = 0;
    int fail_cnt = 0;

    conventional_multiplier #(.N(N)) dut (
        .A(A),
        .B(B),
        .P(P)
    );

    task automatic check(
        input logic [N-1:0] a_test,
        input logic [N-1:0] b_test
    );
        logic [2*N-1:0] expected;

        begin
            A = a_test;
            B = b_test;

            #1;

            expected = a_test * b_test;

            if (P !== expected) begin
                $display(
                    "FAIL: A=%0d B=%0d P=%0d Expected=%0d",
                    A, B, P, expected
                );
                fail_cnt++;
            end
            else begin
                $display(
                    "PASS: A=%0d B=%0d P=%0d",
                    A, B, P
                );
                pass_cnt++;
            end
        end
    endtask

    initial begin
        $dumpfile("multiplier.vcd");
        $dumpvars(0, tb_conventional_multiplier);

        $display("Conventional Multiplier Verification");
        $display("Width: %0d bits", N);
        $display("Running directed and random tests...");

        // Directed tests
        check('0, '0);
        check('0, {N{1'b1}});
        check({N{1'b1}}, '0);
        check({N{1'b1}}, {N{1'b1}});
        check(1, 1);
        check(1, {N{1'b1}});
        check(2, 3);
        check(10, 15);

        // Random tests
        for (int i = 0; i < NUM_RANDOM_TESTS; i++) begin
            check($urandom, $urandom);
        end

        $display("");
        $display(
            "Verification complete: %0d passed, %0d failed.",
            pass_cnt, fail_cnt
        );

        if (fail_cnt == 0) begin
            $display("STATUS: PASS");
        end
        else begin
            $display("STATUS: FAIL");
        end

        $finish;
    end

endmodule
