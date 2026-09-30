module sdm_crypto_axi_ram #(
    parameter integer ADDR_WIDTH = 14
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         zeroize,

    input  wire [3:0]   s_axi_awid,
    input  wire [31:0]  s_axi_awaddr,
    input  wire [7:0]   s_axi_awlen,
    input  wire [2:0]   s_axi_awsize,
    input  wire [1:0]   s_axi_awburst,
    input  wire         s_axi_awvalid,
    output wire         s_axi_awready,

    input  wire [63:0]  s_axi_wdata,
    input  wire [7:0]   s_axi_wstrb,
    input  wire         s_axi_wlast,
    input  wire         s_axi_wvalid,
    output wire         s_axi_wready,

    output reg  [3:0]   s_axi_bid,
    output reg  [1:0]   s_axi_bresp,
    output reg          s_axi_bvalid,
    input  wire         s_axi_bready,

    input  wire [3:0]   s_axi_arid,
    input  wire [31:0]  s_axi_araddr,
    input  wire [7:0]   s_axi_arlen,
    input  wire [2:0]   s_axi_arsize,
    input  wire [1:0]   s_axi_arburst,
    input  wire         s_axi_arvalid,
    output wire         s_axi_arready,

    output reg  [3:0]   s_axi_rid,
    output reg  [63:0]  s_axi_rdata,
    output reg  [1:0]   s_axi_rresp,
    output reg          s_axi_rlast,
    output reg          s_axi_rvalid,
    input  wire         s_axi_rready,

    output reg          ready,
    output reg  [7:0]   error_code
);
    localparam integer WORD_COUNT = (1 << (ADDR_WIDTH - 3));
    localparam [1:0] AXI_OKAY   = 2'b00;
    localparam [1:0] AXI_SLVERR = 2'b10;
    localparam [1:0] AXI_DECERR = 2'b11;

    reg [63:0] memory [0:WORD_COUNT-1];
    reg [ADDR_WIDTH-4:0] scrub_index;
    reg                  scrub_active;

    reg                  write_active;
    reg [3:0]            write_id;
    reg [31:0]           write_addr;
    reg [7:0]            write_beats_left;
    reg [2:0]            write_size;
    reg [1:0]            write_burst;
    reg                  write_error;

    reg                  read_active;
    reg [3:0]            read_id;
    reg [31:0]           read_addr;
    reg [7:0]            read_beats_left;
    reg [2:0]            read_size;
    reg [1:0]            read_burst;

    integer lane;

    function automatic address_in_range;
        input [31:0] address;
        begin
            address_in_range = (address[31:ADDR_WIDTH] == 0);
        end
    endfunction

    function automatic [31:0] next_address;
        input [31:0] address;
        input [2:0]  size;
        input [1:0]  burst;
        begin
            if (burst == 2'b01)
                next_address = address + (32'd1 << size);
            else
                next_address = address;
        end
    endfunction

    wire write_beat_error = !address_in_range(write_addr) ||
                            (write_size > 3) || write_burst[1];
    wire read_beat_error  = !address_in_range(read_addr) ||
                            (read_size > 3) || read_burst[1];
    wire memory_write_enable = scrub_active ||
                               (s_axi_wready && s_axi_wvalid &&
                                !write_beat_error);
    wire [ADDR_WIDTH-4:0] memory_write_index = scrub_active ? scrub_index :
                                                  write_addr[ADDR_WIDTH-1:3];
    wire [63:0] memory_write_data = scrub_active ? 64'd0 : s_axi_wdata;
    wire [7:0]  memory_write_strobe = scrub_active ? 8'hFF : s_axi_wstrb;

    assign s_axi_awready = ready && !write_active && !s_axi_bvalid;
    assign s_axi_wready  = ready && write_active && !s_axi_bvalid;
    assign s_axi_arready = ready && !read_active && !s_axi_rvalid;

    // Keep exactly one write process for the array so Quartus can infer M20K
    // block RAM. Reset/zeroize uses the same port as normal AXI writes.
    always @(posedge clk) begin
        if (memory_write_enable) begin
            for (lane = 0; lane < 8; lane = lane + 1)
                if (memory_write_strobe[lane])
                    memory[memory_write_index][lane*8 +: 8]
                        <= memory_write_data[lane*8 +: 8];
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            scrub_index      <= {ADDR_WIDTH-3{1'b0}};
            scrub_active     <= 1'b1;
            ready            <= 1'b0;
            error_code       <= 8'h00;
            write_active     <= 1'b0;
            write_id         <= 4'd0;
            write_addr       <= 32'd0;
            write_beats_left <= 8'd0;
            write_size       <= 3'd0;
            write_burst      <= 2'd0;
            write_error      <= 1'b0;
            s_axi_bid        <= 4'd0;
            s_axi_bresp      <= AXI_OKAY;
            s_axi_bvalid     <= 1'b0;
            read_active      <= 1'b0;
            read_id          <= 4'd0;
            read_addr        <= 32'd0;
            read_beats_left  <= 8'd0;
            read_size        <= 3'd0;
            read_burst       <= 2'd0;
            s_axi_rid        <= 4'd0;
            s_axi_rdata      <= 64'd0;
            s_axi_rresp      <= AXI_OKAY;
            s_axi_rlast      <= 1'b0;
            s_axi_rvalid     <= 1'b0;
        end else if (zeroize) begin
            scrub_index      <= {ADDR_WIDTH-3{1'b0}};
            scrub_active     <= 1'b1;
            ready            <= 1'b0;
            error_code       <= 8'h00;
            write_active     <= 1'b0;
            write_error      <= 1'b0;
            s_axi_bvalid     <= 1'b0;
            read_active      <= 1'b0;
            s_axi_rvalid     <= 1'b0;
        end else if (scrub_active) begin
            write_active        <= 1'b0;
            s_axi_bvalid        <= 1'b0;
            read_active         <= 1'b0;
            s_axi_rvalid        <= 1'b0;
            if (scrub_index == WORD_COUNT-1) begin
                scrub_active <= 1'b0;
                ready        <= 1'b1;
            end else begin
                scrub_index <= scrub_index + 1'b1;
            end
        end else begin
            if (s_axi_bvalid && s_axi_bready)
                s_axi_bvalid <= 1'b0;

            if (s_axi_awready && s_axi_awvalid) begin
                write_active     <= 1'b1;
                write_id         <= s_axi_awid;
                write_addr       <= s_axi_awaddr;
                write_beats_left <= s_axi_awlen;
                write_size       <= s_axi_awsize;
                write_burst      <= s_axi_awburst;
                write_error      <= 1'b0;
            end

            if (s_axi_wready && s_axi_wvalid) begin
                if (write_beat_error) begin
                    write_error <= 1'b1;
                    error_code  <= 8'h02;
                end

                if ((write_beats_left == 0) || s_axi_wlast) begin
                    write_active <= 1'b0;
                    s_axi_bid    <= write_id;
                    s_axi_bresp  <= (write_error || write_beat_error ||
                                     (s_axi_wlast != (write_beats_left == 0))) ?
                                    AXI_SLVERR : AXI_OKAY;
                    s_axi_bvalid <= 1'b1;
                    if (s_axi_wlast != (write_beats_left == 0))
                        error_code <= 8'h03;
                end else begin
                    write_beats_left <= write_beats_left - 1'b1;
                    write_addr <= next_address(write_addr, write_size,
                                               write_burst);
                end
            end

            if (s_axi_arready && s_axi_arvalid) begin
                read_active     <= 1'b1;
                read_id         <= s_axi_arid;
                read_addr       <= s_axi_araddr;
                read_beats_left <= s_axi_arlen;
                read_size       <= s_axi_arsize;
                read_burst      <= s_axi_arburst;
            end

            if (read_active && !s_axi_rvalid) begin
                s_axi_rid    <= read_id;
                s_axi_rdata  <= read_beat_error ? 64'd0 :
                                 memory[read_addr[ADDR_WIDTH-1:3]];
                s_axi_rresp  <= read_beat_error ? AXI_DECERR : AXI_OKAY;
                s_axi_rlast  <= (read_beats_left == 0);
                s_axi_rvalid <= 1'b1;
                if (read_beat_error)
                    error_code <= 8'h02;
            end else if (s_axi_rvalid && s_axi_rready) begin
                s_axi_rvalid <= 1'b0;
                if (s_axi_rlast) begin
                    read_active <= 1'b0;
                end else begin
                    read_beats_left <= read_beats_left - 1'b1;
                    read_addr <= next_address(read_addr, read_size,
                                              read_burst);
                end
            end
        end
    end
endmodule
