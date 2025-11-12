//round robin arbiter
import DEFINE_PKG::*;

module rr_arbiter #(
    parameter NUM_REQ = `SA_NUM
)(
    input clk,
    input rstn,
    input gnt_en, //decide whether we want to write back
    input [NUM_REQ-1:0]req, //~empty in FIFO
    output logic [NUM_REQ-1:0] gnt // grant/rd_en in FIFO
);

    logic [NUM_REQ-1:0] mask_ff; //store the previous mask

    logic [NUM_REQ-1:0] masked_req;
    logic [NUM_REQ-1:0] masked_mask;
    logic [NUM_REQ-1:0] masked_gnt;

    logic [NUM_REQ-1:0] unmasked_mask;
    logic [NUM_REQ-1:0] unmasked_gnt;


    //maksed priority arbiter
    assign masked_req = req & mask_ff;
    /* if req[i] is the first 1, mask[i:0] will be 0 and p_req[N-1:i+1] will be 1
       0 has highest priority, N-1 has lowest priority  
        for example: req = 1010;  mask = 1100; gnt = 1010 & 0011 = 0010
    */
    assign masked_mask[0] = 1'b0;
    assign masked_mask[NUM_REQ-1:1] = masked_mask[NUM_REQ-2:0] | masked_req[NUM_REQ-2:0];
    assign masked_gnt = masked_req & ~masked_mask;



    //unmaksed priority arbiter
    assign unmasked_mask[0] = 1'b0;
    assign unmasked_mask[NUM_REQ-1:1] = unmasked_mask[NUM_REQ-2:0] | req[NUM_REQ-2:0];
    assign unmasked_gnt = req & ~unmasked_mask;


    //if the masked request is all zero, we need to wrap around and use the unmasked grant
    assign gnt =    (~gnt_en)?      '0:
                    (|masked_req) ? masked_gnt : unmasked_gnt;


    //update the mask accordingly
    always_ff @(posedge clk or negedge rstn)begin
        if(~rstn) begin
            mask_ff <= {NUM_REQ{1'b1}};
        end else if (gnt_en)begin
            if (|masked_req)begin  
                mask_ff <= masked_mask;
            end else if (|req)begin
                mask_ff <= unmasked_mask;
            end
        end
    end

endmodule