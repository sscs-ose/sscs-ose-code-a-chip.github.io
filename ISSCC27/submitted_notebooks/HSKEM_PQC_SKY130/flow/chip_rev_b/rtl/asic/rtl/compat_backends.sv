// Compatibility adapters let the unchanged common TrustEdge hierarchy use
// ASIC-V0 macro contracts. The FPGA project does not compile this file.

module trng #(
    parameter integer WIDTH = 32,
    parameter integer RO_COUNT = 8,
    parameter integer STARTUP_SAMPLES = 64,
    parameter integer RCT_CUTOFF = 64,
    parameter integer APT_WINDOW = 512,
    parameter integer APT_LOW = 128,
    parameter integer APT_HIGH = 384,
    parameter integer SIM_FAULT_MODE = 0
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire             enable,
    input  wire             clear_health,
    output wire             valid,
    output wire [WIDTH-1:0] data,
    output wire             ready,
    output wire             unhealthy,
    output wire [7:0]       health_code,
    output wire [31:0]      raw_sample_count,
    output wire [15:0]      word_count
);
    // FPGA-specific thresholds remain part of the source API but are enforced
    // by the characterized entropy backend in ASIC-V0.
    wire unused_parameters = (RO_COUNT == 0) || (STARTUP_SAMPLES == 0) ||
                             (RCT_CUTOFF == 0) || (APT_WINDOW == 0) ||
                             (APT_LOW == APT_HIGH) || (SIM_FAULT_MODE != 0);

    te_entropy_backend #(.WIDTH(WIDTH)) u_backend (
        .clk(clk), .rst_n(rst_n), .enable(enable),
        .clear_health(clear_health), .valid(valid), .data(data),
        .ready(ready), .unhealthy(unhealthy), .health_code(health_code),
        .raw_sample_count(raw_sample_count), .word_count(word_count)
    );
endmodule

module puf_char_engine #(
    parameter integer PAIR_COUNT = 256,
    parameter integer BITS_PER_BANK = 64,
    parameter integer WINDOW_CYCLES = 1024,
    parameter integer SETTLE_CYCLES = 8,
    parameter integer COUNTER_WIDTH = 16
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        scrub,
    input  wire        start,
    input  wire [1:0]  bank_id,
    input  wire        private_mode,
    output wire        busy,
    output wire        done,
    output wire [63:0] raw_response,
    output wire [15:0] min_abs_delta,
    output wire [15:0] max_abs_delta,
    output wire [7:0]  health_flags,
    output wire        physical_backend,
    output wire [31:0] measurement_cycles
);
    wire unused_parameters = (WINDOW_CYCLES == 0) ||
                             (SETTLE_CYCLES == 0) ||
                             (COUNTER_WIDTH == 0);
    assign physical_backend = 1'b1;

    te_puf_backend #(
        .PAIR_COUNT(PAIR_COUNT), .BITS_PER_BANK(BITS_PER_BANK)
    ) u_backend (
        .clk(clk), .rst_n(rst_n), .scrub(scrub), .start(start),
        .bank_id(bank_id), .private_mode(private_mode),
        .busy(busy), .done(done), .response(raw_response),
        .min_delta(min_abs_delta), .max_delta(max_abs_delta),
        .health(health_flags), .cycles(measurement_cycles)
    );
endmodule

module puf_top #(
    parameter integer ID_BITS = 32
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               cmd_enroll,
    input  wire               cmd_verify,
    input  wire [7:0]         challenge,
    input  wire [31:0]        nonce,
    output wire               busy,
    output wire               enroll_done,
    output wire               verify_done,
    output wire               verify_ok,
    output wire               enrolled,
    output wire [ID_BITS-1:0] device_id,
    output wire [31:0]        expected_nonce
);
    te_puf_session_backend #(.ID_BITS(ID_BITS)) u_backend (
        .clk(clk), .rst_n(rst_n), .enroll(cmd_enroll),
        .verify(cmd_verify), .challenge(challenge), .nonce(nonce),
        .busy(busy), .enroll_done(enroll_done), .verify_done(verify_done),
        .verify_ok(verify_ok), .enrolled(enrolled),
        .device_id(device_id), .expected_nonce(expected_nonce)
    );
endmodule
