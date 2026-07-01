module mux(
    input logic x0, 
    input logic x1,
    input logic s, 
    output logic Y
);
    assign Y = (s == 1'b0) ? x0 : x1;
endmodule