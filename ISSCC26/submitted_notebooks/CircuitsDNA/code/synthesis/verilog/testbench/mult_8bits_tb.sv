// testbench for mult_8bits (no clock, no reset)

`timescale 1ns/1ps

module mult_8bits_tb();

    reg  [7:0]  A;
    reg  [7:0]  B;
    wire [15:0] OUT;

    // DUT instance (no clk, no reset)
    mult_8bits my_mult(
        .A(A),
        .B(B),
        .OUT(OUT)
    );

    integer read_file;
    integer write_file;
    reg [15:0] temp;
    integer return_value;

    initial begin
        $dumpfile(`VCD_FILE);
        $dumpvars(0, mult_8bits_tb);

        A = 8'd0;
        B = 8'd0;

        read_file = $fopen("code/synthesis/goldenbrick/goldenbrick.txt", "r");
        if (read_file == 0) begin
            $display("Cannot open file goldenbrick.txt");
            $finish;
        end

        write_file = $fopen(`VSIM_OUT, "w");
        if (write_file == 0) begin
            $display("Cannot open output file");
            $finish;
        end

        // Apply test vectors from goldenbrick.txt
        while(!$feof(read_file)) begin
            return_value = $fscanf(read_file, "A = %b\tB = %b\tRESULT = %b\n", A, B, temp);
            #1; // small delay to allow propagation
            $fwrite(write_file, "A = %b B = %b RESULT = %b\n", A, B, OUT);
        end

        $fclose(read_file);
        $fclose(write_file);
        $finish;
    end

endmodule
