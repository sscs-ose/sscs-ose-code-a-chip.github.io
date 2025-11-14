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

module core_quant #(
    parameter   IDATA_WIDTH = `ODATA_WIDTH,
    parameter   ODATA_BIT = `IDATA_WIDTH,
    parameter   CDATA_ACCU_NUM_WIDTH = `CDATA_ACCU_NUM_WIDTH,
    parameter   CDATA_SCALE_WIDTH = `CDATA_SCALE_WIDTH,
    parameter   CDATA_BIAS_WIDTH = `CDATA_BIAS_WIDTH,
    parameter   CDATA_SHIFT_WIDTH = `CDATA_SHIFT_WIDTH,
    parameter   QUANT_SCALE_RETIMING = `QUANT_SCALE_RETIMING,
    parameter   TEMP_BIT  = (IDATA_WIDTH+CDATA_SCALE_WIDTH)
)(
    // Global Signals
    input                                       clk,
    input                                       rstn,

    // Global Config Signals
    input       [CDATA_SCALE_WIDTH-1:0]         cfg_quant_scale,
    input       [CDATA_BIAS_WIDTH-1:0]          cfg_quant_bias,
    input       [CDATA_SHIFT_WIDTH-1:0]         cfg_quant_shift,

    // Data Signals
    input       [IDATA_WIDTH-1:0]               idata,
    input                                       idata_valid,
    output  reg [ODATA_BIT-1:0]                 odata,
    output  reg                                 odata_valid
);
    reg signed  [(TEMP_BIT-1):0]   quantized_product; 
    reg signed  [TEMP_BIT:0]       quantized_bias,quantized_bias_reg; 
    reg                            quantized_product_valid,quantized_bias_valid,quantized_shift_valid,quantized_round_valid;
    reg signed  [(TEMP_BIT):0]     quantized_shift,quantized_shift_reg;
    reg signed                     quantized_round,quantized_round_reg;

    // Quantize: Scale x Input + Bias
    // Scaling
    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            quantized_product <= 'd0;
        end
        else if (idata_valid) begin
            quantized_product <= $signed(idata) * $signed({1'b0, cfg_quant_scale}); //This may be the critical path, 24bits * 16bits
                                                                            //We should notice this
                                                                            //Try retiming?
        end
    end
    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            quantized_product_valid <= 1'b0;
        end
        else begin
            quantized_product_valid <= idata_valid;
        end
    end

    //scale retiming
    genvar i;
    generate;
        for(i = 0; i < QUANT_SCALE_RETIMING; i=i+1)begin : quant_scale_retiming_gen_array
            reg quantized_product_valid_delay;
            reg signed  [(TEMP_BIT-1):0]   quantized_product_delay; 
            if(i==0)begin
                always @(posedge clk or negedge rstn) begin
                    if(~rstn)begin
                        quantized_product_valid_delay <= 0;
                        quantized_product_delay <= 0;
                    end
                    else begin
                        quantized_product_valid_delay <= quantized_product_valid;
                        quantized_product_delay <= quantized_product;
                    end
                end
            end
            else begin
                always @(posedge clk or negedge rstn) begin
                    if(~rstn)begin
                        quantized_product_valid_delay <= 0;
                        quantized_product_delay <= 0;
                    end
                    else begin
                        quantized_product_valid_delay <= quant_scale_retiming_gen_array[i-1].quantized_product_valid_delay;
                        quantized_product_delay <= quant_scale_retiming_gen_array[i-1].quantized_product_delay;
                    end
                end
            end
        end
    endgenerate

    // Adding Bias and Shifting
    always @(*) begin
        quantized_bias = $signed(quant_scale_retiming_gen_array[QUANT_SCALE_RETIMING-1].quantized_product_delay) + $signed(cfg_quant_bias);
        // quantized_round = quantized_bias[cfg_quant_shift-1];
        quantized_round = (cfg_quant_shift > 0) ? quantized_bias[cfg_quant_shift-1] : 0;
    end
    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            quantized_bias_reg <= 'd0;
            quantized_round_reg <= 1'b0;
        end
        else if(quant_scale_retiming_gen_array[QUANT_SCALE_RETIMING-1].quantized_product_valid_delay)begin
            quantized_bias_reg <= quantized_bias;
            quantized_round_reg <= quantized_round;
        end
    end
    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            quantized_bias_valid <= 1'b0;
        end
        else begin
            quantized_bias_valid <= quant_scale_retiming_gen_array[QUANT_SCALE_RETIMING-1].quantized_product_valid_delay;
        end
    end

    //Rounding
    always @(*) begin
        quantized_shift = (quantized_bias_reg >>> cfg_quant_shift);
        quantized_shift = quantized_round_reg ? $signed(quantized_shift)+1 : $signed(quantized_shift);
    end
    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            quantized_shift_reg <= 'd0;
        end
        else if(quantized_bias_valid)begin
            quantized_shift_reg <= quantized_shift;
        end
    end
    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            quantized_shift_valid <= 1'b0;
        end
        else begin
            quantized_shift_valid <= quantized_bias_valid;
        end
    end

    // Quantize: Detect Overflow
    reg         [ODATA_BIT-1:0]     quantized_overflow;

    always @(*) begin 
        if ((quantized_shift_reg[(TEMP_BIT)] & (~(&quantized_shift_reg[(TEMP_BIT)-1:ODATA_BIT-1]))) ||
            (~quantized_shift_reg[(TEMP_BIT)] & (|quantized_shift_reg[(TEMP_BIT)-1:ODATA_BIT-1]))) begin

            quantized_overflow = {quantized_shift_reg[(TEMP_BIT)], {(ODATA_BIT-1){~quantized_shift_reg[(TEMP_BIT)]}}};
            
        end
        else begin
            quantized_overflow = {quantized_shift_reg[(TEMP_BIT)], quantized_shift_reg[ODATA_BIT-2:0]};
        end
    end

    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            odata <= 'd0;
        end
        else if (quantized_shift_valid) begin
            odata <= quantized_overflow;
        end
    end

    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            odata_valid <= 'd0;
        end
        else begin
            odata_valid <= quantized_shift_valid;
        end
    end

endmodule