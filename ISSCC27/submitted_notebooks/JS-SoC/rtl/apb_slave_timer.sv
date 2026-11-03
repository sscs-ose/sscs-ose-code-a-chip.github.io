
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

module apb_slave_timer(
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
    output logic        wave1,
    output logic        wave2
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
            if(psel==2'b11 && penable && trans && pwrite && pready_p)
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
    
    timer timer_peri(
                     .clk(clk),
                     .rst(~prstn),
                     .data_word(p_data),
                     .write(pwrite_en),
                     .master_ready(pready_p),
                     .wave1(wave1),
                     .wave2(wave2)
                    );
endmodule: apb_slave_timer

