// Copyright (c) 2024, Saligane's Group at University of Michigan and Google Research
//
// Licensed under the Apache License, Version 2.0 (the "License");

// you may not use this file except in compliance with the License.

// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// MAC Top Module

module core_mac #(
    parameter   MAC_MULT_NUM   = `MAC_MULT_NUM, // MAC Line Size
    parameter   IDATA_WIDTH = `IDATA_WIDTH,  // Input
    parameter   ODATA_BIT = (IDATA_WIDTH*2+$clog2(MAC_MULT_NUM)) // Output
)(
    // Global Signals
    input                                       clk,
    input                                       rstn,

    // Data Signals
    input       [IDATA_WIDTH*MAC_MULT_NUM-1:0]  idataA,
    input       [IDATA_WIDTH*MAC_MULT_NUM-1:0]  idataB,
    input                                       idata_valid,
    output   signed   [ODATA_BIT-1:0]           odata,
    output                                      odata_valid
);
    localparam      MAC_ODATA_BIT = IDATA_WIDTH*2 + $clog2(MAC_MULT_NUM);
    wire            [MAC_ODATA_BIT-1:0] mac_odata;
    // assign  odata = {{(ODATA_BIT - MAC_ODATA_BIT){mac_odata[MAC_ODATA_BIT-1]}}, mac_odata};
    assign odata = $signed(mac_odata);
    // Multiplication
    wire    [IDATA_WIDTH*2*MAC_MULT_NUM-1:0]   product;
    wire                                product_valid;

    mul_line    #(.MAC_MULT_NUM(MAC_MULT_NUM), .IDATA_WIDTH(IDATA_WIDTH)) mul_inst (
        .clk                            (clk),
        .rstn                           (rstn),
        .idataA                         (idataA),
        .idataB                         (idataB),
        .idata_valid                    (idata_valid),
        .odata                          (product),
        .odata_valid                    (product_valid)
    );

    // Addition
    adder_tree  #(.MAC_MULT_NUM(MAC_MULT_NUM), .IDATA_WIDTH(IDATA_WIDTH*2)) adt_inst (
        .clk                            (clk),
        .rstn                           (rstn),
        .idata                          (product),
        .idata_valid                    (product_valid),
        .odata                          (mac_odata),
        .odata_valid                    (odata_valid)
    );  

endmodule

// =============================================================================
// MUL Line
// 1 cycle delay
module mul_line #(
    parameter   MAC_MULT_NUM = 64,
    parameter   IDATA_WIDTH = 8,
    parameter   ODATA_BIT = IDATA_WIDTH * 2
)(
    // Global Signals
    input                               clk,
    input                               rstn,

    // Data Signals
    input       [IDATA_WIDTH*MAC_MULT_NUM-1:0] idataA,
    input       [IDATA_WIDTH*MAC_MULT_NUM-1:0] idataB,
    input                               idata_valid,
    output  reg [ODATA_BIT*MAC_MULT_NUM-1:0] odata,
    output  reg                         odata_valid
);

    // Input Gating
    reg     [IDATA_WIDTH-1:0] idataA_reg  [0:MAC_MULT_NUM-1];
    reg     [IDATA_WIDTH-1:0] idataB_reg  [0:MAC_MULT_NUM-1];

    genvar i;
    generate
        for (i = 0; i < MAC_MULT_NUM; i = i + 1) begin: gen_mul_input
            always @(posedge clk or negedge rstn) begin
                if (!rstn) begin
                    idataA_reg[i] <= 'd0;
                    idataB_reg[i] <= 'd0;
                end
                else if (idata_valid) begin
                    idataA_reg[i] <= idataA[i*IDATA_WIDTH+:IDATA_WIDTH];
                    idataB_reg[i] <= idataB[i*IDATA_WIDTH+:IDATA_WIDTH];
                end
            end
        end
    endgenerate

    // Mutiplication
    wire    [ODATA_BIT-1:0] product [0:MAC_MULT_NUM-1];
    reg                     nxt_odata_valid;

    generate 
        for (i = 0; i < MAC_MULT_NUM; i = i + 1) begin: gen_mul
            //$display(gen_mul);
            mul_int #(.IDATA_WIDTH(IDATA_WIDTH), .ODATA_BIT(ODATA_BIT)) mul_inst (
                .idataA                 (idataA_reg[i]), 
                .idataB                 (idataB_reg[i]),
                .odata                  (product[i])
            );
        end
    endgenerate


    // Output
    generate
        for (i = 0; i < MAC_MULT_NUM; i = i + 1) begin: gen_mul_output
            always @(posedge clk) begin
                odata[i*ODATA_BIT+:ODATA_BIT] <= product[i]; 
            end
        end
    endgenerate
    //mult no output register, I add one -BUCK

    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            nxt_odata_valid <= 'd0;
            odata_valid <= 'd0;
        end
        else begin
            nxt_odata_valid <= idata_valid;
            odata_valid <= nxt_odata_valid;
        end
    end

