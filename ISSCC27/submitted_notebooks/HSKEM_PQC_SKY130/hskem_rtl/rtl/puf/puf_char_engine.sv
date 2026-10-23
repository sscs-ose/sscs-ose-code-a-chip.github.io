// HSM-4D0 measurement-only RO-PUF engine.
//
// One pair is enabled at a time.  Two asynchronous counters run for a fixed
// reference-clock window, both ROs are stopped, and only then are the stable
// counts captured by clk.  The physical response is deliberately isolated
// from enrollment, sessions and the key vault.
module puf_char_engine #(
    parameter integer PAIR_COUNT       = 256,
    parameter integer BITS_PER_BANK    = 64,
    parameter integer WINDOW_CYCLES    = 1024,
    parameter integer SETTLE_CYCLES    = 8,
    parameter integer COUNTER_WIDTH    = 16
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        scrub,
    input  wire        start,
    input  wire [1:0]  bank_id,
    input  wire        private_mode,
    output reg         busy,
    output reg         done,
    output reg  [63:0] raw_response,
    output reg  [15:0] min_abs_delta,
    output reg  [15:0] max_abs_delta,
    output reg  [7:0]  health_flags,
    output wire        physical_backend,
    output reg  [31:0] measurement_cycles
);
    localparam integer PAIR_INDEX_WIDTH = 8;
    localparam [3:0] ST_IDLE=4'd0, ST_RESET=4'd1, ST_ARM=4'd2,
                     ST_MEASURE=4'd3, ST_SETTLE=4'd4, ST_SAMPLE=4'd5,
                     ST_CAPTURE=4'd6, ST_DONE=4'd7;

    reg [3:0] state;
    reg [PAIR_INDEX_WIDTH-1:0] pair_index;
    reg [5:0] bit_index;
    reg [15:0] window_count;
    reg [7:0] settle_count;
    reg ro_enable;
    reg counter_reset_n;
    reg [31:0] sample_sequence;
    reg [COUNTER_WIDTH-1:0] stable_count_a;
    reg [COUNTER_WIDTH-1:0] stable_count_b;

    wire [COUNTER_WIDTH-1:0] observed_count_a;
    wire [COUNTER_WIDTH-1:0] observed_count_b;

