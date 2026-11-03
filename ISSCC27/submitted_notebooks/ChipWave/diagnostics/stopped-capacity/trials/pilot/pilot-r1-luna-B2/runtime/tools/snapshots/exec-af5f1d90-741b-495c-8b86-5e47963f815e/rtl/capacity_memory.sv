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

    localparam logic [2:0] FREE  = 3'd0,
                           OFFER = 3'd1,
                           WAIT  = 3'd2,
                           DONE  = 3'd3,
                           STALE = 3'd4;

    logic [2:0] state [0:3];
    logic       owner [0:3];
    logic [7:0] saved_id [0:3];
    logic       saved_write [0:3];
    logic [31:0] saved_rdata [0:3];
    logic       saved_err [0:3];
    logic [1:0] queue [0:1][0:3];
    logic [1:0] q_head [0:1], q_tail [0:1];
    logic [2:0] q_count [0:1];
    logic       priority_client;

    logic have_slot;
    logic [1:0] free_tag;
    logic grant_valid, grant_client;
    logic held_offer;
    logic [1:0] held_tag;
    logic held_client, held_write;
    logic [31:0] held_addr, held_wdata;
    logic [3:0] held_wstrb;
    logic [7:0] held_id;
    logic [1:0] selected_tag;
    logic selected_client, selected_write;
    logic [31:0] selected_addr, selected_wdata;
    logic [3:0] selected_wstrb;
    logic [7:0] selected_id;
    logic push0, push1, pop0, pop1;

    integer i;
    always_comb begin
        have_slot = 1'b0;
        free_tag = 2'd0;
        for (integer n = 0; n < 4; n = n + 1) begin
            if (!have_slot && state[n] == FREE) begin
                have_slot = 1'b1;
                free_tag = n[1:0];
            end
        end

        grant_valid = 1'b0;
        grant_client = 1'b0;
        if (req_valid[0] && req_valid[1]) begin
            grant_valid = 1'b1;
            grant_client = priority_client;
        end else if (req_valid[0]) begin
            grant_valid = 1'b1;
            grant_client = 1'b0;
        end else if (req_valid[1]) begin
            grant_valid = 1'b1;
            grant_client = 1'b1;
        end

        selected_tag = held_offer ? held_tag : free_tag;
        selected_client = held_offer ? held_client : grant_client;
        selected_write = held_offer ? held_write : req_write[grant_client];
        selected_addr = held_offer ? held_addr : req_addr[32*grant_client +: 32];
        selected_wdata = held_offer ? held_wdata : req_wdata[32*grant_client +: 32];
        selected_wstrb = held_offer ? held_wstrb : req_wstrb[4*grant_client +: 4];
        selected_id = held_offer ? held_id : req_id[8*grant_client +: 8];
        m_req_valid = rst_n && !flush &&
                      (held_offer || (have_slot && grant_valid));
        m_req_tag = selected_tag;
        m_req_write = selected_write;
        m_req_addr = selected_addr;
        m_req_wdata = selected_wdata;
        m_req_wstrb = selected_wstrb;
        req_ready = 2'b00;
        if (rst_n && !flush && m_req_valid && m_req_ready)
            req_ready[selected_client] = 1'b1;

        rsp_valid = 2'b00;
        rsp_rdata = 64'b0;
        rsp_id = 16'b0;
        rsp_err = 2'b0;
        for (integer c = 0; c < 2; c = c + 1) begin
            if (rst_n && !flush && q_count[c] != 0 &&
                state[queue[c][q_head[c]]] == DONE) begin
                rsp_valid[c] = 1'b1;
                rsp_id[8*c +: 8] = saved_id[queue[c][q_head[c]]];
                rsp_err[c] = saved_err[queue[c][q_head[c]]];
                rsp_rdata[32*c +: 32] = saved_write[queue[c][q_head[c]]] ?
                    32'b0 : saved_rdata[queue[c][q_head[c]]];
            end
        end

        // Flush drops client-visible state but still accepts old external
        // completions so their tags can be retired safely.
        m_rsp_ready = rst_n;
        push0 = req_ready[0];
        push1 = req_ready[1];
        pop0 = rsp_valid[0] && rsp_ready[0];
        pop1 = rsp_valid[1] && rsp_ready[1];
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            priority_client <= 1'b0;
            held_offer <= 1'b0;
            held_tag <= 2'b0;
            held_client <= 1'b0;
            held_write <= 1'b0;
            held_addr <= 32'b0;
            held_wdata <= 32'b0;
            held_wstrb <= 4'b0;
            held_id <= 8'b0;
            for (i = 0; i < 4; i = i + 1) begin
                state[i] <= FREE;
                owner[i] <= 1'b0;
                saved_id[i] <= 8'b0;
                saved_write[i] <= 1'b0;
                saved_rdata[i] <= 32'b0;
                saved_err[i] <= 1'b0;
            end
            for (i = 0; i < 2; i = i + 1) begin
                q_head[i] <= 2'b0;
                q_tail[i] <= 2'b0;
                q_count[i] <= 3'b0;
            end
        end else if (flush) begin
            held_offer <= 1'b0;
            q_head[0] <= 2'b0;
            q_head[1] <= 2'b0;
            q_tail[0] <= 2'b0;
            q_tail[1] <= 2'b0;
            q_count[0] <= 3'b0;
            q_count[1] <= 3'b0;
            for (i = 0; i < 4; i = i + 1) begin
                if (state[i] == WAIT || state[i] == STALE) begin
                    if (m_rsp_valid && m_rsp_ready && m_rsp_tag == i[1:0])
                        state[i] <= FREE;
                    else
                        state[i] <= STALE;
                end else begin
                    // OFFER was never accepted by memory; DONE has already
                    // consumed its external response. Both may be discarded.
                    state[i] <= FREE;
                end
            end
        end else begin
            if (m_req_valid && !m_req_ready && !held_offer) begin
                state[free_tag] <= OFFER;
                held_offer <= 1'b1;
                held_tag <= free_tag;
                held_client <= grant_client;
                held_write <= req_write[grant_client];
                held_addr <= req_addr[32*grant_client +: 32];
                held_wdata <= req_wdata[32*grant_client +: 32];
                held_wstrb <= req_wstrb[4*grant_client +: 4];
                held_id <= req_id[8*grant_client +: 8];
            end

            if (push0 || push1) begin
                state[selected_tag] <= WAIT;
                owner[selected_tag] <= selected_client;
                saved_id[selected_tag] <= selected_id;
                saved_write[selected_tag] <= selected_write;
                held_offer <= 1'b0;
                if (selected_client == 1'b0) begin
                    queue[0][q_tail[0]] <= selected_tag;
                    q_tail[0] <= q_tail[0] + 2'd1;
                end else begin
                    queue[1][q_tail[1]] <= selected_tag;
                    q_tail[1] <= q_tail[1] + 2'd1;
                end
                priority_client <= ~selected_client;
            end

            if (m_rsp_valid && m_rsp_ready) begin
                if (state[m_rsp_tag] == WAIT) begin
                    saved_rdata[m_rsp_tag] <= m_rsp_rdata;
                    saved_err[m_rsp_tag] <= m_rsp_err;
                    state[m_rsp_tag] <= DONE;
                end else if (state[m_rsp_tag] == STALE) begin
                    state[m_rsp_tag] <= FREE;
                end
            end

            if (pop0) begin
                state[queue[0][q_head[0]]] <= FREE;
                q_head[0] <= q_head[0] + 2'd1;
            end
            if (pop1) begin
                state[queue[1][q_head[1]]] <= FREE;
                q_head[1] <= q_head[1] + 2'd1;
            end

            case ({push0, pop0})
                2'b10: q_count[0] <= q_count[0] + 3'd1;
                2'b01: q_count[0] <= q_count[0] - 3'd1;
                default: q_count[0] <= q_count[0];
            endcase
            case ({push1, pop1})
                2'b10: q_count[1] <= q_count[1] + 3'd1;
                2'b01: q_count[1] <= q_count[1] - 3'd1;
                default: q_count[1] <= q_count[1];
            endcase
        end
    end

endmodule
