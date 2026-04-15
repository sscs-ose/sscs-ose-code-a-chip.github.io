//inverter gate
module inverter (
    input logic in, 
    output logic out
);
    assign out = ~in;
endmodule