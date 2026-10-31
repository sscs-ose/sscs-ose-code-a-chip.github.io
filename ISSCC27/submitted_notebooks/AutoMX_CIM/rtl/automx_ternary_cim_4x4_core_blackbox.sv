// Physical transistor-core contract. Pin names/order match the Stage-4 SPICE
// subcircuit automx_ternary_cim_4x4_core exactly. This is not the clocked
// controller wrapper and must not expose the wrapper handshake interface.
`default_nettype none
(* blackbox *)
module automx_ternary_cim_4x4_core (
    inout wire BLP0, BLN0, BLP1, BLN1, BLP2, BLN2, BLP3, BLN3,
    input wire WLP0, WLN0, WLP1, WLN1, WLP2, WLN2, WLP3, WLN3,
    input wire WPOS_0_0, WNEG_0_0, WPOS_0_1, WNEG_0_1,
    input wire WPOS_0_2, WNEG_0_2, WPOS_0_3, WNEG_0_3,
    input wire WPOS_1_0, WNEG_1_0, WPOS_1_1, WNEG_1_1,
    input wire WPOS_1_2, WNEG_1_2, WPOS_1_3, WNEG_1_3,
    input wire WPOS_2_0, WNEG_2_0, WPOS_2_1, WNEG_2_1,
    input wire WPOS_2_2, WNEG_2_2, WPOS_2_3, WNEG_2_3,
    input wire WPOS_3_0, WNEG_3_0, WPOS_3_1, WNEG_3_1,
    input wire WPOS_3_2, WNEG_3_2, WPOS_3_3, WNEG_3_3,
    inout wire VGND,
    inout wire VSUBS
);
endmodule
`default_nettype wire