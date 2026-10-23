// Compact 0x3A/0x3B service for HSM-4D0 characterization.
// It is intentionally outside hsm_shell so repeated measurements do not alter
// vault/session/replay/audit state.
module puf_char_service (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         cmd_valid,
    input  wire         header_valid,
    input  wire         provision_enable,
    input  wire [7:0]   api_version,
    input  wire [7:0]   subcmd,
    input  wire [7:0]   flags,
    input  wire [31:0]  counter,
    input  wire [7:0]   data_len,
    input  wire [255:0] data,
    output reg          done,
    output reg  [7:0]   response_len,
    output reg  [255:0] response_data
);
    localparam [7:0] EXT_API_VERSION = 8'h01;
    localparam [7:0] SUB_PUF_CHAR     = 8'h40;
    localparam [7:0] MODE_INFO        = 8'h00;
    localparam [7:0] MODE_SAMPLE      = 8'h01;
    localparam [7:0] RESULT_OK             = 8'h00;
    localparam [7:0] RESULT_BAD_LENGTH     = 8'h04;
    localparam [7:0] RESULT_POLICY_DENIED  = 8'h09;
    localparam [7:0] RESULT_BAD_COMMAND    = 8'h7F;

    reg engine_start;
    reg [1:0] engine_bank;
    wire engine_busy;
    wire engine_done;
    wire [63:0] engine_raw;
    wire [15:0] engine_min_delta;
    wire [15:0] engine_max_delta;
    wire [7:0] engine_health;
    wire engine_physical;
    wire [31:0] engine_cycles;

    reg waiting_sample;
    reg [31:0] pending_counter;
    reg [1:0] pending_bank;

    puf_char_engine u_engine (
        .clk(clk), .rst_n(rst_n), .scrub(1'b0),
        .start(engine_start), .bank_id(engine_bank),
        .private_mode(1'b0),
        .busy(engine_busy), .done(engine_done), .raw_response(engine_raw),
        .min_abs_delta(engine_min_delta), .max_abs_delta(engine_max_delta),
        .health_flags(engine_health), .physical_backend(engine_physical),
        .measurement_cycles(engine_cycles)
    );

    task automatic set_common_header;
        input [7:0] result;
        input [31:0] tx_counter;
        begin
            response_data <= 256'd0;
            response_data[255:248] <= EXT_API_VERSION;
            response_data[247:240] <= SUB_PUF_CHAR;
            response_data[239:232] <= result;
            response_data[231:200] <= tx_counter;
        end
    endtask

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            done <= 1'b0;
            response_len <= 8'd0;
            response_data <= 256'd0;
            engine_start <= 1'b0;
            engine_bank <= 2'd0;
            waiting_sample <= 1'b0;
            pending_counter <= 32'd0;
            pending_bank <= 2'd0;
        end else begin
            done <= 1'b0;
            engine_start <= 1'b0;

            if (cmd_valid && !waiting_sample) begin
                if (!header_valid || api_version != EXT_API_VERSION ||
                    subcmd != SUB_PUF_CHAR || flags != 8'd0) begin
                    set_common_header(RESULT_BAD_COMMAND, counter);
                    response_len <= 8'd7;
                    done <= 1'b1;
                end else if (data_len < 8'd1) begin
                    set_common_header(RESULT_BAD_LENGTH, counter);
                    response_len <= 8'd7;
                    done <= 1'b1;
                end else if (data[255:248] == MODE_INFO) begin
                    if (data_len != 8'd1) begin
                        set_common_header(RESULT_BAD_LENGTH, counter);
                        response_len <= 8'd7;
                    end else begin
                        set_common_header(RESULT_OK, counter);
                        response_data[199:192] <= 8'd1;       // format
                        response_data[191:184] <= {7'd0, engine_physical};
                        response_data[183:176] <= 8'd4;       // banks
                        response_data[175:168] <= 8'd64;      // bits/bank
                        response_data[167:136] <= 32'd1024;   // window cycles/pair
                        response_data[135:104] <= 32'hD0400101; // architecture ID
                        response_len <= 8'd19;
                    end
                    done <= 1'b1;
                end else if (data[255:248] == MODE_SAMPLE) begin
                    if (data_len != 8'd2 || data[247:246] != 2'b00) begin
                        set_common_header(RESULT_BAD_LENGTH, counter);
                        response_len <= 8'd7;
                        done <= 1'b1;
                    end else if (!provision_enable) begin
                        set_common_header(RESULT_POLICY_DENIED, counter);
                        response_len <= 8'd7;
                        done <= 1'b1;
                    end else begin
                        engine_bank <= data[241:240];
                        pending_bank <= data[241:240];
                        pending_counter <= counter;
                        engine_start <= 1'b1;
                        waiting_sample <= 1'b1;
                    end
                end else begin
                    set_common_header(RESULT_BAD_COMMAND, counter);
                    response_len <= 8'd7;
                    done <= 1'b1;
                end
            end

            if (waiting_sample && engine_done) begin
                set_common_header(RESULT_OK, pending_counter);
                response_data[199:192] <= 8'd1;       // format
                response_data[191:184] <= {7'd0, engine_physical};
                response_data[183:176] <= {6'd0, pending_bank};
                response_data[175:168] <= 8'd64;
                response_data[167:160] <= engine_health;
                response_data[159:96]  <= engine_raw;
                response_data[95:80]   <= engine_min_delta;
                response_data[79:64]   <= engine_max_delta;
                response_data[63:32]   <= engine_cycles;
                response_len <= 8'd28;
                done <= 1'b1;
                waiting_sample <= 1'b0;
            end
        end
    end
endmodule
