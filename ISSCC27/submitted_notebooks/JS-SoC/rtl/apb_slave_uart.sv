
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


module apb_slave_uart(
    input  logic        clk,
    input  logic        prstn,
    input  logic [1:0]  psel,
    input  logic        trans,
    //input  logic        pready_p, // Input from the external peripheral
    input  logic        penable,
    input  logic        pwrite,
    input  logic [31:0] pwdata,//data from apb master to write slave 
    //input logic master_ready,//from peripheral to ensure read is enabled
    //input logic [31:0] peri_data,//input for the peripheral data
    //output logic [31:0] p_data,//output for slave for write state
    output logic tx,
    output logic [31:0] pr_data,//output for the peripheral data
    //output logic pwrite_en,
    output logic        pready
        
);
logic write_pending;
logic pready_p;
logic [31:0] p_data;
//logic [31:0] pr_data;
logic [31:0] peri_data;
logic pwrite_en;
logic master_ready;
always_ff @(posedge clk)
begin
    if(!prstn) begin
        p_data        <= 32'b0;
        pwrite_en     <= 1'b0;
        write_pending <= 1'b0;
        p_data<='0;
        //peri_data<='0;
        pwrite_en<='0;
    end
    else begin
        pwrite_en <= 1'b0;

        if(psel==2'b01 && penable && pwrite && trans && pready_p) begin
            p_data        <= pwdata;
            write_pending <= 1'b1;
        end

        if(write_pending) begin
            pwrite_en     <= 1'b1;
            write_pending <= 1'b0;
        end
        if(master_ready) begin
            pr_data <= peri_data;
        end
    end
end
    logic master_busy;
    assign pready_p=~master_busy;
    assign pready=pready_p;
    //assign pwrite_en= trans && psel && pwrite && penable;
    
    uart_soc uart_soc1(
                       .clk(clk),
                       .rst(~prstn),
                       .data_in(p_data),
                       .wr_en(pwrite_en),
                       .master_busy(master_busy),
                       .data_out(peri_data),
                       .tx(tx),
                       .master_ready(master_ready)
                    );

endmodule: apb_slave_uart

