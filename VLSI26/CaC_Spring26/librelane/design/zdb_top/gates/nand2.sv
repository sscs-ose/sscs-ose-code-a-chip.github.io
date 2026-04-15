//nand2 gate
module nand2(
    input logic a, 
    input logic b, 
    output logic out
);
    assign out = ~(a & b);
endmodule