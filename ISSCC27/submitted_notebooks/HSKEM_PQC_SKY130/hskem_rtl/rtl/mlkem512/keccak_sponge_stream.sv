// Byte-stream SHA3/SHAKE sponge around one iterative Keccak-f[1600] engine.
// Messages may cross any number of rate blocks. Output is also streamed and
// can cross blocks for XOF use. The caller supplies message/output lengths at
// start, then transfers one byte per ready/valid handshake.
module keccak_sponge_stream #(
    parameter SERIAL_ROUND = 1'b0
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        zeroize,
    input  wire        start,
    input  wire [1:0]  mode,
    input  wire [15:0] message_len,
    input  wire [15:0] output_len,
    input  wire        in_valid,
    input  wire [7:0]  in_byte,
    output wire        in_ready,
    output wire        out_valid,
    output wire [7:0]  out_byte,
    output wire        out_last,
    input  wire        out_ready,
    output reg         busy,
    output reg         done,
    output reg         error
);
    localparam [1:0] MODE_SHA3_256 = 2'd0,
                     MODE_SHA3_512 = 2'd1,
                     MODE_SHAKE128 = 2'd2,
                     MODE_SHAKE256 = 2'd3;

    localparam [2:0] ST_IDLE       = 3'd0,
                     ST_ABSORB     = 3'd1,
                     ST_PAD        = 3'd2,
                     ST_PERM_START = 3'd3,
                     ST_PERM_WAIT  = 3'd4,
                     ST_SQUEEZE    = 3'd5,
                     ST_DONE       = 3'd6;

    localparam [1:0] PERM_ABSORB_CONTINUE = 2'd0,
                     PERM_PAD_NEW_BLOCK   = 2'd1,
                     PERM_FINAL           = 2'd2,
                     PERM_SQUEEZE_MORE    = 2'd3;

    reg [2:0] state;
    reg [1:0] perm_reason;
    reg [7:0] rate_bytes;
    reg [7:0] domain_byte;
    reg [7:0] byte_pos;
    reg [7:0] out_pos;
    reg [15:0] message_count;
    reg [15:0] output_count;
    reg [15:0] requested_output_len;
    reg [1599:0] sponge_state;
    reg permutation_start;
    wire [1599:0] permutation_output;
    wire permutation_busy;
    wire permutation_done;

    assign in_ready = busy && (state == ST_ABSORB);
    assign out_valid = busy && (state == ST_SQUEEZE);
    assign out_byte = sponge_state[out_pos*8 +: 8];
    assign out_last = out_valid &&
                      ((output_count + 16'd1) == requested_output_len);

    keccak_f1600_iter #(
        .SERIAL_ROUND(SERIAL_ROUND)
    ) u_permutation (
        .clk(clk),
        .rst_n(rst_n),
        .zeroize(zeroize),
        .start(permutation_start),
        .state_in(sponge_state),
        .state_out(permutation_output),
        .busy(permutation_busy),
        .done(permutation_done)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= ST_IDLE;
            perm_reason <= PERM_ABSORB_CONTINUE;
            rate_bytes <= 8'd0;
            domain_byte <= 8'd0;
            byte_pos <= 8'd0;
            out_pos <= 8'd0;
            message_count <= 16'd0;
            output_count <= 16'd0;
            requested_output_len <= 16'd0;
            sponge_state <= 1600'd0;
            permutation_start <= 1'b0;
            busy <= 1'b0;
            done <= 1'b0;
            error <= 1'b0;
        end else if (zeroize) begin
            state <= ST_IDLE;
            perm_reason <= PERM_ABSORB_CONTINUE;
            rate_bytes <= 8'd0;
            domain_byte <= 8'd0;
            byte_pos <= 8'd0;
            out_pos <= 8'd0;
            message_count <= 16'd0;
            output_count <= 16'd0;
            requested_output_len <= 16'd0;
            sponge_state <= 1600'd0;
            permutation_start <= 1'b0;
            busy <= 1'b0;
            done <= 1'b0;
            error <= 1'b0;
        end else begin
            done <= 1'b0;
            permutation_start <= 1'b0;

            case (state)
                ST_IDLE: begin
                    busy <= 1'b0;
                    if (start) begin
                        busy <= 1'b1;
                        error <= 1'b0;
                        byte_pos <= 8'd0;
                        out_pos <= 8'd0;
                        message_count <= 16'd0;
                        output_count <= 16'd0;
                        requested_output_len <= output_len;
                        sponge_state <= 1600'd0;
                        case (mode)
                            MODE_SHA3_256: begin
                                rate_bytes <= 8'd136;
                                domain_byte <= 8'h06;
                                if (output_len != 16'd32)
                                    error <= 1'b1;
                            end
                            MODE_SHA3_512: begin
                                rate_bytes <= 8'd72;
                                domain_byte <= 8'h06;
                                if (output_len != 16'd64)
                                    error <= 1'b1;
                            end
                            MODE_SHAKE128: begin
                                rate_bytes <= 8'd168;
                                domain_byte <= 8'h1F;
                                if (output_len == 16'd0)
                                    error <= 1'b1;
                            end
                            default: begin
                                rate_bytes <= 8'd136;
                                domain_byte <= 8'h1F;
                                if (output_len == 16'd0)
                                    error <= 1'b1;
                            end
                        endcase
                        state <= (message_len == 16'd0) ? ST_PAD : ST_ABSORB;
                    end
                end

                ST_ABSORB: begin
                    if (in_valid) begin
                        sponge_state[byte_pos*8 +: 8] <=
                            sponge_state[byte_pos*8 +: 8] ^ in_byte;
                        message_count <= message_count + 16'd1;
                        if (byte_pos == (rate_bytes - 8'd1)) begin
                            byte_pos <= 8'd0;
                            perm_reason <=
                                ((message_count + 16'd1) == message_len) ?
                                PERM_PAD_NEW_BLOCK : PERM_ABSORB_CONTINUE;
                            state <= ST_PERM_START;
                        end else if ((message_count + 16'd1) == message_len) begin
                            byte_pos <= byte_pos + 8'd1;
                            state <= ST_PAD;
                        end else begin
                            byte_pos <= byte_pos + 8'd1;
                        end
                    end
                end

                ST_PAD: begin
                    if (error) begin
                        state <= ST_DONE;
                    end else begin
                        // If both suffix bytes address the final rate byte,
                        // combine the XORs explicitly so one nonblocking
                        // assignment cannot overwrite the other.
                        if (byte_pos == (rate_bytes - 8'd1)) begin
                            sponge_state[byte_pos*8 +: 8] <=
                                sponge_state[byte_pos*8 +: 8] ^
                                domain_byte ^ 8'h80;
                        end else begin
                            sponge_state[byte_pos*8 +: 8] <=
                                sponge_state[byte_pos*8 +: 8] ^ domain_byte;
                            sponge_state[(rate_bytes-1'b1)*8 +: 8] <=
                                sponge_state[(rate_bytes-1'b1)*8 +: 8] ^ 8'h80;
                        end
                        perm_reason <= PERM_FINAL;
                        state <= ST_PERM_START;
                    end
                end

                ST_PERM_START: begin
                    permutation_start <= 1'b1;
                    state <= ST_PERM_WAIT;
                end

                ST_PERM_WAIT: begin
                    if (permutation_done) begin
                        sponge_state <= permutation_output;
                        byte_pos <= 8'd0;
                        case (perm_reason)
                            PERM_ABSORB_CONTINUE: state <= ST_ABSORB;
                            PERM_PAD_NEW_BLOCK:   state <= ST_PAD;
                            PERM_FINAL: begin
                                out_pos <= 8'd0;
                                output_count <= 16'd0;
                                state <= ST_SQUEEZE;
                            end
                            default: begin
                                out_pos <= 8'd0;
                                state <= ST_SQUEEZE;
                            end
                        endcase
                    end
                end

                ST_SQUEEZE: begin
                    if (out_ready) begin
                        output_count <= output_count + 16'd1;
                        if ((output_count + 16'd1) == requested_output_len) begin
                            state <= ST_DONE;
                        end else if (out_pos == (rate_bytes - 8'd1)) begin
                            perm_reason <= PERM_SQUEEZE_MORE;
                            out_pos <= 8'd0;
                            state <= ST_PERM_START;
                        end else begin
                            out_pos <= out_pos + 8'd1;
                        end
                    end
                end

                ST_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= ST_IDLE;
                end

                default: begin
                    error <= 1'b1;
                    state <= ST_DONE;
                end
            endcase
        end
    end
endmodule
