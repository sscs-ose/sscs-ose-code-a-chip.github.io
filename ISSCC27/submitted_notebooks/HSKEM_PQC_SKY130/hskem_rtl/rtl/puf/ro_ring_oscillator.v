// Physical ring oscillator used by the HSM-4D0 characterization checkpoint
// and the private HSM-4D1 reconstruction build.  The synthesis path is
// intentionally a combinational loop.  ModelSim never elaborates this module
// because puf_char_engine has a deterministic controller fallback.
module ro_ring_oscillator #(
    parameter integer STAGES = 5
) (
    input  wire enable,
    output wire ro_out
);
    // `keep` is the Quartus attribute for combinational nodes.  Do not replace
    // it with `preserve`, which applies to registers rather than this RO chain.
    (* keep = "true" *) wire [STAGES-1:0] ring;

    assign ring[0] = enable ? ~ring[STAGES-1] : 1'b0;

    genvar stage_index;
    generate
        for (stage_index = 1; stage_index < STAGES; stage_index = stage_index + 1) begin : g_stage
            assign ring[stage_index] = ~ring[stage_index-1];
        end
    endgenerate

    assign ro_out = ring[STAGES-1];
endmodule
