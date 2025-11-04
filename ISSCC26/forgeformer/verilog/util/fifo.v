// +FHDR========================================================================
//  License:
//
// =============================================================================
//  File Name:      fifo.v
//                  Shiwei Liu (liushiwei@google.com)
//  Organization:   Space Beaker Team, Google Research
//  Description:
//      Asynchronous and synchronous FIFO
// -FHDR========================================================================

// =============================================================================
// Asynchronous FIFO

module async_fifo #(
    parameter   DATA_BIT = 64,
    parameter   DEPTH = 16, // FIFO depth
    parameter   ADDR_BIT = $clog2(DATA_BIT)
)(
    // Write channel
    input                   wclk,
    input                   wrst,
    input                   wen,
    input       [BIT-1:0]   wdata,
    output  reg             wfull,

    // Read channel
    input                   rclk,
    input                   rrst,
    input                   ren,
    output  reg [BIT-1:0]   rdata,
    output  reg             rempty
);

    // 1. For large FIFO RegFile: Replace registers with RegFile from memory compiler
    reg     [DATA_BIT-1:0]  mem [0:DEPTH-1];

    // 2. Signal declaration
    // 2.1 Read channel
    wire    [ADDR_BIT-1:0]  raddr;
    reg     [ADDR_BIT:0]    rbin;
    wire    [ADDR_BIT:0]    rbinnext, rgraynext;

    // 2.2 Write channel
    wire    [ADDR_BIT-1:0]  waddr;
    reg     [ADDR_BIT:0]    wbin;
    wire    [ADDR_BIT-1:0]  wbinnext, wgraynext;

    // 2.3 Sychronize writing pointer to reading space
    reg     [ADDR_BIT:0]    rptr, rq1_wptr, rq2_wptr;

    // 2.4 Sychronize reading pointer to writing space
    reg     [ADDR_BIT:0]    wptr, wq1_rptr, wq2_rptr;

    // 3. Inside one time-domain
    // 3.1 Read channel: Using binary code for FIFO access and gray code for time-domain crossing
    always @(posedge rclk or posedge rrst) begin
        if (rrst) begin
            rdata <= 'd0;
        end
        else if (ren & ~rempty) begin
            rdata <= mem[raddr];
        end
    end

    assign  raddr = rbin[ADDR_BIT-1:0];
    assign  rbinnext = rbin + (ren & ~rempty);
    assign  rgraynext = (rbinnext >> 1'b1) ^ rbinnext;

    always @(posedge rclk or posedge rrst) begin
        if (rrst) begin
            {rbin, rptr} <= 'd0;
        end
        else begin
            {rbin, rptr} <= rbinnext, rgraynext;
        end
    end

    // 3.2 Write channel: Using binary code for FIFO access and gray code for time-domain crossing
    always @(posedge wclk) begin
        if (wen & ~wfull) begin
            mem[waddr] <= wdata;
        end
    end

    assign  waddr = wbin[ADDR_BIT-1:0];
    assign  wbinnext = wbin + (wen & ~wfull);
    assign  wgraynext = (wbinnext >> 1'b1) ^ wbinnext;

    always @(posedge wclk or posedge wrst) begin
        if (wrst) begin
            {wbin, wptr} <= 'd0;
        end
        begin
            {wbin, wptr} <= wbinnext, wgraynext;
        end
    end

    // 4. Crossing time-domain
    // 4.1 Synchronize writing pointer in read domain and generate rempty
    always @(posedge rclk or posedge rrst) begin
        if (rrst) begin
            {rq2_wptr, rq1_wptr} <= 'd0;
        end
        else begin
            {rq2_wptr, rq1_wptr} <= {rq1_wptr, wptr};
        end
    end

    always @(posedge rclk or posedge rrst) begin
        if (rrst) begin
            rempty <= 1'b1;
        end
        else begin
            rempty <= rgraynext == rq2_wptr;
        end
    end

    // 4.2 Synchronize reading pointer in write domain and generate wfull
    always @(posedge wclk or posedge wrst) begin
        if (wrst) begin
            {wq2_rptr, wq1_rptr} <= 'd0;
        end
        else begin
            {wq2_rptr, wq1_rptr} <= {wq1_rptr, rptr};
        end
    end

    always @(posedge wclk or posedge wrst) begin
        if (wrst) begin
            wfull <= 1'b0;
        end
        else begin
            wfull <= wgraynext == {~wq2_rptr[ADDR_BIT:ADDR_BIT-1], wq2_rptr[ADDR_BIT-2:0]};
        end
    end

endmodule

// =============================================================================
// Synchronous FIFO

module sync_fifo #(
    parameter   DATA_BIT = 64,
    parameter   DEPTH = 16,
    parameter   ADDR_BIT = $clog2(DEPTH)
)(
    // Global Signals
    input                       clk,
    input                       rst,

    // Write Channel
    input                       wen,
    input       [DATA_BIT-1:0]  wdata,
    output                      werror,
    output                      wfull,

    // Read Channel
    input                       ren,
    output  reg [DATA_BIT-1:0]  rdata,
    output                      rerror,
    output                      rempty
);

    // 1. For large FIFO RegFile: Replace registers with RegFile from memory compiler
    reg     [DATA_BIT-1:0]  mem [0:DEPTH-1];

    // 2. Signal declaration
    reg     [ADDR_BIT-1:0]  waddr, raddr;
    reg     [ADDR_BIT:0]    fifo_cnt;

    // 3. Read channel
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            rdata <= 'd0;
        end
        else if (ren & ~rempty) begin
            rdata <= mem[raddr];
        end
    end

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            raddr <= 'd0;
        end if (ren & ~rempty) begin
            raddr <= raddr + 1'b1;
        end
    end

    // 4. Write channel
    always @(posedge clk) begin
        if (wen & ~wfull) begin
            mem[waddr] <= wdata;
        end
    end

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            waddr <= 'd0;
        end
        else if (wen & (~wfull)) begin
            waddr <= waddr + 1'b1;
        end
    end

    // 5. Flag assertation
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            fifo_cnt <= 'd0;
        end
        else if ((wen & ~wfull) && ~(ren & ~rempty)) begin
            fifo_cnt <= fifo_cnt + 1'b1;
        end
        else if ((ren & ~rempty) && ~(wen & ~wfull)) begin
            fifo_cnt <= fifo_cnt - 1'b1;
        end
    end

    assign  rempty = (!fifo_cnt) == 1'b0;
    assign  rerror = rempty & ren;

    assign  wfull = fifo_cnt == {1'b1, {ADDR_BIT{1'b0}}};
    assign  werror = wfull & wen;

endmodule