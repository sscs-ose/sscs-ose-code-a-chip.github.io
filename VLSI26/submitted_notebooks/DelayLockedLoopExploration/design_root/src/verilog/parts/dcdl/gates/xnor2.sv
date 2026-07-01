module xnor2 (
    input  logic a,
    input  logic b,
    output logic y
);

    logic n1, n2, n3, xor_out;

    // XOR using NANDs
    nand2 nand1 (.a(a), .b(b), .out(n1));
    nand2 nand2_1 (.a(a), .b(n1), .out(n2));
    nand2 nand2_2 (.a(b), .b(n1), .out(n3));
    nand2 nand3 (.a(n2), .b(n3), .out(xor_out));

    // invert to get XNOR
    inverter inv1 (.in(xor_out), .out(y));

endmodule