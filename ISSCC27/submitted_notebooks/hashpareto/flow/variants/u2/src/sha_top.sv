module sha_top #(
    parameter int UNROLL = 2
)(
    input  logic        aclk,
    input  logic        aresetn,
    input  logic        m_axis_tready,
    output logic [31:0] m_axis_tdata,
    output logic        m_axis_tvalid,
    output logic        m_axis_tlast,
    input  logic [31:0] s_axis_tdata,
    input  logic [3:0]  s_axis_tkeep,
    input  logic        s_axis_tvalid,
    input  logic        s_axis_tlast,
    output logic        s_axis_tready
);

    logic [255:0] digest;
    logic         digest_valid;
    logic [511:0] block;
    logic         sha_valid;
    logic         done;
    logic         scheduler_ready;
    logic         final_digest_valid;

    assign final_digest_valid = digest_valid & done;

    message_padder message_processing_unit (
        .aclk            (aclk),
        .aresetn         (aresetn),
        .s_axis_tdata    (s_axis_tdata),
        .s_axis_tkeep    (s_axis_tkeep),
        .s_axis_tvalid   (s_axis_tvalid),
        .s_axis_tlast    (s_axis_tlast),
        .s_axis_tready   (s_axis_tready),
        .block           (block),
        .sha_valid       (sha_valid),
        .done            (done),
        .scheduler_ready (scheduler_ready)
    );

    sha256_core #(
        .UNROLL (UNROLL)
    ) core (
        .clk             (aclk),
        .rst_n           (aresetn),
        .block           (block),
        .done            (done),
        .sha_valid       (sha_valid),
        .scheduler_ready (scheduler_ready),
        .digest          (digest),
        .digest_valid    (digest_valid)
    );

    digest_buffer digest_serializer (
        .aclk          (aclk),
        .aresetn       (aresetn),
        .digest        (digest),
        .digest_valid  (final_digest_valid),
        .m_axis_tready (m_axis_tready),
        .m_axis_tdata  (m_axis_tdata),
        .m_axis_tvalid (m_axis_tvalid),
        .m_axis_tlast  (m_axis_tlast)
    );
endmodule
