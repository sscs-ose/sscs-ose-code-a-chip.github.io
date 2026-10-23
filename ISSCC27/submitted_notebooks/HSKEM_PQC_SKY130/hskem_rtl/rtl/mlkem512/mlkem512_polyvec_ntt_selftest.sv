// ML-KEM-512 polyvec NTT self-test.
// Runs two fixed polynomials (k=2) through FIPS 203 NTT, fingerprints all
// 512 forward outputs, then runs NTT^-1 and checks every restored coefficient.
module mlkem512_polyvec_ntt_selftest #(
    parameter USE_EXTERNAL_NTT = 1'b0
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       start,
    output reg        busy,
    output reg        done,
    output reg        pass,
    output reg [31:0] digest,
    output reg [15:0] cycles,
    output wire       ntt_ext_start,
    output wire       ntt_ext_inverse,
    output wire       ntt_ext_we,
    output wire [7:0] ntt_ext_addr,
    output wire [15:0] ntt_ext_wdata,
    input  wire       ntt_ext_busy,
    input  wire       ntt_ext_done,
    input  wire [15:0] ntt_ext_rdata
);
    localparam [31:0] EXPECTED_DIGEST = 32'hA8981500;

    localparam [3:0] S_IDLE  = 4'd0,
                     S_LOAD  = 4'd1,
                     S_FWD_START = 4'd2,
                     S_FWD_WAIT  = 4'd3,
                     S_FWD_PRIME = 4'd4,
                     S_FWD_READ  = 4'd5,
                     S_INV_START = 4'd6,
                     S_INV_WAIT  = 4'd7,
                     S_INV_PRIME = 4'd8,
                     S_INV_READ  = 4'd9,
                     S_NEXT      = 4'd10,
                     S_DONE      = 4'd11;

    reg [3:0] st;
    reg       poly_sel;
    reg [8:0] idx;
    reg [15:0] crc_acc;
    reg [15:0] sum_acc;
    reg        roundtrip_ok;

    wire        ntt_busy;
    wire        ntt_done;
    wire [15:0] ntt_rdata;
    wire        ntt_we    = (st == S_LOAD);
    wire        ntt_start = (st == S_FWD_START) || (st == S_INV_START);
    wire        ntt_inverse = (st == S_INV_START);
    wire [7:0]  ntt_addr  =
        ((st == S_FWD_READ || st == S_INV_READ) && idx != 9'd255) ?
        (idx[7:0] + 8'd1) : idx[7:0];
    wire [15:0] poly0_val = 16'd3 + ({8'd0, idx[7:0]} * 16'd5);
    wire [15:0] poly1_val = 16'd11 + ({8'd0, idx[7:0]} * 16'd7);
    wire [15:0] ntt_wdata = poly_sel ? poly1_val : poly0_val;

    function [15:0] crc16_byte;
        input [15:0] c;
        input [7:0]  d;
        integer i;
        reg [15:0] x;
        begin
            x = c ^ {d, 8'h00};
            for (i = 0; i < 8; i = i + 1)
                x = x[15] ? ({x[14:0], 1'b0} ^ 16'h1021) :
                            {x[14:0], 1'b0};
            crc16_byte = x;
        end
    endfunction

    wire [15:0] crc_after_hi = crc16_byte(crc_acc, ntt_rdata[15:8]);
    wire [15:0] crc_after_lo = crc16_byte(crc_after_hi, ntt_rdata[7:0]);
    wire [15:0] sum_next     = sum_acc + ntt_rdata;
    wire [31:0] digest_next  = {crc_after_lo, sum_next};

    assign ntt_ext_start = ntt_start;
    assign ntt_ext_inverse = ntt_inverse;
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
                .inverse(ntt_inverse),
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
            st <= S_IDLE;
            poly_sel <= 1'b0;
            idx <= 9'd0;
            busy <= 1'b0;
            done <= 1'b0;
            pass <= 1'b0;
            digest <= 32'd0;
            cycles <= 16'd0;
            crc_acc <= 16'hFFFF;
            sum_acc <= 16'd0;
            roundtrip_ok <= 1'b0;
        end else begin
            done <= 1'b0;

            if (busy && cycles != 16'hFFFF)
                cycles <= cycles + 16'd1;

            case (st)
                S_IDLE: begin
                    busy <= 1'b0;
                    if (start) begin
                        busy <= 1'b1;
                        pass <= 1'b0;
                        digest <= 32'd0;
                        cycles <= 16'd0;
                        crc_acc <= 16'hFFFF;
                        sum_acc <= 16'd0;
                        roundtrip_ok <= 1'b1;
                        poly_sel <= 1'b0;
                        idx <= 9'd0;
                        st <= S_LOAD;
                    end
                end

                S_LOAD: begin
                    if (idx == 9'd255) begin
                        idx <= 9'd0;
                        st <= S_FWD_START;
                    end else begin
                        idx <= idx + 9'd1;
                    end
                end

                S_FWD_START: begin
                    st <= S_FWD_WAIT;
                end

                S_FWD_WAIT: begin
                    if (ntt_done) begin
                        idx <= 9'd0;
                        st <= S_FWD_PRIME;
                    end
                end

                S_FWD_PRIME: st <= S_FWD_READ;

                S_FWD_READ: begin
                    crc_acc <= crc_after_lo;
                    sum_acc <= sum_next;
                    if (idx == 9'd255) begin
                        digest <= digest_next;
                        idx <= 9'd0;
                        st <= S_INV_START;
                    end else begin
                        idx <= idx + 9'd1;
                    end
                end

                S_INV_START: st <= S_INV_WAIT;

                S_INV_WAIT: begin
                    if (ntt_done) begin
                        idx <= 9'd0;
                        st <= S_INV_PRIME;
                    end
                end

                S_INV_PRIME: st <= S_INV_READ;

                S_INV_READ: begin
                    if (ntt_rdata != ntt_wdata)
                        roundtrip_ok <= 1'b0;
                    if (idx == 9'd255) begin
                        st <= S_NEXT;
                    end else begin
                        idx <= idx + 9'd1;
                    end
                end

                S_NEXT: begin
                    if (!poly_sel) begin
                        poly_sel <= 1'b1;
                        idx <= 9'd0;
                        st <= S_LOAD;
                    end else begin
                        pass <= roundtrip_ok && (digest == EXPECTED_DIGEST);
                        st <= S_DONE;
                    end
                end

                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    st <= S_IDLE;
                end

                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
