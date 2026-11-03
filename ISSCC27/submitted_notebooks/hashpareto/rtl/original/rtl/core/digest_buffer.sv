module digest_buffer(
    input logic aclk,
    input logic aresetn,
    input logic [255:0] digest,
    input logic digest_valid,
    input logic m_axis_tready,

    output logic [31:0] m_axis_tdata,
    output logic m_axis_tvalid,
    output logic m_axis_tlast
);
    timeunit 1ns;
    timeprecision 1ps;

    logic [31:0] digest_buffer [0:7];
    logic [2:0] digest_count;
    logic digest_valid_prev;

    always_ff @(posedge aclk, negedge aresetn) begin
        if(!aresetn) begin
            digest_count      <= 3'd0;
            m_axis_tvalid     <= 1'b0;
            digest_valid_prev <= 1'b0;
            for(int i = 0; i < 8; i++)
                digest_buffer[i] <= 32'd0;

        end else begin
            digest_valid_prev <= digest_valid;

            if(digest_valid && !digest_valid_prev) begin
               for(int i = 0; i < 8; i++)
                    digest_buffer[i] <= digest[255-(32*i) -: 32];
               m_axis_tvalid <= 1'b1;
               digest_count  <= 3'd0;

            end else if (m_axis_tvalid && m_axis_tready) begin
                digest_count <= digest_count + 1;
                for(int i = 0; i < 7; i++)
                    digest_buffer[i] <= digest_buffer[i+1];

                digest_buffer[7] <= 32'd0;

                if(digest_count == 3'd7)
                    m_axis_tvalid <= 1'b0;
            end
        end
    end

    assign m_axis_tlast = (digest_count == 3'd7) ? 1'b1 : 1'b0;
    assign m_axis_tdata = digest_buffer[0];

endmodule