Create synthesizable SystemVerilog module counter.
Ports: input clk,rst_n,en,load; input [7:0] load_value;
output [7:0] count; output overflow.
Active-low asynchronous reset sets both outputs to zero immediately.
On rising clock edges, load has priority over en: load sets count to
load_value and overflow to zero. Otherwise en increments count modulo 256,
with overflow=1 exactly when that edge wraps previous count 255 to zero.
With neither load nor en, hold count and clear overflow to zero.
overflow is a one-cycle wrap event, not a sticky status bit.
