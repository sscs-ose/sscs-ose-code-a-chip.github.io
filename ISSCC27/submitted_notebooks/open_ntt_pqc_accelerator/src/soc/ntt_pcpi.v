// ---------------------------------------------------------------------------
// ntt_pcpi : PicoRV32 PCPI Custom-Instruction Decoder (N3)
//
// Decodes RISC-V `custom0` (opcode 7'b0001011) instructions for OpenNTT:
//   - rs1: base pointer to polynomial in shared memory
//   - rs2: operation code (0=NTT, 1=NTTB, 2=INTT, 3=PWM, etc.)
//   - rd: returns execution cycle count upon completion
// ---------------------------------------------------------------------------
module ntt_pcpi (
    input  wire        clk,
    input  wire        rst_n,

    // PicoRV32 PCPI Interface
    input  wire        pcpi_valid,
    input  wire [31:0] pcpi_insn,
    input  wire [31:0] pcpi_rs1,
    input  wire [31:0] pcpi_rs2,
    output reg         pcpi_wr,
    output reg  [31:0] pcpi_rd,
    output wire        pcpi_wait,
    output reg         pcpi_ready,

    // OpenNTT Accelerator Control Interface
    output reg         acc_start,
    output reg  [2:0]  acc_op,
    output reg  [31:0] acc_ptr,
    input  wire        acc_done,
    input  wire [31:0] acc_cycles
);

    // RISC-V opcode custom0 = 7'b0001011 (0x0B)
    wire is_custom0 = pcpi_valid && (pcpi_insn[6:0] == 7'b0001011);

    localparam S_IDLE = 2'd0, S_START = 2'd1, S_EXEC = 2'd2, S_FIN = 2'd3;
    reg [1:0] state;

    assign pcpi_wait = (state == S_EXEC) || (state == S_IDLE && is_custom0);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state      <= S_IDLE;
            pcpi_wr    <= 1'b0;
            pcpi_rd    <= 32'd0;
            pcpi_ready <= 1'b0;
            acc_start  <= 1'b0;
            acc_op     <= 3'd0;
            acc_ptr    <= 32'd0;
        end else begin
            pcpi_ready <= 1'b0;
            acc_start  <= 1'b0;

            case (state)
                S_IDLE: begin
                    pcpi_wr <= 1'b0;
                    if (is_custom0) begin
                        acc_op    <= pcpi_rs2[2:0];
                        acc_ptr   <= pcpi_rs1;
                        acc_start <= 1'b1;
                        state     <= S_EXEC;
                    end
                end

                S_EXEC: begin
                    if (acc_done) begin
                        pcpi_ready <= 1'b1;
                        pcpi_wr    <= 1'b1;
                        pcpi_rd    <= acc_cycles;
                        state      <= S_IDLE;
                    end
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
