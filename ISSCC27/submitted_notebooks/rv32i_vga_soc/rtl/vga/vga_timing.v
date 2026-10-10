module vga_timing #(
    parameter H_VISIBLE = 640,
    parameter H_FRONT   = 16,
    parameter H_SYNC    = 96,
    parameter H_BACK    = 48,
    parameter V_VISIBLE = 480,
    parameter V_FRONT   = 10,
    parameter V_SYNC    = 2,
    parameter V_BACK    = 33
)(
    input  wire clk,       
    input  wire rst,      
    output reg  [15:0] H_count,
    output reg  [15:0] V_count,
    output wire Hsync,
    output wire Vsync,
    output wire video_on   
);

// horizontal signals
localparam H_TOTAL   = H_VISIBLE + H_FRONT + H_SYNC + H_BACK; 

//vertical singals
localparam V_TOTAL   = V_VISIBLE + V_FRONT + V_SYNC + V_BACK;


always @(posedge clk or posedge rst) begin
    if (rst) 
    begin
        H_count <= 16'd0;
        V_count <= 16'd0;
    end 
    else 
    begin
        if (H_count == H_TOTAL - 1) 
        begin
            H_count <= 16'd0;
            if (V_count == V_TOTAL - 1) 
            begin
                V_count <= 16'd0;
            end 
            else 
            begin
                V_count <= V_count + 16'd1;
            end
        end 
        else 
        begin
            H_count <= H_count + 16'd1;
        end
    end
end

assign Hsync = !((H_count >= (H_VISIBLE + H_FRONT)) && (H_count < (H_VISIBLE + H_FRONT + H_SYNC)));
assign Vsync = !((V_count >= (V_VISIBLE + V_FRONT)) && (V_count < (V_VISIBLE + V_FRONT + V_SYNC)));

assign video_on = (H_count < H_VISIBLE) && (V_count < V_VISIBLE);

endmodule
