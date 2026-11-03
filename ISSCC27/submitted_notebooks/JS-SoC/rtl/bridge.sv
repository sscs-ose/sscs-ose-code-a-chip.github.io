 
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 23.06.2026 16:46:12
// Design Name: 
// Module Name: bridge
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


module bridge(
    input logic clk,
    input logic rst,
    input logic [31:0] addr,//alu result from the sw instruction,
    input logic [31:0] data,//write data rd2
    input logic memwrite,
    output logic dmem_write,
    output logic [31:0] pr_data,
    output logic tx,
    output logic wave,
    output logic wave1,
    output logic wave2
    );
    logic apb_range;
    logic [63:0] data_in;
    logic full;
    logic apb_write;
    assign apb_range=(addr >=32'h4000_0000 && addr<=32'h4000_0014);
    always_comb
    begin
        dmem_write=0;
        apb_write=0;
        data_in='0;
        if(memwrite)
        begin
            if(apb_range && !full)
                begin
                apb_write=1'b1;
                data_in={addr,data};
                end
            else
                begin
                dmem_write=1'b1;
                end
        end
    end
    
    fifo_master fifo_master1(
                            .clk(clk),
                            .rst(rst),
                            .w_en(apb_write),
                            .data_in(data_in),
                            .full(full),
                            .pr_data(pr_data),
                            .tx(tx),
                            .wave(wave),
                            .wave1(wave1),
                            .wave2(wave2)
                        );
           
endmodule:bridge
