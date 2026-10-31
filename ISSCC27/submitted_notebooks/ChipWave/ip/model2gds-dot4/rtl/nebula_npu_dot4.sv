// AI-authored interface adapter; gemm_pe is reused unchanged from Model2GDS.
module nebula_npu_dot4 (
    input logic clk,rst_n,req_valid,
    output logic req_ready,
    input logic [31:0] req_a,req_b,
    output logic rsp_valid,
    input logic rsp_ready,
    output logic [31:0] rsp_data,
    input logic kill
);
    typedef enum logic [1:0] {IDLE, PRODUCTS, REDUCE, RESPONSE} phase_t;
    phase_t phase;
    logic [31:0] a,b;
    logic signed [31:0] lane_product[0:3];
    logic pe_clear, pe_valid;
    assign pe_clear = !rst_n || kill || phase==IDLE;
    assign pe_valid = rst_n && !kill && phase==PRODUCTS;
    assign req_ready = rst_n && !kill && phase==IDLE;
    assign rsp_valid = rst_n && !kill && phase==RESPONSE;
    for(genvar lane=0;lane<4;lane++)begin:pe_lanes
        gemm_pe pe(.clk(clk),.rst(!rst_n),.clear(pe_clear),
            .a_in($signed(a[8*lane+:8])),.b_in($signed(b[8*lane+:8])),
            .a_valid(pe_valid),.b_valid(pe_valid),.a_last(1'b1),.b_last(1'b1),
            .a_out(),.b_out(),.a_out_valid(),.b_out_valid(),
            .a_out_last(),.b_out_last(),.accumulator(lane_product[lane]),.result_valid());
    end
    always_ff @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin phase<=IDLE;a<=0;b<=0;rsp_data<=0;end
        else if(kill)begin phase<=IDLE;a<=0;b<=0;rsp_data<=0;end
        else case(phase)
            IDLE:if(req_valid)begin a<=req_a;b<=req_b;phase<=PRODUCTS;end
            PRODUCTS:phase<=REDUCE;
            REDUCE:begin
                rsp_data<=lane_product[0]+lane_product[1]+lane_product[2]+lane_product[3];
                phase<=RESPONSE;
            end
            RESPONSE:if(rsp_ready)phase<=IDLE;
            default:phase<=IDLE;
        endcase
    end
endmodule
