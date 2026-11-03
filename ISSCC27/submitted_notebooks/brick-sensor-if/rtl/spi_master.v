// spi_master.v -- Mode-0 SPI master, MSB-first, full duplex.
// SCLK half period = clkdiv_i + 1 system clocks. CPOL=0/CPHA=0:
// MOSI changes on falling edge, MISO sampled on rising edge.
module spi_master (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start_i,    // single-cycle pulse in clk domain
    input  wire [3:0]  len_i,      // bytes per transfer, 1..8
    input  wire [7:0]  clkdiv_i,
    input  wire [63:0] tx_word_i,  // byte0 = bits[7:0], sent first
    output reg  [63:0] rx_word_o,  // byte0 = first received byte
    output reg         busy_o,
    output reg         done_o,     // single-cycle pulse
    output wire        sclk_o,
    output wire        mosi_o,
    input  wire        miso_i,
    output wire        cs_n_o
);

    localparam S_IDLE = 2'd0;
    localparam S_XFER = 2'd1;
    localparam S_DONE = 2'd2;

    reg  [1:0]  state;
    reg  [6:0]  bits_left;   // up to 64
    reg  [7:0]  div_cnt;
    reg         phase;        // 1: next half-period ends with rising edge (sample)
                             // 0: next half-period ends with falling edge (drive)
    reg  [63:0] shreg;       // tx shift register, MSB (bit63) -> MOSI
    reg  [63:0] rxreg;
    reg  [3:0]  len_r;        // bytes for the active transfer (latched at start)
    reg         sclk_r;
    reg         cs_n_r;

    // byte-reverse: tx_word byte0 -> shreg top byte so byte0 goes out first, MSB first
    function [63:0] bytereverse;
        input [63:0] w;
        integer i;
        begin
            bytereverse = 64'd0;
            for (i = 0; i < 8; i = i + 1)
                bytereverse = (bytereverse << 8) | ((w >> (8*i)) & 64'hff);
        end
    endfunction

    assign sclk_o = sclk_r;
    assign mosi_o = shreg[63];
    assign cs_n_o = cs_n_r;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state     <= S_IDLE;
            bits_left <= 7'd0;
            div_cnt   <= 8'd0;
            phase     <= 1'b1;
            shreg     <= 64'd0;
            rxreg     <= 64'd0;
            len_r     <= 4'd8;
            rx_word_o <= 64'd0;
            sclk_r    <= 1'b0;
            cs_n_r    <= 1'b1;
            busy_o    <= 1'b0;
            done_o    <= 1'b0;
        end else begin
            done_o <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (start_i) begin
                        shreg     <= bytereverse(tx_word_i);
                        rxreg     <= 64'd0;
                        len_r     <= len_i;
                        bits_left <= {3'd0, len_i} << 3;  // len*8
                        div_cnt   <= 8'd0;
                        phase     <= 1'b1;   // first edge is rising -> sample bit0
                        sclk_r    <= 1'b0;
                        cs_n_r    <= 1'b0;
                        busy_o    <= 1'b1;
                        state     <= S_XFER;
                    end
                end
                S_XFER: begin
                    if (div_cnt == clkdiv_i) begin
                        div_cnt <= 8'd0;
                        if (phase) begin
                            // rising edge: sample MISO
                            sclk_r <= 1'b1;
                            rxreg  <= {rxreg[62:0], miso_i};
                            phase  <= 1'b0;
                            if (bits_left == 7'd1) begin
                                state <= S_DONE;
                            end else begin
                                bits_left <= bits_left - 7'd1;
                            end
                        end else begin
                            // falling edge: present next MOSI bit
                            sclk_r <= 1'b0;
                            shreg  <= {shreg[62:0], 1'b0};
                            phase  <= 1'b1;
                        end
                    end else begin
                        div_cnt <= div_cnt + 8'd1;
                    end
                end
                S_DONE: begin
                    sclk_r    <= 1'b0;
                    cs_n_r    <= 1'b1;
                    // rxreg holds the received bytes in its LOW 8*len_r bits
                    // (first byte at the top of that region). Left-align the
                    // valid bytes, then byte-reverse so byte0 lands at [7:0].
                    // Short transfers zero the unused upper bytes.
                    rx_word_o <= bytereverse(rxreg << ((8 - len_r) << 3));
                    busy_o    <= 1'b0;
                    done_o    <= 1'b1;
                    state     <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
