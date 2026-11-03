module capacity_memory (
    input logic clk, rst_n, flush,
    input logic [1:0] req_valid,
    output logic [1:0] req_ready,
    input logic [1:0] req_write,
    input logic [63:0] req_addr, req_wdata,
    input logic [7:0] req_wstrb,
    input logic [15:0] req_id,
    output logic [1:0] rsp_valid,
    input logic [1:0] rsp_ready,
    output logic [63:0] rsp_rdata,
    output logic [15:0] rsp_id,
    output logic [1:0] rsp_err,
    output logic m_req_valid,
    input logic m_req_ready,
    output logic m_req_write,
    output logic [31:0] m_req_addr, m_req_wdata,
    output logic [3:0] m_req_wstrb,
    output logic [1:0] m_req_tag,
    input logic m_rsp_valid,
    output logic m_rsp_ready,
    input logic [1:0] m_rsp_tag,
    input logic [31:0] m_rsp_rdata,
    input logic m_rsp_err
);
    typedef enum logic [1:0] {IDLE, WAIT_MEM, RESULT, STALE} state_t;
    state_t state;
    logic prefer_client;
    logic chosen;
    logic owner;
    logic saved_write;
    logic [7:0] saved_id;
    logic [31:0] saved_data;
    logic saved_err;

    always_comb begin
        chosen = prefer_client;
        if (!req_valid[prefer_client] && req_valid[~prefer_client])
            chosen = ~prefer_client;

        req_ready = 2'b00;
        m_req_valid = 1'b0;
        m_req_write = 1'b0;
        m_req_addr = 32'b0;
        m_req_wdata = 32'b0;
        m_req_wstrb = 4'b0;
        m_req_tag = 2'b00;
        m_rsp_ready = 1'b0;
        rsp_valid = 2'b00;
        rsp_rdata = 64'b0;
        rsp_id = 16'b0;
        rsp_err = 2'b0;

        if (rst_n && !flush) begin
            if (state == IDLE && req_valid[chosen]) begin
                m_req_valid = 1'b1;
                m_req_write = req_write[chosen];
                m_req_addr = req_addr[32*chosen +: 32];
                m_req_wdata = req_wdata[32*chosen +: 32];
                m_req_wstrb = req_wstrb[4*chosen +: 4];
                if (m_req_ready) req_ready[chosen] = 1'b1;
            end
            if (state == RESULT) begin
                rsp_valid[owner] = 1'b1;
                rsp_rdata[32*owner +: 32] = saved_data;
                rsp_id[8*owner +: 8] = saved_id;
                rsp_err[owner] = saved_err;
            end
        end

        if (rst_n && (state == WAIT_MEM || state == STALE))
            m_rsp_ready = 1'b1;
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            prefer_client <= 1'b0;
            owner <= 1'b0;
            saved_write <= 1'b0;
            saved_id <= 8'b0;
            saved_data <= 32'b0;
            saved_err <= 1'b0;
        end else if (flush) begin
            if (state == WAIT_MEM && !(m_rsp_valid && m_rsp_ready)) state <= STALE;
            else state <= IDLE;
            saved_data <= 32'b0;
            saved_err <= 1'b0;
        end else begin
            case (state)
                IDLE: if (m_req_valid && m_req_ready) begin
                    owner <= chosen;
                    saved_id <= req_id[8*chosen +: 8];
                    saved_write <= req_write[chosen];
                    prefer_client <= ~chosen;
                    state <= WAIT_MEM;
                end
                WAIT_MEM: if (m_rsp_valid && m_rsp_ready) begin
                    saved_data <= saved_write ? 32'b0 : m_rsp_rdata;
                    saved_err <= m_rsp_err;
                    state <= RESULT;
                end
                RESULT: if (rsp_valid[owner] && rsp_ready[owner])
                    state <= IDLE;
                STALE: if (m_rsp_valid && m_rsp_ready)
                    state <= IDLE;
                default: state <= IDLE;
            endcase
        end
    end
endmodule
