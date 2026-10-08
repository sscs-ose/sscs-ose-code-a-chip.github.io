module sdm_chipid_client #(
    parameter integer STARTUP_DELAY_CYCLES = 1024,
    parameter integer TIMEOUT_CYCLES = 5_000_000
) (
    input  wire        clk,
    input  wire        rst_n,

    output reg  [3:0]  avmm_address,
    output reg         avmm_write,
    output reg  [31:0] avmm_writedata,
    output reg         avmm_read,
    input  wire [31:0] avmm_readdata,
    input  wire        avmm_readdatavalid,
    input  wire        avmm_waitrequest,
    input  wire        mailbox_irq,

    output reg         busy,
    output reg         ready,
    output reg  [7:0]  error_code,
    output reg  [63:0] chip_id
);
    // Public SDM Mailbox command: GET_CHIPID (0x12), no arguments. Client ID
    // 1 is carried in header bits [27:24]. The response contains two words,
    // least-significant word first.
    localparam [31:0] GET_CHIPID_HEADER = 32'h0100_0012;

    localparam [4:0] ST_STARTUP          = 5'd0;
    localparam [4:0] ST_CMD_INFO_REQ     = 5'd1;
    localparam [4:0] ST_CMD_INFO_DATA    = 5'd2;
    localparam [4:0] ST_WRITE_CMD        = 5'd3;
    localparam [4:0] ST_ISR_REQ          = 5'd4;
    localparam [4:0] ST_ISR_DATA         = 5'd5;
    localparam [4:0] ST_HEADER_INFO_REQ  = 5'd6;
    localparam [4:0] ST_HEADER_INFO_DATA = 5'd7;
    localparam [4:0] ST_HEADER_REQ       = 5'd8;
    localparam [4:0] ST_HEADER_DATA      = 5'd9;
    localparam [4:0] ST_WORD0_INFO_REQ   = 5'd10;
    localparam [4:0] ST_WORD0_INFO_DATA  = 5'd11;
    localparam [4:0] ST_WORD0_REQ        = 5'd12;
    localparam [4:0] ST_WORD0_DATA       = 5'd13;
    localparam [4:0] ST_WORD1_INFO_REQ   = 5'd14;
    localparam [4:0] ST_WORD1_INFO_DATA  = 5'd15;
    localparam [4:0] ST_WORD1_REQ        = 5'd16;
    localparam [4:0] ST_WORD1_DATA       = 5'd17;
    localparam [4:0] ST_DONE             = 5'd18;
    localparam [4:0] ST_ERROR            = 5'd19;

    // Stage-specific timeouts make the next hardware failure actionable.
    localparam [7:0] ERR_CMD_FIFO_TIMEOUT = 8'h11;
    localparam [7:0] ERR_ISR_TIMEOUT      = 8'h12;
    localparam [7:0] ERR_FIFO_TIMEOUT     = 8'h13;
    localparam [7:0] ERR_READ_TIMEOUT     = 8'h14;
    localparam [7:0] ERR_FIFO_FORMAT      = 8'h02;
    localparam [7:0] ERR_RESPONSE_ID      = 8'h03;
    localparam [7:0] ERR_RESPONSE_LEN     = 8'h04;
    localparam [7:0] ERR_ISR_STATUS       = 8'h05;

    reg [4:0]  state;
    reg [31:0] timer;
    reg        header_was_eop;

    wire [10:0] response_error = avmm_readdata[10:0];
    wire [10:0] response_length = avmm_readdata[22:12];
    wire [3:0]  response_id = avmm_readdata[27:24];
    wire [29:0] response_fifo_words = avmm_readdata[31:2];

    // IRQ is intentionally not used as the completion condition. The Mailbox
    // IP drives irq as ISR AND IER, and IER resets to zero. Altera's documented
    // polling flow reads ISR (address 8) bit DATA_VALID instead.
    wire unused_mailbox_irq = mailbox_irq;

    task automatic fail;
        input [7:0] code;
        begin
            busy       <= 1'b0;
            ready      <= 1'b0;
            error_code <= code;
            avmm_write <= 1'b0;
            avmm_read  <= 1'b0;
            state      <= ST_ERROR;
        end
    endtask

    task automatic wait_or_timeout;
        input [7:0] code;
        begin
            if (timer + 32'd1 >= TIMEOUT_CYCLES)
                fail(code);
            else
                timer <= timer + 32'd1;
        end
    endtask

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state          <= ST_STARTUP;
            timer          <= 32'd0;
            avmm_address   <= 4'd0;
            avmm_write     <= 1'b0;
            avmm_writedata <= 32'd0;
            avmm_read      <= 1'b0;
            busy           <= 1'b1;
            ready          <= 1'b0;
            error_code     <= 8'd0;
            chip_id        <= 64'd0;
            header_was_eop <= 1'b0;
        end else begin
            case (state)
                ST_STARTUP: begin
                    busy <= 1'b1;
                    if (timer + 32'd1 >= STARTUP_DELAY_CYCLES) begin
                        timer        <= 32'd0;
                        avmm_address <= 4'd2; // command FIFO empty space
                        avmm_read    <= 1'b1;
                        state        <= ST_CMD_INFO_REQ;
                    end else begin
                        timer <= timer + 32'd1;
                    end
                end

                ST_CMD_INFO_REQ: begin
                    if (!avmm_waitrequest) begin
                        avmm_read <= 1'b0;
                        state     <= ST_CMD_INFO_DATA;
                    end else begin
                        wait_or_timeout(ERR_CMD_FIFO_TIMEOUT);
                    end
                end

                ST_CMD_INFO_DATA: begin
                    if (avmm_readdatavalid) begin
                        if (avmm_readdata != 32'd0) begin
                            timer          <= 32'd0;
                            avmm_address   <= 4'd1; // command last-word/EOP
                            avmm_writedata <= GET_CHIPID_HEADER;
                            avmm_write     <= 1'b1;
                            state          <= ST_WRITE_CMD;
                        end else begin
                            avmm_address <= 4'd2;
                            avmm_read    <= 1'b1;
                            state        <= ST_CMD_INFO_REQ;
                            wait_or_timeout(ERR_CMD_FIFO_TIMEOUT);
                        end
                    end else begin
                        wait_or_timeout(ERR_CMD_FIFO_TIMEOUT);
                    end
                end

                ST_WRITE_CMD: begin
                    if (!avmm_waitrequest) begin
                        avmm_write   <= 1'b0;
                        timer        <= 32'd0;
                        avmm_address <= 4'd8; // interrupt status
                        avmm_read    <= 1'b1;
                        state        <= ST_ISR_REQ;
                    end else begin
                        wait_or_timeout(ERR_CMD_FIFO_TIMEOUT);
                    end
                end

                ST_ISR_REQ: begin
                    if (!avmm_waitrequest) begin
                        avmm_read <= 1'b0;
                        state     <= ST_ISR_DATA;
                    end else begin
                        wait_or_timeout(ERR_ISR_TIMEOUT);
                    end
                end

                ST_ISR_DATA: begin
                    if (avmm_readdatavalid) begin
                        // Bits 9,8,5,4,3 are fatal for this non-crypto flow.
                        if (avmm_readdata[9] || avmm_readdata[8] ||
                            avmm_readdata[5] || avmm_readdata[4] ||
                            avmm_readdata[3]) begin
                            fail(ERR_ISR_STATUS);
                        end else if (avmm_readdata[0]) begin
                            timer        <= 32'd0;
                            avmm_address <= 4'd6; // response FIFO info
                            avmm_read    <= 1'b1;
                            state        <= ST_HEADER_INFO_REQ;
                        end else begin
                            avmm_address <= 4'd8;
                            avmm_read    <= 1'b1;
                            state        <= ST_ISR_REQ;
                            wait_or_timeout(ERR_ISR_TIMEOUT);
                        end
                    end else begin
                        wait_or_timeout(ERR_ISR_TIMEOUT);
                    end
                end

                ST_HEADER_INFO_REQ, ST_WORD0_INFO_REQ, ST_WORD1_INFO_REQ: begin
                    if (!avmm_waitrequest) begin
                        avmm_read <= 1'b0;
                        if (state == ST_HEADER_INFO_REQ)
                            state <= ST_HEADER_INFO_DATA;
                        else if (state == ST_WORD0_INFO_REQ)
                            state <= ST_WORD0_INFO_DATA;
                        else
                            state <= ST_WORD1_INFO_DATA;
                    end else begin
                        wait_or_timeout(ERR_FIFO_TIMEOUT);
                    end
                end

                ST_HEADER_INFO_DATA: begin
                    if (avmm_readdatavalid) begin
                        if (response_fifo_words == 0) begin
                            avmm_address <= 4'd6;
                            avmm_read    <= 1'b1;
                            state        <= ST_HEADER_INFO_REQ;
                            wait_or_timeout(ERR_FIFO_TIMEOUT);
                        end else if (!avmm_readdata[0]) begin
                            fail(ERR_FIFO_FORMAT);
                        end else begin
                            header_was_eop <= avmm_readdata[1];
                            timer          <= 32'd0;
                            avmm_address   <= 4'd5; // response header
                            avmm_read      <= 1'b1;
                            state          <= ST_HEADER_REQ;
                        end
                    end else begin
                        wait_or_timeout(ERR_FIFO_TIMEOUT);
                    end
                end

                ST_HEADER_REQ, ST_WORD0_REQ, ST_WORD1_REQ: begin
                    if (!avmm_waitrequest) begin
                        avmm_read <= 1'b0;
                        if (state == ST_HEADER_REQ)
                            state <= ST_HEADER_DATA;
                        else if (state == ST_WORD0_REQ)
                            state <= ST_WORD0_DATA;
                        else
                            state <= ST_WORD1_DATA;
                    end else begin
                        wait_or_timeout(ERR_READ_TIMEOUT);
                    end
                end

                ST_HEADER_DATA: begin
                    if (avmm_readdatavalid) begin
                        if (response_error != 11'd0) begin
                            fail(8'h80 | avmm_readdata[6:0]);
                        end else if (response_id != 4'd1) begin
                            fail(ERR_RESPONSE_ID);
                        end else if (response_length != 11'd2) begin
                            fail(ERR_RESPONSE_LEN);
                        end else if (header_was_eop) begin
                            fail(ERR_FIFO_FORMAT);
                        end else begin
                            timer        <= 32'd0;
                            avmm_address <= 4'd6;
                            avmm_read    <= 1'b1;
                            state        <= ST_WORD0_INFO_REQ;
                        end
                    end else begin
                        wait_or_timeout(ERR_READ_TIMEOUT);
                    end
                end

                ST_WORD0_INFO_DATA: begin
                    if (avmm_readdatavalid) begin
                        if (response_fifo_words == 0) begin
                            avmm_address <= 4'd6;
                            avmm_read    <= 1'b1;
                            state        <= ST_WORD0_INFO_REQ;
                            wait_or_timeout(ERR_FIFO_TIMEOUT);
                        end else if (avmm_readdata[0] || avmm_readdata[1]) begin
                            fail(ERR_FIFO_FORMAT);
                        end else begin
                            timer        <= 32'd0;
                            avmm_address <= 4'd5;
                            avmm_read    <= 1'b1;
                            state        <= ST_WORD0_REQ;
                        end
                    end else begin
                        wait_or_timeout(ERR_FIFO_TIMEOUT);
                    end
                end

                ST_WORD0_DATA: begin
                    if (avmm_readdatavalid) begin
                        chip_id[31:0] <= avmm_readdata;
                        timer         <= 32'd0;
                        avmm_address  <= 4'd6;
                        avmm_read     <= 1'b1;
                        state         <= ST_WORD1_INFO_REQ;
                    end else begin
                        wait_or_timeout(ERR_READ_TIMEOUT);
                    end
                end

                ST_WORD1_INFO_DATA: begin
                    if (avmm_readdatavalid) begin
                        if (response_fifo_words == 0) begin
                            avmm_address <= 4'd6;
                            avmm_read    <= 1'b1;
                            state        <= ST_WORD1_INFO_REQ;
                            wait_or_timeout(ERR_FIFO_TIMEOUT);
                        end else if (avmm_readdata[0] || !avmm_readdata[1]) begin
                            fail(ERR_FIFO_FORMAT);
                        end else begin
                            timer        <= 32'd0;
                            avmm_address <= 4'd5;
                            avmm_read    <= 1'b1;
                            state        <= ST_WORD1_REQ;
                        end
                    end else begin
                        wait_or_timeout(ERR_FIFO_TIMEOUT);
                    end
                end

                ST_WORD1_DATA: begin
                    if (avmm_readdatavalid) begin
                        chip_id[63:32] <= avmm_readdata;
                        busy           <= 1'b0;
                        ready          <= 1'b1;
                        error_code     <= 8'd0;
                        timer          <= 32'd0;
                        state          <= ST_DONE;
                    end else begin
                        wait_or_timeout(ERR_READ_TIMEOUT);
                    end
                end

                ST_DONE: begin
                    busy       <= 1'b0;
                    ready      <= 1'b1;
                    avmm_write <= 1'b0;
                    avmm_read  <= 1'b0;
                end

                default: fail(error_code == 8'd0 ? ERR_READ_TIMEOUT : error_code);
            endcase
        end
    end
endmodule
