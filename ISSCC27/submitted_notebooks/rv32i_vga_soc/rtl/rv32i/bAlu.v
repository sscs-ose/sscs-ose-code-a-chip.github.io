module bAlu(
    input clk,
    input [31:0] op1, op2,
    input [2:0] func3,
    output reg jump
);

always @(*)
begin

    jump = 1'b0;

    if (func3 == 3'd0)
    begin
        if ($signed(op1) == $signed(op2))
            jump = 1'b1;
    end

    if (func3 == 3'd1)
    begin
        if ($signed(op1) != $signed(op2))
            jump = 1'b1;
    end

    if (func3 == 3'd4)
    begin
        if ($signed(op1) < $signed(op2))
            jump = 1'b1;
    end

    if (func3 == 3'd5)
    begin
        if ($signed(op1) >= $signed(op2))
            jump = 1'b1;
    end

    if (func3 == 3'd6)
    begin
        if (op1 < op2)
            jump = 1'b1;
    end

    if (func3 == 3'd7)
    begin
        if (op1 >= op2)
            jump = 1'b1;
    end

end
endmodule
