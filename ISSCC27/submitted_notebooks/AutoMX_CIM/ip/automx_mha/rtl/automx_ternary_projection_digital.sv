// Copyright 2026 EDABK Laboratory. SPDX-License-Identifier: Apache-2.0.
// Matched resident-weight baseline: one conditional sign/add per clock.
`default_nettype none
module automx_ternary_projection_digital (
 input wire clk_i,rst_ni,
 input wire cfg_valid_i,output wire cfg_ready_o,input wire [1:0] cfg_row_i,
 input wire [3:0] cfg_wpos_i,cfg_wneg_i,
 input wire eval_valid_i,output wire eval_ready_o,input wire [19:0] act_x2_i,
 output wire result_valid_o,input wire result_ready_i,output reg [47:0] result_x2_o
);
 localparam [1:0] IDLE=0,ADD=1,RESULT=2;
 reg [1:0] state,row,column;reg [19:0] acts;
 reg [3:0] pos[0:3],neg[0:3];reg [3:0] loaded;
 reg signed [11:0] accumulator;reg signed [11:0] term,next_sum;
 assign cfg_ready_o=state==IDLE && !eval_valid_i && !(|(cfg_wpos_i&cfg_wneg_i));
 assign eval_ready_o=state==IDLE && !cfg_valid_i && (&loaded);
 assign result_valid_o=state==RESULT;
 always @* begin
  term=0;
  if(pos[row][column])term=$signed(acts[5*row+:5]);
  else if(neg[row][column])term=-$signed(acts[5*row+:5]);
  next_sum=accumulator+term;
 end
 always @(posedge clk_i or negedge rst_ni)begin
  if(!rst_ni)begin state<=IDLE;loaded<=0;row<=0;column<=0;accumulator<=0;acts<=0;result_x2_o<=0;end
  else case(state)
   IDLE:begin
    if(cfg_valid_i && cfg_ready_o)begin pos[cfg_row_i]<=cfg_wpos_i;neg[cfg_row_i]<=cfg_wneg_i;loaded[cfg_row_i]<=1;end
    if(eval_valid_i && eval_ready_o)begin acts<=act_x2_i;row<=0;column<=0;accumulator<=0;state<=ADD;end
   end
   ADD:begin
    if(row==3)begin
     result_x2_o[12*column+:12]<=next_sum;accumulator<=0;row<=0;
     if(column==3)state<=RESULT;else column<=column+1;
    end else begin accumulator<=next_sum;row<=row+1;end
   end
   RESULT:if(result_ready_i)state<=IDLE;
   default:state<=IDLE;
  endcase
 end
endmodule

module automx_mha_digital_top (
 input wire clk_i,rst_ni,
 input wire cfg_valid_i,output wire cfg_ready_o,input wire [1:0] cfg_stage_i,cfg_row_i,
 input wire [3:0] cfg_wpos_i,cfg_wneg_i,
 input wire req_valid_i,output wire req_ready_o,input wire [39:0] req_act_x2_i,
 output wire rsp_valid_o,input wire rsp_ready_i,output wire rsp_row_o,
 output wire [47:0] rsp_result_x2_o,output wire busy_o,fault_o
);
 wire core_cfg_valid_o,core_cfg_ready_i,core_eval_valid_o,core_eval_ready_i;
 wire [1:0] core_cfg_row_o;wire [3:0] core_cfg_wpos_o,core_cfg_wneg_o;
 wire [19:0] core_act_x2_o;wire core_result_valid_i,core_result_ready_o;
 wire [47:0] core_result_x2_i;
 automx_mha_ip mha_i(.clk_i(clk_i),.rst_ni(rst_ni),
 .cfg_valid_i(cfg_valid_i),.cfg_ready_o(cfg_ready_o),.cfg_stage_i(cfg_stage_i),.cfg_row_i(cfg_row_i),
 .cfg_wpos_i(cfg_wpos_i),.cfg_wneg_i(cfg_wneg_i),.req_valid_i(req_valid_i),.req_ready_o(req_ready_o),
 .req_act_x2_i(req_act_x2_i),.rsp_valid_o(rsp_valid_o),.rsp_ready_i(rsp_ready_i),.rsp_row_o(rsp_row_o),
 .rsp_result_x2_o(rsp_result_x2_o),.busy_o(busy_o),.fault_o(fault_o),
 .core_available_i(1'b1),.core_fault_i(1'b0),.core_cfg_valid_o(core_cfg_valid_o),.core_cfg_ready_i(core_cfg_ready_i),
 .core_cfg_row_o(core_cfg_row_o),.core_cfg_wpos_o(core_cfg_wpos_o),.core_cfg_wneg_o(core_cfg_wneg_o),
 .core_eval_valid_o(core_eval_valid_o),.core_eval_ready_i(core_eval_ready_i),.core_act_x2_o(core_act_x2_o),
 .core_result_valid_i(core_result_valid_i),.core_result_ready_o(core_result_ready_o),.core_result_x2_i(core_result_x2_i),.core_result_calibrated_i(1'b1));
 automx_ternary_projection_digital projection_i(.clk_i(clk_i),.rst_ni(rst_ni),
 .cfg_valid_i(core_cfg_valid_o),.cfg_ready_o(core_cfg_ready_i),.cfg_row_i(core_cfg_row_o),
 .cfg_wpos_i(core_cfg_wpos_o),.cfg_wneg_i(core_cfg_wneg_o),.eval_valid_i(core_eval_valid_o),
 .eval_ready_o(core_eval_ready_i),.act_x2_i(core_act_x2_o),.result_valid_o(core_result_valid_i),
 .result_ready_i(core_result_ready_o),.result_x2_o(core_result_x2_i));
endmodule
`default_nettype wire
