module message_padder(
    input logic aclk,
    input logic aresetn,
    // slave axi-4 stream ports
    input logic [31:0] s_axis_tdata,
    input logic [3:0] s_axis_tkeep,
    input logic s_axis_tvalid,
    input logic s_axis_tlast,
    output logic s_axis_tready,

    output logic [511:0] block,
    output logic sha_valid,
    output logic done,
    input logic scheduler_ready
);
    timeunit 1ns;
    timeprecision 100ps;

    // state encoding
    typedef enum logic [2:0] {  IDLE, 
                                WRITE_BUFFER, 
                                PADDING, 
                                BUFFER_FULL, 
                                SEND
                            } state_t;
    state_t current_state, next_state;

    // datapaths
    logic [31:0] w_buffer [0:15];
    logic [31:0] w_buffer_next [0:15];
    logic [3:0] w_buffer_index, w_buffer_index_next;
    logic [63:0] total_length, total_length_next;
    logic spillover, spillover_next;
    logic last_packet, last_packet_next;
    logic delim_b2, delim_b2_next;
    logic done_next;

    // functions
    function automatic logic[31:0] pad_message(input logic[3:0] keep);
        case(keep)
            4'b1000: pad_message = {s_axis_tdata[31:24], 24'h800000};
            4'b1100: pad_message = {s_axis_tdata[31:16], 16'h8000};
            4'b1110: pad_message = {s_axis_tdata[31:8], 8'h80};
            4'b1111: pad_message = s_axis_tdata;
            default: pad_message = 32'h80000000;
        endcase
    endfunction
    function automatic logic[5:0] bytestobit(input logic [3:0] keep);
        case(keep)
            4'b1000: bytestobit = 6'd8;
            4'b1100: bytestobit = 6'd16;
            4'b1110: bytestobit = 6'd24;
            4'b1111: bytestobit = 6'd32;
            default: bytestobit = 6'd0;
        endcase
    endfunction

    // output
    always_comb begin
        for(int i = 0; i < 16; i = i + 1)
            block[511-(i*32) -: 32] = w_buffer[i];  
    end

    // state memory
    always_ff @(posedge aclk, negedge aresetn) begin: STATE_MEMORY
        if(!aresetn) begin
            current_state  <= IDLE;
            total_length   <= 64'd0;
            spillover      <= 1'b0;
            last_packet    <= 1'b0;
            w_buffer_index <= 4'd0;
            delim_b2       <= 1'b0;
            done           <= 1'b1;   // paused/idle default until data arrives
            for(int i = 0; i < 16; i = i + 1) begin
                w_buffer[i] <= 32'd0;
            end
        end else begin
            current_state  <= next_state;
            total_length   <= total_length_next;
            spillover      <= spillover_next;
            last_packet    <= last_packet_next;
            w_buffer_index <= w_buffer_index_next;
            delim_b2       <= delim_b2_next;
            done           <= done_next;
            for(int i = 0; i < 16; i = i + 1) begin
                w_buffer[i] <= w_buffer_next[i];
            end
        end
    end

    // next state logic and output logic 
    always_comb begin: NEXT_STATE_LOGIC_OUTPUT_LOGIC
        next_state          = current_state;
        total_length_next   = total_length;
        spillover_next      = spillover;
        last_packet_next    = last_packet;
        w_buffer_index_next = w_buffer_index;
        delim_b2_next       = delim_b2;
        s_axis_tready       = 1'b0;
        sha_valid           = 1'b0;
        done_next           = done;   // hold by default; only changes on the two events below

        for(int i = 0; i < 16; i = i + 1) begin
            w_buffer_next[i] = w_buffer[i];
        end

        case(current_state)
            IDLE: begin
                s_axis_tready     = 1'b1;
                spillover_next    = 1'b0;
                total_length_next = 64'd0;
                last_packet_next  = 1'b0;
                delim_b2_next     = 1'b0;
                if(s_axis_tvalid) begin
                    done_next = 1'b0;
                    total_length_next = bytestobit(s_axis_tkeep);
                    if(s_axis_tlast) begin
                        last_packet_next = 1'b1;
                        w_buffer_next[0] = pad_message(s_axis_tkeep);
                        if(s_axis_tkeep == 4'b1111) begin
                            w_buffer_next[1]    = 32'h80000000;
                            w_buffer_index_next = 4'd1;
                        end else begin
                            w_buffer_index_next = 4'd0;
                        end
                        next_state = PADDING;
                    end else begin
                        w_buffer_next[0]    = s_axis_tdata;
                        w_buffer_index_next = 4'd1;
                        next_state          = WRITE_BUFFER;
                    end
                end
            end

            WRITE_BUFFER: begin
                s_axis_tready = 1'b1;
                if(s_axis_tvalid) begin
                    total_length_next = total_length + bytestobit(s_axis_tkeep);
                    if(!s_axis_tlast) begin
                        w_buffer_next[w_buffer_index] = s_axis_tdata;
                        if(w_buffer_index == 4'd15) begin
                            w_buffer_index_next = 4'd0;
                            next_state          = BUFFER_FULL;
                        end else begin
                            w_buffer_index_next = w_buffer_index + 1'b1; 
                        end
                    end else begin
                        last_packet_next              = 1'b1;
                        w_buffer_next[w_buffer_index] = pad_message(s_axis_tkeep);

                        if(w_buffer_index <= 12 || (w_buffer_index == 13 && s_axis_tkeep !== 4'b1111)) begin
                            spillover_next = 1'b0;
                            delim_b2_next  = 1'b0;
                            if(s_axis_tkeep == 4'b1111) begin
                                w_buffer_next[w_buffer_index + 1] = 32'h80000000;
                                w_buffer_index_next               = w_buffer_index + 1;
                            end
                            next_state = PADDING;
                        end else begin
                            spillover_next = 1'b1;
                            if(s_axis_tkeep == 4'b1111) begin
                                if(w_buffer_index == 4'd15) begin
                                    delim_b2_next = 1'b1;
                                end else begin
                                    delim_b2_next                     = 1'b0;
                                    w_buffer_next[w_buffer_index + 1] = 32'h8000_0000;
                                    if(w_buffer_index == 4'd13) begin
                                        w_buffer_next[15] = 32'h0;
                                    end
                                end
                            end else begin
                                delim_b2_next = 1'b0;
                                if(w_buffer_index == 4'd14) begin
                                    w_buffer_next[15] = 32'h0;
                                end
                            end
                            next_state = BUFFER_FULL;
                        end
                    end
                end
            end

            PADDING: begin
                for(int i = 0; i < 14; i = i + 1)
                    if(i > w_buffer_index) w_buffer_next[i] = 32'd0;
                w_buffer_next[14] = total_length[63:32];
                w_buffer_next[15] = total_length[31:0];
                next_state        = BUFFER_FULL;
            end

            BUFFER_FULL: begin
                if(scheduler_ready) begin
                    next_state = SEND;
                end
            end

            SEND: begin
                s_axis_tready = 1'b0;
                sha_valid     = 1'b1;

                if(scheduler_ready) begin
                    if(spillover) begin
                        if(delim_b2) begin
                            w_buffer_next[0] = 32'h80000000;
                            for(int i = 1; i < 14; i = i + 1)
                                w_buffer_next[i] = 32'd0; 
                        end else begin
                            for(int i = 0; i < 14; i = i + 1)
                                w_buffer_next[i] = 32'd0;
                        end
                        w_buffer_next[14] = total_length[63:32];
                        w_buffer_next[15] = total_length[31:0];

                        spillover_next = 1'b0;
                        next_state     = BUFFER_FULL;
                    end else if (!last_packet) begin
                        for(int i = 0; i < 16; i = i + 1)
                            w_buffer_next[i] = 32'd0;
                        w_buffer_index_next = 4'd0;
                        next_state          = WRITE_BUFFER;
                    end else begin
                        for(int i = 0; i < 16; i = i + 1)
                            w_buffer_next[i] = 32'd0;
                        w_buffer_index_next = 4'd0;
                        total_length_next   = 64'd0;
                        last_packet_next    = 1'b0;
                        done_next           = 1'b1;
                        next_state          = IDLE;
                    end
                end else begin
                    next_state = SEND;
                end
            end

            default: next_state = IDLE;
        endcase
    end

endmodule