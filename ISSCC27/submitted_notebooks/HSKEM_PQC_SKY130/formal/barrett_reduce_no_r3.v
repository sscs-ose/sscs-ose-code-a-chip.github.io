// ============================================================================
// barrett_reduce.v
// ----------------------------------------------------------------------------
// Rut gon Barrett mod q = 3329 (modulus cua Kyber / ML-KEM) cho dau vao 24-bit.
//
// Dau vao a nam trong [0, 2^24). Du de chua tich cua hai he so da rut gon:
//   max = 3328 * 3328 = 11075584 < 2^24 = 16777216.
//
// Thuat toan Barrett (khong dung phep chia phan cung):
//   M = floor(2^24 / q) = 5039
//   t = (a * M) >> 24        // uoc luong thuong, luon <= a/q (khong vuot)
//   r0 = a - t*q             // r0 >= 0 (vi t*q <= a)
//   sau do tru bu toi da 3 lan de dua ve [0, q)
//
// Module thuan to hop (combinational).
// ============================================================================
module barrett_reduce #(
    parameter integer Q = 3329
) (
    input  wire [23:0] a,
    output wire [11:0] r   // ket qua trong [0, 3328], vua 12 bit
);
    // M = floor(2^24 / 3329) = 5039
    localparam integer M = 5039;

    // a (24 bit) * M (13 bit) -> can 37 bit
    wire [36:0] prod = a * M[12:0];

    // uoc luong thuong t = floor(a*M / 2^24), t <= 5039 -> 13 bit
    wire [12:0] t = prod[36:24];

    // t * q -> toi da 5039*3329 = 16774831 < 2^25
    wire [24:0] tq = t * Q[11:0];

    // r0 = a - t*q, dam bao khong am vi t*q <= a
    wire [24:0] r0 = {1'b0, a} - tq;

    // tru bu toi da 3 lan (du vi sai so uoc luong < 3q)
    wire [24:0] r1 = (r0 >= Q) ? (r0 - Q) : r0;
    wire [24:0] r2 = (r1 >= Q) ? (r1 - Q) : r1;
    wire [24:0] r3 = r2;  // MUTANT: third correction removed

    assign r = r3[11:0];
endmodule