`ifdef SYNTHESIS
    assign physical_backend = 1'b1;

    wire [PAIR_COUNT-1:0] ro_a;
    wire [PAIR_COUNT-1:0] ro_b;
    // D1 uses an undisclosed response: A[k] is compared with B[k+17] inside
    // the same logical bank.  D0 exported only A[k] versus B[k], so the D1
    // comparison is a distinct, non-exporting challenge/response mapping.
    wire [7:0] selected_b_index = private_mode ?
          {pair_index[7:6], pair_index[5:0] + 6'd17} : pair_index;
    wire selected_ro_a = ro_a[pair_index];
    wire selected_ro_b = ro_b[selected_b_index];

    genvar ro_index;
    generate
        for (ro_index = 0; ro_index < PAIR_COUNT; ro_index = ro_index + 1) begin : g_physical_pair
            ro_ring_oscillator #(.STAGES(5)) u_ro_a (
                .enable(ro_enable && (pair_index == ro_index)),
                .ro_out(ro_a[ro_index])
            );
            // Matched topology is essential: the response must come from
            // fitted-device delay variation, not from an intentional 5-vs-7
            // stage frequency bias.
            ro_ring_oscillator #(.STAGES(5)) u_ro_b (
                .enable(ro_enable && (selected_b_index == ro_index)),
                .ro_out(ro_b[ro_index])
            );
        end
    endgenerate

    // The counters are the only logic clocked by the selected local RO nets.
    // Saturation makes an unexpectedly fast/stuck implementation observable.
    (* preserve = "true" *) reg [COUNTER_WIDTH-1:0] async_count_a;
    (* preserve = "true" *) reg [COUNTER_WIDTH-1:0] async_count_b;
    always @(posedge selected_ro_a or negedge counter_reset_n) begin
        if (!counter_reset_n)
            async_count_a <= {COUNTER_WIDTH{1'b0}};
        else if (&async_count_a == 1'b0)
            async_count_a <= async_count_a + {{(COUNTER_WIDTH-1){1'b0}}, 1'b1};
    end
    always @(posedge selected_ro_b or negedge counter_reset_n) begin
        if (!counter_reset_n)
            async_count_b <= {COUNTER_WIDTH{1'b0}};
        else if (&async_count_b == 1'b0)
            async_count_b <= async_count_b + {{(COUNTER_WIDTH-1){1'b0}}, 1'b1};
    end
    assign observed_count_a = async_count_a;
    assign observed_count_b = async_count_b;
`else
    // Deterministic controller model only.  It proves sequencing/protocol,
    // never entropy, physical oscillation, bias or silicon stability.
    assign physical_backend = 1'b0;
    wire [7:0] selected_b_index = private_mode ?
          {pair_index[7:6], pair_index[5:0] + 6'd17} : pair_index;
    wire [15:0] sim_base_a = 16'd1200 + {8'd0, pair_index};
    wire [15:0] sim_base_b = 16'd1200 + {8'd0, selected_b_index};
    assign observed_count_a = sim_base_a +
                              ((pair_index[0] ^ pair_index[7]) ? 16'd19 : 16'd31) +
                              {14'd0, sample_sequence[1:0]};
    assign observed_count_b = sim_base_b +
                              ((selected_b_index[1] ^ selected_b_index[6]) ? 16'd13 : 16'd29) +
                              {14'd0, sample_sequence[1:0]};
`endif

    wire [15:0] count_a_16 = {{(16-COUNTER_WIDTH){1'b0}}, observed_count_a};
    wire [15:0] count_b_16 = {{(16-COUNTER_WIDTH){1'b0}}, observed_count_b};
    wire [15:0] abs_delta = (count_a_16 >= count_b_16) ?
                            (count_a_16 - count_b_16) :
                            (count_b_16 - count_a_16);
    wire [15:0] stable_a_16 = {{(16-COUNTER_WIDTH){1'b0}}, stable_count_a};
    wire [15:0] stable_b_16 = {{(16-COUNTER_WIDTH){1'b0}}, stable_count_b};
    wire [15:0] stable_abs_delta = (stable_a_16 >= stable_b_16) ?
                                   (stable_a_16 - stable_b_16) :
                                   (stable_b_16 - stable_a_16);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= ST_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            raw_response <= 64'd0;
            min_abs_delta <= 16'hFFFF;
            max_abs_delta <= 16'd0;
            health_flags <= 8'd0;
            measurement_cycles <= 32'd0;
            pair_index <= 8'd0;
            bit_index <= 6'd0;
            window_count <= 16'd0;
            settle_count <= 8'd0;
            ro_enable <= 1'b0;
            counter_reset_n <= 1'b0;
            sample_sequence <= 32'd0;
            stable_count_a <= {COUNTER_WIDTH{1'b0}};
            stable_count_b <= {COUNTER_WIDTH{1'b0}};
        end else if (scrub) begin
            state <= ST_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            raw_response <= 64'd0;
            min_abs_delta <= 16'hFFFF;
            max_abs_delta <= 16'd0;
            health_flags <= 8'd0;
            measurement_cycles <= 32'd0;
            pair_index <= 8'd0;
            bit_index <= 6'd0;
            window_count <= 16'd0;
            settle_count <= 8'd0;
            ro_enable <= 1'b0;
            counter_reset_n <= 1'b0;
            sample_sequence <= 32'd0;
            stable_count_a <= {COUNTER_WIDTH{1'b0}};
            stable_count_b <= {COUNTER_WIDTH{1'b0}};
        end else begin
            done <= 1'b0;
            if (busy)
                measurement_cycles <= measurement_cycles + 32'd1;

            case (state)
                ST_IDLE: begin
                    busy <= 1'b0;
                    ro_enable <= 1'b0;
                    counter_reset_n <= 1'b0;
                    if (start) begin
                        busy <= 1'b1;
                        raw_response <= 64'd0;
                        min_abs_delta <= 16'hFFFF;
                        max_abs_delta <= 16'd0;
                        health_flags <= 8'd0;
                        measurement_cycles <= 32'd0;
                        bit_index <= 6'd0;
                        pair_index <= {bank_id, 6'd0};
                        sample_sequence <= sample_sequence + 32'd1;
                        state <= ST_RESET;
                    end
                end

                ST_RESET: begin
                    ro_enable <= 1'b0;
                    counter_reset_n <= 1'b0;
                    window_count <= 16'd0;
                    settle_count <= 8'd0;
                    state <= ST_ARM;
                end

                // Release the asynchronous counter reset while both rings are
                // still disabled.  This avoids reset release and the first RO
                // edge being intentionally coincident.
                ST_ARM: begin
                    ro_enable <= 1'b0;
                    counter_reset_n <= 1'b1;
                    state <= ST_MEASURE;
                end

                ST_MEASURE: begin
                    counter_reset_n <= 1'b1;
                    ro_enable <= 1'b1;
                    if (window_count == WINDOW_CYCLES-1) begin
                        ro_enable <= 1'b0;
                        settle_count <= 8'd0;
                        state <= ST_SETTLE;
                    end else begin
                        window_count <= window_count + 16'd1;
                    end
                end

                ST_SETTLE: begin
                    ro_enable <= 1'b0;
                    if (settle_count == SETTLE_CYCLES-1)
                        state <= ST_SAMPLE;
                    else
                        settle_count <= settle_count + 8'd1;
                end


                // Sample twice after the rings have stopped.  A mismatch is a
                // fatal CDC/settling health indication for the private path.
                ST_SAMPLE: begin
                    stable_count_a <= observed_count_a;
                    stable_count_b <= observed_count_b;
                    state <= ST_CAPTURE;
                end

                ST_CAPTURE: begin
                    raw_response[bit_index] <= (stable_a_16 >= stable_b_16);
                    if (stable_abs_delta < min_abs_delta)
                        min_abs_delta <= stable_abs_delta;
                    if (stable_abs_delta > max_abs_delta)
                        max_abs_delta <= stable_abs_delta;
                    if ((stable_a_16 == 16'd0) || (stable_b_16 == 16'd0))
                        health_flags[0] <= 1'b1;
                    if ((&stable_a_16) || (&stable_b_16))
                        health_flags[1] <= 1'b1;
                    if (stable_a_16 == stable_b_16)
                        health_flags[2] <= 1'b1;
                    if ((stable_count_a != observed_count_a) ||
                        (stable_count_b != observed_count_b))
                        health_flags[3] <= 1'b1;

                    if (bit_index == BITS_PER_BANK-1) begin
                        state <= ST_DONE;
                    end else begin
                        bit_index <= bit_index + 6'd1;
                        pair_index <= pair_index + 8'd1;
                        state <= ST_RESET;
                    end
                end

                ST_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    counter_reset_n <= 1'b0;
                    state <= ST_IDLE;
                end

                default: state <= ST_IDLE;
            endcase
        end
    end
endmodule
