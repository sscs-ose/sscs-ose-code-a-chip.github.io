module sha_core(
    input logic clk, 
    input logic rst_n,
    input logic [511:0] block,
    input logic done,
    input logic sha_valid,
    output logic scheduler_ready,
    output logic [255:0] digest,
    output logic digest_valid
);
    timeunit 1ns;
    timeprecision 1ps;
    // interfaces 

    logic [31:0] k_t;
    logic [31:0] w_t;
    logic [5:0] round;
    logic load_block, next_round;

    logic new_block;
    assign new_block = sha_valid & scheduler_ready;

    // submodule instantiation

    hashing_core hash_core(.*);
    message_scheduler scheduler(.*);
    sha_256_constants round_constants(.*);

endmodule