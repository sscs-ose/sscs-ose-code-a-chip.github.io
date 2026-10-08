// ============================================================================
// kyber_ntt_selftest.sv
// ----------------------------------------------------------------------------
// Runtime self-test wrapper for the Kyber forward NTT engine.
//
// The wrapper loads a fixed 256-coefficient polynomial:
//   a[i] = 7 + 13*i
// runs kyber_ntt_engine, then fingerprints all 256 output coefficients as:
//   digest = {CRC16_CCITT(outputs as big-endian 16-bit words), SUM16(outputs)}
//
// Expected digest for the FIPS 203 Algorithm 9 transform: 32'hFC3B59FC.
// This is not a cryptographic proof; it is a compact lab/runtime smoke test that
// proves the Kyber arithmetic path is instantiated and callable from SPI.
// ============================================================================
module kyber_ntt_selftest #(
    // The standalone testbench keeps its private engine.  The DE25 top sets
    // this parameter and connects both Kyber/ML-KEM clients to one engine.
    parameter USE_EXTERNAL_NTT = 1'b0
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    output reg         busy,
    output reg         done,
    output reg         pass,
    output reg [31:0]  digest,
    output reg [15:0]  cycles,
    output wire        ntt_ext_start,
    output wire        ntt_ext_we,
    output wire [7:0]  ntt_ext_addr,
    output wire [15:0] ntt_ext_wdata,
    input  wire        ntt_ext_busy,
    input  wire        ntt_ext_done,
    input  wire [15:0] ntt_ext_rdata
);
    localparam [31:0] EXPECTED_DIGEST = 32'hFC3B59FC;

    localparam [2:0] S_IDLE  = 3'd0,
                     S_LOAD  = 3'd1,
                     S_START = 3'd2,
                     S_WAIT  = 3'd3,
                     S_PRIME = 3'd4,
                     S_READ  = 3'd5,
                     S_DONE  = 3'd6;

    reg [2:0] st;
    reg [8:0] idx;
    reg [15:0] crc_acc;
    reg [15:0] sum_acc;

    wire        ntt_busy;
    wire        ntt_done;
    wire [15:0] ntt_rdata;
    wire        ntt_we    = (st == S_LOAD);
    wire        ntt_start = (st == S_START);
    // The M20K-backed engine has synchronous reads.  During S_READ, request
    // coefficient n+1 while consuming coefficient n.
    wire [7:0]  ntt_addr  =
        (st == S_READ && idx != 9'd255) ? (idx[7:0] + 8'd1) : idx[7:0];
    wire [15:0] ntt_wdata = 16'd7 + ({8'd0, idx[7:0]} * 16'd13);

    function [15:0] crc16_byte;
        input [15:0] c;
        input [7:0]  d;
        integer i;
        reg [15:0] x;
        begin
            x = c ^ {d, 8'h00};
            for (i = 0; i < 8; i = i + 1) begin
                if (x[15])
                    x = {x[14:0], 1'b0} ^ 16'h1021;
                else
                    x = {x[14:0], 1'b0};
            end
            crc16_byte = x;
        end
    endfunction

    wire [15:0] crc_after_hi = crc16_byte(crc_acc, ntt_rdata[15:8]);
    wire [15:0] crc_after_lo = crc16_byte(crc_after_hi, ntt_rdata[7:0]);
    wire [15:0] sum_next     = sum_acc + ntt_rdata;
    wire [31:0] digest_next  = {crc_after_lo, sum_next};

    assign ntt_ext_start = ntt_start;
    assign ntt_ext_we    = ntt_we;
    assign ntt_ext_addr  = ntt_addr;
    assign ntt_ext_wdata = ntt_wdata;

    generate
        if (USE_EXTERNAL_NTT) begin : g_external_ntt
            assign ntt_busy  = ntt_ext_busy;
            assign ntt_done  = ntt_ext_done;
            assign ntt_rdata = ntt_ext_rdata;
        end else begin : g_private_ntt
            kyber_ntt_engine u_ntt (
                .clk(clk),
                .rst_n(rst_n),
                .start(ntt_start),
                .inverse(1'b0),
                .busy(ntt_busy),
                .done(ntt_done),
                .waddr(ntt_addr),
                .wdata(ntt_wdata),
                .we(ntt_we),
                .rdata(ntt_rdata),
                .raddr(ntt_addr)
            );
        end
    endgenerate

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st      <= S_IDLE;
            idx     <= 9'd0;
            busy    <= 1'b0;
            done    <= 1'b0;
            pass    <= 1'b0;
            digest  <= 32'd0;
            cycles  <= 16'd0;
            crc_acc <= 16'hFFFF;
            sum_acc <= 16'd0;
        end else begin
            done <= 1'b0;

            if (busy && cycles != 16'hFFFF)
                cycles <= cycles + 16'd1;

            case (st)
                S_IDLE: begin
                    busy <= 1'b0;
                    if (start) begin
                        busy    <= 1'b1;
                        pass    <= 1'b0;
                        digest  <= 32'd0;
                        cycles  <= 16'd0;
                        crc_acc <= 16'hFFFF;
                        sum_acc <= 16'd0;
                        idx     <= 9'd0;
                        st      <= S_LOAD;
                    end
                end

                S_LOAD: begin
                    if (idx == 9'd255) begin
                        idx <= 9'd0;
                        st  <= S_START;
                    end else begin
                        idx <= idx + 9'd1;
                    end
                end

                S_START: begin
                    st <= S_WAIT;
                end

                S_WAIT: begin
                    if (ntt_done) begin
                        idx <= 9'd0;
                        st  <= S_PRIME;
                    end
                end

                S_PRIME: st <= S_READ;

                S_READ: begin
                    crc_acc <= crc_after_lo;
                    sum_acc <= sum_next;
                    if (idx == 9'd255) begin
                        digest <= digest_next;
                        pass   <= (digest_next == EXPECTED_DIGEST);
                        st     <= S_DONE;
                    end else begin
                        idx <= idx + 9'd1;
                    end
                end

                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    st   <= S_IDLE;
                end

                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
