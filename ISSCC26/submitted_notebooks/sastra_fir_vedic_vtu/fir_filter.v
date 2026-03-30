`timescale 1ns/1ps


module d_ff(
    input clk,
    input reset,
    input [3:0]d,
    output reg [3:0]q
);
    always @(posedge clk or posedge reset) begin
        if (reset)
            q<=4'd0;   
        else
            q<=d;
    end
endmodule

module vedic_mul(
    input  [3:0] a,
    input  [3:0] b,
    output [7:0] p
);
    // Partial products
    wire p00,p01,p02,p03;
    wire p10,p11,p12,p13;
    wire p20,p21,p22,p23;
    wire p30,p31,p32,p33;

    // Generate partial products
    assign p00 = a[0]&b[0];
    assign p01 = a[0]&b[1];
    assign p02 = a[0]&b[2];
    assign p03 = a[0]&b[3];
    
    assign p10 = a[1]&b[0];
    assign p11 = a[1]&b[1];
    assign p12 = a[1]&b[2];
    assign p13 = a[1]&b[3];
    
    assign p20 = a[2]&b[0];
    assign p21 = a[2]&b[1];
    assign p22 = a[2]&b[2];
    assign p23 = a[2]&b[3];
    
    assign p30 = a[3]&b[0];
    assign p31 = a[3]&b[1];
    assign p32 = a[3]&b[2];
    assign p33 = a[3]&b[3];

    
    wire [3:0] s1,s2,s3,s4,s5,s6;   // sums (max width)
    wire [3:0] c1,c2,c3,c4,c5,c6;   // carries ( max 2 bit carry is req)

    // Column 0 (no carry)
    assign p[0]=p00;

    // Column 1:
    assign s1 =p01+p10;
	 assign p[1]=s1[0];
    assign c1= s1[1];  

    // Column 2
    assign s2 = p02+p11+p20+c1;
    assign p[2]=s2[0];
    assign c2= s2[1];

    // Column 3
    
    assign s3 = p03+p12+p21+p30+c2;
    assign p[3]=s3[0];
    assign c3=s3[1];  

    // Column 4
    assign s4 =p13 +p22+p31+c3;
    assign p[4]=s4[0];
    assign c4=s4[1];

    // Column 5
    
    assign s5 =p23+p32+c4;
    assign p[5]=s5[0];
    assign c5=s5[1];

     //Column 6
    assign s6 = p33+c5;
    assign p[6]=s6[0];
    assign c6=s6[1];

    // Column 7
    assign p[7]=c6;

endmodule

module hca8 (
    input wire [7:0] a,
    input wire [7:0] b,
    output wire [8:0] sum
);
    wire [7:0]g,p;
    wire [7:0]G1,P1;
    wire [7:0]G2,P2;
    wire [7:0]G3,P3;
    wire [8:0]c;

    assign g=a&b;
    assign p=a^b;

    //LEVEL 1
    assign G1[0]=g[0];
    assign P1[0]=p[0];

    genvar i1;
    generate
        for (i1 =1;i1<8;i1=i1+1) begin : L1
            assign G1[i1]=g[i1] |(p[i1]&g[i1-1]);
            assign P1[i1]=p[i1]&p[i1-1];
        end
    endgenerate

    // LEVEL 2
    assign G2[1:0]=G1[1:0];
    assign P2[1:0]=P1[1:0];

    genvar i2;
    generate
        for (i2 =2;i2<8;i2=i2+1) begin : L2
            assign G2[i2]=G1[i2]|(P1[i2]&G1[i2-2]);
        assign P2[i2] =P1[i2]&P1[i2-2];
        end
    endgenerate

    // LEVEL 3
    assign G3[3:0]=G2[3:0];
    assign P3[3:0]=P2[3:0];

    genvar i3;
    generate
        for (i3 =4;i3< 8;i3=i3 + 1) begin : L3
            assign G3[i3]=G2[i3] |(P2[i3]&G2[i3-4]);
            assign P3[i3]=P2[i3]&P2[i3-4];
        end
    endgenerate

    // FINAL 
    wire [7:0] Gf;
    assign Gf=G3;

    //  CARRIES 
    assign c[0]=1'b0;

    genvar i4;
    generate
        for (i4 =0;i4<8;i4=i4 + 1) begin : CARRY
            assign c[i4+1]=Gf[i4];
        end
    endgenerate

    // SUM 
    assign sum ={c[8],(p^c[7:0])};

endmodule


module hca9 (
    input  wire[8:0]a,
    input  wire[8:0]b,
    output wire[9:0]sum
);
    // propagate and generate
    wire [8:0]g =a&b;
    wire [8:0]p =a^b;

    // LEVEL 1 (distance 1)
    wire [8:0]G1,P1;
    assign G1[0]=g[0];
    assign P1[0]=p[0];
    genvar i1;
    generate
        for (i1 = 1; i1 < 9; i1 = i1 + 1) begin : L1
            assign G1[i1] =g[i1]|(p[i1]&g[i1-1]);
            assign P1[i1] = p[i1]&p[i1-1];
        end
    endgenerate

    // LEVEL 2 (distance 2)
    wire [8:0]G2,P2;
    assign G2[1:0]=G1[1:0];
    assign P2[1:0]=P1[1:0];
    genvar i2;
    generate
        for (i2 =2;i2<9;i2=i2+1) begin :L2
            assign G2[i2] =G1[i2]|(P1[i2]&G1[i2-2]);
            assign P2[i2]=P1[i2]&P1[i2-2];
        end
    endgenerate

    // LEVEL 3 (distance 4)
    wire [8:0] G3, P3;
    assign G3[3:0]=G2[3:0];
    assign P3[3:0]=P2[3:0];
    genvar i3;
    generate
        for (i3=4;i3<9;i3=i3+1) begin : L3
            assign G3[i3] =G2[i3]|(P2[i3]&G2[i3-4]);
            assign P3[i3] =P2[i3] &P2[i3-4];
        end
    endgenerate

    // LEVEL 4 (distance 8) 
    wire [8:0] G4, P4;

    assign G4[7:0]=G3[7:0];
    assign P4[7:0]=P3[7:0];
    
    assign G4[8]=G3[8]|(P3[8]&G3[0]);
    assign P4[8]=P3[8]&P3[0];

    
    wire [9:0]c;
    assign c[0]=1'b0;
    genvar ic;
    generate
        for (ic=0;ic<9;ic=ic+1) begin : CARRY
            assign c[ic+1] = G4[ic];
        end
    endgenerate

    
    assign sum ={c[9], (p ^ c[8:0])};

endmodule
module digit_sum_bc                                        
 #(                                                        
    parameter WIDTH = 16                                   
)(                                                         
    input  [WIDTH-1:0] in,   // only values 0?60 are expected
    output reg [3:0] ds                                    
);                                                         
                                                           
    reg [3:0] tens, ones;                                  
                                                           
    always @(*) begin                                      
        tens = 4'b0000;                                    
        ones = 4'b0000;                                    
        ds   = 4'b0000;                                    
                                                           
        // Fast path: 0?8                                  
                                                           
                                                           
            // BCD separation (0?60 only)                  
            if (in < 16'd10) begin            // 9         
                tens = 4'b0000;                            
                ones = in[3:0];                            
            end                                            
            else if (in < 16'd20) begin       // 10?19     
                tens = 4'b0001;                            
                ones = in - 16'd10;                        
            end                                            
            else if (in < 16'd30) begin       // 20?29     
                tens = 4'b0010;                            
                ones = in - 16'd20;                        
            end                                            
            else if (in < 16'd40) begin       // 30?39     
                tens = 4'b0011;                            
                ones = in - 16'd30;                        
            end                                            
            else if (in < 16'd50) begin       // 40?49     
                tens = 4'b0100;                            
                ones = in - 16'd40;                        
                                                           
                                                           
            end                                            
            else if (in < 16'd60) begin       // 40?49     
                tens = 4'b0101;                            
                ones = in - 16'd50;                        
            end                                            
            else begin                        // 50?60     
                tens = 4'b0110;                            
                ones = in - 16'd60;                        
            end                                            
                                                           
                                                           
            // Digit sum (max = 5 + 9 = 14)                
            ds = tens + ones;                              
                                                           
             // Final reduction to single digit            
    if (ds >= 10)                                          
        ds = ds - 9;                                       
        end                                                
                                                           
                                                           
endmodule                                                  

module mul_verification(
    input [3:0]a,
    input [3:0]b,
    input [7:0]product,
    output valid
);
    wire [3:0]ds_a, ds_b, ds_prod;
    wire [7:0]prod_ds_mul;
    wire [3:0]ds_expected;

    
    digit_sum_bc #(4)  DS_A  (a,ds_a);
    digit_sum_bc #(4)  DS_B  (b,ds_b);
    digit_sum_bc #(8)  DS_P  (product,ds_prod);

    // multiply 
    assign prod_ds_mul=ds_a *ds_b;  

    
    digit_sum_bc #(8) DS_EXP (prod_ds_mul,ds_expected);

    assign valid =(ds_prod==ds_expected);

endmodule

module adder_verification(
    input  [7:0]a,
    input  [7:0]b,
    input  [8:0]sum,   //hca  9 bit o/p
    output valid
);
    wire [3:0]ds_a,ds_b,ds_sum;
    wire [5:0]ds_add;   // max width
    wire [3:0]ds_expected;

    digit_sum_bc #(8) DS_A(a,ds_a);
    digit_sum_bc #(8) DS_B(b,ds_b);
    digit_sum_bc #(9) DS_S(sum,ds_sum);

    assign ds_add =ds_a+ds_b;     

    digit_sum_bc #(8) DS_EXP ({2'b00, ds_add},ds_expected);


    assign valid = (ds_sum==ds_expected);

endmodule

module adder_verification_9bit(
    input  [8:0] a,      
    input  [8:0] b,      
    input  [9:0] sum,    
    output valid
);
    wire [3:0] ds_a,ds_b,ds_sum;
    wire [6:0] ds_add;   
    wire [3:0] ds_expected;

    digit_sum_bc #(9) DS_A(a,ds_a);
    digit_sum_bc #(9) DS_B(b,ds_b);
    digit_sum_bc #(10) DS_S(sum,ds_sum);

    assign ds_add=ds_a+ds_b;   // 0..18

    digit_sum_bc #(8) DS_EXP ({1'b0, ds_add},ds_expected);


    assign valid =(ds_sum==ds_expected);

endmodule








module fir_filter(
    input clk,
    input reset,
    input [3:0] x,
    input [3:0] a,
    input [3:0] b,
    input [3:0] c,
    output reg [9:0] y,
    output v1,v2,v3,v4,v5
	 //output verif_pass
);
    
    // Delays x1=x(n-1)  x2=x(n-2)
    wire [3:0] x1, x2;
	 
    
    // delay using dff
    d_ff d1(clk, reset, x, x1);
    d_ff d2(clk, reset, x1, x2);
    
    // vedic multiplier
    wire [7:0] p0, p1, p2;
    
    vedic_mul m1(x, a, p0);
    vedic_mul m2(x1, b, p1);
    vedic_mul m3(x2, c, p2);
    
    // han-carlson adder
    wire [8:0] s1;
    hca8 h1(p0, p1, s1);
    wire [9:0] y_comb;
    hca9 h2(s1, {1'b0, p2}, y_comb);
    
    
    always @(posedge clk or posedge reset) begin
        if (reset)
            y <= 0;
        else
            y <= y_comb;
    end
    
    // VTU
    //wire v1, v2, v3, v4, v5;
    mul_verification vtu1( x, a, p0, v1);
    mul_verification vtu2( x1, b, p1, v2);
    mul_verification vtu3( x2, c, p2, v3);
    
    
    adder_verification vtu4( p0, p1, s1, v4);
    adder_verification_9bit vtu5(s1,{1'b0, p2},y_comb, v5);
    
    
    //assign verif_pass = v1 & v2 & v3 & v4 & v5;

endmodule



