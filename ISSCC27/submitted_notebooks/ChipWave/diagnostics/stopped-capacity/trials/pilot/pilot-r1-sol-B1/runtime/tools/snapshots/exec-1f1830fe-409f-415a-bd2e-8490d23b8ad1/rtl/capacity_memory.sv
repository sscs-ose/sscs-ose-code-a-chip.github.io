// Single globally outstanding transaction. Client acceptance is exactly the
// downstream request handshake, so no additional request/data queue is needed.
module capacity_memory (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        flush,
    input  logic [1:0]  req_valid,
    output logic [1:0]  req_ready,
    input  logic [1:0]  req_write,
    input  logic [63:0] req_addr,
    input  logic [63:0] req_wdata,
    input  logic [7:0]  req_wstrb,
    input  logic [15:0] req_id,
    output logic [1:0]  rsp_valid,
    input  logic [1:0]  rsp_ready,
    output logic [63:0] rsp_rdata,
    output logic [15:0] rsp_id,
    output logic [1:0]  rsp_err,
    output logic        m_req_valid,
    input  logic        m_req_ready,
    output logic        m_req_write,
    output logic [31:0] m_req_addr,
    output logic [31:0] m_req_wdata,
    output logic [3:0]  m_req_wstrb,
    output logic [1:0]  m_req_tag,
    input  logic        m_rsp_valid,
    output logic        m_rsp_ready,
    input  logic [1:0]  m_rsp_tag,
    input  logic [31:0] m_rsp_rdata,
    input  logic        m_rsp_err
);
    logic busy, stale;
    logic owner, saved_write;
    logic [7:0] saved_id;
    logic turn, locked, locked_owner;
    logic selected;
    logic response_present;

    // A client keeps its request unchanged until acceptance. Locking just its
    // index also keeps every external request field stable under backpressure.
    assign selected = locked ? locked_owner :
                      (req_valid[turn] ? turn : !turn);
    assign m_req_valid = rst_n && !flush && !busy && req_valid[selected];
    assign m_req_write = selected ? req_write[1] : req_write[0];
    assign m_req_addr = selected ? req_addr[63:32] : req_addr[31:0];
    assign m_req_wdata = selected ? req_wdata[63:32] : req_wdata[31:0];
    assign m_req_wstrb = selected ? req_wstrb[7:4] : req_wstrb[3:0];
    assign m_req_tag = 2'b00;
    assign req_ready[0] = m_req_valid && m_req_ready && !selected;
    assign req_ready[1] = m_req_valid && m_req_ready && selected;

    // Memory already provides a holding register for the response. Retiring
    // directly into the selected client avoids a redundant response buffer.
    assign response_present = rst_n && busy && m_rsp_valid && m_rsp_tag == 2'b00;
    assign rsp_valid[0] = response_present && !flush && !stale && !owner;
    assign rsp_valid[1] = response_present && !flush && !stale && owner;
    assign rsp_rdata = {2{saved_write ? 32'b0 : m_rsp_rdata}};
    assign rsp_id = {2{saved_id}};
    assign rsp_err = {2{m_rsp_err}};
    assign m_rsp_ready = rst_n && busy && m_rsp_tag == 2'b00 &&
                         (flush || stale || rsp_ready[owner]);

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0;
            stale <= 1'b0;
            owner <= 1'b0;
            saved_write <= 1'b0;
            saved_id <= 8'b0;
            turn <= 1'b0;
            locked <= 1'b0;
            locked_owner <= 1'b0;
        end else if (flush) begin
            // An unaccepted offer is canceled; an accepted request remains
            // reserved until its response drains, including during flush.
            locked <= 1'b0;
            if (busy && m_rsp_valid && m_rsp_ready) begin
                busy <= 1'b0;
                stale <= 1'b0;
            end else if (busy) begin
                stale <= 1'b1;
            end
        end else begin
            if (m_req_valid) begin
                if (m_req_ready) begin
                    busy <= 1'b1;
                    stale <= 1'b0;
                    owner <= selected;
                    saved_write <= m_req_write;
                    saved_id <= selected ? req_id[15:8] : req_id[7:0];
                    turn <= !selected;
                    locked <= 1'b0;
                end else begin
                    locked <= 1'b1;
                    locked_owner <= selected;
                end
            end
            if (m_rsp_valid && m_rsp_ready) begin
                busy <= 1'b0;
                stale <= 1'b0;
            end
        end
    end
endmodule
