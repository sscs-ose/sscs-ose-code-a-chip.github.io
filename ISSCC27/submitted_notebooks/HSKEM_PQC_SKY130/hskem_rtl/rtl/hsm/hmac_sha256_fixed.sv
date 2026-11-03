module hmac_sha256_fixed #(
    parameter SHA256_SLIDING_SCHEDULE = 1'b0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         scrub,
    input  wire         start,
    input  wire [255:0] key,
    input  wire [255:0] message,
    input  wire [5:0]   message_len,
    output reg          busy,
    output reg          done,
    output reg  [255:0] digest
);
    localparam [255:0] SHA256_IV =
        256'h6a09e667_bb67ae85_3c6ef372_a54ff53a_510e527f_9b05688c_1f83d9ab_5be0cd19;

    localparam [2:0] ST_IDLE=0, ST_IPAD=1, ST_INNER=2,
                     ST_OPAD=3, ST_OUTER=4;
    reg [2:0] state;
    reg comp_start;
    wire comp_busy;
    wire comp_done;
    wire [255:0] comp_state_out;
    reg [255:0] comp_state_in;
    reg [511:0] comp_block_in;
    reg [255:0] key_latched;
    reg [255:0] message_latched;
    reg [5:0]   message_len_latched;
    reg [255:0] inner_digest;

    function automatic [511:0] make_key_block;
        input [255:0] key_in;
        input [7:0] pad;
        integer j;
        reg [7:0] kb;
        begin
            make_key_block = 512'd0;
            for (j=0; j<64; j=j+1) begin
                kb = (j < 32) ? key_in[255-j*8 -: 8] : 8'd0;
                make_key_block[511-j*8 -: 8] = kb ^ pad;
            end
        end
    endfunction

    function automatic [511:0] make_inner_tail;
        input [255:0] msg;
        input [5:0] len;
        integer j;
        reg [63:0] total_bits;
        begin
            make_inner_tail = 512'd0;
            for (j=0; j<32; j=j+1)
                if (j < len)
                    make_inner_tail[511-j*8 -: 8] = msg[255-j*8 -: 8];
            for (j=0; j<64; j=j+1)
                if (j == len)
                    make_inner_tail[511-j*8 -: 8] = 8'h80;
            total_bits = (64 + len) * 8;
            make_inner_tail[63:0] = total_bits;
        end
    endfunction

    function automatic [511:0] make_outer_tail;
        input [255:0] inner;
        integer j;
        begin
            make_outer_tail = 512'd0;
            for (j=0; j<32; j=j+1)
                make_outer_tail[511-j*8 -: 8] = inner[255-j*8 -: 8];
            make_outer_tail[255:248] = 8'h80;
            make_outer_tail[63:0] = 64'd768;
        end
    endfunction

    sha256_compress #(
        .SLIDING_SCHEDULE(SHA256_SLIDING_SCHEDULE)
    ) u_compress (
        .clk(clk), .rst_n(rst_n), .scrub(scrub), .start(comp_start),
        .state_in(comp_state_in), .block_in(comp_block_in),
        .busy(comp_busy), .done(comp_done), .state_out(comp_state_out)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state               <= ST_IDLE;
            comp_start          <= 1'b0;
            comp_state_in       <= 256'd0;
            comp_block_in       <= 512'd0;
            key_latched         <= 256'd0;
            message_latched     <= 256'd0;
            message_len_latched <= 6'd0;
            inner_digest        <= 256'd0;
            digest              <= 256'd0;
            busy                <= 1'b0;
            done                <= 1'b0;
        end else if (scrub) begin
            state               <= ST_IDLE;
            comp_start          <= 1'b0;
            comp_state_in       <= 256'd0;
            comp_block_in       <= 512'd0;
            key_latched         <= 256'd0;
            message_latched     <= 256'd0;
            message_len_latched <= 6'd0;
            inner_digest        <= 256'd0;
            digest              <= 256'd0;
            busy                <= 1'b0;
            done                <= 1'b0;
        end else begin
            comp_start <= 1'b0;
            done       <= 1'b0;
            case (state)
                ST_IDLE: begin
                    busy <= 1'b0;
                    if (start && message_len <= 6'd32) begin
                        key_latched         <= key;
                        message_latched     <= message;
                        message_len_latched <= message_len;
                        comp_state_in       <= SHA256_IV;
                        comp_block_in       <= make_key_block(key, 8'h36);
                        comp_start          <= 1'b1;
                        busy                <= 1'b1;
                        state               <= ST_IPAD;
                    end
                end
                ST_IPAD: if (comp_done) begin
                    comp_state_in <= comp_state_out;
                    comp_block_in <= make_inner_tail(message_latched,
                                                      message_len_latched);
                    comp_start <= 1'b1;
                    state <= ST_INNER;
                end
                ST_INNER: if (comp_done) begin
                    inner_digest  <= comp_state_out;
                    comp_state_in <= SHA256_IV;
                    comp_block_in <= make_key_block(key_latched, 8'h5c);
                    comp_start <= 1'b1;
                    state <= ST_OPAD;
                end
                ST_OPAD: if (comp_done) begin
                    comp_state_in <= comp_state_out;
                    comp_block_in <= make_outer_tail(inner_digest);
                    comp_start <= 1'b1;
                    state <= ST_OUTER;
                end
                ST_OUTER: if (comp_done) begin
                    digest <= comp_state_out;
                    // The caller may need the digest for one cycle, but the
                    // HMAC key/message/intermediate are no longer needed.
                    key_latched         <= 256'd0;
                    message_latched     <= 256'd0;
                    message_len_latched <= 6'd0;
                    inner_digest        <= 256'd0;
                    comp_state_in       <= 256'd0;
                    comp_block_in       <= 512'd0;
                    busy   <= 1'b0;
                    done   <= 1'b1;
                    state  <= ST_IDLE;
                end
                default: state <= ST_IDLE;
            endcase
        end
    end
endmodule
