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

// =============================================================================
// Combinational INT-Mul logic

module mul_int #(
    parameter   IDATA_WIDTH = 8,
    parameter   ODATA_BIT = IDATA_WIDTH*2
)(
    // Data Signals
    input       [IDATA_WIDTH-1:0] idataA,
    input       [IDATA_WIDTH-1:0] idataB,
    output      [ODATA_BIT-1:0] odata    
);

    reg signed  [ODATA_BIT-1:0] odata_comb;

    always @(*) begin
        odata_comb = $signed(idataA) * $signed(idataB);
    end

    assign  odata = odata_comb;

endmodule

// =============================================================================
// Combinational INT-Add logic

module add_int #(
    parameter   IDATA_WIDTH = 8,
    parameter   ODATA_BIT = 9
)(
    // Data Signals
    input       [IDATA_WIDTH-1:0] idataA,
    input       [IDATA_WIDTH-1:0] idataB,
    output      [ODATA_BIT-1:0] odata
);

    reg signed  [ODATA_BIT-1:0] odata_comb;

    always @(*) begin
        odata_comb = $signed(idataA) + $signed(idataB);
    end

    assign  odata = odata_comb;

endmodule

// =============================================================================
// Combinational FP-Mul logic

module mul_fp #(
    parameter   EXP_BIT = 8,
    parameter   MAT_BIT = 7,
    parameter   DATA_BIT = EXP_BIT + MAT_BIT + 1
)(
    input       [DATA_BIT-1:0]  idataA,
    input       [DATA_BIT-1:0]  idataB,
    output      [DATA_BIT-1:0]  odata
);

    localparam  EXP_BASE = 2 ** (EXP_BIT-1) - 1;

    // Extract Exponent and Mantissam Field of Input A and B
    reg                     idataA_sig, idataB_sig;
    reg     [EXP_BIT-1:0]   idataA_exp, idataB_exp;
    reg     [MAT_BIT:0]     idataA_mat, idataB_mat;

    always @(*) begin
        idataA_sig = idataA[DATA_BIT-1];
        idataA_exp = idataA[MAT_BIT+:EXP_BIT];
        idataA_mat = {1'b1, idataA[MAT_BIT-1:0]};
        idataB_sig = idataB[DATA_BIT-1];
        idataB_exp = idataB[MAT_BIT+:EXP_BIT];
        idataB_mat = {1'b1, idataB[MAT_BIT-1:0]};
    end

    // Sign, Exponent and Mantissa Bit for Output
    reg                     product_sig;
    reg     [EXP_BIT:0]     product_exp;
    reg     [MAT_BIT*2:0]   product_mat;

    always @(*) begin
        product_sig = idataA_sig ^ idataB_sig;
        product_exp = idataA_exp + idataB_exp;
        product_mat = idataA_mat * idataB_mat;
    end

    // Output Normalization: Left shift the mantissia if the top bit is zero.
    reg                     odata_sig;
    reg     [EXP_BIT-1:0]   odata_exp;
    reg     [MAT_BIT-1:0]   odata_mat;

    always @(*) begin
        odata_sig = product_sig;
        odata_exp = product_exp - EXP_BASE + product_mat[MAT_BIT*2];
        odata_mat = product_mat[MAT_BIT*2] ? product_mat[(MAT_BIT*2)-:MAT_BIT] : product_mat[(MAT_BIT*2-1)-:MAT_BIT];
    end

    // Output
    assign  odata = (product_exp < EXP_BASE) ? 'd0 :
                    (idataA_exp == 'd0)      ? 'd0 :
                    (idataB_exp == 'd0)      ? 'd0 :
                    {odata_sig, odata_exp, odata_mat};

endmodule

// =============================================================================
// Combinational FP-Add logic
// FP-Add is always much more expensive than FP-Mul.
// Set a pipeline (a set of DFFs) for higher working frequency.

module add_fp #(
    parameter   EXP_BIT = 8,
    parameter   MAT_BIT = 7,
    parameter   DATA_BIT = EXP_BIT + MAT_BIT + 1,
    parameter   ENABLE_PIPELINE = 1 // 1 for True, 0 for False
)(
    // Global Signals
    input                       clk,
    input                       rst,

    // Data Signals
    input       [DATA_BIT-1:0]  idataA,
    input       [DATA_BIT-1:0]  idataB,
    output      [DATA_BIT-1:0]  odata
);

    // Extract Exponent and Mantissam Field of Input A and B
    reg                     idataA_sig, idataB_sig;
    reg     [EXP_BIT-1:0]   idataA_exp, idataB_exp;
    reg     [MAT_BIT:0]     idataA_mat, idataB_mat;

    always @(*) begin
        idataA_sig = idataA[DATA_BIT-1];
        idataA_exp = idataA[MAT_BIT+:EXP_BIT];
        idataA_mat = {1'b1, idataA[MAT_BIT-1:0]};
        idataB_sig = idataB[DATA_BIT-1];
        idataB_exp = idataB[MAT_BIT+:EXP_BIT];
        idataB_mat = {1'b1, idataB[MAT_BIT-1:0]};
    end

    // Merge InputA and InputB's Mantissas for Output
    // 1. Determine the Larger Input
    wire    idataA_larger;
    assign  idataA_larger = (idataA_exp > idataB_exp) ? 1'b1 :
                            ((idataA_exp == idataB_exp) && (idataA_mat > idataB_mat)) ? 1'b1 : 1'b0;

    // 2. Determine EXP difference
    wire    [EXP_BIT-1:0]   exp_diff;
    assign  exp_diff = idataA_larger ? idataA_exp - idataB_exp : idataB_exp - idataA_exp;

    // 3. Shift the Mantissa of Smaller Input
    wire    [MAT_BIT*2+1:0] idataA_mat_shift;
    wire    [MAT_BIT*2+1:0] idataB_mat_shift;

    assign  idataA_mat_shift = idataA_larger              ? {1'b0, idataA_mat, {(MAT_BIT){1'b0}}} :
                               (exp_diff > (MAT_BIT*2-1)) ? 'd0 :
                               {1'b0, idataA_mat, {(MAT_BIT){1'b0}}} >> exp_diff;
    assign  idataB_mat_shift = ~idataA_larger             ? {1'b0, idataB_mat, {(MAT_BIT){1'b0}}} :
                               (exp_diff > (MAT_BIT*2-1)) ? 'd0 :
                               {1'b0, idataB_mat, {(MAT_BIT){1'b0}}} >> exp_diff;

    // 4. Add or Substract InputA and InputB's Mantissas accoring to Sign Bit
    wire                    pre_sign;
    wire    [EXP_BIT-1:0]   pre_exp;
    wire    [MAT_BIT*2+1:0] pre_mat;

    assign  pre_sign = idataA_larger ? idataA_sig : idataB_sig;
    assign  pre_exp  = idataA_larger ? idataA_exp : idataB_exp;
    assign  pre_mat  = ((idataA_sig^idataB_sig) &&  idataA_larger) ? idataA_mat_shift - idataB_mat_shift :
                       ((idataA_sig^idataB_sig) && ~idataA_larger) ? idataB_mat_shift - idataA_mat_shift :
                       idataA_mat_shift + idataB_mat_shift;

    // Enable Pipeline
    reg                     pre_sig_reg;
    reg     [EXP_BIT-1:0]   pre_exp_reg;
    reg     [MAT_BIT*2+1:0] pre_mat_reg;
    reg     [DATA_BIT-1:0]  idataA_reg;
    reg     [DATA_BIT-1:0]  idataB_reg;
    reg                     idataA_zero_reg, idataB_zero_reg;

    genvar i;
    generate
        if (ENABLE_PIPELINE) begin: gen_fpadd_pipeline
            always @(posedge clk or posedge rst) begin
                if (rst) begin
                    pre_sig_reg <= 1'b0;
                    pre_exp_reg <= 'd0;
                    pre_mat_reg <= 'd0;
                    idataA_reg  <= 'd0;
                    idataB_reg  <= 'd0;
                    idataA_zero_reg <= 1'b0;
                    idataB_zero_reg <= 1'b0;
                end
                else begin
                    pre_sig_reg <= pre_sign;
                    pre_exp_reg <= pre_exp;
                    pre_mat_reg <= pre_mat;
                    idataA_reg  <= idataA;
                    idataB_reg  <= idataB;
                    idataA_zero_reg <= idataA_exp == 'd0;
                    idataB_zero_reg <= idataB_exp == 'd0;
                end
            end
        end
        else begin
            always @(*) begin
                pre_sig_reg = pre_sign;
                pre_exp_reg = pre_exp;
                pre_mat_reg = pre_mat;
                idataA_reg  = idataA;
                idataB_reg  = idataB;
                idataA_zero_reg = idataA_exp == 'd0;
                idataB_zero_reg = idataB_exp == 'd0;
            end
        end
    endgenerate

    // Normalize Pre-Result for Output
    // 1. Left Shift Mantissa to Meet Bit-1 in MSB
    wire    [EXP_BIT-1:0]   pre_exp_shift;
    wire    [MAT_BIT*2+1:0] pre_mat_shift;
    wire    [MAT_BIT-1:0]   shift_cnt;

    lead_one #(.IDATA_WIDTH(MAT_BIT*2+2), .ODATA_BIT(MAT_BIT)) lo_inst (
        .idata              (pre_mat_reg),
        .odata              (shift_cnt)
    );

    assign  pre_exp_shift = pre_exp_reg - shift_cnt + 1'b1;
    assign  pre_mat_shift = pre_mat_reg << ((MAT_BIT*2+2) - shift_cnt + 1'b1);

    // 2. Detect Underflow
    wire    underflow;
    assign  underflow = ~pre_exp_shift[EXP_BIT-1] && pre_exp_reg[EXP_BIT-1] && (shift_cnt != 'd0);

    // 3. Output
    assign  odata = (idataA_zero_reg && idataB_zero_reg) ? 'd0 :
                     underflow                           ? 'd0 :
                    (pre_mat_reg == 'd0)                 ? 'd0 :
                     idataA_zero_reg                     ? idataB_reg :
                     idataB_zero_reg                     ? idataA_reg :
                    {pre_sig_reg, pre_exp_shift, pre_mat_shift[(MAT_BIT*2+1)-:MAT_BIT]};

endmodule

// =============================================================================
// First-One-Bit Detector used in FP-Add logic

module lead_one #(
    parameter   IDATA_WIDTH = 36,
    parameter   ODATA_BIT = 8
)(
    // Data Signals
    input       [IDATA_WIDTH-1:0] idata,
    output      [ODATA_BIT-1:0] odata
);

    wire    [ODATA_BIT-1:0] postion [0:IDATA_WIDTH];
    assign  postion[0] = 'd0;   // Default Value if Bit-0 is zero

    // Check Each Bit
    genvar i;
    generate
        for (i = 0; i < IDATA_WIDTH; i = i + 1) begin: gen_lead_one
            assign  postion[i+1] = idata[i] ? i : postion[i];
        end
    endgenerate

    // Output: Check All Bits are Zero (|idata == 0)
    assign  odata = |idata == 1'b0 ? 'd0 : (postion[IDATA_WIDTH] + 1'b1); 

endmodule