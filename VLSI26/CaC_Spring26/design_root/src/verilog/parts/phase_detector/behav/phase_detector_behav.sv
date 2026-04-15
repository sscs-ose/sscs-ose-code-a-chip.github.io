`timescale 1ps/1ps

/* |======================================================================= */
/* | */                                                                          
/* | Author             : Mythri Muralikannan */                                                   
/* | Description        : Bang-Bang Phase detector */                                       
/* | This detector does not measure the exact phase error but just outputs a 1-bit decision */                                                                     
/* | UP = 1 --> the reference clock is ahead and there must be a speed up*/                                                                      
/* | DOWN = 1 --> the feedback clock is ahead and there must be a slow down*/                                                                      
/* | NOT SYNTHESIZEABLE : ONLY BEHAVIORAL SIMULATION
/* |======================================================================= */


module phase_detector (
    input  wire clk_in,    //Reference input clock
    input  wire clk_out,   //Feedback output clock
    input  wire rst,       //Posedge asynchronous reset
    output reg  up,        //Speed Up if 1
    output reg  down       //Slow Down if 1
);

    // Time tracking variables for the behavioral simulation
    // Timescale in pico seconds
    time last_clk_in;
    time last_clk_out;


    // Capture the last edge of the input clock
    always @(posedge clk_in or posedge rst) begin
        if (rst) begin
            last_clk_in <= 0;
        end else begin
            last_clk_in <= $time;
        end
    end

    // Capture the last edge of the output clock
    always @(posedge clk_out or posedge rst) begin
        if (rst) begin
            last_clk_out <= 0;
        end else begin
            last_clk_out <= $time;
        end
    end

    // Combinational logic to continuously compare the 2 timestamps
    always @(*) begin
        // Clear outputs if reset
        if (rst) begin
            up   = 1'b0;
            down = 1'b0;
        // Speed Up
        end else if (last_clk_in > last_clk_out) begin
            up   = 1'b1;
            down = 1'b0;
        // Slow Down
        end else if (last_clk_out > last_clk_in) begin
            up   = 1'b0;
            down = 1'b1;
        // No change
        end else begin
            up   = 1'b0;
            down = 1'b0;
        end
    end

endmodule
