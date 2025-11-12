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

module core_buf #(
    // Core-to-Core Link (Access Activation Buffer)
    parameter   CACHE_DATA_WIDTH = (`MAC_MULT_NUM * `IDATA_WIDTH)
)(
    // Global Signals
    input                              clk,
    input                              rstn,

    // Channel - Core-to-Core Link
    input       [CACHE_DATA_WIDTH-1:0] hlink_wdata,
    input                              hlink_wen,
    output      [CACHE_DATA_WIDTH-1:0] hlink_rdata,
    output                             hlink_rvalid
    );

    // =============================================================================
    // Core-to-Core Link Channel

    // 1. Write Channel: HLINK -> Core
    reg     [CACHE_DATA_WIDTH-1:0]     hlink_reg;
    reg                                hlink_reg_valid;

    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            hlink_reg <= 'd0;
        end
        else if (hlink_wen) begin
            hlink_reg <= hlink_wdata;
        end
    end

    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            hlink_reg_valid <= 1'b0;
        end
        else begin
            hlink_reg_valid <= hlink_wen;
        end
    end

    // 2. Read Channel: Core -> HLINK
    assign  hlink_rdata  = hlink_reg;
    assign  hlink_rvalid = hlink_reg_valid;
endmodule 