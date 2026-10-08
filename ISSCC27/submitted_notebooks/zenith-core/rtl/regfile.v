`default_nettype none

// Banco de Registros

module regfile (
    input  wire       clk,
    input  wire       rst_n,

    // Puerto de lectura A
    input  wire [2:0] rs1_addr,
    output wire [7:0] rs1_data,

    // Puerto de lectura B
    input  wire [2:0] rs2_addr,
    output wire [7:0] rs2_data,

    // Puerto de escritura
    input  wire [2:0] rd_addr,
    input  wire [7:0] rd_data,
    input  wire       rd_we        // Write enable
);

    reg [7:0] regs [0:7];          // 8 registros de 8 bits

    // Lectura combinacional; r0 siempre devuelve 0 como en RISC V
    assign rs1_data = (rs1_addr == 3'd0) ? 8'h00 : regs[rs1_addr];
    assign rs2_data = (rs2_addr == 3'd0) ? 8'h00 : regs[rs2_addr];

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < 8; i = i + 1)
                regs[i] <= 8'h00;
        end else if (rd_we && rd_addr != 3'd0) begin
            regs[rd_addr] <= rd_data;
        end
    end

endmodule

`default_nettype wire
