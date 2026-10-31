

module bootloader(
    input logic clk,
    input logic rst,
    input logic [7:0] data_in,
    input logic write,
    output logic ready,
    output logic [31:0] data_out,
    output logic [4:0] address,
    output logic sel,
    output logic imem_write,
    output logic hold
);

    logic [7:0] counter;
    logic [7:0] instr_counter;

    typedef enum logic [2:0] {
        idle,
        load_counter,
        load_data,
        increment_address,
        done
    } state_t;

    state_t state;

    logic [31:0] mem;
    logic [1:0] mem_counter;

    always_ff @(posedge clk)
    begin
        if (rst)
        begin
            counter       <= 8'd0;
            instr_counter <= 8'd0;
            ready         <= 1'b0;
            data_out      <= 32'd0;
            address       <= 5'd0;
            sel           <= 1'b0;
            hold          <= 1'b1;
            imem_write    <= 1'b0;
            mem           <= 32'd0;
            mem_counter   <= 2'd0;
            state         <= idle;
        end
        else
        begin
            imem_write <= 1'b0;

            case (state)

                idle:
                begin
                    ready <= 1'b1;
                    hold  <= 1'b1;
                    sel   <= 1'b1;
                    state <= load_counter;
                end

                load_counter:
                begin
                    if (write && ready)
                    begin
                        counter       <= data_in;
                        instr_counter <= 8'd0;
                        mem_counter   <= 2'd0;
                        address       <= 5'd0;
                        ready         <= 1'b0;
                        state         <= load_data;
                    end
                end

                load_data:
                begin
                    if (!ready)
                    begin
                        ready <= 1'b1;
                    end
                    else if (write && ready)
                    begin
                        ready <= 1'b0;

                        case (mem_counter)

                            2'b00:
                            begin
                                mem[31:24] <= data_in;
                                mem_counter <= 2'b01;
                            end

                            2'b01:
                            begin
                                mem[23:16] <= data_in;
                                mem_counter <= 2'b10;
                            end

                            2'b10:
                            begin
                                mem[15:8] <= data_in;
                                mem_counter <= 2'b11;
                            end

                            2'b11:
                            begin
                                mem[7:0] <= data_in;
                                data_out <= {mem[31:8], data_in};
                                imem_write <= 1'b1;
                                instr_counter <= instr_counter + 1'b1;
                                mem_counter <= 2'b00;

                                if (instr_counter + 1'b1 >= counter)
                                begin
                                    state <= done;
                                end
                                else
                                begin
                                    state <= increment_address;
                                end
                            end

                        endcase
                    end
                end

                increment_address:
                begin
                    address <= address + 1'b1;
                    ready   <= 1'b1;
                    state   <= load_data;
                end

                done:
                begin
                    ready      <= 1'b0;
                    hold       <= 1'b0;
                    sel        <= 1'b0;
                    imem_write <= 1'b0;
                    state      <= done;
                end

                default:
                begin
                    state <= idle;
                end

            endcase
        end
    end

endmodule
