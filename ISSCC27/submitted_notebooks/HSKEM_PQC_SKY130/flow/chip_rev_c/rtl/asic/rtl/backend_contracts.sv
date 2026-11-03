// ASIC-V0 technology contracts. These modules are intentionally empty
// black boxes during A1 logic synthesis. A2 must replace each used instance
// with a characterized macro/model and verify the locked protocol semantics.

(* blackbox *) module te_puf_backend #(
    parameter integer PAIR_COUNT = 256,
    parameter integer BITS_PER_BANK = 64
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        scrub,
    input  wire        start,
    input  wire [1:0]  bank_id,
    input  wire        private_mode,
    output wire        busy,
    output wire        done,
    output wire [63:0] response,
    output wire [15:0] min_delta,
    output wire [15:0] max_delta,
    output wire [7:0]  health,
    output wire [31:0] cycles
);
endmodule

(* blackbox *) module te_puf_session_backend #(
    parameter integer ID_BITS = 32
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               enroll,
    input  wire               verify,
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
endmodule

(* blackbox *) module te_entropy_backend #(
    parameter integer WIDTH = 32
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
endmodule

(* blackbox *) module te_identity_backend (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        request,
    input  wire        zeroize,
    output wire        ready,
    output wire [7:0]  error,
    output wire [63:0] public_id
);
endmodule

// Parameterized SRAM contracts. A1 may leave these as black boxes only after
// the source memories are migrated to the matching one-cycle-latency wrapper.
// M3 replaces only this contract with the audited SKY130 macro binding in its
// ASIC-only source set.  The FPGA build never reads this file.
`ifndef TRUSTEDGE_ASIC_MACRO_BIND
(* blackbox *) module te_sram_1rw #(
    parameter integer WIDTH = 32,
    parameter integer DEPTH = 256,
    parameter integer ADDR_WIDTH = 8
) (
    input  wire                  clk,
    input  wire                  we,
    input  wire [ADDR_WIDTH-1:0] addr,
    input  wire [WIDTH-1:0]      wdata,
    output wire [WIDTH-1:0]      rdata
);
endmodule
`endif

(* blackbox *) module te_sram_1r1w #(
    parameter integer WIDTH = 32,
    parameter integer DEPTH = 256,
    parameter integer ADDR_WIDTH = 8
) (
    input  wire                  clk,
    input  wire                  we,
    input  wire [ADDR_WIDTH-1:0] waddr,
    input  wire [WIDTH-1:0]      wdata,
    input  wire [ADDR_WIDTH-1:0] raddr,
    output wire [WIDTH-1:0]      rdata
);
endmodule

(* blackbox *) module te_sram_2rw #(
    parameter integer WIDTH = 32,
    parameter integer DEPTH = 256,
    parameter integer ADDR_WIDTH = 8
) (
    input  wire                  clk,
    input  wire                  a_we,
    input  wire [ADDR_WIDTH-1:0] a_addr,
    input  wire [WIDTH-1:0]      a_wdata,
    output wire [WIDTH-1:0]      a_rdata,
    input  wire                  b_we,
    input  wire [ADDR_WIDTH-1:0] b_addr,
    input  wire [WIDTH-1:0]      b_wdata,
    output wire [WIDTH-1:0]      b_rdata
);
endmodule

(* blackbox *) module te_sram_1w2r #(
    parameter integer WIDTH = 32,
    parameter integer DEPTH = 256,
    parameter integer ADDR_WIDTH = 8
) (
    input  wire                  clk,
    input  wire                  we,
    input  wire [ADDR_WIDTH-1:0] waddr,
    input  wire [WIDTH-1:0]      wdata,
    input  wire [ADDR_WIDTH-1:0] raddr_a,
    output wire [WIDTH-1:0]      rdata_a,
    input  wire [ADDR_WIDTH-1:0] raddr_b,
    output wire [WIDTH-1:0]      rdata_b
);
endmodule

(* blackbox *) module te_sram_1rw_be #(
    parameter integer WIDTH = 64,
    parameter integer DEPTH = 2048,
    parameter integer ADDR_WIDTH = 11,
    parameter integer BYTE_COUNT = WIDTH / 8
) (
    input  wire                    clk,
    input  wire                    we,
    input  wire [BYTE_COUNT-1:0]   be,
    input  wire [ADDR_WIDTH-1:0]   addr,
    input  wire [WIDTH-1:0]        wdata,
    output wire [WIDTH-1:0]        rdata
);
endmodule
