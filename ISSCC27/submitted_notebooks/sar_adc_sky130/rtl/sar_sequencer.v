// SPDX-License-Identifier: Apache-2.0
//
// sar_sequencer -- one-hot successive-approximation sequencer, MSB first.
//
// Structure matches the transistor-level sequencer it replaces:
//
//   phases      p[0]            sample / reset of the code register's source
//               p[1] .. p[N]    trial 0 .. trial N-1   (trial i is active in p[i+1])
//               p[N+1]          read: load the code register, clear q
//               -> back to p[0]
//
//   DAC drive   d[i] = p[i+1] | q[i]
//                      ^^^^^^   force cap i high for its own trial
//                               ^^^^ hold the decision afterwards
//
//   capture     q[i] <= cmp on the FALLING edge of the phase clock, enabled by p[i+1]
//
// Bit order, because it is easy to read backwards: trial 0 decides the MSB
// (weight 2^(N-1)) and lands in q[0]/code[0]. code[N-1] is the LSB. This is the
// same q0..q7 order as the netlist, NOT the usual byte order where bit 7 is MSB.
// `code_bin` is provided as the conventional weighted value.
//
// -------------------------------------------------------------------------
// Why the phase count is N+2 and why that matters
// -------------------------------------------------------------------------
// The analog sequencer captured trial i a quarter phase past the end of p[i+1],
// and a code-register clear pinned to an absolute time collided with the last
// trial's capture at N = 8 (and only at N = 8). Here read and clear live in
// their own phase, p[N+1], and are derived from the one-hot register rather
// than from a constant. There is no constant left to disagree with N, so the
// bug class cannot recur silently at any N.
//
// -------------------------------------------------------------------------
// Timing constraint this imposes on the implementation flow
// -------------------------------------------------------------------------
// The phase advances on posedge clk and the comparator is captured on negedge
// clk, so the DAC settling + comparator decision path has HALF a clock period,
// not a full one. Constrain it as such; do not let the tool assume a full cycle:
//
//   create_clock -name clk -period ${TP} [get_ports clk]
//   set_output_delay ... [get_ports d[*]]   ;# to the DAC
//   set_input_delay  ... [get_ports cmp]    ;# from the comparator
//   # the d -> cmp loop closes outside this block; budget it explicitly
//
// `cmp` is the registered output of a clocked comparator, so it is already
// synchronous to clk and needs no synchroniser. If that ever stops being true,
// this module is wrong, not the constraint file.

`default_nettype none

module sar_sequencer #(
    parameter integer N = 8                 // resolution in bits
) (
    input  wire              clk,           // phase clock: one period per phase
    input  wire              rst_n,         // active-low async reset
    input  wire              start,         // sampled in p[0]; begins a conversion
    input  wire              cmp,           // comparator output, already clocked

    output wire [N-1:0]      d,             // DAC drive, d[0] = MSB capacitor
    output wire [N+1:0]      phase,         // one-hot over all N+2 phases, for observability
    output reg  [N-1:0]      code,          // MSB-first, code[0] = MSB
    output wire [N-1:0]      code_bin,      // conventional weighting, bit N-1 = MSB
    output reg               eoc            // one clk pulse, asserted in p[N+1]
);

    // ---------------------------------------------------------------- checks
    // Elaboration-time, so a bad parameter fails at compile rather than in a
    // waveform three weeks later.
    generate
        if (N < 2) begin : g_bad_n
            illegal_parameter_N_must_be_at_least_2 err();
        end
    endgenerate

    localparam integer NPH      = N + 2;    // p[0] sample, p[1..N] trials, p[N+1] read
    localparam integer PH_READ  = N + 1;

    // ------------------------------------------------------- phase register
    // One-hot. Held in p[0] until start; then walks to p[N+1] and wraps.
    reg [NPH-1:0] p;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            p <= {{(NPH-1){1'b0}}, 1'b1};       // p[0]
        end else if (p[0]) begin
            p <= start ? {{(NPH-2){1'b0}}, 2'b10} : {{(NPH-1){1'b0}}, 1'b1};
        end else if (p[PH_READ]) begin
            p <= {{(NPH-1){1'b0}}, 1'b1};       // back to p[0]
        end else begin
            p <= p << 1;
        end
    end

    assign phase = p;          // all NPH bits: [N:0] would drop the read phase p[N+1],
                               // leaving `phase` all-zero for one phase in every N+2.

    // ------------------------------------------------------- decision register
    // Captured on the falling edge of clk, enabled by the active phase. This is
    // an enable on a negedge flop, deliberately NOT a gated clock: gating p[i+1]
    // onto the clock pin is what the analog version effectively did, and it is
    // what makes the capture edge depend on when the gate happens to resolve.
    reg [N-1:0] q;
    integer i;

    always @(negedge clk or negedge rst_n) begin
        if (!rst_n) begin
            q <= {N{1'b0}};
        end else if (p[PH_READ]) begin
            q <= {N{1'b0}};                     // clear, after the last capture
        end else begin
            for (i = 0; i < N; i = i + 1)
                if (p[i+1]) q[i] <= cmp;        // trial i lives in p[i+1]
        end
    end

    // ------------------------------------------------------------- DAC drive
    genvar b;
    generate
        for (b = 0; b < N; b = b + 1) begin : g_dac
            if (b == 0) begin : g_msb
                // The MSB additionally holds through the sampling phase p[0].
                // Without this term every bottom plate is grounded the instant
                // sampling ends, the top plate sits at Vcm - Vin -- negative for
                // any input above Vcm -- and the substrate diode clamps it,
                // destroying the charge just sampled. This matches or{0}a in the
                // netlist: d0 = p0 | p1 | q0.
                assign d[b] = p[0] | p[b+1] | q[b];
            end else begin : g_rest
                assign d[b] = p[b+1] | q[b];
            end
        end
    endgenerate

    // ------------------------------------------------------ code register
    // Read happens at the posedge that ENDS p[N] -- after the LSB capture on the
    // negedge inside p[N], and before the clear on the negedge inside p[N+1].
    // That is the read-then-clear ordering the analog version got backwards, and
    // here it follows from the phase register rather than from a constant.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            code <= {N{1'b0}};
            eoc  <= 1'b0;
        end else begin
            eoc <= p[N];                        // asserted throughout p[N+1]
            if (p[N]) code <= q;
        end
    end

    // code[0] is the MSB; reverse for a conventionally weighted word.
    generate
        for (b = 0; b < N; b = b + 1) begin : g_bin
            assign code_bin[b] = code[N-1-b];
        end
    endgenerate

`ifdef SAR_ASSERT
    // The three orderings the analog version violated. Stated once, checked
    // every cycle, rather than re-derived by hand per resolution.
    always @(posedge clk) if (rst_n) begin
        // exactly one phase active
        if ($countones(p) !== 1)
            $error("phase register is not one-hot: %b", p);
        // the clear phase never coincides with a trial phase
        if (p[PH_READ] && (|p[N:1]))
            $error("read phase overlaps a trial phase");
    end

    // the last trial must capture before the clear phase begins
    always @(negedge clk) if (rst_n && p[N])
        if (p[PH_READ]) $error("LSB capture and clear in the same phase");
`endif

endmodule

`default_nettype wire
