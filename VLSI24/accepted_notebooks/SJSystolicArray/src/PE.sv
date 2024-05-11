module PE
    (
        input logic clk_i, rstn_i,
        input logic [9:0] psum_i,
        input logic [7:0] filter_i, 
        input logic [7:0] ifmap_i, 
        input logic read_new_filter_val,
        input logic read_new_ifmap_val,
        input logic start_conv,
        output logic [9:0] psum_o, 
        output logic psum_valid_o
    );

    //Scratchpad regs
    logic signed [7:0] filter_spad [0:2];
    logic signed [7:0] ifmap_spad [0:2];
    logic signed [9:0] psum_spad;
    
    //psum buffer reg
    logic signed [9:0] psum_buffer;

    //datapath wires
    // logic signed [DATA_SIZE-1:0] mult_input_filter, mult_input_ifmap; //wires between regs and multiplier
    logic signed [15:0] mult_out_raw; //full multiplication result
    logic signed [9:0] mult_out_trunc;
    logic signed [9:0] adder_input, adder_output, psum_spad_input; // result of multiplexor. chooses either result of MAC or the psum from above PE to go to adder

    //counter reg and wires
    logic [1:0] counter; //Tells which regs to use in scratchpad
    logic [1:0] next_counter; // 1 + index
    logic acc_psum;

    //state reg and wire
    logic next_calculating;
    logic calculating;


    always_comb begin
        //============= Time to accumulate psum? ===============
        acc_psum = (counter == 2'd3);

        //============= Next State ==================
        if ((!calculating && start_conv) || (calculating && !acc_psum)) next_calculating = '1;
        else next_calculating = '0;

        //============= Next Counter =================
        next_counter = calculating ? counter + 1 : '0;

        //============= Multiplication ===============
        mult_out_raw = filter_spad[counter] * ifmap_spad[counter];
        mult_out_trunc = mult_out_raw[15:6]; //truncate to 10 bits

        //============= Accumulation ================
        adder_input = acc_psum ? psum_i : mult_out_trunc;
        adder_output = adder_input + psum_spad;
        psum_spad_input = (calculating && !acc_psum) ? adder_output : '0;

        //============= Set Output =================
        psum_o = psum_buffer;
    end

    always_ff @(posedge clk_i, negedge rstn_i) begin
        if (!rstn_i) begin
            //============ set all the registers to 0 =========
            counter <= '0;
            for (int i = 0; i < 3; i++) begin
                filter_spad[i] <= '0;
                ifmap_spad[i] <= '0;
            end
            psum_spad <= '0;
            psum_buffer <= '0;
            calculating <= '0;
            psum_valid_o <= '0;

        end else begin
            //==========   update state ===========
            calculating <= next_calculating;

            //==========  update counter  =============
            counter <= next_counter;

            //==========  update filter scratchpad  =============
            if (read_new_filter_val) begin
                for (int i = 0; i < 2; i++) begin
                    filter_spad[i] <= filter_spad[i+1];
                end
                filter_spad[2] <= filter_i;
            end

            //==========  update ifmap scratchpad  =============
            if (read_new_ifmap_val) begin
                for (int i = 0; i < 2; i++) begin
                    ifmap_spad[i] <= ifmap_spad[i+1];
                end
                ifmap_spad[2] <= ifmap_i;
            end

            //========= update psum buffer ==========
            if (acc_psum) psum_buffer <= adder_output;

            //========= update psum scratchpad ======
            psum_spad <= psum_spad_input;

            //============= valid bit ===================
            psum_valid_o <= acc_psum;
        end
    end

endmodule