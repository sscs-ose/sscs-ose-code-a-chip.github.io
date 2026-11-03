module hashing_core(
    input logic clk, 
    input logic rst_n,
    input logic new_block,
    input logic done,
    input logic [31:0] k_t,
    input logic [31:0] w_t,
    output logic [255:0] digest,
    output logic [5:0] round,
    output logic load_block, next_round,
    output logic digest_valid
);
    timeunit 1ns;
    timeprecision 1ps;

    // initial hashes 
    localparam SHA256_H0 = 32'h6a09e667, 
               SHA256_H1 = 32'hbb67ae85,
               SHA256_H2 = 32'h3c6ef372, 
               SHA256_H3 = 32'ha54ff53a,
               SHA256_H4 = 32'h510e527f,
               SHA256_H5 = 32'h9b05688c,
               SHA256_H6 = 32'h1f83d9ab,
               SHA256_H7 = 32'h5be0cd19;
    
    // state encoding
    typedef enum logic [1:0] {
                                IDLE, 
                                COMPRESSION, 
                                DIGEST

                            } state_t;

    state_t current_state, next_state;

    // datapaths
    logic [5:0] round_count, round_next;
    logic [63:0] digest_count, digest_next;
    logic digest_valid_reg, digest_valid_next;
    logic [31:0] a_reg, a_next;
    logic [31:0] b_reg, b_next;
    logic [31:0] c_reg, c_next;
    logic [31:0] d_reg, d_next;
    logic [31:0] e_reg, e_next;
    logic [31:0] f_reg, f_next;
    logic [31:0] g_reg, g_next;
    logic [31:0] h_reg, h_next;
    logic [31:0] H0_reg, H0_next;
    logic [31:0] H1_reg, H1_next;
    logic [31:0] H2_reg, H2_next;
    logic [31:0] H3_reg, H3_next;
    logic [31:0] H4_reg, H4_next;
    logic [31:0] H5_reg, H5_next;
    logic [31:0] H6_reg, H6_next;
    logic [31:0] H7_reg, H7_next;

    // primitives functions

    function automatic logic [31:0] captial_sigma_0(input logic [31:0] x);
        captial_sigma_0 = {x[1:0], x[31:2]} ^ {x[12:0], x[31:13]} ^ {x[21:0], x[31:22]};
    endfunction

    function automatic logic [31:0] captial_sigma_1(input logic [31:0] x);
        captial_sigma_1 = {x[5:0], x[31:6]} ^ {x[10:0], x[31:11]} ^ {x[24:0], x[31:25]};
    endfunction

    function automatic logic [31:0] ch_x_y_z(input logic [31:0] x, y, z);
        ch_x_y_z = (x & y) ^ (~x & z);
    endfunction

    function automatic logic [31:0] maj_x_y_z(input logic [31:0] x, y, z);
        maj_x_y_z = (x & y) ^ (x & z) ^ (y & z);
    endfunction

    logic [31:0] t1, t1_next;
    logic [31:0] t2, t2_next;

    logic mid_message, mid_message_next;

    // output
    assign round = round_count;
    assign digest = {H0_reg, H1_reg, H2_reg, H3_reg, H4_reg, H5_reg, H6_reg, H7_reg};
    assign digest_valid = digest_valid_reg;

    // state memory
    always_ff @(posedge clk, negedge rst_n) begin: STATE_MEMORY
        if(!rst_n) begin
            current_state <= IDLE;
            round_count <= 6'd0;
            digest_count <= 64'd0;
            digest_valid_reg <= 1'b0;
            t1 <= 32'd0;
            t2 <= 32'd0;
            mid_message <= 1'b0;
            a_reg <= 32'd0;
            b_reg <= 32'd0;
            c_reg <= 32'd0;
            d_reg <= 32'd0;
            e_reg <= 32'd0;
            f_reg <= 32'd0;
            g_reg <= 32'd0;
            h_reg <= 32'd0;
            H0_reg <= 32'd0;
            H1_reg <= 32'd0;
            H2_reg <= 32'd0;
            H3_reg <= 32'd0;
            H4_reg <= 32'd0;
            H5_reg <= 32'd0;
            H6_reg <= 32'd0;
            H7_reg <= 32'd0;
        end else begin
            current_state <= next_state;
            round_count <= round_next;
            digest_count <= digest_next;
            digest_valid_reg <= digest_valid_next;
            t1 <= t1_next;
            t2 <= t2_next;
            mid_message <= mid_message_next;
            a_reg <= a_next;
            b_reg <= b_next;
            c_reg <= c_next;
            d_reg <= d_next;
            e_reg <= e_next;
            f_reg <= f_next;
            g_reg <= g_next;
            h_reg <= h_next;
            H0_reg <= H0_next;
            H1_reg <= H1_next;
            H2_reg <= H2_next;
            H3_reg <= H3_next;
            H4_reg <= H4_next;
            H5_reg <= H5_next;
            H6_reg <= H6_next;
            H7_reg <= H7_next;
        end
    end

    always_comb begin: NEXT_STATE_LOGIC_OUTPUT_LOGIC
        next_state = current_state;
        round_next = round_count;
        digest_next = digest_count;
        digest_valid_next = digest_valid_reg;
        a_next = a_reg;
        b_next = b_reg;
        c_next = c_reg;
        d_next = d_reg;
        e_next = e_reg;
        f_next = f_reg;
        g_next = g_reg;
        h_next = h_reg;
        H0_next = H0_reg;
        H1_next = H1_reg;
        H2_next = H2_reg;
        H3_next = H3_reg;
        H4_next = H4_reg;
        H5_next = H5_reg;
        H6_next = H6_reg;
        H7_next = H7_reg;
        
        load_block = 1'b0;
        next_round = 1'b0;
        t1_next = t1;
        t2_next = t2;
        mid_message_next = mid_message;

        case(current_state)
            IDLE: begin
                if(new_block) begin
                    digest_valid_next = 1'b0;
                    load_block        = 1'b1; 
                    if(!mid_message) begin
                        mid_message_next = 1'b1;
                        a_next = SHA256_H0;
                        b_next = SHA256_H1;
                        c_next = SHA256_H2;
                        d_next = SHA256_H3;
                        e_next = SHA256_H4;
                        f_next = SHA256_H5;
                        g_next = SHA256_H6;
                        h_next = SHA256_H7;
                        H0_next = SHA256_H0;
                        H1_next = SHA256_H1;
                        H2_next = SHA256_H2;
                        H3_next = SHA256_H3;
                        H4_next = SHA256_H4;
                        H5_next = SHA256_H5;
                        H6_next = SHA256_H6;
                        H7_next = SHA256_H7;
                    end else begin
                        a_next = H0_reg;
                        b_next = H1_reg;
                        c_next = H2_reg;
                        d_next = H3_reg;
                        e_next = H4_reg;
                        f_next = H5_reg;
                        g_next = H6_reg;
                        h_next = H7_reg;
                        H0_next = H0_reg;
                        H1_next = H1_reg;
                        H2_next = H2_reg;
                        H3_next = H3_reg;
                        H4_next = H4_reg;
                        H5_next = H5_reg;
                        H6_next = H6_reg;
                        H7_next = H7_reg;
                    end
                    next_state = COMPRESSION; 
                end
            end
            COMPRESSION: begin
                next_round = 1'b1;
                t1_next = h_reg + captial_sigma_1(e_reg) + ch_x_y_z(e_reg, f_reg, g_reg) + k_t + w_t;
                t2_next = captial_sigma_0(a_reg) + maj_x_y_z(a_reg, b_reg, c_reg);
                a_next = t1_next + t2_next;
                b_next = a_reg;
                c_next = b_reg;
                d_next = c_reg;
                e_next = d_reg + t1_next;
                f_next = e_reg;
                g_next = f_reg;
                h_next = g_reg;
                round_next = round_count + 1;
                if(round_count == 6'd63) begin
                    next_state = DIGEST;
                end
            end
            DIGEST: begin
                H0_next = H0_reg + a_reg;
                H1_next = H1_reg + b_reg;
                H2_next = H2_reg + c_reg;
                H3_next = H3_reg + d_reg;
                H4_next = H4_reg + e_reg;
                H5_next = H5_reg + f_reg;
                H6_next = H6_reg + g_reg;
                H7_next = H7_reg + h_reg;
                digest_valid_next = 1'b1;
                digest_next = digest_count + 1;
                if(done) begin
                    mid_message_next = 1'b0;
                end
                next_state = IDLE; 
            end
            default: next_state = IDLE;
        endcase
    end

endmodule