//**************************************************************************
// Author: Alfi Misha Antony Selvin Raj
// Description: 4-NAND Delay line (DCDL)
//**************************************************************************
(* dont_touch = "true" *)
module nand_dcdl(
    input logic A,
    input logic [3:0] Q, 
    output logic Y
);
    (* keep = "true" *) logic s3;
    (* keep = "true" *) logic s2;
    (* keep = "true" *) logic s1;
    (* keep = "true" *) logic s0;
    //delay cell 3 :)
    nand_dcdl_cell cell3 (
        .in1(1'b0),
        .in0(A),
        .ctl(Q[3]),
        .out(s3)
    );
    nand_dcdl_cell cell2(
        .in1(s3),
        .in0(A),
        .ctl(Q[2]),
        .out(s2)
    );
    nand_dcdl_cell cell1 (
        .in1(s2),
        .in0(A),
        .ctl(Q[1]),
        .out(s1)
    );
    nand_dcdl_cell cell0 (
        .in1(s1),
        .in0(A),
        .ctl(Q[0]),
        .out(s0)
    );
    assign Y = s0;
endmodule