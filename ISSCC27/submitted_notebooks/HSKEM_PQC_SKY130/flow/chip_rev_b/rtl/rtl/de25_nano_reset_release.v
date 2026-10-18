// Agilex 5 Reset Release integration.
// The Altera Reset Release endpoint exposes nINIT_DONE as an active-high
// configuration reset. It stays high until the SDM reports that the complete
// device has entered user mode. The behavioural branch keeps board-wrapper
// simulation independent from the Quartus device library.

module de25_nano_reset_release (

    output wire config_reset

);

`ifdef SYNTHESIS
    de25_reset_release u_reset_release (
        .conf_reset_out_0 (config_reset)
    );
`else
    assign config_reset = 1'b0;
`endif

endmodule

// Assert reset immediately, then release it only after two CLOCK1_50 edges.
// This is the reset-domain-crossing boundary between the board/configuration
// signals and the synchronous TrustEdge core.
module de25_nano_reset_sync (
    input  wire clk,
    input  wire reset_n_in,
    output wire reset_n_out
);

    (* ASYNC_REG = "TRUE" *) reg [1:0] release_ff;

    always @(posedge clk or negedge reset_n_in) begin
        if (!reset_n_in)
            release_ff <= 2'b00;
        else
            release_ff <= {release_ff[0], 1'b1};
    end

    assign reset_n_out = release_ff[1];

endmodule
