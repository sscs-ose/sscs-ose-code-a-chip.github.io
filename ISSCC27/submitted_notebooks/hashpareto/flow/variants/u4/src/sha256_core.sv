module sha256_core #(
    parameter int UNROLL = 4
)(
    input  logic         clk,
    input  logic         rst_n,
    input  logic [511:0] block,
    input  logic         done,
    input  logic         sha_valid,
    output logic         scheduler_ready,
    output logic [255:0] digest,
    output logic         digest_valid
);
    localparam int NCHUNK = 64 / UNROLL;


    function automatic logic [31:0] kconst(input int t);
        case (t)
            0:  kconst = 32'h428a2f98;
            1:  kconst = 32'h71374491;
            2:  kconst = 32'hb5c0fbcf;
            3:  kconst = 32'he9b5dba5;
            4:  kconst = 32'h3956c25b;
            5:  kconst = 32'h59f111f1;
            6:  kconst = 32'h923f82a4;
            7:  kconst = 32'hab1c5ed5;
            8:  kconst = 32'hd807aa98;
            9:  kconst = 32'h12835b01;
            10: kconst = 32'h243185be;
            11: kconst = 32'h550c7dc3;
            12: kconst = 32'h72be5d74;
            13: kconst = 32'h80deb1fe;
            14: kconst = 32'h9bdc06a7;
            15: kconst = 32'hc19bf174;
            16: kconst = 32'he49b69c1;
            17: kconst = 32'hefbe4786;
            18: kconst = 32'h0fc19dc6;
            19: kconst = 32'h240ca1cc;
            20: kconst = 32'h2de92c6f;
            21: kconst = 32'h4a7484aa;
            22: kconst = 32'h5cb0a9dc;
            23: kconst = 32'h76f988da;
            24: kconst = 32'h983e5152;
            25: kconst = 32'ha831c66d;
            26: kconst = 32'hb00327c8;
            27: kconst = 32'hbf597fc7;
            28: kconst = 32'hc6e00bf3;
            29: kconst = 32'hd5a79147;
            30: kconst = 32'h06ca6351;
            31: kconst = 32'h14292967;
            32: kconst = 32'h27b70a85;
            33: kconst = 32'h2e1b2138;
            34: kconst = 32'h4d2c6dfc;
            35: kconst = 32'h53380d13;
            36: kconst = 32'h650a7354;
            37: kconst = 32'h766a0abb;
            38: kconst = 32'h81c2c92e;
            39: kconst = 32'h92722c85;
            40: kconst = 32'ha2bfe8a1;
            41: kconst = 32'ha81a664b;
            42: kconst = 32'hc24b8b70;
            43: kconst = 32'hc76c51a3;
            44: kconst = 32'hd192e819;
            45: kconst = 32'hd6990624;
            46: kconst = 32'hf40e3585;
            47: kconst = 32'h106aa070;
            48: kconst = 32'h19a4c116;
            49: kconst = 32'h1e376c08;
            50: kconst = 32'h2748774c;
            51: kconst = 32'h34b0bcb5;
            52: kconst = 32'h391c0cb3;
            53: kconst = 32'h4ed8aa4a;
            54: kconst = 32'h5b9cca4f;
            55: kconst = 32'h682e6ff3;
            56: kconst = 32'h748f82ee;
            57: kconst = 32'h78a5636f;
            58: kconst = 32'h84c87814;
            59: kconst = 32'h8cc70208;
            60: kconst = 32'h90befffa;
            61: kconst = 32'ha4506ceb;
            62: kconst = 32'hbef9a3f7;
            63: kconst = 32'hc67178f2;
            default: kconst = 32'h00000000;
        endcase
    endfunction

    localparam logic [31:0] H0_INIT = 32'h6a09e667;
    localparam logic [31:0] H1_INIT = 32'hbb67ae85;
    localparam logic [31:0] H2_INIT = 32'h3c6ef372;
    localparam logic [31:0] H3_INIT = 32'ha54ff53a;
    localparam logic [31:0] H4_INIT = 32'h510e527f;
    localparam logic [31:0] H5_INIT = 32'h9b05688c;
    localparam logic [31:0] H6_INIT = 32'h1f83d9ab;
    localparam logic [31:0] H7_INIT = 32'h5be0cd19;

    function automatic logic [31:0] rotr(input logic [31:0] x, input int n);
        rotr = (x >> n) | (x << (32 - n));
    endfunction

    function automatic logic [31:0] big_sigma0(input logic [31:0] x);
        big_sigma0 = rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22);
    endfunction

    function automatic logic [31:0] big_sigma1(input logic [31:0] x);
        big_sigma1 = rotr(x, 6) ^ rotr(x, 11) ^ rotr(x, 25);
    endfunction

    function automatic logic [31:0] small_sigma0(input logic [31:0] x);
        small_sigma0 = rotr(x, 7) ^ rotr(x, 18) ^ (x >> 3);
    endfunction

    function automatic logic [31:0] small_sigma1(input logic [31:0] x);
        small_sigma1 = rotr(x, 17) ^ rotr(x, 19) ^ (x >> 10);
    endfunction

    function automatic logic [31:0] ch(input logic [31:0] x, y, z);
        ch = (x & y) ^ (~x & z);
    endfunction

    function automatic logic [31:0] maj(input logic [31:0] x, y, z);
        maj = (x & y) ^ (x & z) ^ (y & z);
    endfunction

    typedef enum logic [1:0] { IDLE, COMPRESSION, DIGEST } state_t;
    state_t state, state_next;

    logic [31:0] chunk_count;
    logic [31:0] round_base;
    logic       mid_message;
    logic       digest_valid_reg;

    logic [31:0] a_reg, b_reg, c_reg, d_reg, e_reg, f_reg, g_reg, h_reg;
    logic [31:0] H0_reg, H1_reg, H2_reg, H3_reg, H4_reg, H5_reg, H6_reg, H7_reg;

    logic [31:0] wm [0:15];
    logic [31:0] ext [0:15+UNROLL];
    logic [31:0] t1a [0:UNROLL-1];
    logic [31:0] t2a [0:UNROLL-1];
    logic [31:0] ra [0:UNROLL];
    logic [31:0] rb [0:UNROLL];
    logic [31:0] rc [0:UNROLL];
    logic [31:0] rd [0:UNROLL];
    logic [31:0] re [0:UNROLL];
    logic [31:0] rf [0:UNROLL];
    logic [31:0] rg [0:UNROLL];
    logic [31:0] rh [0:UNROLL];

    assign round_base      = chunk_count * UNROLL;
    assign scheduler_ready = (state == IDLE);
    assign digest          = {H0_reg, H1_reg, H2_reg, H3_reg, H4_reg, H5_reg, H6_reg, H7_reg};
    assign digest_valid    = digest_valid_reg;

    always_comb begin
        for (int j = 0; j < 16; j = j + 1)
            ext[j] = wm[j];

        for (int k = 0; k < UNROLL; k = k + 1)
            ext[16+k] = small_sigma1(ext[14+k]) + ext[9+k] + small_sigma0(ext[1+k]) + ext[0+k];

        ra[0] = a_reg; rb[0] = b_reg; rc[0] = c_reg; rd[0] = d_reg;
        re[0] = e_reg; rf[0] = f_reg; rg[0] = g_reg; rh[0] = h_reg;

        for (int i = 0; i < UNROLL; i = i + 1) begin
            t1a[i] = rh[i] + big_sigma1(re[i]) + ch(re[i], rf[i], rg[i]) + kconst(round_base+i) + ext[i];
            t2a[i] = big_sigma0(ra[i]) + maj(ra[i], rb[i], rc[i]);
            ra[i+1] = t1a[i] + t2a[i];
            rb[i+1] = ra[i];
            rc[i+1] = rb[i];
            rd[i+1] = rc[i];
            re[i+1] = rd[i] + t1a[i];
            rf[i+1] = re[i];
            rg[i+1] = rf[i];
            rh[i+1] = rg[i];
        end
    end

    always_comb begin
        state_next = state;
        case (state)
            IDLE:        if (sha_valid && scheduler_ready) state_next = COMPRESSION;
            COMPRESSION: if (chunk_count == NCHUNK-1)       state_next = DIGEST;
            DIGEST:                                          state_next = IDLE;
            default:                                         state_next = IDLE;
        endcase
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state            <= IDLE;
            chunk_count      <= 32'd0;
            mid_message      <= 1'b0;
            digest_valid_reg <= 1'b0;
            a_reg <= 32'd0; b_reg <= 32'd0; c_reg <= 32'd0; d_reg <= 32'd0;
            e_reg <= 32'd0; f_reg <= 32'd0; g_reg <= 32'd0; h_reg <= 32'd0;
            H0_reg <= 32'd0; H1_reg <= 32'd0; H2_reg <= 32'd0; H3_reg <= 32'd0;
            H4_reg <= 32'd0; H5_reg <= 32'd0; H6_reg <= 32'd0; H7_reg <= 32'd0;
            for (int i = 0; i < 16; i = i + 1) wm[i] <= 32'd0;
        end else begin
            state            <= state_next;
            digest_valid_reg <= 1'b0;

            case (state)
                IDLE: begin
                    if (sha_valid && scheduler_ready) begin
                        for (int i = 0; i < 16; i = i + 1)
                            wm[i] <= block[511 - 32*i -: 32];
                        chunk_count      <= 32'd0;
                        if (!mid_message) begin
                            mid_message <= 1'b1;
                            a_reg <= H0_INIT; b_reg <= H1_INIT; c_reg <= H2_INIT; d_reg <= H3_INIT;
                            e_reg <= H4_INIT; f_reg <= H5_INIT; g_reg <= H6_INIT; h_reg <= H7_INIT;
                            H0_reg <= H0_INIT; H1_reg <= H1_INIT; H2_reg <= H2_INIT; H3_reg <= H3_INIT;
                            H4_reg <= H4_INIT; H5_reg <= H5_INIT; H6_reg <= H6_INIT; H7_reg <= H7_INIT;
                        end else begin
                            a_reg <= H0_reg; b_reg <= H1_reg; c_reg <= H2_reg; d_reg <= H3_reg;
                            e_reg <= H4_reg; f_reg <= H5_reg; g_reg <= H6_reg; h_reg <= H7_reg;
                        end
                    end
                end
                COMPRESSION: begin
                    a_reg <= ra[UNROLL]; b_reg <= rb[UNROLL]; c_reg <= rc[UNROLL]; d_reg <= rd[UNROLL];
                    e_reg <= re[UNROLL]; f_reg <= rf[UNROLL]; g_reg <= rg[UNROLL]; h_reg <= rh[UNROLL];
                    for (int i = 0; i < 16; i = i + 1)
                        wm[i] <= ext[UNROLL+i];
                    chunk_count <= chunk_count + 32'd1;
                end
                DIGEST: begin
                    H0_reg <= H0_reg + a_reg;
                    H1_reg <= H1_reg + b_reg;
                    H2_reg <= H2_reg + c_reg;
                    H3_reg <= H3_reg + d_reg;
                    H4_reg <= H4_reg + e_reg;
                    H5_reg <= H5_reg + f_reg;
                    H6_reg <= H6_reg + g_reg;
                    H7_reg <= H7_reg + h_reg;
                    digest_valid_reg <= 1'b1;
                    chunk_count      <= 32'd0;
                    if (done) mid_message <= 1'b0;
                end
                default: ;
            endcase
        end
    end
endmodule
