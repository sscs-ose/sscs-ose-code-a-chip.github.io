// Physical RO entropy source and online health gate for the C2 live profile.
//
// SYNTHESIS uses eight independent five-stage ring oscillators.  Simulation
// uses a deterministic LFSR so controller and fault handling are reproducible;
// simulation output is never evidence of physical entropy.  The thresholds
// below are conservative prototype gates, not an SP 800-90B validation claim.
module trng #(
    parameter integer WIDTH = 32,
    parameter integer RO_COUNT = 8,
    parameter integer STARTUP_SAMPLES = 64,
    // A cutoff of 32 creates a material false-alarm probability when this
    // monitor runs continuously at 50 MHz (the first board run accumulated
    // 164M samples).  64 still rejects a stuck source quickly while making an
    // iid false trip negligible at the prototype's operating duration.
    parameter integer RCT_CUTOFF = 64,
    parameter integer APT_WINDOW = 512,
    parameter integer APT_LOW = 128,
    parameter integer APT_HIGH = 384,
    // Simulation only: 0=deterministic varying stream, 1=stuck zero,
    // 2=stuck one.  The synthesis RO path ignores this parameter.
    parameter integer SIM_FAULT_MODE = 0
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire             enable,
    input  wire             clear_health,
    output reg              valid,
    output reg  [WIDTH-1:0] data,
    output reg              ready,
    output reg              unhealthy,
    output reg  [7:0]       health_code,
    output reg  [31:0]      raw_sample_count,
    output reg  [15:0]      word_count
);
    localparam integer APT_COUNT_WIDTH = 10;

`ifdef SYNTHESIS
    wire [RO_COUNT-1:0] ro_bits;
    genvar ro_index;
    generate
        for (ro_index = 0; ro_index < RO_COUNT; ro_index = ro_index + 1) begin : g_entropy_ro
            ro_ring_oscillator #(.STAGES(5)) u_ro (
                .enable(enable),
                .ro_out(ro_bits[ro_index])
            );
        end
    endgenerate
    wire physical_raw = ^ro_bits;
`else
    reg [31:0] sim_lfsr;
    wire sim_feedback = sim_lfsr[31] ^ sim_lfsr[21] ^
                        sim_lfsr[1] ^ sim_lfsr[0];
    wire physical_raw = (SIM_FAULT_MODE == 1) ? 1'b0 :
                        (SIM_FAULT_MODE == 2) ? 1'b1 : sim_lfsr[0];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            sim_lfsr <= 32'h1ACE_B00C;
        else if (enable && SIM_FAULT_MODE == 0)
            sim_lfsr <= {sim_lfsr[30:0], sim_feedback};
    end
`endif

    // Two-flop synchronizer deliberately samples the asynchronous RO XOR.
    (* preserve = "true" *) reg raw_meta;
    (* preserve = "true" *) reg raw_sync;
    reg previous_raw;
    reg [7:0] run_length;
    reg [APT_COUNT_WIDTH-1:0] apt_index;
    reg [APT_COUNT_WIDTH-1:0] apt_ones;
    reg [7:0] startup_count;
    reg [5:0] bit_count;
    reg [WIDTH-1:0] shift_word;
    reg [WIDTH-1:0] previous_word;
    reg previous_word_valid;

    wire [APT_COUNT_WIDTH:0] apt_ones_final =
        {1'b0, apt_ones} + {{APT_COUNT_WIDTH{1'b0}}, raw_sync};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            raw_meta <= 1'b0;
            raw_sync <= 1'b0;
        end else if (enable) begin
            raw_meta <= physical_raw;
            raw_sync <= raw_meta;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid <= 1'b0;
            data <= {WIDTH{1'b0}};
            ready <= 1'b0;
            unhealthy <= 1'b0;
            health_code <= 8'd0;
            raw_sample_count <= 32'd0;
            word_count <= 16'd0;
            previous_raw <= 1'b0;
            run_length <= 8'd0;
            apt_index <= {APT_COUNT_WIDTH{1'b0}};
            apt_ones <= {APT_COUNT_WIDTH{1'b0}};
            startup_count <= 8'd0;
            bit_count <= 6'd0;
            shift_word <= {WIDTH{1'b0}};
            previous_word <= {WIDTH{1'b0}};
            previous_word_valid <= 1'b0;
        end else if (clear_health) begin
            valid <= 1'b0;
            data <= {WIDTH{1'b0}};
            ready <= 1'b0;
            unhealthy <= 1'b0;
            health_code <= 8'd0;
            raw_sample_count <= 32'd0;
            word_count <= 16'd0;
            previous_raw <= 1'b0;
            run_length <= 8'd0;
            apt_index <= {APT_COUNT_WIDTH{1'b0}};
            apt_ones <= {APT_COUNT_WIDTH{1'b0}};
            startup_count <= 8'd0;
            bit_count <= 6'd0;
            shift_word <= {WIDTH{1'b0}};
            previous_word <= {WIDTH{1'b0}};
            previous_word_valid <= 1'b0;
        end else begin
            valid <= 1'b0;
            if (!enable) begin
                ready <= 1'b0;
            end else if (!unhealthy) begin
                if (raw_sample_count != 32'hFFFF_FFFF)
                    raw_sample_count <= raw_sample_count + 32'd1;

                if (raw_sync == previous_raw) begin
                    if (run_length != 8'hFF)
                        run_length <= run_length + 8'd1;
                    if (run_length + 8'd1 >= RCT_CUTOFF) begin
                        unhealthy <= 1'b1;
                        health_code[0] <= 1'b1;
                        ready <= 1'b0;
                    end
                end else begin
                    previous_raw <= raw_sync;
                    run_length <= 8'd1;
                end

                if (apt_index == APT_WINDOW-1) begin
                    if ((apt_ones_final < APT_LOW) ||
                        (apt_ones_final > APT_HIGH)) begin
                        unhealthy <= 1'b1;
                        health_code[1] <= 1'b1;
                        ready <= 1'b0;
                    end
                    apt_index <= {APT_COUNT_WIDTH{1'b0}};
                    apt_ones <= {APT_COUNT_WIDTH{1'b0}};
                end else begin
                    apt_index <= apt_index + {{(APT_COUNT_WIDTH-1){1'b0}}, 1'b1};
                    if (raw_sync)
                        apt_ones <= apt_ones + {{(APT_COUNT_WIDTH-1){1'b0}}, 1'b1};
                end

                if (startup_count < STARTUP_SAMPLES) begin
                    startup_count <= startup_count + 8'd1;
                    bit_count <= 6'd0;
                    shift_word <= {WIDTH{1'b0}};
                end else begin
                    shift_word <= {shift_word[WIDTH-2:0], raw_sync};
                    if (bit_count == WIDTH-1) begin
                        bit_count <= 6'd0;
                        data <= {shift_word[WIDTH-2:0], raw_sync};
                        if (previous_word_valid &&
                            ({shift_word[WIDTH-2:0], raw_sync} == previous_word)) begin
                            unhealthy <= 1'b1;
                            health_code[2] <= 1'b1;
                            ready <= 1'b0;
                        end else begin
                            previous_word <= {shift_word[WIDTH-2:0], raw_sync};
                            previous_word_valid <= 1'b1;
                            valid <= 1'b1;
                            if (word_count != 16'hFFFF)
                                word_count <= word_count + 16'd1;
                            if (word_count >= 16'd7)
                                ready <= 1'b1;
                        end
                    end else begin
                        bit_count <= bit_count + 6'd1;
                    end
                end
            end
        end
    end
endmodule
