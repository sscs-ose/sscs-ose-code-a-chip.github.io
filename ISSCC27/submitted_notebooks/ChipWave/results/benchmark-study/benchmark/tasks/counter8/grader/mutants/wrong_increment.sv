module benchmark_counter(input logic clk,rst_n,en,load,
 input logic [7:0] load_value, output logic [7:0] count, output logic overflow);
 always_ff @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin count<='0;overflow<=0;end
  else if(load) begin count<=load_value;overflow<=0;end
  else if(en) begin count<=count+2'd2;overflow<=&count;end
  else overflow<=0;
 end
endmodule
