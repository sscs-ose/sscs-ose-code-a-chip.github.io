// can_framer.v -- Transmit-only CAN 2.0A data-frame framer.
// Builds SOF + 11-bit ID + RTR + IDE + r0 + DLC + data + CRC-15,
// applies CAN bit-stuffing over SOF..CRC, then appends
// CRC-delimiter + ACK slot + ACK delimiter + EOF(7) + IFS(3), all recessive.
// CRC-15/CAN: poly x^15+x^14+x^10+x^8+x^7+x^4+x^3+1 (0x4599), init 0.
// One CAN bit time = bitdiv_i + 1 system clocks. tx_o = 1 when idle (recessive).
module can_framer (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start_i,    // single-cycle pulse
    input  wire [10:0] id_i,
    input  wire [3:0]  dlc_i,      // 0..8
    input  wire [63:0] data_i,     // byte0 = data[7:0], sent first, MSB-first per byte
    input  wire [7:0]  bitdiv_i,
    output reg         tx_o,
    output reg         busy_o,
    output reg         done_o      // single-cycle pulse
);

    localparam S_IDLE = 2'd0;
    localparam S_SEND = 2'd1;
    localparam S_DONE = 2'd2;
    localparam TRAIL_BITS = 13;    // crc-delim + ack + ack-delim + EOF(7) + IFS(3)

    reg  [1:0]  state;
    reg  [97:0] frame_raw;   // unstuffed frame, SOF at bit (raw_len-1), MSB-first
    reg  [6:0]  raw_len;     // 34 + 8*dlc, max 98
    reg  [6:0]  ptr;         // next raw bit index
    reg  [3:0]  trail;       // trail bit counter
    reg  [7:0]  div_cnt;
    reg         last_bit;
    reg  [2:0]  run;         // consecutive equal bits (0..5)
    reg         b;

    // ---- combinational frame assembly (single driver for frame_raw/raw_len:
    //      the clocked block below only) ----
    reg [97:0] tmp;
    reg [14:0] crc;
    reg [6:0]  flen;
    reg [3:0]  dlc_c;
    integer k;
    wire [97:0] frame_next;
    wire [6:0]  raw_len_next;

    always @(*) begin
        dlc_c = (dlc_i > 4'd8) ? 4'd8 : dlc_i;   // clamp, self-protecting
        // header: SOF(0) | ID[10:0] | RTR(0) | IDE(0) | r0(0) | DLC[3:0]
        tmp = {1'b0, id_i, 3'b000, dlc_c};
        for (k = 0; k < 8; k = k + 1) begin
            if (k < dlc_c)
                tmp = (tmp << 8) | ((data_i >> (8*k)) & 98'hff);
        end
        flen = 19 + (dlc_c << 3);
        crc  = crc15_calc(tmp, flen);
    end
    assign frame_next   = (tmp << 15) | crc;
    assign raw_len_next = flen + 15;

    // CRC-15 over bits[flen-1:0] of 'bits', MSB first
    function [14:0] crc15_calc;
        input [97:0] bits;
        input [6:0]  flen;
        integer i;
        reg [14:0] crc;
        reg bit_in;
        begin
            crc = 15'd0;
            for (i = 0; i < 98; i = i + 1) begin
                if (i < flen) begin
                    bit_in = bits[flen-1-i];
                    if (crc[14] ^ bit_in)
                        crc = ({crc[13:0], 1'b0}) ^ 15'h4599;
                    else
                        crc = {crc[13:0], 1'b0};
                end
            end
            crc15_calc = crc;
        end
    endfunction

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state     <= S_IDLE;
            frame_raw <= 98'd0;
            raw_len   <= 7'd0;
            ptr       <= 7'd0;
            trail     <= 4'd0;
            div_cnt   <= 8'd0;
            last_bit  <= 1'b1;
            run       <= 3'd0;
            tx_o      <= 1'b1;
            busy_o    <= 1'b0;
            done_o    <= 1'b0;
            b         <= 1'b0;
        end else begin
            done_o <= 1'b0;
            case (state)
                S_IDLE: begin
                    tx_o <= 1'b1;
                    if (start_i) begin
                        frame_raw <= frame_next;    // latch assembled frame
                        raw_len   <= raw_len_next;
                        state    <= S_SEND;
                        busy_o   <= 1'b1;
                        ptr      <= 7'd0;
                        trail    <= 4'd0;
                        div_cnt  <= 8'd0;
                        last_bit <= 1'b1;
                        run      <= 3'd0;
                    end
                end
                S_SEND: begin
                    if (div_cnt == bitdiv_i) begin
                        div_cnt <= 8'd0;
                        if (ptr < raw_len) begin
                            b = frame_raw[raw_len-1-ptr];
                            if (run == 3'd5) begin
                                // insert stuff bit (complement), don't advance ptr.
                                // The receiver discards the stuff bit before
                                // run-counting, so reset the counter here too.
                                tx_o     <= ~last_bit;
                                run      <= 3'd0;
                            end else begin
                                tx_o <= b;
                                if (b == last_bit)
                                    run <= run + 3'd1;
                                else begin
                                    last_bit <= b;
                                    run      <= 3'd1;
                                end
                                ptr <= ptr + 7'd1;
                            end
                        end else if (run == 3'd5) begin
                            // trailing stuff bit: the CRC field ended on five
                            // consecutive equal bits, so CAN still requires the
                            // complementary stuff bit before the CRC delimiter
                            tx_o     <= ~last_bit;
                            run      <= 3'd0;
                        end else if (trail < TRAIL_BITS) begin
                            tx_o  <= 1'b1;   // no stuffing in trailer
                            trail <= trail + 4'd1;
                        end else begin
                            state <= S_DONE;
                        end
                    end else begin
                        div_cnt <= div_cnt + 8'd1;
                    end
                end
                S_DONE: begin
                    tx_o   <= 1'b1;
                    busy_o <= 1'b0;
                    done_o <= 1'b1;
                    state  <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
