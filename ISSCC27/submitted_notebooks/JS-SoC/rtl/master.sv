
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 24.06.2026 00:03:55
// Design Name: 
// Module Name: master
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


module master(
    input logic clk,
    input logic rst,
    //input logic apb_write,
    input logic [63:0] fifo_data,
    input logic fifo_empty,
    output logic [31:0] pr_data,
    output logic tx,
    output logic r_en,
    output logic wave,
    output logic wave1,
    output logic wave2
    );
    logic [1:0] psel;
    logic trans;
    logic pwrite;
    logic [31:0] pwdata;
    logic pready;
    //logic trans;
    logic penable;
    apb_master master_apb(
                          .clk(clk),
                          .prstn(~rst),
//                          .paddr(fifo_data[63:32]),
//                          .data(fifo_data[31:0]),
                          .fifo_data(fifo_data),
                          .fifo_empty(fifo_empty),
                          .pready(pready),
                          .r_en(r_en),
                          //.apb_write(fifo_data[64]),
                          .psel(psel),
                          .penable(penable),
                          .pwrite(pwrite),
                          .pwdata(pwdata),
                          .trans(trans)
                        );
    logic pready_uart;
    logic pready_pwm;
    logic pready_timer;
    apb_slave_uart  apb_slave_uart1(
                                   .clk(clk),
                                   .prstn(~rst),
                                   .psel(psel),
                                   .trans(trans),
                                   .penable(penable),
                                   .pwrite(pwrite),
                                   .pwdata(pwdata),
                                   .pr_data(pr_data),
                                   .tx(tx),
                                   .pready(pready_uart)
                                );
    
    apb_slave_pwm apb_slave_pwm1(
                                .clk(clk),
                                .prstn(~rst),
                                .psel(psel),
                                .trans(trans),
                                .penable(penable),
                                .pwrite(pwrite),
                                .pwdata(pwdata),
                                .wave(wave),
                                .pready(pready_pwm)
                            );
    apb_slave_timer apb_slave_timer1(
                                     .clk(clk),
                                     .prstn(~rst),
                                     .psel(psel),
                                     .trans(trans),
                                     .penable(penable),
                                     .pwrite(pwrite),
                                     .pwdata(pwdata),
                                     .wave1(wave1),
                                     .wave2(wave2),
                                     .pready(pready_timer)
                                );
    always_comb
    begin
        case(psel)
            2'b01:pready=pready_uart;
            2'b10:pready=pready_pwm;
            2'b11:pready=pready_timer;
            default:pready=1'b1;
        endcase
    end                     
endmodule:master

