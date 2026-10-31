
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 30.05.2026 17:46:17
// Design Name: 
// Module Name: apb_slave
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////

module apb_slave_pwm(
    input  logic        clk,
    input  logic        prstn,
    input  logic [1:0]  psel,
    input  logic        trans,
    //input  logic        pready_p, // Input from the external peripheral
    input  logic        penable,
    input  logic        pwrite,
    input  logic [31:0] pwdata,
    //output logic [31:0] p_data,
    output logic        pready, 
    //output logic        pwrite_en,
    output logic        wave
);
    logic pready_p;
    logic [31:0] p_data;
    logic pwrite_en;
    logic write_pending;
    always_ff @ (posedge clk)
    begin
        if(!prstn)
        begin
        p_data<=32'b0;
        write_pending<=1'b0;
        pwrite_en<=1'b0;
        end
        else 
            begin
            pwrite_en<=1'b0;
            if(psel==2'b10 && penable && trans && pwrite && pready_p)
                begin
                p_data<=pwdata;
                write_pending<=1'b1;
                end
            if(write_pending)
                begin
                write_pending<=1'b0;
                pwrite_en<=1'b1;
                end
            end
    end
    //assign stop=(pwdata==32'b0);
    assign pready=pready_p;
    
    pwm pwm_peri(
                 .clk(clk),
                 .rst(~prstn),
                 .data(p_data),
                 .write(pwrite_en),
                 .wave(wave),
                 .pready_p(pready_p)
                );
endmodule: apb_slave_pwm