endmodule

// =============================================================================
// Configurable Adder Tree. Please double-check it's synthesizable.
// (STAGE_NUM+1)/2 delay
module adder_tree #(
    parameter   MAC_MULT_NUM = 64,
    parameter   IDATA_WIDTH = 16,
    parameter   ODATA_BIT = IDATA_WIDTH + $clog2(MAC_MULT_NUM) 
)(
    // Global Signals
    input                               clk,
    input                               rstn,

    // Data Signals
    input       [IDATA_WIDTH*MAC_MULT_NUM-1:0] idata,
    input                               idata_valid,
    output  reg signed [ODATA_BIT-1:0]  odata,
    output  reg                         odata_valid
);

    localparam  STAGE_NUM = $clog2(MAC_MULT_NUM);

    // Insert a pipeline every two stages
    // Validation
    genvar i, j;
    generate
        for (i = 0; i < STAGE_NUM; i = i + 1) begin: gen_adt_valid
            reg             add_valid;

            if (i == 0) begin   // Input Stage
                always @(posedge clk or negedge rstn) begin
                    if (!rstn) begin
                        add_valid <= 1'b0;
                    end
                    else begin
                        add_valid <= idata_valid;
                    end
                end
            end
            else if (i % 2 == 1'b0) begin   // Even Stage, Insert a pipeline, Start from 0, 2, 4...
                always @(posedge clk or negedge rstn) begin
                    if (!rstn) begin
                        add_valid <= 1'b0;
                    end
                    else begin
                        add_valid <= gen_adt_valid[i-1].add_valid;
                    end
                end
            end
            else begin  // Odd Stage, Combinational, Start from 1, 3, 5...
                always @(*) begin
                    add_valid = gen_adt_valid[i-1].add_valid;
                end
            end
        end
    endgenerate

    // Adder
    generate
        for (i = 0; i <STAGE_NUM; i = i + 1) begin: gen_adt_stage
            localparam  OUT_BIT = IDATA_WIDTH + (i + 1'b1);
            localparam  OUT_NUM = MAC_MULT_NUM  >> (i + 1'b1);

            reg     [OUT_BIT-2:0]   add_idata   [0:OUT_NUM*2-1];
            wire    [OUT_BIT-1:0]   add_odata   [0:OUT_NUM-1];

            for (j = 0; j < OUT_NUM; j = j + 1) begin: gen_adt_adder

                // Organize adder inputs
                if (i == 0) begin   // Input Stage
                    always @(posedge clk or negedge rstn) begin
                        if (!rstn) begin
                            add_idata[j*2]   <= 'd0;
                            add_idata[j*2+1] <= 'd0;
                        end
                        else if (idata_valid) begin
                            add_idata[j*2]   <= idata[(j*2+0)*IDATA_WIDTH+:IDATA_WIDTH];
                            add_idata[j*2+1] <= idata[(j*2+1)*IDATA_WIDTH+:IDATA_WIDTH];
                        end
                    end
                end
                else if (i % 2 == 0) begin  // Even Stage, Insert a pipeline
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
                else begin  // Odd Stage, Combinational
                    always @(*) begin
                        add_idata[j*2]   = gen_adt_stage[i-1].add_odata[j*2];
                        add_idata[j*2+1] = gen_adt_stage[i-1].add_odata[j*2+1];
                    end
                end

                // Adder instantization
                add_int #(.IDATA_WIDTH(OUT_BIT-1), .ODATA_BIT(OUT_BIT)) adder_inst (
                    .idataA                 (add_idata[j*2]),
                    .idataB                 (add_idata[j*2+1]),
                    .odata                  (add_odata[j])
                );
            end
        end
    endgenerate

    //I add another register here -BUCK
    reg [ODATA_BIT-1:0]         nxt_odata;
    reg                         nxt_odata_valid;    

    // Output
    always @(*) begin
        nxt_odata       = $signed(gen_adt_stage[STAGE_NUM-1].add_odata[0]); //BUCK, 这里如果位宽不匹配，也会做符号位扩展
        nxt_odata_valid = gen_adt_valid[STAGE_NUM-1].add_valid;
    end
    always @(posedge clk or negedge rstn) begin
        if(~rstn)begin
            odata <= 0       ;
            odata_valid <= 0 ;
        end
        else begin
            odata <= nxt_odata       ;
            odata_valid <= nxt_odata_valid ;
        end
    end
endmodule 