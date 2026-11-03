
module eq16_check;
    localparam int N = 16;

    logic [N-1:0] A, B;
    logic [2*N-1:0] P_conventional, P_karatsuba;

    conventional_multiplier #(.N(N)) u_conv (
        .A(A), .B(B), .P(P_conventional)
    );

    karatsuba_multiplier #(.N(N)) u_kara (
        .A(A), .B(B), .P(P_karatsuba)
    );

    task automatic check(input logic [15:0] a, b);
        begin
            A = a;
            B = b;
            #1;
            if (P_conventional !== P_karatsuba) begin
                $error("Mismatch A=%0d B=%0d conventional=%0d karatsuba=%0d",
                       A, B, P_conventional, P_karatsuba);
                $fatal(1);
            end
        end
    endtask

    initial begin
        check(16'h0000, 16'h0000);
        check(16'h0001, 16'hFFFF);
        check(16'hFFFF, 16'hFFFF);
        check(16'hAAAA, 16'h5555);
        check(16'h8000, 16'h0002);

        for (int i = 0; i < 1000; i++)
            check($urandom, $urandom);

        $display("PASS: 1005 16-bit comparisons matched");
        $finish;
    end
endmodule
