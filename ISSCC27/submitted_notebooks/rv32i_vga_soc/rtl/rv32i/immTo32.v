module immTo32(
    input  [11:0] imm,
    output [31:0] imm_ext
);

assign imm_ext = {{20{imm[11]}}, imm};

endmodule
