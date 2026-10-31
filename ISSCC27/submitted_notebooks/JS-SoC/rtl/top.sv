
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 22.05.2026 16:25:12
// Design Name: 
// Module Name: top
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


module top(
    input logic clk,
    input logic rst,
    output logic tx,
    //output logic [31:0] write_data,data_add,
    //output logic mem_write,
    //output logic [31:0] pr_data,
    input logic [7:0] bootloader_data,
    input logic bootloader_write,
    output logic bootloader_ready,
    output logic wave,
    output logic wave1,
    output logic wave2
    );
    logic [31:0] imem_data;
    logic [31:0] bootloader_data_out;
    logic [4:0] bootloader_address;
    logic bootloader_sel;
    logic imem_write;
    logic stall;
    logic [31:0] pr_data;
    logic mem_write;
    logic [31:0] write_data,data_add;
    logic memwrite;
    logic [31:0] pc,instr,read_data;
    
    bootloader bootloader1(.clk(clk),.rst(rst),.data_in(bootloader_data),.write(bootloader_write),
               .ready(bootloader_ready),.data_out(bootloader_data_out),.address(bootloader_address),.sel(bootloader_sel),.imem_write(imem_write),
               .hold(stall));
    core core1(.clk(clk),.rst(rst),.instr(instr),.read_data(read_data),.stall(stall),
               .pc(pc),.alu_result(data_add),.write_data(write_data),.mem_write(memwrite));
    imem imem1(.clk(clk),.rst(rst),.a(imem_data),.boot_address(bootloader_address),.imem_write(imem_write),.hold(stall),.out(instr));
    bridge bridge1(.clk(clk),.rst(rst),.addr(data_add),.data(write_data),.memwrite(memwrite),.dmem_write(mem_write),.pr_data(pr_data),.wave(wave),.tx(tx),
                   .wave1(wave1),.wave2(wave2));
    dmem dmem1(.clk(clk),.a(data_add),.write_data(write_data),.mem_write(mem_write),.out(read_data));
    mux_2 bootloader_mux (.a(pc),.b(bootloader_data_out),.sel(bootloader_sel),.y(imem_data));
    always_comb begin
    if(|pr_data[31:0])begin
    end
    end
endmodule:top
