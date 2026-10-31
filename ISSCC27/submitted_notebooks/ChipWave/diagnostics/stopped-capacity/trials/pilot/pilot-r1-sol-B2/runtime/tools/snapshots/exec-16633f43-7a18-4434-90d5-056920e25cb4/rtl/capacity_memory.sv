module capacity_memory (
    input  logic clk, rst_n, flush,
    input  logic [1:0] req_valid,
    output logic [1:0] req_ready,
    input  logic [1:0] req_write,
    input  logic [63:0] req_addr, req_wdata,
    input  logic [7:0] req_wstrb,
    input  logic [15:0] req_id,
    output logic [1:0] rsp_valid,
    input  logic [1:0] rsp_ready,
    output logic [63:0] rsp_rdata,
    output logic [15:0] rsp_id,
    output logic [1:0] rsp_err,
    output logic m_req_valid,
    input  logic m_req_ready,
    output logic m_req_write,
    output logic [31:0] m_req_addr, m_req_wdata,
    output logic [3:0] m_req_wstrb,
    output logic [1:0] m_req_tag,
    input  logic m_rsp_valid,
    output logic m_rsp_ready,
    input  logic [1:0] m_rsp_tag,
    input  logic [31:0] m_rsp_rdata,
    input  logic m_rsp_err
);
    // A slot remains reserved through client retirement. A non-live reserved
    // slot is a pre-flush request whose memory response must still drain.
    logic [3:0] busy, live, done, was_write;
    logic [7:0] ids [0:3];
    logic [31:0] data [0:3];
    logic [3:0] errors;
    logic [1:0] order [0:1][0:3];
    logic [1:0] head [0:1], tail [0:1];
    logic [2:0] count [0:1];
    logic prefer, locked, locked_client;
    logic [1:0] locked_tag;
    logic chosen, free_valid;
    logic [1:0] free_tag;
    logic accept;
    logic [1:0] pop;

    always_comb begin
        free_valid = 1'b1;
        if (!busy[0]) free_tag = 2'd0;
        else if (!busy[1]) free_tag = 2'd1;
        else if (!busy[2]) free_tag = 2'd2;
        else if (!busy[3]) free_tag = 2'd3;
        else begin free_valid = 1'b0; free_tag = 2'd0; end

        chosen = req_valid[prefer] ? prefer : !prefer;
        if (locked) chosen = locked_client;
        m_req_tag = locked ? locked_tag : free_tag;
        m_req_valid = rst_n && !flush && (locked || free_valid)
                      && req_valid[chosen];
        m_req_write = req_write[chosen];
        m_req_addr = chosen ? req_addr[63:32] : req_addr[31:0];
        m_req_wdata = chosen ? req_wdata[63:32] : req_wdata[31:0];
        m_req_wstrb = chosen ? req_wstrb[7:4] : req_wstrb[3:0];
        req_ready = 2'b00;
        req_ready[chosen] = m_req_valid && m_req_ready;
        accept = m_req_valid && m_req_ready;
        m_rsp_ready = rst_n;

        rsp_valid = 2'b00;
        rsp_rdata = 64'b0;
        rsp_id = 16'b0;
        rsp_err = 2'b00;
        for (integer c = 0; c < 2; c = c + 1) begin
            if (count[c] != 0) begin
                rsp_valid[c] = rst_n && !flush && done[order[c][head[c]]];
                rsp_rdata[32*c +: 32] = data[order[c][head[c]]];
                rsp_id[8*c +: 8] = ids[order[c][head[c]]];
                rsp_err[c] = errors[order[c][head[c]]];
            end
        end
        pop = rsp_valid & rsp_ready;
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 0;
            live <= 0;
            done <= 0;
            was_write <= 0;
            errors <= 0;
            prefer <= 0;
            locked <= 0;
            locked_client <= 0;
            locked_tag <= 0;
            for (integer c = 0; c < 2; c = c + 1) begin
                head[c] <= 0;
                tail[c] <= 0;
                count[c] <= 0;
            end
        end else if (flush) begin
            locked <= 0;
            prefer <= 0;
            live <= 0;
            done <= 0;
            // Completed slots are immediately free; externally outstanding
            // slots remain reserved, except for a response draining now.
            for (integer t = 0; t < 4; t = t + 1)
                busy[t] <= busy[t] && !done[t]
                           && !(m_rsp_valid && m_rsp_tag == t);
            for (integer c = 0; c < 2; c = c + 1) begin
                head[c] <= 0;
                tail[c] <= 0;
                count[c] <= 0;
            end
        end else begin
            if (m_req_valid && !m_req_ready) begin
                locked <= 1;
                locked_client <= chosen;
                locked_tag <= m_req_tag;
            end
            if (accept) begin
                locked <= 0;
                prefer <= !chosen;
                order[chosen][tail[chosen]] <= m_req_tag;
                tail[chosen] <= tail[chosen] + 2'd1;
            end
            for (integer c = 0; c < 2; c = c + 1) begin
                case ({(accept && chosen == c), pop[c]})
                    2'b10: count[c] <= count[c] + 3'd1;
                    2'b01: count[c] <= count[c] - 3'd1;
                    default: ;
                endcase
                if (pop[c]) head[c] <= head[c] + 2'd1;
            end
            for (integer t = 0; t < 4; t = t + 1) begin
                if ((pop[0] && order[0][head[0]] == t) ||
                    (pop[1] && order[1][head[1]] == t)) begin
                    busy[t] <= 0;
                    live[t] <= 0;
                    done[t] <= 0;
                end
                if (accept && m_req_tag == t) begin
                    busy[t] <= 1;
                    live[t] <= 1;
                    done[t] <= 0;
                    ids[t] <= chosen ? req_id[15:8] : req_id[7:0];
                    was_write[t] <= m_req_write;
                end
                if (m_rsp_valid && m_rsp_tag == t) begin
                    if (accept && m_req_tag == t) begin
                        // Also support a memory that responds at acceptance.
                        data[t] <= m_req_write ? 32'b0 : m_rsp_rdata;
                        errors[t] <= m_rsp_err;
                        done[t] <= 1;
                    end else if (busy[t] && live[t]) begin
                        data[t] <= was_write[t] ? 32'b0 : m_rsp_rdata;
                        errors[t] <= m_rsp_err;
                        done[t] <= 1;
                    end else if (busy[t]) begin
                        busy[t] <= 0;
                    end
                end
            end
        end
    end
endmodule
