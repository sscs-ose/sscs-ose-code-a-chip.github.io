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
    typedef enum logic [1:0] {IDLE, WAIT_MEMORY, RESULT, DRAIN} state_t;
    state_t state;
    logic owner, saved_write;
    logic [7:0] saved_id;
    logic [31:0] result_data;
    logic result_error;
    logic turn, locked, locked_owner;
    logic selected;

    // A client keeps its request unchanged until acceptance. Locking just its
    // index also keeps every external request field stable under backpressure.
    assign selected = locked ? locked_owner :
                      (req_valid[turn] ? turn : !turn);
    assign m_req_valid = rst_n && !flush && state == IDLE && req_valid[selected];
    assign m_req_write = selected ? req_write[1] : req_write[0];
    assign m_req_addr = selected ? req_addr[63:32] : req_addr[31:0];
    assign m_req_wdata = selected ? req_wdata[63:32] : req_wdata[31:0];
    assign m_req_wstrb = selected ? req_wstrb[7:4] : req_wstrb[3:0];
    assign m_req_tag = 2'b00;
    assign req_ready[0] = m_req_valid && m_req_ready && !selected;
    assign req_ready[1] = m_req_valid && m_req_ready && selected;

    // The one transaction slot also holds a completed result. This decouples
    // external completion from client response backpressure and cuts the
    // memory-to-CPU combinational data path.
    assign rsp_valid[0] = rst_n && state == RESULT && !flush && !owner;
    assign rsp_valid[1] = rst_n && state == RESULT && !flush && owner;
    assign rsp_rdata = {2{result_data}};
    assign rsp_id = {2{saved_id}};
    assign rsp_err = {2{result_error}};
    assign m_rsp_ready = rst_n && (state == WAIT_MEMORY || state == DRAIN) &&
                         m_rsp_tag == 2'b00;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            owner <= 1'b0;
            saved_write <= 1'b0;
            saved_id <= 8'b0;
            result_data <= 32'b0;
            result_error <= 1'b0;
            turn <= 1'b0;
            locked <= 1'b0;
            locked_owner <= 1'b0;
        end else if (flush) begin
            // An unaccepted offer is canceled; an accepted request remains
            // reserved until its response drains, including during flush.
            locked <= 1'b0;
            if ((state == WAIT_MEMORY || state == DRAIN) &&
                !(m_rsp_valid && m_rsp_ready)) state <= DRAIN;
            else state <= IDLE;
        end else begin
            if (m_req_valid) begin
                if (m_req_ready) begin
                    state <= WAIT_MEMORY;
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
                if (state == DRAIN) state <= IDLE;
                else begin
                    result_data <= saved_write ? 32'b0 : m_rsp_rdata;
                    result_error <= m_rsp_err;
                    state <= RESULT;
                end
            end
            if (state == RESULT && rsp_ready[owner]) state <= IDLE;
        end
    end
endmodule
