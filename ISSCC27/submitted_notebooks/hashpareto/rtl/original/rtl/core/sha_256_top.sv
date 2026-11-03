module sha_top(
    input logic aclk,
    input logic aresetn,
    // master interfaces
    input logic m_axis_tready,
    output logic [31:0] m_axis_tdata,
    output logic m_axis_tvalid,
    output logic m_axis_tlast,
    // slave interfaces
    input logic [31:0] s_axis_tdata,
    input logic [3:0] s_axis_tkeep,
    input logic s_axis_tvalid,
    input logic s_axis_tlast,
    output logic s_axis_tready
);
    timeunit 1ns;
    timeprecision 1ps;

    logic [255:0] digest;
    logic digest_valid;
    logic [511:0] block;
    logic sha_valid;
    logic done;
    logic scheduler_ready;
    logic final_digest_valid;
    assign final_digest_valid = digest_valid & done;

    // instantiation of submodule
    digest_buffer buffer(.*, .digest_valid(final_digest_valid));
    message_padder message_processing_unit(.*);
    sha_core core(.clk(aclk), .rst_n(aresetn), .block, .done, .sha_valid, .digest, .digest_valid, .scheduler_ready);
endmodule