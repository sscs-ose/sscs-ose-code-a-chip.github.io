module benchmark_dot(input logic clk,rst_n,req_valid,
 output wire req_ready,input logic [15:0] req_a,req_b,
 output wire rsp_valid,input logic rsp_ready,output logic [31:0] rsp_data,input logic kill);
 localparam IDLE=0, PRODUCTS=1, REDUCE=2, RESPONSE=3;
 logic [1:0] phase;
 logic signed [15:0] product[0:1];
 assign req_ready=rst_n && !kill && phase==IDLE;
 assign rsp_valid=rst_n && !kill && phase==RESPONSE;
 always_ff @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin phase<=IDLE;rsp_data<=0;for(integer i=0;i<2;i++)product[i]<=0;end
  else if(kill) begin phase<=IDLE;rsp_data<=0;for(integer i=0;i<2;i++)product[i]<=0;end
  else case(phase)
   IDLE: if(req_valid) begin
    for(integer i=0;i<2;i++)product[i]<=$signed(req_a[8*i+:8])*$signed(req_b[8*i+:8]);
    phase<=PRODUCTS;
   end
   PRODUCTS: phase<=REDUCE;
   REDUCE: begin rsp_data<=$signed({{16{product[0][15]}}, product[0]}) + $signed({{16{product[1][15]}}, product[1]});phase<=RESPONSE;end
   RESPONSE: if(rsp_ready)phase<=IDLE;
   default: phase<=IDLE;
  endcase
 end
endmodule
