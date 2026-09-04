/* |======================================================================= */
/* | */                                                                          
/* | Author             :Alfi Misha Antony Selvin Raj */                                                   
/* | Description        : Simple inverter                                           
/* | */                                                                      
/* | */                                                                      
/* |======================================================================= */

module inverter (
    input logic in, 
    output logic out
);

assign out = ~in;

endmodule
