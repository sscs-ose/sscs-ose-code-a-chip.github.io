// C2B stateful SHAKE256 conditioner/generator.
//
// Each run absorbs a domain separator, the previous private state, 256 fresh
// bits from the health-gated physical source, and a generation counter.  The
// 128-byte SHAKE256 result becomes ML-KEM d/z/m plus the next private state.
// Raw entropy and generated ML-KEM inputs are intentionally not exported.
// This is an academic FPGA construction, not a claimed SP 800-90A DRBG.
module c2_shake_drbg (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         clear,
    input  wire         run_start,
    input  wire         entropy_ready,
    input  wire         entropy_unhealthy,
    input  wire         entropy_valid,
    input  wire [31:0]  entropy_word,
    output reg          busy,
    output reg          done,
    output reg          pass,
    output reg  [7:0]   status,
    output reg          seeded,
    output reg          fresh,
    output reg  [31:0]  reseed_count,
    output reg  [31:0]  generate_count,
    output reg  [255:0] mlkem_d,
    output reg  [255:0] mlkem_z,
    output reg  [255:0] mlkem_m,
    output wire         sponge_active,
    output reg          sponge_start,
    output wire [1:0]   sponge_mode,
    output wire [15:0]  sponge_message_len,
    output wire [15:0]  sponge_output_len,
    output wire         sponge_in_valid,
    output reg  [7:0]   sponge_in_byte,
    output wire         sponge_out_ready,
    input  wire         sponge_in_ready,
    input  wire         sponge_out_valid,
    input  wire [7:0]   sponge_out_byte,
    input  wire         sponge_out_last,
    input  wire         sponge_busy,
    input  wire         sponge_done,
    input  wire         sponge_error
);
    localparam [2:0] ST_IDLE    = 3'd0,
                     ST_COLLECT = 3'd1,
                     ST_START   = 3'd2,
                     ST_FEED    = 3'd3,
                     ST_OUTPUT  = 3'd4;

    reg [2:0] state;
    reg [2:0] collect_index;
    reg [6:0] feed_index;
    reg [7:0] output_index;
    reg [255:0] entropy_buffer;
    reg [255:0] private_state;
    reg [255:0] next_d;
    reg [255:0] next_z;
    reg [255:0] next_m;
    reg [255:0] next_state;
    reg health_failed;
    wire [31:0] next_counter = generate_count + 32'd1;

    assign sponge_active = busy && (state >= ST_START);
    assign sponge_mode = 2'd3;              // SHAKE256
    assign sponge_message_len = 16'd76;     // domain8 + state32 + entropy32 + counter4
    assign sponge_output_len = 16'd128;     // d32 + z32 + m32 + next_state32
    assign sponge_in_valid = state == ST_FEED;
    assign sponge_out_ready = state == ST_OUTPUT;

    always @* begin
        sponge_in_byte = 8'd0;
        if (feed_index < 7'd8) begin
            case (feed_index)
                7'd0: sponge_in_byte = 8'h54; // T
                7'd1: sponge_in_byte = 8'h45; // E
                7'd2: sponge_in_byte = 8'h43; // C
                7'd3: sponge_in_byte = 8'h32; // 2
                7'd4: sponge_in_byte = 8'h52; // R
                7'd5: sponge_in_byte = 8'h55; // U
                7'd6: sponge_in_byte = 8'h4E; // N
                default: sponge_in_byte = 8'h31; // 1
            endcase
        end else if (feed_index < 7'd40) begin
            sponge_in_byte = private_state[(feed_index-7'd8)*8 +: 8];
        end else if (feed_index < 7'd72) begin
            sponge_in_byte = entropy_buffer[(feed_index-7'd40)*8 +: 8];
        end else begin
            sponge_in_byte = next_counter[(feed_index-7'd72)*8 +: 8];
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= ST_IDLE;
            collect_index <= 3'd0;
            feed_index <= 7'd0;
            output_index <= 8'd0;
            entropy_buffer <= 256'd0;
            private_state <= 256'd0;
            next_d <= 256'd0;
            next_z <= 256'd0;
            next_m <= 256'd0;
            next_state <= 256'd0;
            health_failed <= 1'b0;
            busy <= 1'b0;
            done <= 1'b0;
            pass <= 1'b0;
            status <= 8'd0;
            seeded <= 1'b0;
            fresh <= 1'b0;
            reseed_count <= 32'd0;
            generate_count <= 32'd0;
            mlkem_d <= 256'd0;
            mlkem_z <= 256'd0;
            mlkem_m <= 256'd0;
            sponge_start <= 1'b0;
        end else if (clear) begin
            state <= ST_IDLE;
            collect_index <= 3'd0;
            feed_index <= 7'd0;
            output_index <= 8'd0;
            entropy_buffer <= 256'd0;
            private_state <= 256'd0;
            next_d <= 256'd0;
            next_z <= 256'd0;
            next_m <= 256'd0;
            next_state <= 256'd0;
            health_failed <= 1'b0;
            busy <= 1'b0;
            done <= 1'b0;
            pass <= 1'b0;
            status <= 8'd0;
            seeded <= 1'b0;
            fresh <= 1'b0;
            reseed_count <= 32'd0;
            generate_count <= 32'd0;
            mlkem_d <= 256'd0;
            mlkem_z <= 256'd0;
            mlkem_m <= 256'd0;
            sponge_start <= 1'b0;
        end else begin
            done <= 1'b0;
            sponge_start <= 1'b0;
            if (busy && entropy_unhealthy)
                health_failed <= 1'b1;

            case (state)
                ST_IDLE: begin
                    busy <= 1'b0;
                    if (run_start) begin
                        pass <= 1'b0;
                        fresh <= 1'b0;
                        status <= 8'd0;
                        health_failed <= entropy_unhealthy;
                        entropy_buffer <= 256'd0;
                        next_d <= 256'd0;
                        next_z <= 256'd0;
                        next_m <= 256'd0;
                        next_state <= 256'd0;
                        collect_index <= 3'd0;
                        if (!entropy_ready || entropy_unhealthy) begin
                            done <= 1'b1;
                            status <= 8'h01;
                        end else begin
                            busy <= 1'b1;
                            state <= ST_COLLECT;
                        end
                    end
                end

                ST_COLLECT: begin
                    if (entropy_valid) begin
                        entropy_buffer[collect_index*32 +: 32] <= entropy_word;
                        if (collect_index == 3'd7) begin
                            feed_index <= 7'd0;
                            output_index <= 8'd0;
                            state <= ST_START;
                        end else begin
                            collect_index <= collect_index + 3'd1;
                        end
                    end
                end

                ST_START: begin
                    sponge_start <= 1'b1;
                    state <= ST_FEED;
                end

                ST_FEED: begin
                    if (sponge_in_ready) begin
                        if (feed_index == 7'd75)
                            state <= ST_OUTPUT;
                        else
                            feed_index <= feed_index + 7'd1;
                    end
                end

                ST_OUTPUT: begin
                    if (sponge_out_valid) begin
                        if (output_index < 8'd32)
                            next_d[output_index*8 +: 8] <= sponge_out_byte;
                        else if (output_index < 8'd64)
                            next_z[(output_index-8'd32)*8 +: 8] <= sponge_out_byte;
                        else if (output_index < 8'd96)
                            next_m[(output_index-8'd64)*8 +: 8] <= sponge_out_byte;
                        else
                            next_state[(output_index-8'd96)*8 +: 8] <= sponge_out_byte;
                        output_index <= output_index + 8'd1;
                    end
                    if (sponge_done) begin
                        busy <= 1'b0;
                        done <= 1'b1;
                        state <= ST_IDLE;
                        entropy_buffer <= 256'd0;
                        if (sponge_error || health_failed ||
                            output_index != 8'd128) begin
                            pass <= 1'b0;
                            status <= health_failed ? 8'h01 : 8'h02;
                            private_state <= 256'd0;
                            next_d <= 256'd0;
                            next_z <= 256'd0;
                            next_m <= 256'd0;
                            next_state <= 256'd0;
                            seeded <= 1'b0;
                            mlkem_d <= 256'd0;
                            mlkem_z <= 256'd0;
                            mlkem_m <= 256'd0;
                        end else begin
                            pass <= 1'b1;
                            status <= 8'hC2;
                            fresh <= (generate_count == 32'd0) ||
                                     next_d != mlkem_d || next_z != mlkem_z ||
                                     next_m != mlkem_m;
                            mlkem_d <= next_d;
                            mlkem_z <= next_z;
                            mlkem_m <= next_m;
                            private_state <= next_state;
                            seeded <= 1'b1;
                            reseed_count <= reseed_count + 32'd1;
                            generate_count <= generate_count + 32'd1;
                        end
                    end
                end

                default: state <= ST_IDLE;
            endcase
        end
    end

    // These inputs are intentionally consumed only through their handshakes.
    wire _unused = sponge_busy ^ sponge_out_last;
endmodule
