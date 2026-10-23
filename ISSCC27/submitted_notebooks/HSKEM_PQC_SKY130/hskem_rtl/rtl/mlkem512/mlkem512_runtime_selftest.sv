module mlkem512_runtime_selftest #(
    parameter USE_EXTERNAL_NTT = 1'b0
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       start,
    output reg        busy,
    output reg        done,
    output reg        pass,
    output reg [7:0]  status,
    output reg [31:0] partial_digest,
    output reg [31:0] polyvec_digest,
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
    localparam [2:0] S_IDLE = 3'd0,
                     S_PART_START = 3'd1,
                     S_PART_WAIT = 3'd2,
                     S_VEC_START = 3'd3,
                     S_VEC_WAIT = 3'd4,
                     S_DONE = 3'd5;

    reg [2:0] st;
    reg part_start;
    reg vec_start;

    wire part_busy;
    wire part_done;
    wire part_pass;
    wire [7:0] part_status;
    wire [31:0] part_digest;

    wire vec_busy;
    wire vec_done;
    wire vec_pass;
    wire [31:0] vec_digest;
    wire [15:0] vec_cycles;

    mlkem512_partial_selftest u_partial (
        .clk(clk),
        .rst_n(rst_n),
        .start(part_start),
        .busy(part_busy),
        .done(part_done),
        .pass(part_pass),
        .status(part_status),
        .digest(part_digest)
    );

    mlkem512_polyvec_ntt_selftest #(
        .USE_EXTERNAL_NTT(USE_EXTERNAL_NTT)
    ) u_polyvec (
        .clk(clk),
        .rst_n(rst_n),
        .start(vec_start),
        .busy(vec_busy),
        .done(vec_done),
        .pass(vec_pass),
        .digest(vec_digest),
        .cycles(vec_cycles),
        .ntt_ext_start(ntt_ext_start),
        .ntt_ext_inverse(ntt_ext_inverse),
        .ntt_ext_we(ntt_ext_we),
        .ntt_ext_addr(ntt_ext_addr),
        .ntt_ext_wdata(ntt_ext_wdata),
        .ntt_ext_busy(ntt_ext_busy),
        .ntt_ext_done(ntt_ext_done),
        .ntt_ext_rdata(ntt_ext_rdata)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE;
            part_start <= 1'b0;
            vec_start <= 1'b0;
            busy <= 1'b0;
            done <= 1'b0;
            pass <= 1'b0;
            status <= 8'd0;
            partial_digest <= 32'd0;
            polyvec_digest <= 32'd0;
            cycles <= 16'd0;
        end else begin
            done <= 1'b0;
            part_start <= 1'b0;
            vec_start <= 1'b0;

            if (busy && cycles != 16'hFFFF)
                cycles <= cycles + 16'd1;

            case (st)
                S_IDLE: begin
                    busy <= 1'b0;
                    if (start) begin
                        busy <= 1'b1;
                        pass <= 1'b0;
                        status <= 8'd0;
                        partial_digest <= 32'd0;
                        polyvec_digest <= 32'd0;
                        cycles <= 16'd0;
                        st <= S_PART_START;
                    end
                end

                S_PART_START: begin
                    part_start <= 1'b1;
                    st <= S_PART_WAIT;
                end

                S_PART_WAIT: begin
                    if (part_done) begin
                        status <= part_status;
                        partial_digest <= part_digest;
                        st <= S_VEC_START;
                    end
                end

                S_VEC_START: begin
                    vec_start <= 1'b1;
                    st <= S_VEC_WAIT;
                end

                S_VEC_WAIT: begin
                    if (vec_done) begin
                        polyvec_digest <= vec_digest;
                        pass <= part_pass && vec_pass;
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
