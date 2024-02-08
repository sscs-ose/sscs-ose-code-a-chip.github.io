module systolic_array_tb;

  // Declare input signals
  reg [7:0] a11;
  reg [7:0] a12;
  reg [7:0] a21;
  reg [7:0] a22;
  reg [7:0] b11;
  reg [7:0] b12;
  reg [7:0] b21;
  reg [7:0] b22;
  reg clk;
  reg rst;

  // Declare output signals
  wire [16:0] c11;
  wire [16:0] c12;
  wire [16:0] c21;
  wire [16:0] c22;

  // Instantiate the Unit Under Test (UUT)
  systolic_array UUT(
    .a11(a11),
    .a12(a12),
    .a21(a21),
    .a22(a22),
    .b11(b11),
    .b12(b12),
    .b21(b21),
    .b22(b22),
    .clk(clk),
    .c11(c11),
    .c12(c12),
    .c21(c21),
    .c22(c22),
    .rst(rst)
  );

  // Initialize input signals
  initial begin
    $dumpfile("systolic_array_tb.vcd");
  	$dumpvars(0,systolic_array_tb);
    clk = 0;
    rst = 0;
    #5;
    rst = 1;
    #10;
    rst = 0;
    a11 = 8'b10000011;
    a12 = 8'b00000111;
    a21 = 8'b00000110;
    a22 = 8'b00000010;
    b11 = 8'b00001101;
    b12 = 8'b00010011;
    b21 = 8'b00010010;
    b22 = 8'b00000011;
  end

  // Toggle the clock signal
  always begin
    #5 clk = ~clk;
  end

endmodule
