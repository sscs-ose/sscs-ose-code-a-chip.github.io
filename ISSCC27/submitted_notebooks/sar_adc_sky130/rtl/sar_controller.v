// SPDX-License-Identifier: Apache-2.0
//
// sar_controller -- an NCH-channel SAR controller: NCH independent sequencers
// sharing one phase clock, reset and start.
//
// Why this exists. A single sar_sequencer is 79 Nangate45 cells and gives a
// 17.86 um core, which is below the geometry the OpenLayout flow scripts assume:
// detail_place aborts with PDN-0185 because the hardcoded 20 um power-strap
// offset does not fit inside the die. The benchmark designs that flow targets
// (BlackParrot, Ariane, ethernet) are thousands to hundreds of thousands of
// cells. This wrapper reaches that range with a real structure rather than
// padding: multi-channel SAR converters are ordinary, and every channel here is
// the same sequencer that drives the 8-bit converter in this project.
//
// Sharing, and what is NOT shared. clk, rst_n and start are common, so all
// channels convert in lockstep -- that is the usual arrangement when one timing
// generator serves an array. Each channel keeps its own comparator input and
// its own DAC drive, because those are per-channel analog.
//
// Pin budget. NCH*N DAC lines have to leave the block (they drive NCH physical
// capacitor arrays) so d is flattened and exposed. The conversion results do NOT
// need that bandwidth -- they are read back over a shared bus -- so code is
// multiplexed behind ch_sel. That keeps the port count at 3 + NCH + $clog2(NCH)
// inputs and NCH*N + N + NCH outputs instead of 2*NCH*N.

`default_nettype none

module sar_controller #(
    parameter integer N   = 8,          // bits per channel
    parameter integer NCH = 16          // channels
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    start,
    input  wire [NCH-1:0]          cmp,        // one comparator per channel
    input  wire [$clog2(NCH)-1:0]  ch_sel,     // which channel's code to read

    output wire [NCH*N-1:0]        d,          // flattened DAC drive, channel-major
    output wire [N-1:0]            code_bin,   // selected channel, conventional weighting
    output wire [NCH-1:0]          eoc
);

    generate
        if (NCH < 2) begin : g_bad_nch
            illegal_parameter_NCH_must_be_at_least_2 err();
        end
    endgenerate

    wire [N-1:0] code_bin_ch [0:NCH-1];

    genvar c;
    generate
        for (c = 0; c < NCH; c = c + 1) begin : g_ch
            sar_sequencer #(.N(N)) u_seq (
                .clk      (clk),
                .rst_n    (rst_n),
                .start    (start),
                .cmp      (cmp[c]),
                .d        (d[c*N +: N]),
                .phase    (),                  // per-channel observability not brought out
                .code     (),
                .code_bin (code_bin_ch[c]),
                .eoc      (eoc[c])
            );
        end
    endgenerate

    // Read-back mux. Registered would add a cycle to a path that has a whole
    // conversion to settle in; combinational is the honest choice here and the
    // SDC budgets it as an ordinary output.
    assign code_bin = code_bin_ch[ch_sel];

endmodule

`default_nettype wire
