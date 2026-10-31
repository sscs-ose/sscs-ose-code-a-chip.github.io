// Clocked SRAM-inference boundary around one AutoMX-CIM K=32 slice.
// Configuration banks: 0=WPOS, 1=WNEG, 2=COL_V_Q, 3=ALPHA_Q,
// 4=BETA_Q, 5=RESIDUAL_Q.  Bank contents use the exporter memory order.
`default_nettype none
module automx_cim_sram_tile #(
    parameter int N = 32,
    parameter int M = 32,
    parameter int ACT_W = 5,
    parameter int META_W = 16,
    parameter int ACC_W = 48,
    parameter int CFG_ADDR_W = 16
) (
    input  logic                      clk_i,
    input  logic                      rst_ni,
    input  logic                      cfg_valid_i,
    input  logic                      cfg_write_i,
    output logic                      cfg_ready_o,
    input  logic [2:0]                cfg_bank_i,
    input  logic [CFG_ADDR_W-1:0]     cfg_addr_i,
    input  logic [31:0]               cfg_wdata_i,
    input  logic                      req_valid_i,
    output logic                      req_ready_o,
    input  logic signed [ACT_W*N-1:0] req_act_x2_i,
    output logic                      rsp_valid_o,
    input  logic                      rsp_ready_i,
    output logic signed [ACC_W*M-1:0] rsp_group_acc_q_o
);
    localparam logic [2:0] BANK_WPOS     = 3'd0;
    localparam logic [2:0] BANK_WNEG     = 3'd1;
    localparam logic [2:0] BANK_COLV     = 3'd2;
    localparam logic [2:0] BANK_ALPHA    = 3'd3;
    localparam logic [2:0] BANK_BETA     = 3'd4;
    localparam logic [2:0] BANK_RESIDUAL = 3'd5;
    localparam int ROW_ADDR_W = (N <= 1) ? 1 : $clog2(N);
    localparam int COL_ADDR_W = (M <= 1) ? 1 : $clog2(M);
    localparam int RES_ADDR_W = (N*M <= 1) ? 1 : $clog2(N*M);

    logic [M-1:0] wpos_mem [0:N-1];
    logic [M-1:0] wneg_mem [0:N-1];
    logic [META_W-1:0] col_v_mem [0:N-1];
    logic [META_W-1:0] alpha_mem [0:M-1];
    logic signed [META_W-1:0] beta_mem [0:M-1];
    logic signed [META_W-1:0] residual_mem [0:N*M-1];
    logic [N*M-1:0] wpos_flat, wneg_flat;
    logic [META_W*N-1:0] col_v_flat;
    logic [META_W*M-1:0] alpha_flat;
    logic signed [META_W*M-1:0] beta_flat;
    logic signed [META_W*N*M-1:0] residual_flat;
    logic signed [ACC_W*M-1:0] comb_group_acc_q;
    integer r, c;

    initial begin
        if (N != 32) $fatal(1, "automx_cim_sram_tile baseline requires N=32");
        if (M > 32 || META_W > 32) $fatal(1, "configuration word is 32 bits");
    end

    // Configuration and compute are mutually exclusive.  A response is held
    // until rsp_ready_i, so clients may back-pressure the one-entry result FIFO.
    assign cfg_ready_o = !req_valid_i && (!rsp_valid_o || rsp_ready_i);
    assign req_ready_o = !cfg_valid_i && (!rsp_valid_o || rsp_ready_i);

    always_comb begin
        wpos_flat = '0; wneg_flat = '0; col_v_flat = '0;
        alpha_flat = '0; beta_flat = '0; residual_flat = '0;
        for (r = 0; r < N; r = r + 1) begin
            wpos_flat[M*r +: M] = wpos_mem[r];
            wneg_flat[M*r +: M] = wneg_mem[r];
            col_v_flat[META_W*r +: META_W] = col_v_mem[r];
        end
        for (c = 0; c < M; c = c + 1) begin
            alpha_flat[META_W*c +: META_W] = alpha_mem[c];
            beta_flat[META_W*c +: META_W] = beta_mem[c];
        end
        for (r = 0; r < N; r = r + 1)
            for (c = 0; c < M; c = c + 1)
                residual_flat[META_W*(r*M+c) +: META_W] = residual_mem[r*M+c];
    end

    automx_cim_slice #(
        .N(N), .M(M), .ACT_W(ACT_W), .META_W(META_W), .ACC_W(ACC_W)
    ) u_slice (
        .ACT_X2(req_act_x2_i), .WPOS(wpos_flat), .WNEG(wneg_flat),
        .COL_V_Q(col_v_flat), .ALPHA_Q(alpha_flat), .BETA_Q(beta_flat),
        .RESIDUAL_Q(residual_flat), .GROUP_ACC_Q(comb_group_acc_q)
    );

    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            rsp_valid_o <= 1'b0;
            rsp_group_acc_q_o <= '0;
        end else begin
            if (rsp_valid_o && rsp_ready_i)
                rsp_valid_o <= 1'b0;
            if (cfg_valid_i && cfg_ready_o && cfg_write_i) begin
                case (cfg_bank_i)
                    BANK_WPOS: if (int'(cfg_addr_i) < N) wpos_mem[cfg_addr_i[ROW_ADDR_W-1:0]] <= cfg_wdata_i[M-1:0];
                    BANK_WNEG: if (int'(cfg_addr_i) < N) wneg_mem[cfg_addr_i[ROW_ADDR_W-1:0]] <= cfg_wdata_i[M-1:0];
                    BANK_COLV: if (int'(cfg_addr_i) < N) col_v_mem[cfg_addr_i[ROW_ADDR_W-1:0]] <= cfg_wdata_i[META_W-1:0];
                    BANK_ALPHA: if (int'(cfg_addr_i) < M) alpha_mem[cfg_addr_i[COL_ADDR_W-1:0]] <= cfg_wdata_i[META_W-1:0];
                    BANK_BETA: if (int'(cfg_addr_i) < M) beta_mem[cfg_addr_i[COL_ADDR_W-1:0]] <= cfg_wdata_i[META_W-1:0];
                    BANK_RESIDUAL: if (int'(cfg_addr_i) < N*M) residual_mem[cfg_addr_i[RES_ADDR_W-1:0]] <= cfg_wdata_i[META_W-1:0];
                    default: begin end
                endcase
            end
            if (req_valid_i && req_ready_o) begin
                rsp_group_acc_q_o <= comb_group_acc_q;
                rsp_valid_o <= 1'b1;
            end
        end
    end
endmodule
`default_nettype wire