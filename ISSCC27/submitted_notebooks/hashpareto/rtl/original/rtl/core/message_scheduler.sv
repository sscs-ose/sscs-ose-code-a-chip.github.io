module message_scheduler(
    input logic clk, rst_n,
    input logic [511:0] block,
    input logic load_block, next_round,
    output logic [31:0] w_t,
    output logic scheduler_ready
);
    timeunit 1ns;
    timeprecision 100ps;

    // new window for rounds > 16
    logic [31:0] w_new;
    // hashing primitive functions
    logic [31:0] sigma_0, sigma_1;
    logic [31:0] w_mem [0:15];
    logic [31:0] wt_minus_2, wt_minus_7, wt_minus_15, wt_minus_16; 
    logic [6:0] schedule_count;


    always_ff @(posedge clk, negedge rst_n) begin
        if(!rst_n) begin
            for(int i = 0; i < 16; i = i + 1) 
                w_mem[i] <= 32'd0;
            schedule_count <= 0;
        end else if (load_block) begin
            w_mem[0] <= block[511:480];
            w_mem[1] <= block[479:448];
            w_mem[2] <= block[447:416];
            w_mem[3] <= block[415:384];
            w_mem[4] <= block[383:352];
            w_mem[5] <= block[351:320];
            w_mem[6] <= block[319:288];
            w_mem[7] <= block[287:256];
            w_mem[8] <= block[255:224];
            w_mem[9] <= block[223:192];
            w_mem[10] <= block[191:160];
            w_mem[11] <= block[159:128];
            w_mem[12] <= block[127:96];
            w_mem[13] <= block[95:64];
            w_mem[14] <= block[63:32];
            w_mem[15] <= block[31:0];
            schedule_count <= 1;
        end else if (next_round) begin
            for (int i = 0; i < 15; i = i + 1)
                w_mem[i] <= w_mem[i + 1];

            w_mem[15] <= w_new;
            if(schedule_count == 7'd64)
                schedule_count <= 7'd0;
            else
                schedule_count <= schedule_count + 1;
        end
    end
    // outputs
    assign w_t = w_mem[0];
    assign scheduler_ready = (schedule_count == 0) ? 1'b1 : 1'b0;

    assign wt_minus_2 = w_mem[14];
    assign wt_minus_7 = w_mem[9];
    assign wt_minus_15 = w_mem[1];
    assign wt_minus_16 = w_mem[0];
      // Sigma 0: sigma0(x) = ROTR7(x) ^ ROTR18(x) ^ SHR3(x)
    assign sigma_0 = {wt_minus_15[6:0], wt_minus_15[31:7]} ^ {wt_minus_15[17:0], wt_minus_15[31:18]} ^ {3'd0, wt_minus_15[31:3]};
    // Sigma 1: sigma1(x) = ROTR17(x) ^ ROTR19(x) ^ SHR10(x)
    assign sigma_1 = {wt_minus_2[16:0], wt_minus_2[31:17]} ^ {wt_minus_2[18:0], wt_minus_2[31:19]} ^ {10'd0, wt_minus_2[31:10]};
    assign w_new = sigma_1 + wt_minus_7 + sigma_0 + wt_minus_16;

endmodule