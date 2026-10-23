// Area-conscious Keccak-f[1600] permutation engine.  The default keeps the
// fitted FPGA behavior: one complete round per clock using one 1600-bit state
// register.  ASIC can select a row-serialized round with an explicit parameter.
module keccak_f1600_iter #(
    parameter SERIAL_ROUND = 1'b0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          zeroize,
    input  wire          start,
    input  wire [1599:0] state_in,
    output wire [1599:0] state_out,
    output reg           busy,
    output reg           done
);
    reg [1599:0] state_q;
    reg [4:0] round_q;

    function automatic [63:0] rol64;
        input [63:0] value;
        input integer amount;
        begin
            if (amount == 0)
                rol64 = value;
            else
                rol64 = (value << amount) | (value >> (64 - amount));
        end
    endfunction

    function automatic integer rho_offset;
        input integer lane;
        begin
            case (lane)
                 0: rho_offset =  0;  1: rho_offset =  1;
                 2: rho_offset = 62;  3: rho_offset = 28;
                 4: rho_offset = 27;  5: rho_offset = 36;
                 6: rho_offset = 44;  7: rho_offset =  6;
                 8: rho_offset = 55;  9: rho_offset = 20;
                10: rho_offset =  3; 11: rho_offset = 10;
                12: rho_offset = 43; 13: rho_offset = 25;
                14: rho_offset = 39; 15: rho_offset = 41;
                16: rho_offset = 45; 17: rho_offset = 15;
                18: rho_offset = 21; 19: rho_offset =  8;
                20: rho_offset = 18; 21: rho_offset =  2;
                22: rho_offset = 61; 23: rho_offset = 56;
                24: rho_offset = 14;
                default: rho_offset = 0;
            endcase
        end
    endfunction

    function automatic [63:0] round_constant;
        input [4:0] round_index;
        begin
            case (round_index)
                 0: round_constant = 64'h0000000000000001;
                 1: round_constant = 64'h0000000000008082;
                 2: round_constant = 64'h800000000000808A;
                 3: round_constant = 64'h8000000080008000;
                 4: round_constant = 64'h000000000000808B;
                 5: round_constant = 64'h0000000080000001;
                 6: round_constant = 64'h8000000080008081;
                 7: round_constant = 64'h8000000000008009;
                 8: round_constant = 64'h000000000000008A;
                 9: round_constant = 64'h0000000000000088;
                10: round_constant = 64'h0000000080008009;
                11: round_constant = 64'h000000008000000A;
                12: round_constant = 64'h000000008000808B;
                13: round_constant = 64'h800000000000008B;
                14: round_constant = 64'h8000000000008089;
                15: round_constant = 64'h8000000000008003;
                16: round_constant = 64'h8000000000008002;
                17: round_constant = 64'h8000000000000080;
                18: round_constant = 64'h000000000000800A;
                19: round_constant = 64'h800000008000000A;
                20: round_constant = 64'h8000000080008081;
                21: round_constant = 64'h8000000000008080;
                22: round_constant = 64'h0000000080000001;
                23: round_constant = 64'h8000000080008008;
                default: round_constant = 64'd0;
            endcase
        end
    endfunction

    function automatic [1599:0] keccak_round;
        input [1599:0] in_state;
        input [4:0] round_index;
        reg [63:0] a [0:24];
        reg [63:0] b [0:24];
        reg [63:0] c [0:4];
        reg [63:0] d [0:4];
        reg [1599:0] result;
        integer x;
        integer y;
        integer lane;
        integer destination;
        begin
            for (lane = 0; lane < 25; lane = lane + 1) begin
                a[lane] = in_state[lane*64 +: 64];
                b[lane] = 64'd0;
            end

            // theta
            for (x = 0; x < 5; x = x + 1)
                c[x] = a[x] ^ a[x+5] ^ a[x+10] ^ a[x+15] ^ a[x+20];
            for (x = 0; x < 5; x = x + 1)
                d[x] = c[(x+4)%5] ^ rol64(c[(x+1)%5], 1);
            for (y = 0; y < 5; y = y + 1)
                for (x = 0; x < 5; x = x + 1)
                    a[x+5*y] = a[x+5*y] ^ d[x];

            // rho and pi: B[y, 2*x+3*y] = ROT(A[x,y], r[x,y])
            for (y = 0; y < 5; y = y + 1) begin
                for (x = 0; x < 5; x = x + 1) begin
                    lane = x + 5*y;
                    destination = y + 5*((2*x + 3*y) % 5);
                    b[destination] = rol64(a[lane], rho_offset(lane));
                end
            end

            // chi
            for (y = 0; y < 5; y = y + 1)
                for (x = 0; x < 5; x = x + 1)
                    a[x+5*y] = b[x+5*y] ^
                               ((~b[((x+1)%5)+5*y]) & b[((x+2)%5)+5*y]);

            // iota
            a[0] = a[0] ^ round_constant(round_index);

            result = 1600'd0;
            for (lane = 0; lane < 25; lane = lane + 1)
                result[lane*64 +: 64] = a[lane];
            keccak_round = result;
        end
    endfunction

    // Retain only the five 64-bit Theta correction lanes between phases.
    // The original state remains in state_q, avoiding a second 1600-bit
    // register bank and the global Rho/Pi-to-register wiring it introduced.
    function automatic [319:0] keccak_theta_d;
        input [1599:0] in_state;
        reg [63:0] a [0:24];
        reg [63:0] c [0:4];
        reg [63:0] d [0:4];
        reg [319:0] result;
        integer x;
        integer lane;
        begin
            for (lane = 0; lane < 25; lane = lane + 1)
                a[lane] = in_state[lane*64 +: 64];

            for (x = 0; x < 5; x = x + 1)
                c[x] = a[x] ^ a[x+5] ^ a[x+10] ^ a[x+15] ^ a[x+20];
            for (x = 0; x < 5; x = x + 1)
                d[x] = c[(x+4)%5] ^ rol64(c[(x+1)%5], 1);

            result = 320'd0;
            for (x = 0; x < 5; x = x + 1)
                result[x*64 +: 64] = d[x];
            keccak_theta_d = result;
        end
    endfunction

    function automatic [1599:0] keccak_theta_rhopi_from_d;
        input [1599:0] in_state;
        input [319:0] theta_d;
        reg [63:0] a [0:24];
        reg [63:0] b [0:24];
        reg [63:0] d [0:4];
        reg [1599:0] result;
        integer x;
        integer y;
        integer lane;
        integer destination;
        begin
            for (lane = 0; lane < 25; lane = lane + 1) begin
                a[lane] = in_state[lane*64 +: 64];
                b[lane] = 64'd0;
            end
            for (x = 0; x < 5; x = x + 1)
                d[x] = theta_d[x*64 +: 64];

            for (y = 0; y < 5; y = y + 1)
                for (x = 0; x < 5; x = x + 1)
                    a[x+5*y] = a[x+5*y] ^ d[x];

            for (y = 0; y < 5; y = y + 1) begin
                for (x = 0; x < 5; x = x + 1) begin
                    lane = x + 5*y;
                    destination = y + 5*((2*x + 3*y) % 5);
                    b[destination] = rol64(a[lane], rho_offset(lane));
                end
            end

            result = 1600'd0;
            for (lane = 0; lane < 25; lane = lane + 1)
                result[lane*64 +: 64] = b[lane];
            keccak_theta_rhopi_from_d = result;
        end
    endfunction

    function automatic [319:0] keccak_chi_row;
        input [319:0] in_row;
        input         apply_iota;
        input [4:0]   round_index;
        reg [63:0] b [0:4];
        reg [63:0] a [0:4];
        reg [319:0] result;
        integer x;
        begin
            for (x = 0; x < 5; x = x + 1)
                b[x] = in_row[x*64 +: 64];
            for (x = 0; x < 5; x = x + 1)
                a[x] = b[x] ^ ((~b[(x+1)%5]) & b[(x+2)%5]);
            if (apply_iota)
                a[0] = a[0] ^ round_constant(round_index);

            result = 320'd0;
            for (x = 0; x < 5; x = x + 1)
                result[x*64 +: 64] = a[x];
            keccak_chi_row = result;
        end
    endfunction

    // state_q already holds the completed round-23 value when done is
    // observed by the caller.  Driving the output directly avoids retaining
    // a second 1600-bit copy of the permutation state.
    assign state_out = state_q;

    generate
        if (!SERIAL_ROUND) begin : g_one_phase
            wire [1599:0] round_result = keccak_round(state_q, round_q);

            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    state_q <= 1600'd0;
                    round_q <= 5'd0;
                    busy <= 1'b0;
                    done <= 1'b0;
                end else if (zeroize) begin
                    state_q <= 1600'd0;
                    round_q <= 5'd0;
                    busy <= 1'b0;
                    done <= 1'b0;
                end else begin
                    done <= 1'b0;
                    if (start && !busy) begin
                        state_q <= state_in;
                        round_q <= 5'd0;
                        busy <= 1'b1;
                    end else if (busy) begin
                        state_q <= round_result;
                        if (round_q == 5'd23) begin
                            busy <= 1'b0;
                            done <= 1'b1;
                        end else begin
                            round_q <= round_q + 5'd1;
                        end
                    end
                end
            end
        end else begin : g_serial_round
            reg [319:0] theta_d_q;
            reg [2:0]    phase_q;
            reg [319:0]  chi_row_input;
            wire [319:0] theta_d_result = keccak_theta_d(state_q);
            wire [1599:0] theta_rhopi_result =
                keccak_theta_rhopi_from_d(state_q, theta_d_q);
            wire [319:0] chi_row_result =
                keccak_chi_row(chi_row_input, phase_q == 3'd2, round_q);

            always @* begin
                case (phase_q)
                    3'd2: chi_row_input = state_q[319:0];
                    3'd3: chi_row_input = state_q[639:320];
                    3'd4: chi_row_input = state_q[959:640];
                    3'd5: chi_row_input = state_q[1279:960];
                    3'd6: chi_row_input = state_q[1599:1280];
                    default: chi_row_input = 320'd0;
                endcase
            end

            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    state_q <= 1600'd0;
                    theta_d_q <= 320'd0;
                    round_q <= 5'd0;
                    phase_q <= 3'd0;
                    busy <= 1'b0;
                    done <= 1'b0;
                end else if (zeroize) begin
                    state_q <= 1600'd0;
                    theta_d_q <= 320'd0;
                    round_q <= 5'd0;
                    phase_q <= 3'd0;
                    busy <= 1'b0;
                    done <= 1'b0;
                end else begin
                    done <= 1'b0;
                    if (start && !busy) begin
                        state_q <= state_in;
                        theta_d_q <= 320'd0;
                        round_q <= 5'd0;
                        phase_q <= 3'd0;
                        busy <= 1'b1;
                    end else if (busy) begin
                        case (phase_q)
                            3'd0: begin
                                theta_d_q <= theta_d_result;
                                phase_q <= 3'd1;
                            end
                            3'd1: begin
                                state_q <= theta_rhopi_result;
                                phase_q <= 3'd2;
                            end
                            3'd2: begin
                                state_q[319:0] <= chi_row_result;
                                phase_q <= 3'd3;
                            end
                            3'd3: begin
                                state_q[639:320] <= chi_row_result;
                                phase_q <= 3'd4;
                            end
                            3'd4: begin
                                state_q[959:640] <= chi_row_result;
                                phase_q <= 3'd5;
                            end
                            3'd5: begin
                                state_q[1279:960] <= chi_row_result;
                                phase_q <= 3'd6;
                            end
                            default: begin
                                state_q[1599:1280] <= chi_row_result;
                                phase_q <= 3'd0;
                                if (round_q == 5'd23) begin
                                    busy <= 1'b0;
                                    done <= 1'b1;
                                end else begin
                                    round_q <= round_q + 5'd1;
                                end
                            end
                        endcase
                    end
                end
            end
        end
    endgenerate
endmodule
