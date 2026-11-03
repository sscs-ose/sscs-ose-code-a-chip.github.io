module benchmark_fifo(input logic clk,rst_n,wr_en,rd_en,
 input logic [7:0] wr_data,output wire [7:0] rd_data, output wire full,empty);
 localparam integer DEPTH=4;
 logic [7:0] storage[0:DEPTH-1];
 logic [1:0] wptr,rptr;
 logic [2:0] used;
 assign full=(used==DEPTH-1); assign empty=(used==0);
 assign rd_data=empty ? '0 : storage[rptr];
 always_ff @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin wptr<=0;rptr<=0;used<=0;end
  else begin
   if(wr_en && !full) begin storage[wptr]<=wr_data;wptr<=(wptr+1)%DEPTH;end
   if(rd_en && !empty) rptr<=(rptr+1)%DEPTH;
   case({wr_en && !full,rd_en && !empty})
    2'b10: used<=used+1'b1;
    2'b01: used<=used-1'b1;
    default: used<=used;
   endcase
  end
 end
endmodule
