//**************************************************************************
// Author: Alfi Misha Antony Selvin Raj
// Description: Single NAND based delay cell for 4 stage Nand Delay line
//**************************************************************************
(* dont_touch = "true" *) //telling synthesizer not to optimize this as nand gates can be changed to 2:1 MUX
module nand_dcdl_cell(
    input logic in1,
    input logic in0, 
    input logic ctl, 
    output logic out
);
    (* keep = "true" *) logic inv1_output;
    (* keep = "true" *) logic nand_cell_1;
    (* keep = "true" *) logic nand_cell_2;
    inverter inv1 (.in(ctl), .out(inv1_output));
    nand2 nand2_1 (.a(in1), .b(inv1_output), .out(nand_cell_1)); //the commented below line is the actual action. 
    //assign n1 = ~(in1 & ~ctl);
    nand2 nand2_2 (.a(in0), .b(ctl), .out(nand_cell_2));
    //assign n2 = ~(in0 & ctl);
    nand2 nand2_3 (.a(nand_cell_1), .b(nand_cell_2), .out(out));
    //assign out = ~(n1 & n2);
endmodule