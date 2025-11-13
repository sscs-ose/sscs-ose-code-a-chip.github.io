module fadd_tree #(
    parameter   sig_width = 8,//bfloat16
    parameter   exp_width = 7,
    parameter   MAC_NUM = 8,
    parameter   IDATA_BIT = (sig_width+exp_width+1),
    parameter   ODATA_BIT = (sig_width+exp_width+1),
    localparam  ieee_compliance = 0
)(
    // Global Signals
    input                               clk,
    input                               rstn,

    // Data Signals
    input       [IDATA_BIT*MAC_NUM-1:0] idata,
    input       [MAC_NUM-1:0]           idata_valid,
    input                               last_in,
    output  reg [ODATA_BIT-1:0]         odata,
    output  reg                         odata_valid,
    output  reg                         last_out
);

    localparam STAGE_NUM = $clog2(MAC_NUM);

    // Insert a pipeline every two stages
    // Validation
    genvar i, j;
    generate
        for (i = 0; i < $clog2(MAC_NUM); i = i + 1) begin: gen_adt_valid
            reg             add_valid;
            reg             last_valid;

            if (i == 0) begin   // Input Stage
                always @(posedge clk or negedge rstn) begin
                    if (!rstn) begin
                        add_valid <= 1'b0;
                        last_valid <= 0;
                    end
                    else begin
                        add_valid <= |idata_valid;
                        last_valid <= last_in;
                    end
                end
            end
            else begin
                always @(posedge clk or negedge rstn) begin //insert pipeline every stage
                    if (!rstn) begin
                        add_valid <= 1'b0;
                        last_valid <= 0;
                    end
                    else begin
                        add_valid <= gen_adt_valid[i-1].add_valid;
                        last_valid <= gen_adt_valid[i-1].last_valid;
                    end
                end
            end
        end
    endgenerate

    // Adder
    generate
        for (i = 0; i <STAGE_NUM; i = i + 1) begin: gen_adt_stage
            localparam  OUT_BIT = IDATA_BIT;
            localparam  OUT_NUM = MAC_NUM  >> (i + 1'b1);

            reg     [OUT_BIT-1:0]   add_idata   [0:OUT_NUM*2-1];
            wire    [OUT_BIT-1:0]   add_odata   [0:OUT_NUM-1];

            for (j = 0; j < OUT_NUM; j = j + 1) begin: gen_adt_adder

                // Organize adder inputs
                if (i == 0) begin   // Input Stage
                    always @(posedge clk or negedge rstn) begin
                        if (!rstn) begin
                            add_idata[j*2]   <= 'd0;
                        end
                        else if (idata_valid[j*2]) begin
                            add_idata[j*2]   <= idata[(j*2+0)*IDATA_BIT+:IDATA_BIT];
                        end
                        else begin
                            add_idata[j*2]  <= 'd0;
                        end
                    end
                    always @(posedge clk or negedge rstn) begin
                        if (!rstn) begin
                            add_idata[j*2+1] <= 'd0;
                        end
                        else if (idata_valid[j*2+1]) begin
                            add_idata[j*2+1] <= idata[(j*2+1)*IDATA_BIT+:IDATA_BIT];
                        end
                        else begin
                            add_idata[j*2+1]  <= 'd0;
                        end
                    end
                end
                else begin
                    //insert pipeline at every stage
                    always @(posedge clk or negedge rstn) begin
                        if (!rstn) begin
                            add_idata[j*2]   <= 'd0;
                            add_idata[j*2+1] <= 'd0;
                        end
                        else if (gen_adt_valid[i-1].add_valid) begin
                            add_idata[j*2]   <= gen_adt_stage[i-1].add_odata[j*2];
                            add_idata[j*2+1] <= gen_adt_stage[i-1].add_odata[j*2+1];
                        end
                    end
                end
            end
                // Adder instantization
                // DW_fp_add #(sig_width, exp_width, ieee_compliance)
                // fadd_inst ( .a(add_idata[j*2]), .b(add_idata[j*2+1]), .rnd(3'b000), .z(add_odata[j]), .status());
                // fp_add #(sig_width, exp_width, ieee_compliance)
                // fadd_inst ( .a(add_idata[j*2]), .b(add_idata[j*2+1]), .rnd(3'b000), .z(add_odata[j]), .status());
            for (j = 0; j < OUT_NUM; j = j + 1) begin: gen_adt_adder_inst
                fp_add #(sig_width, exp_width)
                fadd_inst ( .a(add_idata[j*2]), .b(add_idata[j*2+1]), .rnd(3'b000), .z(add_odata[j]), .status());
            end



        end
    endgenerate

    //I add another register here -BUCK
    reg [ODATA_BIT-1:0]         nxt_odata;
    reg                         nxt_odata_valid;
    reg                         nxt_last_out;

    // Output
    always @(*) begin
        nxt_odata       = gen_adt_stage[STAGE_NUM-1].add_odata[0];
        nxt_odata_valid = gen_adt_valid[STAGE_NUM-1].add_valid;
        nxt_last_out    = gen_adt_valid[STAGE_NUM-1].last_valid;
    end
    always @(posedge clk or negedge rstn) begin
        if(~rstn)begin
            odata <= 0;
            odata_valid <= 0;
            last_out <= 0;
        end
        else begin
            odata <= nxt_odata       ;
            odata_valid <= nxt_odata_valid ;
            last_out <= nxt_last_out;
        end
    end
endmodule 