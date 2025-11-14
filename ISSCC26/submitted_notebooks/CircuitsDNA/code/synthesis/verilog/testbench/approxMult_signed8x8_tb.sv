
module approxMult_signed8x8_tb();

    reg signed [7:0] A;
    reg signed [7:0] B;
    wire signed [15:0] OUT;
    int Expected_out;
    integer file_handle;
    
    approxMult_signed8x8 dut (
        .A(A),
        .B(B),
        .OUT(OUT)
    );
    
    initial begin
        file_handle = $fopen("code/genetic_algorithm/output/extracted_truth_table.txt", "w");
        if (file_handle == 0) begin
            $display("Error: Could not open output file");
            $finish;
        end
        
        $fwrite(file_handle, "A\tB\tOUT\tExpected\tError\n");
        
        for(int i = -128; i <= 127; i = i + 1) begin
            for(int j = -128; j <= 127; j = j + 1) begin
                A = i;
                B = j;
                Expected_out = $signed(A) * $signed(B);
                #1;
                $display("A: %d, B: %d, OUT: %d, Expected: %d", A, B, OUT, Expected_out);
                $fwrite(file_handle, "%d\t%d\t%d\t%d\t%d\n", A, B, OUT, Expected_out, OUT - Expected_out    );
            end
        end
        
        $fclose(file_handle);
        $display("code/genetic_algorithm/output/extracted_truth_table.txt");
        $finish;
    end

endmodule