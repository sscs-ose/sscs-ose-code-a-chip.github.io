module RegFile( 
input clk,reset,write_enable,
input [4:0] rd, rs1, rs2,
input [31:0] rw,
output reg [31:0] rs1out,rs2out
);

//registers
reg [31:0] x0 = 32'd0;
reg [31:0] x1;
reg [31:0] x2;
reg [31:0] x3;
reg [31:0] x4;
reg [31:0] x5;
reg [31:0] x6;
reg [31:0] x7;
reg [31:0] x8;
reg [31:0] x9;
reg [31:0] x10;
reg [31:0] x11;
reg [31:0] x12;
reg [31:0] x13;
reg [31:0] x14;
reg [31:0] x15;
reg [31:0] x16;
reg [31:0] x17;
reg [31:0] x18;
reg [31:0] x19;
reg [31:0] x20;
reg [31:0] x21;
reg [31:0] x22;
reg [31:0] x23;
reg [31:0] x24;
reg [31:0] x25;
reg [31:0] x26;
reg [31:0] x27;
reg [31:0] x28;
reg [31:0] x29;
reg [31:0] x30;
reg [31:0] x31;

always @(*)
begin

case(rs1)
    5'd0:  rs1out = x0;
    5'd1:  rs1out = x1;
    5'd2:  rs1out = x2;
    5'd3:  rs1out = x3;
    5'd4:  rs1out = x4;
    5'd5:  rs1out = x5;
    5'd6:  rs1out = x6;
    5'd7:  rs1out = x7;
    5'd8:  rs1out = x8;
    5'd9:  rs1out = x9;
    5'd10: rs1out = x10;
    5'd11: rs1out = x11;
    5'd12: rs1out = x12;
    5'd13: rs1out = x13;
    5'd14: rs1out = x14;
    5'd15: rs1out = x15;
    5'd16: rs1out = x16;
    5'd17: rs1out = x17;
    5'd18: rs1out = x18;
    5'd19: rs1out = x19;
    5'd20: rs1out = x20;
    5'd21: rs1out = x21;
    5'd22: rs1out = x22;
    5'd23: rs1out = x23;
    5'd24: rs1out = x24;
    5'd25: rs1out = x25;
    5'd26: rs1out = x26;
    5'd27: rs1out = x27;
    5'd28: rs1out = x28;
    5'd29: rs1out = x29;
    5'd30: rs1out = x30;
    5'd31: rs1out = x31;
endcase

case(rs2)
    5'd0:  rs2out = x0;
    5'd1:  rs2out = x1;
    5'd2:  rs2out = x2;
    5'd3:  rs2out = x3;
    5'd4:  rs2out = x4;
    5'd5:  rs2out = x5;
    5'd6:  rs2out = x6;
    5'd7:  rs2out = x7;
    5'd8:  rs2out = x8;
    5'd9:  rs2out = x9;
    5'd10: rs2out = x10;
    5'd11: rs2out = x11;
    5'd12: rs2out = x12;
    5'd13: rs2out = x13;
    5'd14: rs2out = x14;
    5'd15: rs2out = x15;
    5'd16: rs2out = x16;
    5'd17: rs2out = x17;
    5'd18: rs2out = x18;
    5'd19: rs2out = x19;
    5'd20: rs2out = x20;
    5'd21: rs2out = x21;
    5'd22: rs2out = x22;
    5'd23: rs2out = x23;
    5'd24: rs2out = x24;
    5'd25: rs2out = x25;
    5'd26: rs2out = x26;
    5'd27: rs2out = x27;
    5'd28: rs2out = x28;
    5'd29: rs2out = x29;
    5'd30: rs2out = x30;
    5'd31: rs2out = x31;
endcase

end


always @(posedge clk)
begin
    if(reset) begin
        x0 <= 32'd0;
        x1 <= 32'd0;
        x2 <= 32'd0;
        x3 <= 32'd0;
        x4 <= 32'd0;
        x5 <= 32'd0;
        x6 <= 32'd0;
        x7 <= 32'd0;
        x8 <= 32'd0;
        x9 <= 32'd0;
        x10 <= 32'd0;
        x11 <= 32'd0;
        x12 <= 32'd0;
        x13 <= 32'd0;
        x14 <= 32'd0;
        x15 <= 32'd0;
        x16 <= 32'd0;
        x17 <= 32'd0;
        x18 <= 32'd0;
        x19 <= 32'd0;
        x20 <= 32'd0;
        x21 <= 32'd0;
        x22 <= 32'd0;
        x23 <= 32'd0;
        x24 <= 32'd0;
        x25 <= 32'd0;
        x26 <= 32'd0;
        x27 <= 32'd0;
        x28 <= 32'd0;
        x29 <= 32'd0;
        x30 <= 32'd0;
        x31 <= 32'd0;
    end
    else if(write_enable)
        case(rd)
            5'd0:  x0  <= 32'd0;
            5'd1:  x1  <= rw;
            5'd2:  x2  <= rw;
            5'd3:  x3  <= rw;
    5'd4:  x4  <= rw;
    5'd5:  x5  <= rw;
    5'd6:  x6  <= rw;
    5'd7:  x7  <= rw;
    5'd8:  x8  <= rw;
    5'd9:  x9  <= rw;
    5'd10: x10 <= rw;
    5'd11: x11 <= rw;
    5'd12: x12 <= rw;
    5'd13: x13 <= rw;
    5'd14: x14 <= rw;
    5'd15: x15 <= rw;
    5'd16: x16 <= rw;
    5'd17: x17 <= rw;
    5'd18: x18 <= rw;
    5'd19: x19 <= rw;
    5'd20: x20 <= rw;
    5'd21: x21 <= rw;
    5'd22: x22 <= rw;
    5'd23: x23 <= rw;
    5'd24: x24 <= rw;
    5'd25: x25 <= rw;
    5'd26: x26 <= rw;
    5'd27: x27 <= rw;
    5'd28: x28 <= rw;
    5'd29: x29 <= rw;
    5'd30: x30 <= rw;
    5'd31: x31 <= rw;
endcase

end

endmodule
