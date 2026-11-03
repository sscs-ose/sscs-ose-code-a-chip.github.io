// HSM-4D1 public secure sketch for a 192-bit private PUF response.
//
// Twelve independent extended-Hamming parity checks cover 16 bits each.
// Each 5-bit public helper corrects one bit in its own block and detects every
// two-bit error in that block.  A root-derived verifier in puf_root_service is
// still mandatory because larger error patterns can alias a valid syndrome.
module puf_secded_sketch (
    input  wire [191:0] enroll_response,
    input  wire [191:0] noisy_response,
    input  wire [59:0]  helper_in,
    output reg  [59:0]  helper_enroll,
    output reg  [191:0] corrected_response,
    output reg  [4:0]   corrected_blocks,
    output reg          uncorrectable
);
    function automatic [4:0] syndrome16;
        input [15:0] value;
        integer bit_index;
        reg [3:0] position_xor;
        reg overall;
        begin
            position_xor = 4'd0;
            overall = 1'b0;
            for (bit_index = 0; bit_index < 16; bit_index = bit_index + 1) begin
                if (value[bit_index]) begin
                    overall = overall ^ 1'b1;
                    if (bit_index < 15)
                        position_xor = position_xor ^ (bit_index + 1);
                end
            end
            syndrome16 = {overall, position_xor};
        end
    endfunction

    integer block_index;
    reg [15:0] noisy_block;
    reg [4:0] delta;
    reg [15:0] fixed_block;
    always @* begin
        helper_enroll = 60'd0;
        corrected_response = noisy_response;
        corrected_blocks = 5'd0;
        uncorrectable = 1'b0;
        noisy_block = 16'd0;
        delta = 5'd0;
        fixed_block = 16'd0;

        for (block_index = 0; block_index < 12; block_index = block_index + 1) begin
            helper_enroll[block_index*5 +: 5] =
                syndrome16(enroll_response[block_index*16 +: 16]);
            noisy_block = noisy_response[block_index*16 +: 16];
            delta = syndrome16(noisy_block) ^ helper_in[block_index*5 +: 5];
            fixed_block = noisy_block;

            if (delta != 5'd0) begin
                if (delta[4]) begin
                    // low=0 identifies the sixteenth/overall-parity bit;
                    // low=1..15 identifies that one-based data position.
                    if (delta[3:0] == 4'd0)
                        fixed_block[15] = ~fixed_block[15];
                    else
                        fixed_block[delta[3:0]-1'b1] =
                            ~fixed_block[delta[3:0]-1'b1];
                    corrected_blocks = corrected_blocks + 5'd1;
                end else begin
                    // Non-zero position syndrome with even overall parity is
                    // the guaranteed two-bit detection case.
                    uncorrectable = 1'b1;
                end
            end
            corrected_response[block_index*16 +: 16] = fixed_block;
        end
    end
endmodule
