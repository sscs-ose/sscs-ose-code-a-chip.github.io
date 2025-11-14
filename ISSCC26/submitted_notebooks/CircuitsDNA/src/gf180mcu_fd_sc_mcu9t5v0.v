// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__ADDF_1_V
`define GF180MCU_FD_SC_MCU9T5V0__ADDF_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__addf_1( S, A, CI, B, CO, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__addf_1( S, A, CI, B, CO );
`endif // If not USE_POWER_PINS
input A, B, CI;
output CO, S;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__addf_func gf180mcu_fd_sc_mcu9t5v0__addf_inst(.S(S),.A(A),.CI(CI),.B(B),.CO(CO),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__addf_func gf180mcu_fd_sc_mcu9t5v0__addf_inst(.S(S),.A(A),.CI(CI),.B(B),.CO(CO));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B===1'b0 && CI===1'b1)
	// comb arc A --> CO
	 (A => CO) = (1.0,1.0);

	if(B===1'b1 && CI===1'b0)
	// comb arc A --> CO
	 (A => CO) = (1.0,1.0);

	ifnone
	// comb arc A --> CO
	 (A => CO) = (1.0,1.0);

	if(A===1'b0 && CI===1'b1)
	// comb arc B --> CO
	 (B => CO) = (1.0,1.0);

	if(A===1'b1 && CI===1'b0)
	// comb arc B --> CO
	 (B => CO) = (1.0,1.0);

	ifnone
	// comb arc B --> CO
	 (B => CO) = (1.0,1.0);

	if(A===1'b0 && B===1'b1)
	// comb arc CI --> CO
	 (CI => CO) = (1.0,1.0);

	if(A===1'b1 && B===1'b0)
	// comb arc CI --> CO
	 (CI => CO) = (1.0,1.0);

	ifnone
	// comb arc CI --> CO
	 (CI => CO) = (1.0,1.0);

	if(B===1'b0 && CI===1'b1)
	// comb arc A --> S
	 (A => S) = (1.0,1.0);

	if(B===1'b1 && CI===1'b0)
	// comb arc A --> S
	 (A => S) = (1.0,1.0);

	ifnone
	// comb arc posedge A --> (S:A)
	 (posedge A => (S:A)) = (1.0,1.0);

	ifnone
	// comb arc negedge A --> (S:A)
	 (negedge A => (S:A)) = (1.0,1.0);

	if(B===1'b0 && CI===1'b0)
	// comb arc A --> S
	 (A => S) = (1.0,1.0);

	if(B===1'b1 && CI===1'b1)
	// comb arc A --> S
	 (A => S) = (1.0,1.0);

	if(A===1'b0 && CI===1'b1)
	// comb arc B --> S
	 (B => S) = (1.0,1.0);

	if(A===1'b1 && CI===1'b0)
	// comb arc B --> S
	 (B => S) = (1.0,1.0);

	ifnone
	// comb arc posedge B --> (S:B)
	 (posedge B => (S:B)) = (1.0,1.0);

	ifnone
	// comb arc negedge B --> (S:B)
	 (negedge B => (S:B)) = (1.0,1.0);

	if(A===1'b0 && CI===1'b0)
	// comb arc B --> S
	 (B => S) = (1.0,1.0);

	if(A===1'b1 && CI===1'b1)
	// comb arc B --> S
	 (B => S) = (1.0,1.0);

	if(A===1'b0 && B===1'b1)
	// comb arc CI --> S
	 (CI => S) = (1.0,1.0);

	if(A===1'b1 && B===1'b0)
	// comb arc CI --> S
	 (CI => S) = (1.0,1.0);

	ifnone
	// comb arc posedge CI --> (S:CI)
	 (posedge CI => (S:CI)) = (1.0,1.0);

	ifnone
	// comb arc negedge CI --> (S:CI)
	 (negedge CI => (S:CI)) = (1.0,1.0);

	if(A===1'b0 && B===1'b0)
	// comb arc CI --> S
	 (CI => S) = (1.0,1.0);

	if(A===1'b1 && B===1'b1)
	// comb arc CI --> S
	 (CI => S) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__ADDF_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__ADDF_2_V
`define GF180MCU_FD_SC_MCU9T5V0__ADDF_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__addf_2( S, A, CI, B, CO, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__addf_2( S, A, CI, B, CO );
`endif // If not USE_POWER_PINS
input A, B, CI;
output CO, S;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__addf_func gf180mcu_fd_sc_mcu9t5v0__addf_inst(.S(S),.A(A),.CI(CI),.B(B),.CO(CO),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__addf_func gf180mcu_fd_sc_mcu9t5v0__addf_inst(.S(S),.A(A),.CI(CI),.B(B),.CO(CO));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B===1'b0 && CI===1'b1)
	// comb arc A --> CO
	 (A => CO) = (1.0,1.0);

	if(B===1'b1 && CI===1'b0)
	// comb arc A --> CO
	 (A => CO) = (1.0,1.0);

	ifnone
	// comb arc A --> CO
	 (A => CO) = (1.0,1.0);

	if(A===1'b0 && CI===1'b1)
	// comb arc B --> CO
	 (B => CO) = (1.0,1.0);

	if(A===1'b1 && CI===1'b0)
	// comb arc B --> CO
	 (B => CO) = (1.0,1.0);

	ifnone
	// comb arc B --> CO
	 (B => CO) = (1.0,1.0);

	if(A===1'b0 && B===1'b1)
	// comb arc CI --> CO
	 (CI => CO) = (1.0,1.0);

	if(A===1'b1 && B===1'b0)
	// comb arc CI --> CO
	 (CI => CO) = (1.0,1.0);

	ifnone
	// comb arc CI --> CO
	 (CI => CO) = (1.0,1.0);

	if(B===1'b0 && CI===1'b1)
	// comb arc A --> S
	 (A => S) = (1.0,1.0);

	if(B===1'b1 && CI===1'b0)
	// comb arc A --> S
	 (A => S) = (1.0,1.0);

	ifnone
	// comb arc posedge A --> (S:A)
	 (posedge A => (S:A)) = (1.0,1.0);

	ifnone
	// comb arc negedge A --> (S:A)
	 (negedge A => (S:A)) = (1.0,1.0);

	if(B===1'b0 && CI===1'b0)
	// comb arc A --> S
	 (A => S) = (1.0,1.0);

	if(B===1'b1 && CI===1'b1)
	// comb arc A --> S
	 (A => S) = (1.0,1.0);

	if(A===1'b0 && CI===1'b1)
	// comb arc B --> S
	 (B => S) = (1.0,1.0);

	if(A===1'b1 && CI===1'b0)
	// comb arc B --> S
	 (B => S) = (1.0,1.0);

	ifnone
	// comb arc posedge B --> (S:B)
	 (posedge B => (S:B)) = (1.0,1.0);

	ifnone
	// comb arc negedge B --> (S:B)
	 (negedge B => (S:B)) = (1.0,1.0);

	if(A===1'b0 && CI===1'b0)
	// comb arc B --> S
	 (B => S) = (1.0,1.0);

	if(A===1'b1 && CI===1'b1)
	// comb arc B --> S
	 (B => S) = (1.0,1.0);

	if(A===1'b0 && B===1'b1)
	// comb arc CI --> S
	 (CI => S) = (1.0,1.0);

	if(A===1'b1 && B===1'b0)
	// comb arc CI --> S
	 (CI => S) = (1.0,1.0);

	ifnone
	// comb arc posedge CI --> (S:CI)
	 (posedge CI => (S:CI)) = (1.0,1.0);

	ifnone
	// comb arc negedge CI --> (S:CI)
	 (negedge CI => (S:CI)) = (1.0,1.0);

	if(A===1'b0 && B===1'b0)
	// comb arc CI --> S
	 (CI => S) = (1.0,1.0);

	if(A===1'b1 && B===1'b1)
	// comb arc CI --> S
	 (CI => S) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__ADDF_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__ADDF_4_V
`define GF180MCU_FD_SC_MCU9T5V0__ADDF_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__addf_4( S, A, CI, B, CO, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__addf_4( S, A, CI, B, CO );
`endif // If not USE_POWER_PINS
input A, B, CI;
output CO, S;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__addf_func gf180mcu_fd_sc_mcu9t5v0__addf_inst(.S(S),.A(A),.CI(CI),.B(B),.CO(CO),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__addf_func gf180mcu_fd_sc_mcu9t5v0__addf_inst(.S(S),.A(A),.CI(CI),.B(B),.CO(CO));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B===1'b0 && CI===1'b1)
	// comb arc A --> CO
	 (A => CO) = (1.0,1.0);

	if(B===1'b1 && CI===1'b0)
	// comb arc A --> CO
	 (A => CO) = (1.0,1.0);

	ifnone
	// comb arc A --> CO
	 (A => CO) = (1.0,1.0);

	if(A===1'b0 && CI===1'b1)
	// comb arc B --> CO
	 (B => CO) = (1.0,1.0);

	if(A===1'b1 && CI===1'b0)
	// comb arc B --> CO
	 (B => CO) = (1.0,1.0);

	ifnone
	// comb arc B --> CO
	 (B => CO) = (1.0,1.0);

	if(A===1'b0 && B===1'b1)
	// comb arc CI --> CO
	 (CI => CO) = (1.0,1.0);

	if(A===1'b1 && B===1'b0)
	// comb arc CI --> CO
	 (CI => CO) = (1.0,1.0);

	ifnone
	// comb arc CI --> CO
	 (CI => CO) = (1.0,1.0);

	if(B===1'b0 && CI===1'b1)
	// comb arc A --> S
	 (A => S) = (1.0,1.0);

	if(B===1'b1 && CI===1'b0)
	// comb arc A --> S
	 (A => S) = (1.0,1.0);

	ifnone
	// comb arc posedge A --> (S:A)
	 (posedge A => (S:A)) = (1.0,1.0);

	ifnone
	// comb arc negedge A --> (S:A)
	 (negedge A => (S:A)) = (1.0,1.0);

	if(B===1'b0 && CI===1'b0)
	// comb arc A --> S
	 (A => S) = (1.0,1.0);

	if(B===1'b1 && CI===1'b1)
	// comb arc A --> S
	 (A => S) = (1.0,1.0);

	if(A===1'b0 && CI===1'b1)
	// comb arc B --> S
	 (B => S) = (1.0,1.0);

	if(A===1'b1 && CI===1'b0)
	// comb arc B --> S
	 (B => S) = (1.0,1.0);

	ifnone
	// comb arc posedge B --> (S:B)
	 (posedge B => (S:B)) = (1.0,1.0);

	ifnone
	// comb arc negedge B --> (S:B)
	 (negedge B => (S:B)) = (1.0,1.0);

	if(A===1'b0 && CI===1'b0)
	// comb arc B --> S
	 (B => S) = (1.0,1.0);

	if(A===1'b1 && CI===1'b1)
	// comb arc B --> S
	 (B => S) = (1.0,1.0);

	if(A===1'b0 && B===1'b1)
	// comb arc CI --> S
	 (CI => S) = (1.0,1.0);

	if(A===1'b1 && B===1'b0)
	// comb arc CI --> S
	 (CI => S) = (1.0,1.0);

	ifnone
	// comb arc posedge CI --> (S:CI)
	 (posedge CI => (S:CI)) = (1.0,1.0);

	ifnone
	// comb arc negedge CI --> (S:CI)
	 (negedge CI => (S:CI)) = (1.0,1.0);

	if(A===1'b0 && B===1'b0)
	// comb arc CI --> S
	 (CI => S) = (1.0,1.0);

	if(A===1'b1 && B===1'b1)
	// comb arc CI --> S
	 (CI => S) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__ADDF_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__ADDF_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__ADDF_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__addf_func( S, A, CI, B, CO, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__addf_func( S, A, CI, B, CO );
`endif // If not USE_POWER_PINS
input A, B, CI;
output CO, S;

	wire CO_row1;

	and MGM_BG_0( CO_row1, A, B );

	wire CO_row2;

	and MGM_BG_1( CO_row2, A, CI );

	wire CO_row3;

	and MGM_BG_2( CO_row3, B, CI );

	or MGM_BG_3( CO, CO_row1, CO_row2, CO_row3 );

	wire S_row1;

	and MGM_BG_4( S_row1, A, B, CI );

	wire B_inv_for_gf180mcu_fd_sc_mcu9t5v0__addf_1;

	not MGM_BG_5( B_inv_for_gf180mcu_fd_sc_mcu9t5v0__addf_1, B );

	wire CI_inv_for_gf180mcu_fd_sc_mcu9t5v0__addf_1;

	not MGM_BG_6( CI_inv_for_gf180mcu_fd_sc_mcu9t5v0__addf_1, CI );

	wire S_row2;

	and MGM_BG_7( S_row2, B_inv_for_gf180mcu_fd_sc_mcu9t5v0__addf_1, CI_inv_for_gf180mcu_fd_sc_mcu9t5v0__addf_1, A );

	wire A_inv_for_gf180mcu_fd_sc_mcu9t5v0__addf_1;

	not MGM_BG_8( A_inv_for_gf180mcu_fd_sc_mcu9t5v0__addf_1, A );

	wire S_row3;

	and MGM_BG_9( S_row3, A_inv_for_gf180mcu_fd_sc_mcu9t5v0__addf_1, CI_inv_for_gf180mcu_fd_sc_mcu9t5v0__addf_1, B );

	wire S_row4;

	and MGM_BG_10( S_row4, A_inv_for_gf180mcu_fd_sc_mcu9t5v0__addf_1, B_inv_for_gf180mcu_fd_sc_mcu9t5v0__addf_1, CI );

	or MGM_BG_11( S, S_row1, S_row2, S_row3, S_row4 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__ADDF_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__ADDH_1_V
`define GF180MCU_FD_SC_MCU9T5V0__ADDH_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__addh_1( CO, A, B, S, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__addh_1( CO, A, B, S );
`endif // If not USE_POWER_PINS
input A, B;
output CO, S;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__addh_func gf180mcu_fd_sc_mcu9t5v0__addh_inst(.CO(CO),.A(A),.B(B),.S(S),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__addh_func gf180mcu_fd_sc_mcu9t5v0__addh_inst(.CO(CO),.A(A),.B(B),.S(S));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A --> CO
	 (A => CO) = (1.0,1.0);

	// comb arc B --> CO
	 (B => CO) = (1.0,1.0);

	ifnone
	// comb arc posedge A --> (S:A)
	 (posedge A => (S:A)) = (1.0,1.0);

	ifnone
	// comb arc negedge A --> (S:A)
	 (negedge A => (S:A)) = (1.0,1.0);

	ifnone
	// comb arc posedge B --> (S:B)
	 (posedge B => (S:B)) = (1.0,1.0);

	ifnone
	// comb arc negedge B --> (S:B)
	 (negedge B => (S:B)) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__ADDH_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__ADDH_2_V
`define GF180MCU_FD_SC_MCU9T5V0__ADDH_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__addh_2( CO, A, B, S, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__addh_2( CO, A, B, S );
`endif // If not USE_POWER_PINS
input A, B;
output CO, S;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__addh_func gf180mcu_fd_sc_mcu9t5v0__addh_inst(.CO(CO),.A(A),.B(B),.S(S),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__addh_func gf180mcu_fd_sc_mcu9t5v0__addh_inst(.CO(CO),.A(A),.B(B),.S(S));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A --> CO
	 (A => CO) = (1.0,1.0);

	// comb arc B --> CO
	 (B => CO) = (1.0,1.0);

	ifnone
	// comb arc posedge A --> (S:A)
	 (posedge A => (S:A)) = (1.0,1.0);

	ifnone
	// comb arc negedge A --> (S:A)
	 (negedge A => (S:A)) = (1.0,1.0);

	ifnone
	// comb arc posedge B --> (S:B)
	 (posedge B => (S:B)) = (1.0,1.0);

	ifnone
	// comb arc negedge B --> (S:B)
	 (negedge B => (S:B)) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__ADDH_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__ADDH_4_V
`define GF180MCU_FD_SC_MCU9T5V0__ADDH_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__addh_4( A, B, CO, S, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__addh_4( A, B, CO, S );
`endif // If not USE_POWER_PINS
input A, B;
output CO, S;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__addh_func gf180mcu_fd_sc_mcu9t5v0__addh_inst(.A(A),.B(B),.CO(CO),.S(S),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__addh_func gf180mcu_fd_sc_mcu9t5v0__addh_inst(.A(A),.B(B),.CO(CO),.S(S));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A --> CO
	 (A => CO) = (1.0,1.0);

	// comb arc B --> CO
	 (B => CO) = (1.0,1.0);

	ifnone
	// comb arc posedge A --> (S:A)
	 (posedge A => (S:A)) = (1.0,1.0);

	ifnone
	// comb arc negedge A --> (S:A)
	 (negedge A => (S:A)) = (1.0,1.0);

	ifnone
	// comb arc posedge B --> (S:B)
	 (posedge B => (S:B)) = (1.0,1.0);

	ifnone
	// comb arc negedge B --> (S:B)
	 (negedge B => (S:B)) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__ADDH_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__ADDH_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__ADDH_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__addh_func( CO, A, B, S, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__addh_func( CO, A, B, S );
`endif // If not USE_POWER_PINS
input A, B;
output CO, S;

	and MGM_BG_0( CO, A, B );

	wire B_inv_for_gf180mcu_fd_sc_mcu9t5v0__addh_1;

	not MGM_BG_1( B_inv_for_gf180mcu_fd_sc_mcu9t5v0__addh_1, B );

	wire S_row1;

	and MGM_BG_2( S_row1, B_inv_for_gf180mcu_fd_sc_mcu9t5v0__addh_1, A );

	wire A_inv_for_gf180mcu_fd_sc_mcu9t5v0__addh_1;

	not MGM_BG_3( A_inv_for_gf180mcu_fd_sc_mcu9t5v0__addh_1, A );

	wire S_row2;

	and MGM_BG_4( S_row2, A_inv_for_gf180mcu_fd_sc_mcu9t5v0__addh_1, B );

	or MGM_BG_5( S, S_row1, S_row2 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__ADDH_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AND2_1_V
`define GF180MCU_FD_SC_MCU9T5V0__AND2_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and2_1( A1, A2, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and2_1( A1, A2, Z );
`endif // If not USE_POWER_PINS
input A1, A2;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__and2_func gf180mcu_fd_sc_mcu9t5v0__and2_inst(.A1(A1),.A2(A2),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__and2_func gf180mcu_fd_sc_mcu9t5v0__and2_inst(.A1(A1),.A2(A2),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AND2_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AND2_2_V
`define GF180MCU_FD_SC_MCU9T5V0__AND2_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and2_2( A1, A2, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and2_2( A1, A2, Z );
`endif // If not USE_POWER_PINS
input A1, A2;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__and2_func gf180mcu_fd_sc_mcu9t5v0__and2_inst(.A1(A1),.A2(A2),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__and2_func gf180mcu_fd_sc_mcu9t5v0__and2_inst(.A1(A1),.A2(A2),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AND2_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AND2_4_V
`define GF180MCU_FD_SC_MCU9T5V0__AND2_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and2_4( A2, A1, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and2_4( A2, A1, Z );
`endif // If not USE_POWER_PINS
input A1, A2;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__and2_func gf180mcu_fd_sc_mcu9t5v0__and2_inst(.A2(A2),.A1(A1),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__and2_func gf180mcu_fd_sc_mcu9t5v0__and2_inst(.A2(A2),.A1(A1),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AND2_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AND2_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__AND2_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and2_func( A1, A2, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and2_func( A1, A2, Z );
`endif // If not USE_POWER_PINS
input A1, A2;
output Z;

	and MGM_BG_0( Z, A1, A2 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AND2_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AND3_1_V
`define GF180MCU_FD_SC_MCU9T5V0__AND3_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and3_1( A1, A3, A2, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and3_1( A1, A3, A2, Z );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__and3_func gf180mcu_fd_sc_mcu9t5v0__and3_inst(.A1(A1),.A3(A3),.A2(A2),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__and3_func gf180mcu_fd_sc_mcu9t5v0__and3_inst(.A1(A1),.A3(A3),.A2(A2),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AND3_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AND3_2_V
`define GF180MCU_FD_SC_MCU9T5V0__AND3_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and3_2( A1, A2, A3, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and3_2( A1, A2, A3, Z );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__and3_func gf180mcu_fd_sc_mcu9t5v0__and3_inst(.A1(A1),.A2(A2),.A3(A3),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__and3_func gf180mcu_fd_sc_mcu9t5v0__and3_inst(.A1(A1),.A2(A2),.A3(A3),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AND3_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AND3_4_V
`define GF180MCU_FD_SC_MCU9T5V0__AND3_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and3_4( A3, A1, A2, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and3_4( A3, A1, A2, Z );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__and3_func gf180mcu_fd_sc_mcu9t5v0__and3_inst(.A3(A3),.A1(A1),.A2(A2),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__and3_func gf180mcu_fd_sc_mcu9t5v0__and3_inst(.A3(A3),.A1(A1),.A2(A2),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AND3_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AND3_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__AND3_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and3_func( A3, A1, A2, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and3_func( A3, A1, A2, Z );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output Z;

	and MGM_BG_0( Z, A1, A2, A3 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AND3_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AND4_1_V
`define GF180MCU_FD_SC_MCU9T5V0__AND4_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and4_1( A1, A2, A3, A4, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and4_1( A1, A2, A3, A4, Z );
`endif // If not USE_POWER_PINS
input A1, A2, A3, A4;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__and4_func gf180mcu_fd_sc_mcu9t5v0__and4_inst(.A1(A1),.A2(A2),.A3(A3),.A4(A4),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__and4_func gf180mcu_fd_sc_mcu9t5v0__and4_inst(.A1(A1),.A2(A2),.A3(A3),.A4(A4),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	// comb arc A4 --> Z
	 (A4 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AND4_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AND4_2_V
`define GF180MCU_FD_SC_MCU9T5V0__AND4_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and4_2( A1, A2, A3, A4, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and4_2( A1, A2, A3, A4, Z );
`endif // If not USE_POWER_PINS
input A1, A2, A3, A4;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__and4_func gf180mcu_fd_sc_mcu9t5v0__and4_inst(.A1(A1),.A2(A2),.A3(A3),.A4(A4),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__and4_func gf180mcu_fd_sc_mcu9t5v0__and4_inst(.A1(A1),.A2(A2),.A3(A3),.A4(A4),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	// comb arc A4 --> Z
	 (A4 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AND4_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AND4_4_V
`define GF180MCU_FD_SC_MCU9T5V0__AND4_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and4_4( A4, A3, A1, A2, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and4_4( A4, A3, A1, A2, Z );
`endif // If not USE_POWER_PINS
input A1, A2, A3, A4;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__and4_func gf180mcu_fd_sc_mcu9t5v0__and4_inst(.A4(A4),.A3(A3),.A1(A1),.A2(A2),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__and4_func gf180mcu_fd_sc_mcu9t5v0__and4_inst(.A4(A4),.A3(A3),.A1(A1),.A2(A2),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	// comb arc A4 --> Z
	 (A4 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AND4_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AND4_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__AND4_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and4_func( A4, A3, A1, A2, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__and4_func( A4, A3, A1, A2, Z );
`endif // If not USE_POWER_PINS
input A1, A2, A3, A4;
output Z;

	and MGM_BG_0( Z, A1, A2, A3, A4 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AND4_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__ANTENNA_V
`define GF180MCU_FD_SC_MCU9T5V0__ANTENNA_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__antenna( I, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__antenna( I );
`endif // If not USE_POWER_PINS
input I;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__antenna_func gf180mcu_fd_sc_mcu9t5v0__antenna_inst(.I(I),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__antenna_func gf180mcu_fd_sc_mcu9t5v0__antenna_inst(.I(I));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__ANTENNA_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__ANTENNA_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__ANTENNA_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__antenna_func( I, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__antenna_func( I );
`endif // If not USE_POWER_PINS
input I;

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__ANTENNA_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AOI21_1_V
`define GF180MCU_FD_SC_MCU9T5V0__AOI21_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi21_1( A2, ZN, A1, B, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi21_1( A2, ZN, A1, B );
`endif // If not USE_POWER_PINS
input A1, A2, B;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi21_func gf180mcu_fd_sc_mcu9t5v0__aoi21_inst(.A2(A2),.ZN(ZN),.A1(A1),.B(B),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi21_func gf180mcu_fd_sc_mcu9t5v0__aoi21_inst(.A2(A2),.ZN(ZN),.A1(A1),.B(B));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	ifnone
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AOI21_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AOI21_2_V
`define GF180MCU_FD_SC_MCU9T5V0__AOI21_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi21_2( B, ZN, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi21_2( B, ZN, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, B;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi21_func gf180mcu_fd_sc_mcu9t5v0__aoi21_inst(.B(B),.ZN(ZN),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi21_func gf180mcu_fd_sc_mcu9t5v0__aoi21_inst(.B(B),.ZN(ZN),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	ifnone
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AOI21_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AOI21_4_V
`define GF180MCU_FD_SC_MCU9T5V0__AOI21_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi21_4( A1, A2, ZN, B, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi21_4( A1, A2, ZN, B );
`endif // If not USE_POWER_PINS
input A1, A2, B;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi21_func gf180mcu_fd_sc_mcu9t5v0__aoi21_inst(.A1(A1),.A2(A2),.ZN(ZN),.B(B),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi21_func gf180mcu_fd_sc_mcu9t5v0__aoi21_inst(.A1(A1),.A2(A2),.ZN(ZN),.B(B));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	ifnone
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AOI21_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AOI21_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__AOI21_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi21_func( A1, A2, ZN, B, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi21_func( A1, A2, ZN, B );
`endif // If not USE_POWER_PINS
input A1, A2, B;
output ZN;

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi21_4;

	not MGM_BG_0( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi21_4, A1 );

	wire B_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi21_4;

	not MGM_BG_1( B_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi21_4, B );

	wire ZN_row1;

	and MGM_BG_2( ZN_row1, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi21_4, B_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi21_4 );

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi21_4;

	not MGM_BG_3( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi21_4, A2 );

	wire ZN_row2;

	and MGM_BG_4( ZN_row2, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi21_4, B_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi21_4 );

	or MGM_BG_5( ZN, ZN_row1, ZN_row2 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AOI21_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AOI22_1_V
`define GF180MCU_FD_SC_MCU9T5V0__AOI22_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi22_1( B2, B1, ZN, A1, A2, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi22_1( B2, B1, ZN, A1, A2 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi22_func gf180mcu_fd_sc_mcu9t5v0__aoi22_inst(.B2(B2),.B1(B1),.ZN(ZN),.A1(A1),.A2(A2),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi22_func gf180mcu_fd_sc_mcu9t5v0__aoi22_inst(.B2(B2),.B1(B1),.ZN(ZN),.A1(A1),.A2(A2));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AOI22_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AOI22_2_V
`define GF180MCU_FD_SC_MCU9T5V0__AOI22_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi22_2( B2, B1, ZN, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi22_2( B2, B1, ZN, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi22_func gf180mcu_fd_sc_mcu9t5v0__aoi22_inst(.B2(B2),.B1(B1),.ZN(ZN),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi22_func gf180mcu_fd_sc_mcu9t5v0__aoi22_inst(.B2(B2),.B1(B1),.ZN(ZN),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AOI22_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AOI22_4_V
`define GF180MCU_FD_SC_MCU9T5V0__AOI22_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi22_4( B2, ZN, B1, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi22_4( B2, ZN, B1, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi22_func gf180mcu_fd_sc_mcu9t5v0__aoi22_inst(.B2(B2),.ZN(ZN),.B1(B1),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi22_func gf180mcu_fd_sc_mcu9t5v0__aoi22_inst(.B2(B2),.ZN(ZN),.B1(B1),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AOI22_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AOI22_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__AOI22_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi22_func( B2, B1, ZN, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi22_func( B2, B1, ZN, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2;
output ZN;

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi22_2;

	not MGM_BG_0( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi22_2, A1 );

	wire B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi22_2;

	not MGM_BG_1( B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi22_2, B1 );

	wire ZN_row1;

	and MGM_BG_2( ZN_row1, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi22_2, B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi22_2 );

	wire B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi22_2;

	not MGM_BG_3( B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi22_2, B2 );

	wire ZN_row2;

	and MGM_BG_4( ZN_row2, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi22_2, B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi22_2 );

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi22_2;

	not MGM_BG_5( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi22_2, A2 );

	wire ZN_row3;

	and MGM_BG_6( ZN_row3, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi22_2, B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi22_2 );

	wire ZN_row4;

	and MGM_BG_7( ZN_row4, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi22_2, B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi22_2 );

	or MGM_BG_8( ZN, ZN_row1, ZN_row2, ZN_row3, ZN_row4 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AOI22_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AOI211_1_V
`define GF180MCU_FD_SC_MCU9T5V0__AOI211_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi211_1( A2, ZN, A1, B, C, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi211_1( A2, ZN, A1, B, C );
`endif // If not USE_POWER_PINS
input A1, A2, B, C;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi211_func gf180mcu_fd_sc_mcu9t5v0__aoi211_inst(.A2(A2),.ZN(ZN),.A1(A1),.B(B),.C(C),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi211_func gf180mcu_fd_sc_mcu9t5v0__aoi211_inst(.A2(A2),.ZN(ZN),.A1(A1),.B(B),.C(C));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	ifnone
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	ifnone
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AOI211_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AOI211_2_V
`define GF180MCU_FD_SC_MCU9T5V0__AOI211_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi211_2( A2, ZN, A1, B, C, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi211_2( A2, ZN, A1, B, C );
`endif // If not USE_POWER_PINS
input A1, A2, B, C;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi211_func gf180mcu_fd_sc_mcu9t5v0__aoi211_inst(.A2(A2),.ZN(ZN),.A1(A1),.B(B),.C(C),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi211_func gf180mcu_fd_sc_mcu9t5v0__aoi211_inst(.A2(A2),.ZN(ZN),.A1(A1),.B(B),.C(C));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	ifnone
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	ifnone
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AOI211_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AOI211_4_V
`define GF180MCU_FD_SC_MCU9T5V0__AOI211_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi211_4( ZN, A2, A1, B, C, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi211_4( ZN, A2, A1, B, C );
`endif // If not USE_POWER_PINS
input A1, A2, B, C;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi211_func gf180mcu_fd_sc_mcu9t5v0__aoi211_inst(.ZN(ZN),.A2(A2),.A1(A1),.B(B),.C(C),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi211_func gf180mcu_fd_sc_mcu9t5v0__aoi211_inst(.ZN(ZN),.A2(A2),.A1(A1),.B(B),.C(C));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	ifnone
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	ifnone
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AOI211_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AOI211_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__AOI211_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi211_func( ZN, A2, A1, B, C, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi211_func( ZN, A2, A1, B, C );
`endif // If not USE_POWER_PINS
input A1, A2, B, C;
output ZN;

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi211_4;

	not MGM_BG_0( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi211_4, A1 );

	wire B_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi211_4;

	not MGM_BG_1( B_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi211_4, B );

	wire C_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi211_4;

	not MGM_BG_2( C_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi211_4, C );

	wire ZN_row1;

	and MGM_BG_3( ZN_row1, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi211_4, B_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi211_4, C_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi211_4 );

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi211_4;

	not MGM_BG_4( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi211_4, A2 );

	wire ZN_row2;

	and MGM_BG_5( ZN_row2, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi211_4, B_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi211_4, C_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi211_4 );

	or MGM_BG_6( ZN, ZN_row1, ZN_row2 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AOI211_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AOI221_1_V
`define GF180MCU_FD_SC_MCU9T5V0__AOI221_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi221_1( B2, B1, C, ZN, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi221_1( B2, B1, C, ZN, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2, C;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi221_func gf180mcu_fd_sc_mcu9t5v0__aoi221_inst(.B2(B2),.B1(B1),.C(C),.ZN(ZN),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi221_func gf180mcu_fd_sc_mcu9t5v0__aoi221_inst(.B2(B2),.B1(B1),.C(C),.ZN(ZN),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b0 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	ifnone
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AOI221_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AOI221_2_V
`define GF180MCU_FD_SC_MCU9T5V0__AOI221_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi221_2( ZN, C, B2, B1, A1, A2, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi221_2( ZN, C, B2, B1, A1, A2 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2, C;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi221_func gf180mcu_fd_sc_mcu9t5v0__aoi221_inst(.ZN(ZN),.C(C),.B2(B2),.B1(B1),.A1(A1),.A2(A2),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi221_func gf180mcu_fd_sc_mcu9t5v0__aoi221_inst(.ZN(ZN),.C(C),.B2(B2),.B1(B1),.A1(A1),.A2(A2));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b0 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	ifnone
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AOI221_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AOI221_4_V
`define GF180MCU_FD_SC_MCU9T5V0__AOI221_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi221_4( ZN, B1, B2, C, A1, A2, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi221_4( ZN, B1, B2, C, A1, A2 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2, C;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi221_func gf180mcu_fd_sc_mcu9t5v0__aoi221_inst(.ZN(ZN),.B1(B1),.B2(B2),.C(C),.A1(A1),.A2(A2),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi221_func gf180mcu_fd_sc_mcu9t5v0__aoi221_inst(.ZN(ZN),.B1(B1),.B2(B2),.C(C),.A1(A1),.A2(A2));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b0 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	ifnone
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AOI221_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AOI221_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__AOI221_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi221_func( ZN, C, B2, B1, A1, A2, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi221_func( ZN, C, B2, B1, A1, A2 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2, C;
output ZN;

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi221_2;

	not MGM_BG_0( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi221_2, A1 );

	wire B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi221_2;

	not MGM_BG_1( B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi221_2, B1 );

	wire C_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi221_2;

	not MGM_BG_2( C_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi221_2, C );

	wire ZN_row1;

	and MGM_BG_3( ZN_row1, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi221_2, B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi221_2, C_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi221_2 );

	wire B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi221_2;

	not MGM_BG_4( B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi221_2, B2 );

	wire ZN_row2;

	and MGM_BG_5( ZN_row2, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi221_2, B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi221_2, C_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi221_2 );

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi221_2;

	not MGM_BG_6( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi221_2, A2 );

	wire ZN_row3;

	and MGM_BG_7( ZN_row3, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi221_2, B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi221_2, C_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi221_2 );

	wire ZN_row4;

	and MGM_BG_8( ZN_row4, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi221_2, B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi221_2, C_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi221_2 );

	or MGM_BG_9( ZN, ZN_row1, ZN_row2, ZN_row3, ZN_row4 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AOI221_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AOI222_1_V
`define GF180MCU_FD_SC_MCU9T5V0__AOI222_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi222_1( C2, C1, B1, ZN, B2, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi222_1( C2, C1, B1, ZN, B2, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2, C1, C2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi222_func gf180mcu_fd_sc_mcu9t5v0__aoi222_inst(.C2(C2),.C1(C1),.B1(B1),.ZN(ZN),.B2(B2),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi222_func gf180mcu_fd_sc_mcu9t5v0__aoi222_inst(.C2(C2),.C1(C1),.B1(B1),.ZN(ZN),.B2(B2),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b0 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b0 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b0 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b0 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b0 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b0 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AOI222_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AOI222_2_V
`define GF180MCU_FD_SC_MCU9T5V0__AOI222_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi222_2( C1, ZN, C2, B2, B1, A1, A2, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi222_2( C1, ZN, C2, B2, B1, A1, A2 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2, C1, C2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi222_func gf180mcu_fd_sc_mcu9t5v0__aoi222_inst(.C1(C1),.ZN(ZN),.C2(C2),.B2(B2),.B1(B1),.A1(A1),.A2(A2),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi222_func gf180mcu_fd_sc_mcu9t5v0__aoi222_inst(.C1(C1),.ZN(ZN),.C2(C2),.B2(B2),.B1(B1),.A1(A1),.A2(A2));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b0 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b0 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b0 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b0 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b0 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b0 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AOI222_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AOI222_4_V
`define GF180MCU_FD_SC_MCU9T5V0__AOI222_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi222_4( ZN, C1, C2, B1, B2, A1, A2, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi222_4( ZN, C1, C2, B1, B2, A1, A2 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2, C1, C2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi222_func gf180mcu_fd_sc_mcu9t5v0__aoi222_inst(.ZN(ZN),.C1(C1),.C2(C2),.B1(B1),.B2(B2),.A1(A1),.A2(A2),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__aoi222_func gf180mcu_fd_sc_mcu9t5v0__aoi222_inst(.ZN(ZN),.C1(C1),.C2(C2),.B1(B1),.B2(B2),.A1(A1),.A2(A2));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b0 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b0 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b0 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b0 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b0 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b0 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b0 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AOI222_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__AOI222_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__AOI222_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi222_func( ZN, C1, C2, B1, B2, A1, A2, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__aoi222_func( ZN, C1, C2, B1, B2, A1, A2 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2, C1, C2;
output ZN;

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4;

	not MGM_BG_0( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4, A1 );

	wire B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4;

	not MGM_BG_1( B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4, B1 );

	wire C1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4;

	not MGM_BG_2( C1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4, C1 );

	wire ZN_row1;

	and MGM_BG_3( ZN_row1, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4, B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4, C1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4 );

	wire C2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4;

	not MGM_BG_4( C2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4, C2 );

	wire ZN_row2;

	and MGM_BG_5( ZN_row2, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4, B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4, C2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4 );

	wire B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4;

	not MGM_BG_6( B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4, B2 );

	wire ZN_row3;

	and MGM_BG_7( ZN_row3, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4, B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4, C1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4 );

	wire ZN_row4;

	and MGM_BG_8( ZN_row4, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4, B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4, C2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4 );

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4;

	not MGM_BG_9( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4, A2 );

	wire ZN_row5;

	and MGM_BG_10( ZN_row5, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4, B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4, C1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4 );

	wire ZN_row6;

	and MGM_BG_11( ZN_row6, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4, B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4, C2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4 );

	wire ZN_row7;

	and MGM_BG_12( ZN_row7, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4, B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4, C1_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4 );

	wire ZN_row8;

	and MGM_BG_13( ZN_row8, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4, B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4, C2_inv_for_gf180mcu_fd_sc_mcu9t5v0__aoi222_4 );

	or MGM_BG_14( ZN, ZN_row1, ZN_row2, ZN_row3, ZN_row4, ZN_row5, ZN_row6, ZN_row7, ZN_row8 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__AOI222_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__BUF_1_V
`define GF180MCU_FD_SC_MCU9T5V0__BUF_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__buf_1( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__buf_1( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__buf_func gf180mcu_fd_sc_mcu9t5v0__buf_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__buf_func gf180mcu_fd_sc_mcu9t5v0__buf_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__BUF_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__BUF_2_V
`define GF180MCU_FD_SC_MCU9T5V0__BUF_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__buf_2( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__buf_2( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__buf_func gf180mcu_fd_sc_mcu9t5v0__buf_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__buf_func gf180mcu_fd_sc_mcu9t5v0__buf_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__BUF_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__BUF_3_V
`define GF180MCU_FD_SC_MCU9T5V0__BUF_3_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__buf_3( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__buf_3( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__buf_func gf180mcu_fd_sc_mcu9t5v0__buf_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__buf_func gf180mcu_fd_sc_mcu9t5v0__buf_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__BUF_3_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__BUF_4_V
`define GF180MCU_FD_SC_MCU9T5V0__BUF_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__buf_4( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__buf_4( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__buf_func gf180mcu_fd_sc_mcu9t5v0__buf_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__buf_func gf180mcu_fd_sc_mcu9t5v0__buf_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__BUF_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__BUF_8_V
`define GF180MCU_FD_SC_MCU9T5V0__BUF_8_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__buf_8( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__buf_8( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__buf_func gf180mcu_fd_sc_mcu9t5v0__buf_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__buf_func gf180mcu_fd_sc_mcu9t5v0__buf_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__BUF_8_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__BUF_12_V
`define GF180MCU_FD_SC_MCU9T5V0__BUF_12_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__buf_12( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__buf_12( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__buf_func gf180mcu_fd_sc_mcu9t5v0__buf_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__buf_func gf180mcu_fd_sc_mcu9t5v0__buf_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__BUF_12_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__BUF_16_V
`define GF180MCU_FD_SC_MCU9T5V0__BUF_16_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__buf_16( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__buf_16( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__buf_func gf180mcu_fd_sc_mcu9t5v0__buf_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__buf_func gf180mcu_fd_sc_mcu9t5v0__buf_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__BUF_16_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__BUF_20_V
`define GF180MCU_FD_SC_MCU9T5V0__BUF_20_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__buf_20( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__buf_20( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__buf_func gf180mcu_fd_sc_mcu9t5v0__buf_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__buf_func gf180mcu_fd_sc_mcu9t5v0__buf_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__BUF_20_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__BUF_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__BUF_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__buf_func( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__buf_func( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

	buf MGM_BG_0( Z, I );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__BUF_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__BUFZ_1_V
`define GF180MCU_FD_SC_MCU9T5V0__BUFZ_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__bufz_1( EN, I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__bufz_1( EN, I, Z );
`endif // If not USE_POWER_PINS
input EN, I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__bufz_func gf180mcu_fd_sc_mcu9t5v0__bufz_inst(.EN(EN),.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__bufz_func gf180mcu_fd_sc_mcu9t5v0__bufz_inst(.EN(EN),.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc EN --> Z
	 (EN => Z) = (1.0,1.0);

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__BUFZ_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__BUFZ_2_V
`define GF180MCU_FD_SC_MCU9T5V0__BUFZ_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__bufz_2( EN, I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__bufz_2( EN, I, Z );
`endif // If not USE_POWER_PINS
input EN, I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__bufz_func gf180mcu_fd_sc_mcu9t5v0__bufz_inst(.EN(EN),.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__bufz_func gf180mcu_fd_sc_mcu9t5v0__bufz_inst(.EN(EN),.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc EN --> Z
	 (EN => Z) = (1.0,1.0);

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__BUFZ_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__BUFZ_3_V
`define GF180MCU_FD_SC_MCU9T5V0__BUFZ_3_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__bufz_3( EN, I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__bufz_3( EN, I, Z );
`endif // If not USE_POWER_PINS
input EN, I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__bufz_func gf180mcu_fd_sc_mcu9t5v0__bufz_inst(.EN(EN),.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__bufz_func gf180mcu_fd_sc_mcu9t5v0__bufz_inst(.EN(EN),.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc EN --> Z
	 (EN => Z) = (1.0,1.0);

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__BUFZ_3_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__BUFZ_4_V
`define GF180MCU_FD_SC_MCU9T5V0__BUFZ_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__bufz_4( EN, I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__bufz_4( EN, I, Z );
`endif // If not USE_POWER_PINS
input EN, I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__bufz_func gf180mcu_fd_sc_mcu9t5v0__bufz_inst(.EN(EN),.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__bufz_func gf180mcu_fd_sc_mcu9t5v0__bufz_inst(.EN(EN),.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc EN --> Z
	 (EN => Z) = (1.0,1.0);

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__BUFZ_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__BUFZ_8_V
`define GF180MCU_FD_SC_MCU9T5V0__BUFZ_8_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__bufz_8( EN, I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__bufz_8( EN, I, Z );
`endif // If not USE_POWER_PINS
input EN, I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__bufz_func gf180mcu_fd_sc_mcu9t5v0__bufz_inst(.EN(EN),.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__bufz_func gf180mcu_fd_sc_mcu9t5v0__bufz_inst(.EN(EN),.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc EN --> Z
	 (EN => Z) = (1.0,1.0);

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__BUFZ_8_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__BUFZ_12_V
`define GF180MCU_FD_SC_MCU9T5V0__BUFZ_12_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__bufz_12( EN, I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__bufz_12( EN, I, Z );
`endif // If not USE_POWER_PINS
input EN, I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__bufz_func gf180mcu_fd_sc_mcu9t5v0__bufz_inst(.EN(EN),.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__bufz_func gf180mcu_fd_sc_mcu9t5v0__bufz_inst(.EN(EN),.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc EN --> Z
	 (EN => Z) = (1.0,1.0);

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__BUFZ_12_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__BUFZ_16_V
`define GF180MCU_FD_SC_MCU9T5V0__BUFZ_16_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__bufz_16( EN, I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__bufz_16( EN, I, Z );
`endif // If not USE_POWER_PINS
input EN, I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__bufz_func gf180mcu_fd_sc_mcu9t5v0__bufz_inst(.EN(EN),.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__bufz_func gf180mcu_fd_sc_mcu9t5v0__bufz_inst(.EN(EN),.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc EN --> Z
	 (EN => Z) = (1.0,1.0);

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__BUFZ_16_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__BUFZ_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__BUFZ_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__bufz_func( EN, I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__bufz_func( EN, I, Z );
`endif // If not USE_POWER_PINS
input EN, I;
output Z;

	wire MGM_WB_0;

	wire MGM_WB_1;

	and MGM_BG_0( MGM_WB_0, EN, I );

	not MGM_BG_1( MGM_WB_1, EN );

	bufif0 MGM_BG_2( Z, MGM_WB_0,MGM_WB_1 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__BUFZ_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__CLKBUF_1_V
`define GF180MCU_FD_SC_MCU9T5V0__CLKBUF_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkbuf_1( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkbuf_1( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkbuf_func gf180mcu_fd_sc_mcu9t5v0__clkbuf_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkbuf_func gf180mcu_fd_sc_mcu9t5v0__clkbuf_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__CLKBUF_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__CLKBUF_2_V
`define GF180MCU_FD_SC_MCU9T5V0__CLKBUF_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkbuf_2( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkbuf_2( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkbuf_func gf180mcu_fd_sc_mcu9t5v0__clkbuf_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkbuf_func gf180mcu_fd_sc_mcu9t5v0__clkbuf_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__CLKBUF_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__CLKBUF_3_V
`define GF180MCU_FD_SC_MCU9T5V0__CLKBUF_3_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkbuf_3( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkbuf_3( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkbuf_func gf180mcu_fd_sc_mcu9t5v0__clkbuf_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkbuf_func gf180mcu_fd_sc_mcu9t5v0__clkbuf_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__CLKBUF_3_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__CLKBUF_4_V
`define GF180MCU_FD_SC_MCU9T5V0__CLKBUF_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkbuf_4( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkbuf_4( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkbuf_func gf180mcu_fd_sc_mcu9t5v0__clkbuf_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkbuf_func gf180mcu_fd_sc_mcu9t5v0__clkbuf_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__CLKBUF_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__CLKBUF_8_V
`define GF180MCU_FD_SC_MCU9T5V0__CLKBUF_8_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkbuf_8( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkbuf_8( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkbuf_func gf180mcu_fd_sc_mcu9t5v0__clkbuf_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkbuf_func gf180mcu_fd_sc_mcu9t5v0__clkbuf_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__CLKBUF_8_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__CLKBUF_12_V
`define GF180MCU_FD_SC_MCU9T5V0__CLKBUF_12_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkbuf_12( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkbuf_12( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkbuf_func gf180mcu_fd_sc_mcu9t5v0__clkbuf_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkbuf_func gf180mcu_fd_sc_mcu9t5v0__clkbuf_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__CLKBUF_12_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__CLKBUF_16_V
`define GF180MCU_FD_SC_MCU9T5V0__CLKBUF_16_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkbuf_16( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkbuf_16( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkbuf_func gf180mcu_fd_sc_mcu9t5v0__clkbuf_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkbuf_func gf180mcu_fd_sc_mcu9t5v0__clkbuf_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__CLKBUF_16_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__CLKBUF_20_V
`define GF180MCU_FD_SC_MCU9T5V0__CLKBUF_20_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkbuf_20( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkbuf_20( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkbuf_func gf180mcu_fd_sc_mcu9t5v0__clkbuf_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkbuf_func gf180mcu_fd_sc_mcu9t5v0__clkbuf_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__CLKBUF_20_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__CLKBUF_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__CLKBUF_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkbuf_func( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkbuf_func( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

	buf MGM_BG_0( Z, I );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__CLKBUF_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__CLKINV_1_V
`define GF180MCU_FD_SC_MCU9T5V0__CLKINV_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkinv_1( I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkinv_1( I, ZN );
`endif // If not USE_POWER_PINS
input I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkinv_func gf180mcu_fd_sc_mcu9t5v0__clkinv_inst(.I(I),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkinv_func gf180mcu_fd_sc_mcu9t5v0__clkinv_inst(.I(I),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__CLKINV_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__CLKINV_2_V
`define GF180MCU_FD_SC_MCU9T5V0__CLKINV_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkinv_2( I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkinv_2( I, ZN );
`endif // If not USE_POWER_PINS
input I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkinv_func gf180mcu_fd_sc_mcu9t5v0__clkinv_inst(.I(I),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkinv_func gf180mcu_fd_sc_mcu9t5v0__clkinv_inst(.I(I),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__CLKINV_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__CLKINV_3_V
`define GF180MCU_FD_SC_MCU9T5V0__CLKINV_3_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkinv_3( I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkinv_3( I, ZN );
`endif // If not USE_POWER_PINS
input I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkinv_func gf180mcu_fd_sc_mcu9t5v0__clkinv_inst(.I(I),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkinv_func gf180mcu_fd_sc_mcu9t5v0__clkinv_inst(.I(I),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__CLKINV_3_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__CLKINV_4_V
`define GF180MCU_FD_SC_MCU9T5V0__CLKINV_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkinv_4( I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkinv_4( I, ZN );
`endif // If not USE_POWER_PINS
input I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkinv_func gf180mcu_fd_sc_mcu9t5v0__clkinv_inst(.I(I),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkinv_func gf180mcu_fd_sc_mcu9t5v0__clkinv_inst(.I(I),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__CLKINV_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__CLKINV_8_V
`define GF180MCU_FD_SC_MCU9T5V0__CLKINV_8_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkinv_8( I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkinv_8( I, ZN );
`endif // If not USE_POWER_PINS
input I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkinv_func gf180mcu_fd_sc_mcu9t5v0__clkinv_inst(.I(I),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkinv_func gf180mcu_fd_sc_mcu9t5v0__clkinv_inst(.I(I),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__CLKINV_8_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__CLKINV_12_V
`define GF180MCU_FD_SC_MCU9T5V0__CLKINV_12_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkinv_12( I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkinv_12( I, ZN );
`endif // If not USE_POWER_PINS
input I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkinv_func gf180mcu_fd_sc_mcu9t5v0__clkinv_inst(.I(I),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkinv_func gf180mcu_fd_sc_mcu9t5v0__clkinv_inst(.I(I),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__CLKINV_12_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__CLKINV_16_V
`define GF180MCU_FD_SC_MCU9T5V0__CLKINV_16_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkinv_16( I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkinv_16( I, ZN );
`endif // If not USE_POWER_PINS
input I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkinv_func gf180mcu_fd_sc_mcu9t5v0__clkinv_inst(.I(I),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkinv_func gf180mcu_fd_sc_mcu9t5v0__clkinv_inst(.I(I),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__CLKINV_16_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__CLKINV_20_V
`define GF180MCU_FD_SC_MCU9T5V0__CLKINV_20_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkinv_20( I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkinv_20( I, ZN );
`endif // If not USE_POWER_PINS
input I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkinv_func gf180mcu_fd_sc_mcu9t5v0__clkinv_inst(.I(I),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__clkinv_func gf180mcu_fd_sc_mcu9t5v0__clkinv_inst(.I(I),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__CLKINV_20_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__CLKINV_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__CLKINV_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkinv_func( I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__clkinv_func( I, ZN );
`endif // If not USE_POWER_PINS
input I;
output ZN;

	not MGM_BG_0( ZN, I );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__CLKINV_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFNQ_1_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFNQ_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnq_1( CLKN, D, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnq_1( CLKN, D, Q );
`endif // If not USE_POWER_PINS
input CLKN, D;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnq_func gf180mcu_fd_sc_mcu9t5v0__dffnq_inst(.CLKN(CLKN),.D(D),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnq_func gf180mcu_fd_sc_mcu9t5v0__dffnq_inst(.CLKN(CLKN),.D(D),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(ENABLE_NOT_D,D);


	buf MGM_G1(ENABLE_D,D);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLKN --> Q
	(negedge CLKN => (Q : D))  = (1.0,1.0);

	$width(negedge CLKN &&& (ENABLE_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLKN &&& (ENABLE_D === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_D === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLKN-HL
	$hold(negedge CLKN,negedge D,1.0,notifier);

	// hold D-LH CLKN-HL
	$hold(negedge CLKN,posedge D,1.0,notifier);

	// setup D-HL CLKN-HL
	$setup(negedge D,negedge CLKN,1.0,notifier);

	// setup D-LH CLKN-HL
	$setup(posedge D,negedge CLKN,1.0,notifier);

	// mpw CLKN_lh
	$width(posedge CLKN,1.0,0,notifier);

	// mpw CLKN_hl
	$width(negedge CLKN,1.0,0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_NOT_D === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_D === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(posedge CLKN,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFNQ_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFNQ_2_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFNQ_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnq_2( CLKN, D, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnq_2( CLKN, D, Q );
`endif // If not USE_POWER_PINS
input CLKN, D;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnq_func gf180mcu_fd_sc_mcu9t5v0__dffnq_inst(.CLKN(CLKN),.D(D),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnq_func gf180mcu_fd_sc_mcu9t5v0__dffnq_inst(.CLKN(CLKN),.D(D),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(ENABLE_NOT_D,D);


	buf MGM_G1(ENABLE_D,D);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLKN --> Q
	(negedge CLKN => (Q : D))  = (1.0,1.0);

	$width(negedge CLKN &&& (ENABLE_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLKN &&& (ENABLE_D === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_D === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLKN-HL
	$hold(negedge CLKN,negedge D,1.0,notifier);

	// hold D-LH CLKN-HL
	$hold(negedge CLKN,posedge D,1.0,notifier);

	// setup D-HL CLKN-HL
	$setup(negedge D,negedge CLKN,1.0,notifier);

	// setup D-LH CLKN-HL
	$setup(posedge D,negedge CLKN,1.0,notifier);

	// mpw CLKN_lh
	$width(posedge CLKN,1.0,0,notifier);

	// mpw CLKN_hl
	$width(negedge CLKN,1.0,0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_NOT_D === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_D === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(posedge CLKN,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFNQ_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFNQ_4_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFNQ_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnq_4( CLKN, D, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnq_4( CLKN, D, Q );
`endif // If not USE_POWER_PINS
input CLKN, D;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnq_func gf180mcu_fd_sc_mcu9t5v0__dffnq_inst(.CLKN(CLKN),.D(D),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnq_func gf180mcu_fd_sc_mcu9t5v0__dffnq_inst(.CLKN(CLKN),.D(D),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(ENABLE_NOT_D,D);


	buf MGM_G1(ENABLE_D,D);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLKN --> Q
	(negedge CLKN => (Q : D))  = (1.0,1.0);

	$width(negedge CLKN &&& (ENABLE_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLKN &&& (ENABLE_D === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_D === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLKN-HL
	$hold(negedge CLKN,negedge D,1.0,notifier);

	// hold D-LH CLKN-HL
	$hold(negedge CLKN,posedge D,1.0,notifier);

	// setup D-HL CLKN-HL
	$setup(negedge D,negedge CLKN,1.0,notifier);

	// setup D-LH CLKN-HL
	$setup(posedge D,negedge CLKN,1.0,notifier);

	// mpw CLKN_lh
	$width(posedge CLKN,1.0,0,notifier);

	// mpw CLKN_hl
	$width(negedge CLKN,1.0,0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_NOT_D === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_D === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(posedge CLKN,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFNQ_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFNQ_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFNQ_FUNC_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnq_func( CLKN, D, Q, VDD, VSS, VNW, VPW, notifier );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnq_func( CLKN, D, Q, notifier );
`endif // If not USE_POWER_PINS
input CLKN, D, notifier;
output Q;

	not MGM_BG_0( MGM_CLK0, CLKN );

	not MGM_BG_1( MGM_D0, D );

	gf180mcu_fd_sc_mcu9t5v0__udp_n_iq_ff( IQ1, 1'b0, 1'b0, MGM_CLK0, MGM_D0, notifier );

	not MGM_BG_2( Q, IQ1 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFNQ_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFNRNQ_1_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFNRNQ_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnrnq_1( CLKN, D, RN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnrnq_1( CLKN, D, RN, Q );
`endif // If not USE_POWER_PINS
input CLKN, D, RN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnrnq_func gf180mcu_fd_sc_mcu9t5v0__dffnrnq_inst(.CLKN(CLKN),.D(D),.RN(RN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnrnq_func gf180mcu_fd_sc_mcu9t5v0__dffnrnq_inst(.CLKN(CLKN),.D(D),.RN(RN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(ENABLE_NOT_D_AND_RN,RN,MGM_W0);


	and MGM_G2(ENABLE_D_AND_RN,RN,D);


	buf MGM_G3(ENABLE_RN,RN);


	not MGM_G4(MGM_W1,CLKN);


	not MGM_G5(MGM_W2,D);


	and MGM_G6(ENABLE_NOT_CLKN_AND_NOT_D,MGM_W2,MGM_W1);


	not MGM_G7(MGM_W3,CLKN);


	and MGM_G8(ENABLE_NOT_CLKN_AND_D,D,MGM_W3);


	not MGM_G9(MGM_W4,D);


	and MGM_G10(ENABLE_CLKN_AND_NOT_D,MGM_W4,CLKN);


	and MGM_G11(ENABLE_CLKN_AND_D,D,CLKN);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLKN --> Q
	(negedge CLKN => (Q : D))  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	$width(negedge CLKN &&& (ENABLE_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLKN &&& (ENABLE_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLKN-HL
	$hold(negedge CLKN &&& (ENABLE_RN === 1'b1),
		negedge D &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// hold D-LH CLKN-HL
	$hold(negedge CLKN &&& (ENABLE_RN === 1'b1),
		posedge D &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// setup D-HL CLKN-HL
	$setup(negedge D &&& (ENABLE_RN === 1'b1),
		negedge CLKN &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// setup D-LH CLKN-HL
	$setup(posedge D &&& (ENABLE_RN === 1'b1),
		negedge CLKN &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// recovery RN-LH CLKN-HL
	$recovery(posedge RN,negedge CLKN,1.0,notifier);

	// removal RN-LH CLKN-HL
	$removal(posedge RN,negedge CLKN,1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLKN_AND_D === 1'b1)
		,1.0,0,notifier);

	// mpw CLKN_lh
	$width(posedge CLKN,1.0,0,notifier);

	// mpw CLKN_hl
	$width(negedge CLKN,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_NOT_D_AND_RN === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_D_AND_RN === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(posedge CLKN,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFNRNQ_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFNRNQ_2_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFNRNQ_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnrnq_2( CLKN, D, RN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnrnq_2( CLKN, D, RN, Q );
`endif // If not USE_POWER_PINS
input CLKN, D, RN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnrnq_func gf180mcu_fd_sc_mcu9t5v0__dffnrnq_inst(.CLKN(CLKN),.D(D),.RN(RN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnrnq_func gf180mcu_fd_sc_mcu9t5v0__dffnrnq_inst(.CLKN(CLKN),.D(D),.RN(RN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(ENABLE_NOT_D_AND_RN,RN,MGM_W0);


	and MGM_G2(ENABLE_D_AND_RN,RN,D);


	buf MGM_G3(ENABLE_RN,RN);


	not MGM_G4(MGM_W1,CLKN);


	not MGM_G5(MGM_W2,D);


	and MGM_G6(ENABLE_NOT_CLKN_AND_NOT_D,MGM_W2,MGM_W1);


	not MGM_G7(MGM_W3,CLKN);


	and MGM_G8(ENABLE_NOT_CLKN_AND_D,D,MGM_W3);


	not MGM_G9(MGM_W4,D);


	and MGM_G10(ENABLE_CLKN_AND_NOT_D,MGM_W4,CLKN);


	and MGM_G11(ENABLE_CLKN_AND_D,D,CLKN);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLKN --> Q
	(negedge CLKN => (Q : D))  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	$width(negedge CLKN &&& (ENABLE_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLKN &&& (ENABLE_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLKN-HL
	$hold(negedge CLKN &&& (ENABLE_RN === 1'b1),
		negedge D &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// hold D-LH CLKN-HL
	$hold(negedge CLKN &&& (ENABLE_RN === 1'b1),
		posedge D &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// setup D-HL CLKN-HL
	$setup(negedge D &&& (ENABLE_RN === 1'b1),
		negedge CLKN &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// setup D-LH CLKN-HL
	$setup(posedge D &&& (ENABLE_RN === 1'b1),
		negedge CLKN &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// recovery RN-LH CLKN-HL
	$recovery(posedge RN,negedge CLKN,1.0,notifier);

	// removal RN-LH CLKN-HL
	$removal(posedge RN,negedge CLKN,1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLKN_AND_D === 1'b1)
		,1.0,0,notifier);

	// mpw CLKN_lh
	$width(posedge CLKN,1.0,0,notifier);

	// mpw CLKN_hl
	$width(negedge CLKN,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_NOT_D_AND_RN === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_D_AND_RN === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(posedge CLKN,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFNRNQ_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFNRNQ_4_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFNRNQ_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnrnq_4( CLKN, D, RN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnrnq_4( CLKN, D, RN, Q );
`endif // If not USE_POWER_PINS
input CLKN, D, RN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnrnq_func gf180mcu_fd_sc_mcu9t5v0__dffnrnq_inst(.CLKN(CLKN),.D(D),.RN(RN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnrnq_func gf180mcu_fd_sc_mcu9t5v0__dffnrnq_inst(.CLKN(CLKN),.D(D),.RN(RN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(ENABLE_NOT_D_AND_RN,RN,MGM_W0);


	and MGM_G2(ENABLE_D_AND_RN,RN,D);


	buf MGM_G3(ENABLE_RN,RN);


	not MGM_G4(MGM_W1,CLKN);


	not MGM_G5(MGM_W2,D);


	and MGM_G6(ENABLE_NOT_CLKN_AND_NOT_D,MGM_W2,MGM_W1);


	not MGM_G7(MGM_W3,CLKN);


	and MGM_G8(ENABLE_NOT_CLKN_AND_D,D,MGM_W3);


	not MGM_G9(MGM_W4,D);


	and MGM_G10(ENABLE_CLKN_AND_NOT_D,MGM_W4,CLKN);


	and MGM_G11(ENABLE_CLKN_AND_D,D,CLKN);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLKN --> Q
	(negedge CLKN => (Q : D))  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	$width(negedge CLKN &&& (ENABLE_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLKN &&& (ENABLE_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLKN-HL
	$hold(negedge CLKN &&& (ENABLE_RN === 1'b1),
		negedge D &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// hold D-LH CLKN-HL
	$hold(negedge CLKN &&& (ENABLE_RN === 1'b1),
		posedge D &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// setup D-HL CLKN-HL
	$setup(negedge D &&& (ENABLE_RN === 1'b1),
		negedge CLKN &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// setup D-LH CLKN-HL
	$setup(posedge D &&& (ENABLE_RN === 1'b1),
		negedge CLKN &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// recovery RN-LH CLKN-HL
	$recovery(posedge RN,negedge CLKN,1.0,notifier);

	// removal RN-LH CLKN-HL
	$removal(posedge RN,negedge CLKN,1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLKN_AND_D === 1'b1)
		,1.0,0,notifier);

	// mpw CLKN_lh
	$width(posedge CLKN,1.0,0,notifier);

	// mpw CLKN_hl
	$width(negedge CLKN,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_NOT_D_AND_RN === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_D_AND_RN === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(posedge CLKN,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFNRNQ_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFNRNQ_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFNRNQ_FUNC_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnrnq_func( CLKN, D, RN, Q, VDD, VSS, VNW, VPW, notifier );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnrnq_func( CLKN, D, RN, Q, notifier );
`endif // If not USE_POWER_PINS
input CLKN, D, RN, notifier;
output Q;

	not MGM_BG_0( MGM_CLK0, CLKN );

	not MGM_BG_1( MGM_P0, RN );

	not MGM_BG_2( MGM_D0, D );

	gf180mcu_fd_sc_mcu9t5v0__udp_n_iq_ff( IQ1, 1'b0, MGM_P0, MGM_CLK0, MGM_D0, notifier );

	not MGM_BG_3( Q, IQ1 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFNRNQ_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFNRSNQ_1_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFNRSNQ_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnrsnq_1( CLKN, D, SETN, RN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnrsnq_1( CLKN, D, SETN, RN, Q );
`endif // If not USE_POWER_PINS
input CLKN, D, RN, SETN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnrsnq_func gf180mcu_fd_sc_mcu9t5v0__dffnrsnq_inst(.CLKN(CLKN),.D(D),.SETN(SETN),.RN(RN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnrsnq_func gf180mcu_fd_sc_mcu9t5v0__dffnrsnq_inst(.CLKN(CLKN),.D(D),.SETN(SETN),.RN(RN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(MGM_W1,RN,MGM_W0);


	and MGM_G2(ENABLE_NOT_D_AND_RN_AND_SETN,SETN,MGM_W1);


	and MGM_G3(MGM_W2,RN,D);


	and MGM_G4(ENABLE_D_AND_RN_AND_SETN,SETN,MGM_W2);


	and MGM_G5(ENABLE_RN_AND_SETN,SETN,RN);


	buf MGM_G6(ENABLE_SETN,SETN);


	not MGM_G7(MGM_W3,CLKN);


	not MGM_G8(MGM_W4,D);


	and MGM_G9(MGM_W5,MGM_W4,MGM_W3);


	and MGM_G10(ENABLE_NOT_CLKN_AND_NOT_D_AND_SETN,SETN,MGM_W5);


	not MGM_G11(MGM_W6,CLKN);


	and MGM_G12(MGM_W7,D,MGM_W6);


	and MGM_G13(ENABLE_NOT_CLKN_AND_D_AND_SETN,SETN,MGM_W7);


	not MGM_G14(MGM_W8,D);


	and MGM_G15(MGM_W9,MGM_W8,CLKN);


	and MGM_G16(ENABLE_CLKN_AND_NOT_D_AND_SETN,SETN,MGM_W9);


	and MGM_G17(MGM_W10,D,CLKN);


	and MGM_G18(ENABLE_CLKN_AND_D_AND_SETN,SETN,MGM_W10);


	not MGM_G19(MGM_W11,CLKN);


	not MGM_G20(MGM_W12,D);


	and MGM_G21(ENABLE_NOT_CLKN_AND_NOT_D,MGM_W12,MGM_W11);


	not MGM_G22(MGM_W13,CLKN);


	and MGM_G23(ENABLE_NOT_CLKN_AND_D,D,MGM_W13);


	not MGM_G24(MGM_W14,D);


	and MGM_G25(ENABLE_CLKN_AND_NOT_D,MGM_W14,CLKN);


	and MGM_G26(ENABLE_CLKN_AND_D,D,CLKN);


	buf MGM_G27(ENABLE_RN,RN);


	not MGM_G28(MGM_W15,CLKN);


	not MGM_G29(MGM_W16,D);


	and MGM_G30(MGM_W17,MGM_W16,MGM_W15);


	and MGM_G31(ENABLE_NOT_CLKN_AND_NOT_D_AND_RN,RN,MGM_W17);


	not MGM_G32(MGM_W18,CLKN);


	and MGM_G33(MGM_W19,D,MGM_W18);


	and MGM_G34(ENABLE_NOT_CLKN_AND_D_AND_RN,RN,MGM_W19);


	not MGM_G35(MGM_W20,D);


	and MGM_G36(MGM_W21,MGM_W20,CLKN);


	and MGM_G37(ENABLE_CLKN_AND_NOT_D_AND_RN,RN,MGM_W21);


	and MGM_G38(MGM_W22,D,CLKN);


	and MGM_G39(ENABLE_CLKN_AND_D_AND_RN,RN,MGM_W22);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLKN --> Q
	(negedge CLKN => (Q : D))  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b0 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b0 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b1 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b1 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b0 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b0 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b1 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b1 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	$width(negedge CLKN &&& (ENABLE_NOT_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_NOT_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLKN &&& (ENABLE_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLKN-HL
	$hold(negedge CLKN &&& (ENABLE_RN_AND_SETN === 1'b1),
		negedge D &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// hold D-LH CLKN-HL
	$hold(negedge CLKN &&& (ENABLE_RN_AND_SETN === 1'b1),
		posedge D &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// setup D-HL CLKN-HL
	$setup(negedge D &&& (ENABLE_RN_AND_SETN === 1'b1),
		negedge CLKN &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// setup D-LH CLKN-HL
	$setup(posedge D &&& (ENABLE_RN_AND_SETN === 1'b1),
		negedge CLKN &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// recovery RN-LH CLKN-HL
	$recovery(posedge RN &&& (ENABLE_SETN === 1'b1),
		negedge CLKN &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// removal RN-LH CLKN-HL
	$removal(posedge RN &&& (ENABLE_SETN === 1'b1),
		negedge CLKN &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLKN_AND_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLKN_AND_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLKN_AND_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLKN_AND_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLKN_AND_D === 1'b1),
		posedge RN &&& (ENABLE_CLKN_AND_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLKN_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_CLKN_AND_D === 1'b1),1.0,notifier);

	// recovery SETN-LH CLKN-HL
	$recovery(posedge SETN &&& (ENABLE_RN === 1'b1),
		negedge CLKN &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// removal SETN-LH CLKN-HL
	$removal(posedge SETN &&& (ENABLE_RN === 1'b1),
		negedge CLKN &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLKN_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_CLKN_AND_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLKN_AND_D === 1'b1),
		posedge RN &&& (ENABLE_CLKN_AND_D === 1'b1),1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLKN_AND_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLKN_AND_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLKN_AND_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLKN_AND_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	// mpw CLKN_lh
	$width(posedge CLKN,1.0,0,notifier);

	// mpw CLKN_hl
	$width(negedge CLKN,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_NOT_D_AND_RN_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_D_AND_RN_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(posedge CLKN,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFNRSNQ_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFNRSNQ_2_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFNRSNQ_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnrsnq_2( CLKN, D, SETN, RN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnrsnq_2( CLKN, D, SETN, RN, Q );
`endif // If not USE_POWER_PINS
input CLKN, D, RN, SETN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnrsnq_func gf180mcu_fd_sc_mcu9t5v0__dffnrsnq_inst(.CLKN(CLKN),.D(D),.SETN(SETN),.RN(RN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnrsnq_func gf180mcu_fd_sc_mcu9t5v0__dffnrsnq_inst(.CLKN(CLKN),.D(D),.SETN(SETN),.RN(RN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(MGM_W1,RN,MGM_W0);


	and MGM_G2(ENABLE_NOT_D_AND_RN_AND_SETN,SETN,MGM_W1);


	and MGM_G3(MGM_W2,RN,D);


	and MGM_G4(ENABLE_D_AND_RN_AND_SETN,SETN,MGM_W2);


	and MGM_G5(ENABLE_RN_AND_SETN,SETN,RN);


	buf MGM_G6(ENABLE_SETN,SETN);


	not MGM_G7(MGM_W3,CLKN);


	not MGM_G8(MGM_W4,D);


	and MGM_G9(MGM_W5,MGM_W4,MGM_W3);


	and MGM_G10(ENABLE_NOT_CLKN_AND_NOT_D_AND_SETN,SETN,MGM_W5);


	not MGM_G11(MGM_W6,CLKN);


	and MGM_G12(MGM_W7,D,MGM_W6);


	and MGM_G13(ENABLE_NOT_CLKN_AND_D_AND_SETN,SETN,MGM_W7);


	not MGM_G14(MGM_W8,D);


	and MGM_G15(MGM_W9,MGM_W8,CLKN);


	and MGM_G16(ENABLE_CLKN_AND_NOT_D_AND_SETN,SETN,MGM_W9);


	and MGM_G17(MGM_W10,D,CLKN);


	and MGM_G18(ENABLE_CLKN_AND_D_AND_SETN,SETN,MGM_W10);


	not MGM_G19(MGM_W11,CLKN);


	not MGM_G20(MGM_W12,D);


	and MGM_G21(ENABLE_NOT_CLKN_AND_NOT_D,MGM_W12,MGM_W11);


	not MGM_G22(MGM_W13,CLKN);


	and MGM_G23(ENABLE_NOT_CLKN_AND_D,D,MGM_W13);


	not MGM_G24(MGM_W14,D);


	and MGM_G25(ENABLE_CLKN_AND_NOT_D,MGM_W14,CLKN);


	and MGM_G26(ENABLE_CLKN_AND_D,D,CLKN);


	buf MGM_G27(ENABLE_RN,RN);


	not MGM_G28(MGM_W15,CLKN);


	not MGM_G29(MGM_W16,D);


	and MGM_G30(MGM_W17,MGM_W16,MGM_W15);


	and MGM_G31(ENABLE_NOT_CLKN_AND_NOT_D_AND_RN,RN,MGM_W17);


	not MGM_G32(MGM_W18,CLKN);


	and MGM_G33(MGM_W19,D,MGM_W18);


	and MGM_G34(ENABLE_NOT_CLKN_AND_D_AND_RN,RN,MGM_W19);


	not MGM_G35(MGM_W20,D);


	and MGM_G36(MGM_W21,MGM_W20,CLKN);


	and MGM_G37(ENABLE_CLKN_AND_NOT_D_AND_RN,RN,MGM_W21);


	and MGM_G38(MGM_W22,D,CLKN);


	and MGM_G39(ENABLE_CLKN_AND_D_AND_RN,RN,MGM_W22);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLKN --> Q
	(negedge CLKN => (Q : D))  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b0 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b0 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b1 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b1 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b0 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b0 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b1 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b1 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	$width(negedge CLKN &&& (ENABLE_NOT_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_NOT_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLKN &&& (ENABLE_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLKN-HL
	$hold(negedge CLKN &&& (ENABLE_RN_AND_SETN === 1'b1),
		negedge D &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// hold D-LH CLKN-HL
	$hold(negedge CLKN &&& (ENABLE_RN_AND_SETN === 1'b1),
		posedge D &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// setup D-HL CLKN-HL
	$setup(negedge D &&& (ENABLE_RN_AND_SETN === 1'b1),
		negedge CLKN &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// setup D-LH CLKN-HL
	$setup(posedge D &&& (ENABLE_RN_AND_SETN === 1'b1),
		negedge CLKN &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// recovery RN-LH CLKN-HL
	$recovery(posedge RN &&& (ENABLE_SETN === 1'b1),
		negedge CLKN &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// removal RN-LH CLKN-HL
	$removal(posedge RN &&& (ENABLE_SETN === 1'b1),
		negedge CLKN &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLKN_AND_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLKN_AND_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLKN_AND_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLKN_AND_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLKN_AND_D === 1'b1),
		posedge RN &&& (ENABLE_CLKN_AND_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLKN_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_CLKN_AND_D === 1'b1),1.0,notifier);

	// recovery SETN-LH CLKN-HL
	$recovery(posedge SETN &&& (ENABLE_RN === 1'b1),
		negedge CLKN &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// removal SETN-LH CLKN-HL
	$removal(posedge SETN &&& (ENABLE_RN === 1'b1),
		negedge CLKN &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLKN_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_CLKN_AND_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLKN_AND_D === 1'b1),
		posedge RN &&& (ENABLE_CLKN_AND_D === 1'b1),1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLKN_AND_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLKN_AND_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLKN_AND_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLKN_AND_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	// mpw CLKN_lh
	$width(posedge CLKN,1.0,0,notifier);

	// mpw CLKN_hl
	$width(negedge CLKN,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_NOT_D_AND_RN_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_D_AND_RN_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(posedge CLKN,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFNRSNQ_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFNRSNQ_4_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFNRSNQ_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnrsnq_4( CLKN, D, SETN, RN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnrsnq_4( CLKN, D, SETN, RN, Q );
`endif // If not USE_POWER_PINS
input CLKN, D, RN, SETN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnrsnq_func gf180mcu_fd_sc_mcu9t5v0__dffnrsnq_inst(.CLKN(CLKN),.D(D),.SETN(SETN),.RN(RN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnrsnq_func gf180mcu_fd_sc_mcu9t5v0__dffnrsnq_inst(.CLKN(CLKN),.D(D),.SETN(SETN),.RN(RN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(MGM_W1,RN,MGM_W0);


	and MGM_G2(ENABLE_NOT_D_AND_RN_AND_SETN,SETN,MGM_W1);


	and MGM_G3(MGM_W2,RN,D);


	and MGM_G4(ENABLE_D_AND_RN_AND_SETN,SETN,MGM_W2);


	and MGM_G5(ENABLE_RN_AND_SETN,SETN,RN);


	buf MGM_G6(ENABLE_SETN,SETN);


	not MGM_G7(MGM_W3,CLKN);


	not MGM_G8(MGM_W4,D);


	and MGM_G9(MGM_W5,MGM_W4,MGM_W3);


	and MGM_G10(ENABLE_NOT_CLKN_AND_NOT_D_AND_SETN,SETN,MGM_W5);


	not MGM_G11(MGM_W6,CLKN);


	and MGM_G12(MGM_W7,D,MGM_W6);


	and MGM_G13(ENABLE_NOT_CLKN_AND_D_AND_SETN,SETN,MGM_W7);


	not MGM_G14(MGM_W8,D);


	and MGM_G15(MGM_W9,MGM_W8,CLKN);


	and MGM_G16(ENABLE_CLKN_AND_NOT_D_AND_SETN,SETN,MGM_W9);


	and MGM_G17(MGM_W10,D,CLKN);


	and MGM_G18(ENABLE_CLKN_AND_D_AND_SETN,SETN,MGM_W10);


	not MGM_G19(MGM_W11,CLKN);


	not MGM_G20(MGM_W12,D);


	and MGM_G21(ENABLE_NOT_CLKN_AND_NOT_D,MGM_W12,MGM_W11);


	not MGM_G22(MGM_W13,CLKN);


	and MGM_G23(ENABLE_NOT_CLKN_AND_D,D,MGM_W13);


	not MGM_G24(MGM_W14,D);


	and MGM_G25(ENABLE_CLKN_AND_NOT_D,MGM_W14,CLKN);


	and MGM_G26(ENABLE_CLKN_AND_D,D,CLKN);


	buf MGM_G27(ENABLE_RN,RN);


	not MGM_G28(MGM_W15,CLKN);


	not MGM_G29(MGM_W16,D);


	and MGM_G30(MGM_W17,MGM_W16,MGM_W15);


	and MGM_G31(ENABLE_NOT_CLKN_AND_NOT_D_AND_RN,RN,MGM_W17);


	not MGM_G32(MGM_W18,CLKN);


	and MGM_G33(MGM_W19,D,MGM_W18);


	and MGM_G34(ENABLE_NOT_CLKN_AND_D_AND_RN,RN,MGM_W19);


	not MGM_G35(MGM_W20,D);


	and MGM_G36(MGM_W21,MGM_W20,CLKN);


	and MGM_G37(ENABLE_CLKN_AND_NOT_D_AND_RN,RN,MGM_W21);


	and MGM_G38(MGM_W22,D,CLKN);


	and MGM_G39(ENABLE_CLKN_AND_D_AND_RN,RN,MGM_W22);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLKN --> Q
	(negedge CLKN => (Q : D))  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b0 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b0 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b1 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b1 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b0 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b0 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b1 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b1 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	$width(negedge CLKN &&& (ENABLE_NOT_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_NOT_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLKN &&& (ENABLE_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLKN-HL
	$hold(negedge CLKN &&& (ENABLE_RN_AND_SETN === 1'b1),
		negedge D &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// hold D-LH CLKN-HL
	$hold(negedge CLKN &&& (ENABLE_RN_AND_SETN === 1'b1),
		posedge D &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// setup D-HL CLKN-HL
	$setup(negedge D &&& (ENABLE_RN_AND_SETN === 1'b1),
		negedge CLKN &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// setup D-LH CLKN-HL
	$setup(posedge D &&& (ENABLE_RN_AND_SETN === 1'b1),
		negedge CLKN &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// recovery RN-LH CLKN-HL
	$recovery(posedge RN &&& (ENABLE_SETN === 1'b1),
		negedge CLKN &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// removal RN-LH CLKN-HL
	$removal(posedge RN &&& (ENABLE_SETN === 1'b1),
		negedge CLKN &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLKN_AND_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLKN_AND_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLKN_AND_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLKN_AND_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLKN_AND_D === 1'b1),
		posedge RN &&& (ENABLE_CLKN_AND_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLKN_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_CLKN_AND_D === 1'b1),1.0,notifier);

	// recovery SETN-LH CLKN-HL
	$recovery(posedge SETN &&& (ENABLE_RN === 1'b1),
		negedge CLKN &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// removal SETN-LH CLKN-HL
	$removal(posedge SETN &&& (ENABLE_RN === 1'b1),
		negedge CLKN &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLKN_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_CLKN_AND_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLKN_AND_D === 1'b1),
		posedge RN &&& (ENABLE_CLKN_AND_D === 1'b1),1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLKN_AND_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLKN_AND_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLKN_AND_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLKN_AND_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	// mpw CLKN_lh
	$width(posedge CLKN,1.0,0,notifier);

	// mpw CLKN_hl
	$width(negedge CLKN,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_NOT_D_AND_RN_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_D_AND_RN_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(posedge CLKN,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFNRSNQ_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFNRSNQ_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFNRSNQ_FUNC_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnrsnq_func( CLKN, D, SETN, RN, Q, VDD, VSS, VNW, VPW, notifier );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnrsnq_func( CLKN, D, SETN, RN, Q, notifier );
`endif // If not USE_POWER_PINS
input CLKN, D, RN, SETN, notifier;
output Q;

	not MGM_BG_0( MGM_CLK0, CLKN );

	not MGM_BG_1( MGM_P0, RN );

	not MGM_BG_2( MGM_C0, SETN );

	not MGM_BG_3( MGM_D0, D );

	gf180mcu_fd_sc_mcu9t5v0__udp_hn_iq_ff( IQ1, MGM_C0, MGM_P0, MGM_CLK0, MGM_D0, notifier );

	not MGM_BG_4( Q, IQ1 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFNRSNQ_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFNSNQ_1_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFNSNQ_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnsnq_1( CLKN, D, SETN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnsnq_1( CLKN, D, SETN, Q );
`endif // If not USE_POWER_PINS
input CLKN, D, SETN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnsnq_func gf180mcu_fd_sc_mcu9t5v0__dffnsnq_inst(.CLKN(CLKN),.D(D),.SETN(SETN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnsnq_func gf180mcu_fd_sc_mcu9t5v0__dffnsnq_inst(.CLKN(CLKN),.D(D),.SETN(SETN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(ENABLE_NOT_D_AND_SETN,SETN,MGM_W0);


	and MGM_G2(ENABLE_D_AND_SETN,SETN,D);


	buf MGM_G3(ENABLE_SETN,SETN);


	not MGM_G4(MGM_W1,CLKN);


	not MGM_G5(MGM_W2,D);


	and MGM_G6(ENABLE_NOT_CLKN_AND_NOT_D,MGM_W2,MGM_W1);


	not MGM_G7(MGM_W3,CLKN);


	and MGM_G8(ENABLE_NOT_CLKN_AND_D,D,MGM_W3);


	not MGM_G9(MGM_W4,D);


	and MGM_G10(ENABLE_CLKN_AND_NOT_D,MGM_W4,CLKN);


	and MGM_G11(ENABLE_CLKN_AND_D,D,CLKN);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLKN --> Q
	(negedge CLKN => (Q : D))  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	$width(negedge CLKN &&& (ENABLE_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLKN &&& (ENABLE_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLKN-HL
	$hold(negedge CLKN &&& (ENABLE_SETN === 1'b1),
		negedge D &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// hold D-LH CLKN-HL
	$hold(negedge CLKN &&& (ENABLE_SETN === 1'b1),
		posedge D &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// setup D-HL CLKN-HL
	$setup(negedge D &&& (ENABLE_SETN === 1'b1),
		negedge CLKN &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// setup D-LH CLKN-HL
	$setup(posedge D &&& (ENABLE_SETN === 1'b1),
		negedge CLKN &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// recovery SETN-LH CLKN-HL
	$recovery(posedge SETN,negedge CLKN,1.0,notifier);

	// removal SETN-LH CLKN-HL
	$removal(posedge SETN,negedge CLKN,1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLKN_AND_D === 1'b1)
		,1.0,0,notifier);

	// mpw CLKN_lh
	$width(posedge CLKN,1.0,0,notifier);

	// mpw CLKN_hl
	$width(negedge CLKN,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_NOT_D_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_D_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(posedge CLKN,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFNSNQ_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFNSNQ_2_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFNSNQ_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnsnq_2( CLKN, D, SETN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnsnq_2( CLKN, D, SETN, Q );
`endif // If not USE_POWER_PINS
input CLKN, D, SETN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnsnq_func gf180mcu_fd_sc_mcu9t5v0__dffnsnq_inst(.CLKN(CLKN),.D(D),.SETN(SETN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnsnq_func gf180mcu_fd_sc_mcu9t5v0__dffnsnq_inst(.CLKN(CLKN),.D(D),.SETN(SETN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(ENABLE_NOT_D_AND_SETN,SETN,MGM_W0);


	and MGM_G2(ENABLE_D_AND_SETN,SETN,D);


	buf MGM_G3(ENABLE_SETN,SETN);


	not MGM_G4(MGM_W1,CLKN);


	not MGM_G5(MGM_W2,D);


	and MGM_G6(ENABLE_NOT_CLKN_AND_NOT_D,MGM_W2,MGM_W1);


	not MGM_G7(MGM_W3,CLKN);


	and MGM_G8(ENABLE_NOT_CLKN_AND_D,D,MGM_W3);


	not MGM_G9(MGM_W4,D);


	and MGM_G10(ENABLE_CLKN_AND_NOT_D,MGM_W4,CLKN);


	and MGM_G11(ENABLE_CLKN_AND_D,D,CLKN);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLKN --> Q
	(negedge CLKN => (Q : D))  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	$width(negedge CLKN &&& (ENABLE_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLKN &&& (ENABLE_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLKN-HL
	$hold(negedge CLKN &&& (ENABLE_SETN === 1'b1),
		negedge D &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// hold D-LH CLKN-HL
	$hold(negedge CLKN &&& (ENABLE_SETN === 1'b1),
		posedge D &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// setup D-HL CLKN-HL
	$setup(negedge D &&& (ENABLE_SETN === 1'b1),
		negedge CLKN &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// setup D-LH CLKN-HL
	$setup(posedge D &&& (ENABLE_SETN === 1'b1),
		negedge CLKN &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// recovery SETN-LH CLKN-HL
	$recovery(posedge SETN,negedge CLKN,1.0,notifier);

	// removal SETN-LH CLKN-HL
	$removal(posedge SETN,negedge CLKN,1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLKN_AND_D === 1'b1)
		,1.0,0,notifier);

	// mpw CLKN_lh
	$width(posedge CLKN,1.0,0,notifier);

	// mpw CLKN_hl
	$width(negedge CLKN,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_NOT_D_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_D_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(posedge CLKN,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFNSNQ_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFNSNQ_4_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFNSNQ_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnsnq_4( CLKN, D, SETN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnsnq_4( CLKN, D, SETN, Q );
`endif // If not USE_POWER_PINS
input CLKN, D, SETN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnsnq_func gf180mcu_fd_sc_mcu9t5v0__dffnsnq_inst(.CLKN(CLKN),.D(D),.SETN(SETN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffnsnq_func gf180mcu_fd_sc_mcu9t5v0__dffnsnq_inst(.CLKN(CLKN),.D(D),.SETN(SETN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(ENABLE_NOT_D_AND_SETN,SETN,MGM_W0);


	and MGM_G2(ENABLE_D_AND_SETN,SETN,D);


	buf MGM_G3(ENABLE_SETN,SETN);


	not MGM_G4(MGM_W1,CLKN);


	not MGM_G5(MGM_W2,D);


	and MGM_G6(ENABLE_NOT_CLKN_AND_NOT_D,MGM_W2,MGM_W1);


	not MGM_G7(MGM_W3,CLKN);


	and MGM_G8(ENABLE_NOT_CLKN_AND_D,D,MGM_W3);


	not MGM_G9(MGM_W4,D);


	and MGM_G10(ENABLE_CLKN_AND_NOT_D,MGM_W4,CLKN);


	and MGM_G11(ENABLE_CLKN_AND_D,D,CLKN);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLKN --> Q
	(negedge CLKN => (Q : D))  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLKN===1'b0 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLKN===1'b1 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	$width(negedge CLKN &&& (ENABLE_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLKN &&& (ENABLE_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLKN-HL
	$hold(negedge CLKN &&& (ENABLE_SETN === 1'b1),
		negedge D &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// hold D-LH CLKN-HL
	$hold(negedge CLKN &&& (ENABLE_SETN === 1'b1),
		posedge D &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// setup D-HL CLKN-HL
	$setup(negedge D &&& (ENABLE_SETN === 1'b1),
		negedge CLKN &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// setup D-LH CLKN-HL
	$setup(posedge D &&& (ENABLE_SETN === 1'b1),
		negedge CLKN &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// recovery SETN-LH CLKN-HL
	$recovery(posedge SETN,negedge CLKN,1.0,notifier);

	// removal SETN-LH CLKN-HL
	$removal(posedge SETN,negedge CLKN,1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLKN_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLKN_AND_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLKN_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLKN_AND_D === 1'b1)
		,1.0,0,notifier);

	// mpw CLKN_lh
	$width(posedge CLKN,1.0,0,notifier);

	// mpw CLKN_hl
	$width(negedge CLKN,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_NOT_D_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(negedge CLKN &&& (ENABLE_D_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLKN
	$period(posedge CLKN,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFNSNQ_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFNSNQ_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFNSNQ_FUNC_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnsnq_func( CLKN, D, SETN, Q, VDD, VSS, VNW, VPW, notifier );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffnsnq_func( CLKN, D, SETN, Q, notifier );
`endif // If not USE_POWER_PINS
input CLKN, D, SETN, notifier;
output Q;

	not MGM_BG_0( MGM_CLK0, CLKN );

	not MGM_BG_1( MGM_C0, SETN );

	not MGM_BG_2( MGM_D0, D );

	gf180mcu_fd_sc_mcu9t5v0__udp_n_iq_ff( IQ1, MGM_C0, 1'b0, MGM_CLK0, MGM_D0, notifier );

	not MGM_BG_3( Q, IQ1 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFNSNQ_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFQ_1_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFQ_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffq_1( CLK, D, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffq_1( CLK, D, Q );
`endif // If not USE_POWER_PINS
input CLK, D;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffq_func gf180mcu_fd_sc_mcu9t5v0__dffq_inst(.CLK(CLK),.D(D),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffq_func gf180mcu_fd_sc_mcu9t5v0__dffq_inst(.CLK(CLK),.D(D),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(ENABLE_NOT_D,D);


	buf MGM_G1(ENABLE_D,D);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK,negedge D,1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK,posedge D,1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D,posedge CLK,1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D,posedge CLK,1.0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFQ_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFQ_2_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFQ_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffq_2( CLK, D, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffq_2( CLK, D, Q );
`endif // If not USE_POWER_PINS
input CLK, D;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffq_func gf180mcu_fd_sc_mcu9t5v0__dffq_inst(.CLK(CLK),.D(D),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffq_func gf180mcu_fd_sc_mcu9t5v0__dffq_inst(.CLK(CLK),.D(D),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(ENABLE_NOT_D,D);


	buf MGM_G1(ENABLE_D,D);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK,negedge D,1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK,posedge D,1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D,posedge CLK,1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D,posedge CLK,1.0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFQ_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFQ_4_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFQ_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffq_4( CLK, D, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffq_4( CLK, D, Q );
`endif // If not USE_POWER_PINS
input CLK, D;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffq_func gf180mcu_fd_sc_mcu9t5v0__dffq_inst(.CLK(CLK),.D(D),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffq_func gf180mcu_fd_sc_mcu9t5v0__dffq_inst(.CLK(CLK),.D(D),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(ENABLE_NOT_D,D);


	buf MGM_G1(ENABLE_D,D);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK,negedge D,1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK,posedge D,1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D,posedge CLK,1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D,posedge CLK,1.0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFQ_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFQ_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFQ_FUNC_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffq_func( CLK, D, Q, VDD, VSS, VNW, VPW, notifier );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffq_func( CLK, D, Q, notifier );
`endif // If not USE_POWER_PINS
input CLK, D, notifier;
output Q;

	not MGM_BG_0( MGM_D0, D );

	gf180mcu_fd_sc_mcu9t5v0__udp_n_iq_ff( IQ1, 1'b0, 1'b0, CLK, MGM_D0, notifier );

	not MGM_BG_1( Q, IQ1 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFQ_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFRNQ_1_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFRNQ_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffrnq_1( CLK, D, RN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffrnq_1( CLK, D, RN, Q );
`endif // If not USE_POWER_PINS
input CLK, D, RN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffrnq_func gf180mcu_fd_sc_mcu9t5v0__dffrnq_inst(.CLK(CLK),.D(D),.RN(RN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffrnq_func gf180mcu_fd_sc_mcu9t5v0__dffrnq_inst(.CLK(CLK),.D(D),.RN(RN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(ENABLE_NOT_D_AND_RN,RN,MGM_W0);


	and MGM_G2(ENABLE_D_AND_RN,RN,D);


	buf MGM_G3(ENABLE_RN,RN);


	not MGM_G4(MGM_W1,CLK);


	not MGM_G5(MGM_W2,D);


	and MGM_G6(ENABLE_NOT_CLK_AND_NOT_D,MGM_W2,MGM_W1);


	not MGM_G7(MGM_W3,CLK);


	and MGM_G8(ENABLE_NOT_CLK_AND_D,D,MGM_W3);


	not MGM_G9(MGM_W4,D);


	and MGM_G10(ENABLE_CLK_AND_NOT_D,MGM_W4,CLK);


	and MGM_G11(ENABLE_CLK_AND_D,D,CLK);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN === 1'b1),
		negedge D &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN === 1'b1),
		posedge D &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_RN === 1'b1),
		posedge CLK &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_RN === 1'b1),
		posedge CLK &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN,posedge CLK,1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN,posedge CLK,1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D === 1'b1)
		,1.0,0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFRNQ_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFRNQ_2_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFRNQ_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffrnq_2( CLK, D, RN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffrnq_2( CLK, D, RN, Q );
`endif // If not USE_POWER_PINS
input CLK, D, RN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffrnq_func gf180mcu_fd_sc_mcu9t5v0__dffrnq_inst(.CLK(CLK),.D(D),.RN(RN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffrnq_func gf180mcu_fd_sc_mcu9t5v0__dffrnq_inst(.CLK(CLK),.D(D),.RN(RN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(ENABLE_NOT_D_AND_RN,RN,MGM_W0);


	and MGM_G2(ENABLE_D_AND_RN,RN,D);


	buf MGM_G3(ENABLE_RN,RN);


	not MGM_G4(MGM_W1,CLK);


	not MGM_G5(MGM_W2,D);


	and MGM_G6(ENABLE_NOT_CLK_AND_NOT_D,MGM_W2,MGM_W1);


	not MGM_G7(MGM_W3,CLK);


	and MGM_G8(ENABLE_NOT_CLK_AND_D,D,MGM_W3);


	not MGM_G9(MGM_W4,D);


	and MGM_G10(ENABLE_CLK_AND_NOT_D,MGM_W4,CLK);


	and MGM_G11(ENABLE_CLK_AND_D,D,CLK);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN === 1'b1),
		negedge D &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN === 1'b1),
		posedge D &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_RN === 1'b1),
		posedge CLK &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_RN === 1'b1),
		posedge CLK &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN,posedge CLK,1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN,posedge CLK,1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D === 1'b1)
		,1.0,0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFRNQ_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFRNQ_4_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFRNQ_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffrnq_4( CLK, D, RN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffrnq_4( CLK, D, RN, Q );
`endif // If not USE_POWER_PINS
input CLK, D, RN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffrnq_func gf180mcu_fd_sc_mcu9t5v0__dffrnq_inst(.CLK(CLK),.D(D),.RN(RN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffrnq_func gf180mcu_fd_sc_mcu9t5v0__dffrnq_inst(.CLK(CLK),.D(D),.RN(RN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(ENABLE_NOT_D_AND_RN,RN,MGM_W0);


	and MGM_G2(ENABLE_D_AND_RN,RN,D);


	buf MGM_G3(ENABLE_RN,RN);


	not MGM_G4(MGM_W1,CLK);


	not MGM_G5(MGM_W2,D);


	and MGM_G6(ENABLE_NOT_CLK_AND_NOT_D,MGM_W2,MGM_W1);


	not MGM_G7(MGM_W3,CLK);


	and MGM_G8(ENABLE_NOT_CLK_AND_D,D,MGM_W3);


	not MGM_G9(MGM_W4,D);


	and MGM_G10(ENABLE_CLK_AND_NOT_D,MGM_W4,CLK);


	and MGM_G11(ENABLE_CLK_AND_D,D,CLK);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN === 1'b1),
		negedge D &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN === 1'b1),
		posedge D &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_RN === 1'b1),
		posedge CLK &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_RN === 1'b1),
		posedge CLK &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN,posedge CLK,1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN,posedge CLK,1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D === 1'b1)
		,1.0,0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFRNQ_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFRNQ_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFRNQ_FUNC_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffrnq_func( CLK, D, RN, Q, VDD, VSS, VNW, VPW, notifier );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffrnq_func( CLK, D, RN, Q, notifier );
`endif // If not USE_POWER_PINS
input CLK, D, RN, notifier;
output Q;

	not MGM_BG_0( MGM_P0, RN );

	not MGM_BG_1( MGM_D0, D );

	gf180mcu_fd_sc_mcu9t5v0__udp_n_iq_ff( IQ1, 1'b0, MGM_P0, CLK, MGM_D0, notifier );

	not MGM_BG_2( Q, IQ1 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFRNQ_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFRSNQ_1_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFRSNQ_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffrsnq_1( CLK, D, SETN, RN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffrsnq_1( CLK, D, SETN, RN, Q );
`endif // If not USE_POWER_PINS
input CLK, D, RN, SETN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffrsnq_func gf180mcu_fd_sc_mcu9t5v0__dffrsnq_inst(.CLK(CLK),.D(D),.SETN(SETN),.RN(RN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffrsnq_func gf180mcu_fd_sc_mcu9t5v0__dffrsnq_inst(.CLK(CLK),.D(D),.SETN(SETN),.RN(RN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(MGM_W1,RN,MGM_W0);


	and MGM_G2(ENABLE_NOT_D_AND_RN_AND_SETN,SETN,MGM_W1);


	and MGM_G3(MGM_W2,RN,D);


	and MGM_G4(ENABLE_D_AND_RN_AND_SETN,SETN,MGM_W2);


	and MGM_G5(ENABLE_RN_AND_SETN,SETN,RN);


	buf MGM_G6(ENABLE_SETN,SETN);


	not MGM_G7(MGM_W3,CLK);


	not MGM_G8(MGM_W4,D);


	and MGM_G9(MGM_W5,MGM_W4,MGM_W3);


	and MGM_G10(ENABLE_NOT_CLK_AND_NOT_D_AND_SETN,SETN,MGM_W5);


	not MGM_G11(MGM_W6,CLK);


	and MGM_G12(MGM_W7,D,MGM_W6);


	and MGM_G13(ENABLE_NOT_CLK_AND_D_AND_SETN,SETN,MGM_W7);


	not MGM_G14(MGM_W8,D);


	and MGM_G15(MGM_W9,MGM_W8,CLK);


	and MGM_G16(ENABLE_CLK_AND_NOT_D_AND_SETN,SETN,MGM_W9);


	and MGM_G17(MGM_W10,D,CLK);


	and MGM_G18(ENABLE_CLK_AND_D_AND_SETN,SETN,MGM_W10);


	not MGM_G19(MGM_W11,CLK);


	not MGM_G20(MGM_W12,D);


	and MGM_G21(ENABLE_NOT_CLK_AND_NOT_D,MGM_W12,MGM_W11);


	not MGM_G22(MGM_W13,CLK);


	and MGM_G23(ENABLE_NOT_CLK_AND_D,D,MGM_W13);


	not MGM_G24(MGM_W14,D);


	and MGM_G25(ENABLE_CLK_AND_NOT_D,MGM_W14,CLK);


	and MGM_G26(ENABLE_CLK_AND_D,D,CLK);


	buf MGM_G27(ENABLE_RN,RN);


	not MGM_G28(MGM_W15,CLK);


	not MGM_G29(MGM_W16,D);


	and MGM_G30(MGM_W17,MGM_W16,MGM_W15);


	and MGM_G31(ENABLE_NOT_CLK_AND_NOT_D_AND_RN,RN,MGM_W17);


	not MGM_G32(MGM_W18,CLK);


	and MGM_G33(MGM_W19,D,MGM_W18);


	and MGM_G34(ENABLE_NOT_CLK_AND_D_AND_RN,RN,MGM_W19);


	not MGM_G35(MGM_W20,D);


	and MGM_G36(MGM_W21,MGM_W20,CLK);


	and MGM_G37(ENABLE_CLK_AND_NOT_D_AND_RN,RN,MGM_W21);


	and MGM_G38(MGM_W22,D,CLK);


	and MGM_G39(ENABLE_CLK_AND_D_AND_RN,RN,MGM_W22);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_SETN === 1'b1),
		negedge D &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_SETN === 1'b1),
		posedge D &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_RN_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_RN_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_SETN === 1'b1),
		posedge CLK &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_SETN === 1'b1),
		posedge CLK &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_D === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_RN === 1'b1),
		posedge CLK &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_RN === 1'b1),
		posedge CLK &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_D === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D === 1'b1),1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFRSNQ_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFRSNQ_2_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFRSNQ_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffrsnq_2( CLK, D, SETN, RN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffrsnq_2( CLK, D, SETN, RN, Q );
`endif // If not USE_POWER_PINS
input CLK, D, RN, SETN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffrsnq_func gf180mcu_fd_sc_mcu9t5v0__dffrsnq_inst(.CLK(CLK),.D(D),.SETN(SETN),.RN(RN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffrsnq_func gf180mcu_fd_sc_mcu9t5v0__dffrsnq_inst(.CLK(CLK),.D(D),.SETN(SETN),.RN(RN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(MGM_W1,RN,MGM_W0);


	and MGM_G2(ENABLE_NOT_D_AND_RN_AND_SETN,SETN,MGM_W1);


	and MGM_G3(MGM_W2,RN,D);


	and MGM_G4(ENABLE_D_AND_RN_AND_SETN,SETN,MGM_W2);


	and MGM_G5(ENABLE_RN_AND_SETN,SETN,RN);


	buf MGM_G6(ENABLE_SETN,SETN);


	not MGM_G7(MGM_W3,CLK);


	not MGM_G8(MGM_W4,D);


	and MGM_G9(MGM_W5,MGM_W4,MGM_W3);


	and MGM_G10(ENABLE_NOT_CLK_AND_NOT_D_AND_SETN,SETN,MGM_W5);


	not MGM_G11(MGM_W6,CLK);


	and MGM_G12(MGM_W7,D,MGM_W6);


	and MGM_G13(ENABLE_NOT_CLK_AND_D_AND_SETN,SETN,MGM_W7);


	not MGM_G14(MGM_W8,D);


	and MGM_G15(MGM_W9,MGM_W8,CLK);


	and MGM_G16(ENABLE_CLK_AND_NOT_D_AND_SETN,SETN,MGM_W9);


	and MGM_G17(MGM_W10,D,CLK);


	and MGM_G18(ENABLE_CLK_AND_D_AND_SETN,SETN,MGM_W10);


	not MGM_G19(MGM_W11,CLK);


	not MGM_G20(MGM_W12,D);


	and MGM_G21(ENABLE_NOT_CLK_AND_NOT_D,MGM_W12,MGM_W11);


	not MGM_G22(MGM_W13,CLK);


	and MGM_G23(ENABLE_NOT_CLK_AND_D,D,MGM_W13);


	not MGM_G24(MGM_W14,D);


	and MGM_G25(ENABLE_CLK_AND_NOT_D,MGM_W14,CLK);


	and MGM_G26(ENABLE_CLK_AND_D,D,CLK);


	buf MGM_G27(ENABLE_RN,RN);


	not MGM_G28(MGM_W15,CLK);


	not MGM_G29(MGM_W16,D);


	and MGM_G30(MGM_W17,MGM_W16,MGM_W15);


	and MGM_G31(ENABLE_NOT_CLK_AND_NOT_D_AND_RN,RN,MGM_W17);


	not MGM_G32(MGM_W18,CLK);


	and MGM_G33(MGM_W19,D,MGM_W18);


	and MGM_G34(ENABLE_NOT_CLK_AND_D_AND_RN,RN,MGM_W19);


	not MGM_G35(MGM_W20,D);


	and MGM_G36(MGM_W21,MGM_W20,CLK);


	and MGM_G37(ENABLE_CLK_AND_NOT_D_AND_RN,RN,MGM_W21);


	and MGM_G38(MGM_W22,D,CLK);


	and MGM_G39(ENABLE_CLK_AND_D_AND_RN,RN,MGM_W22);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_SETN === 1'b1),
		negedge D &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_SETN === 1'b1),
		posedge D &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_RN_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_RN_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_SETN === 1'b1),
		posedge CLK &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_SETN === 1'b1),
		posedge CLK &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_D === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_RN === 1'b1),
		posedge CLK &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_RN === 1'b1),
		posedge CLK &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_D === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D === 1'b1),1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFRSNQ_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFRSNQ_4_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFRSNQ_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffrsnq_4( CLK, D, SETN, RN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffrsnq_4( CLK, D, SETN, RN, Q );
`endif // If not USE_POWER_PINS
input CLK, D, RN, SETN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffrsnq_func gf180mcu_fd_sc_mcu9t5v0__dffrsnq_inst(.CLK(CLK),.D(D),.SETN(SETN),.RN(RN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffrsnq_func gf180mcu_fd_sc_mcu9t5v0__dffrsnq_inst(.CLK(CLK),.D(D),.SETN(SETN),.RN(RN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(MGM_W1,RN,MGM_W0);


	and MGM_G2(ENABLE_NOT_D_AND_RN_AND_SETN,SETN,MGM_W1);


	and MGM_G3(MGM_W2,RN,D);


	and MGM_G4(ENABLE_D_AND_RN_AND_SETN,SETN,MGM_W2);


	and MGM_G5(ENABLE_RN_AND_SETN,SETN,RN);


	buf MGM_G6(ENABLE_SETN,SETN);


	not MGM_G7(MGM_W3,CLK);


	not MGM_G8(MGM_W4,D);


	and MGM_G9(MGM_W5,MGM_W4,MGM_W3);


	and MGM_G10(ENABLE_NOT_CLK_AND_NOT_D_AND_SETN,SETN,MGM_W5);


	not MGM_G11(MGM_W6,CLK);


	and MGM_G12(MGM_W7,D,MGM_W6);


	and MGM_G13(ENABLE_NOT_CLK_AND_D_AND_SETN,SETN,MGM_W7);


	not MGM_G14(MGM_W8,D);


	and MGM_G15(MGM_W9,MGM_W8,CLK);


	and MGM_G16(ENABLE_CLK_AND_NOT_D_AND_SETN,SETN,MGM_W9);


	and MGM_G17(MGM_W10,D,CLK);


	and MGM_G18(ENABLE_CLK_AND_D_AND_SETN,SETN,MGM_W10);


	not MGM_G19(MGM_W11,CLK);


	not MGM_G20(MGM_W12,D);


	and MGM_G21(ENABLE_NOT_CLK_AND_NOT_D,MGM_W12,MGM_W11);


	not MGM_G22(MGM_W13,CLK);


	and MGM_G23(ENABLE_NOT_CLK_AND_D,D,MGM_W13);


	not MGM_G24(MGM_W14,D);


	and MGM_G25(ENABLE_CLK_AND_NOT_D,MGM_W14,CLK);


	and MGM_G26(ENABLE_CLK_AND_D,D,CLK);


	buf MGM_G27(ENABLE_RN,RN);


	not MGM_G28(MGM_W15,CLK);


	not MGM_G29(MGM_W16,D);


	and MGM_G30(MGM_W17,MGM_W16,MGM_W15);


	and MGM_G31(ENABLE_NOT_CLK_AND_NOT_D_AND_RN,RN,MGM_W17);


	not MGM_G32(MGM_W18,CLK);


	and MGM_G33(MGM_W19,D,MGM_W18);


	and MGM_G34(ENABLE_NOT_CLK_AND_D_AND_RN,RN,MGM_W19);


	not MGM_G35(MGM_W20,D);


	and MGM_G36(MGM_W21,MGM_W20,CLK);


	and MGM_G37(ENABLE_CLK_AND_NOT_D_AND_RN,RN,MGM_W21);


	and MGM_G38(MGM_W22,D,CLK);


	and MGM_G39(ENABLE_CLK_AND_D_AND_RN,RN,MGM_W22);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SETN===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SETN===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_SETN === 1'b1),
		negedge D &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_SETN === 1'b1),
		posedge D &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_RN_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_RN_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_SETN === 1'b1),
		posedge CLK &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_SETN === 1'b1),
		posedge CLK &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_D === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_RN === 1'b1),
		posedge CLK &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_RN === 1'b1),
		posedge CLK &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_D === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_D === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D === 1'b1),1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFRSNQ_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFRSNQ_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFRSNQ_FUNC_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffrsnq_func( CLK, D, SETN, RN, Q, VDD, VSS, VNW, VPW, notifier );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffrsnq_func( CLK, D, SETN, RN, Q, notifier );
`endif // If not USE_POWER_PINS
input CLK, D, RN, SETN, notifier;
output Q;

	not MGM_BG_0( MGM_P0, RN );

	not MGM_BG_1( MGM_C0, SETN );

	not MGM_BG_2( MGM_D0, D );

	gf180mcu_fd_sc_mcu9t5v0__udp_hn_iq_ff( IQ1, MGM_C0, MGM_P0, CLK, MGM_D0, notifier );

	not MGM_BG_3( Q, IQ1 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFRSNQ_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFSNQ_1_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFSNQ_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffsnq_1( CLK, D, SETN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffsnq_1( CLK, D, SETN, Q );
`endif // If not USE_POWER_PINS
input CLK, D, SETN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffsnq_func gf180mcu_fd_sc_mcu9t5v0__dffsnq_inst(.CLK(CLK),.D(D),.SETN(SETN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffsnq_func gf180mcu_fd_sc_mcu9t5v0__dffsnq_inst(.CLK(CLK),.D(D),.SETN(SETN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(ENABLE_NOT_D_AND_SETN,SETN,MGM_W0);


	and MGM_G2(ENABLE_D_AND_SETN,SETN,D);


	buf MGM_G3(ENABLE_SETN,SETN);


	not MGM_G4(MGM_W1,CLK);


	not MGM_G5(MGM_W2,D);


	and MGM_G6(ENABLE_NOT_CLK_AND_NOT_D,MGM_W2,MGM_W1);


	not MGM_G7(MGM_W3,CLK);


	and MGM_G8(ENABLE_NOT_CLK_AND_D,D,MGM_W3);


	not MGM_G9(MGM_W4,D);


	and MGM_G10(ENABLE_CLK_AND_NOT_D,MGM_W4,CLK);


	and MGM_G11(ENABLE_CLK_AND_D,D,CLK);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_SETN === 1'b1),
		negedge D &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_SETN === 1'b1),
		posedge D &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_SETN === 1'b1),
		posedge CLK &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_SETN === 1'b1),
		posedge CLK &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN,posedge CLK,1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN,posedge CLK,1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D === 1'b1)
		,1.0,0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFSNQ_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFSNQ_2_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFSNQ_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffsnq_2( CLK, D, SETN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffsnq_2( CLK, D, SETN, Q );
`endif // If not USE_POWER_PINS
input CLK, D, SETN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffsnq_func gf180mcu_fd_sc_mcu9t5v0__dffsnq_inst(.CLK(CLK),.D(D),.SETN(SETN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffsnq_func gf180mcu_fd_sc_mcu9t5v0__dffsnq_inst(.CLK(CLK),.D(D),.SETN(SETN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(ENABLE_NOT_D_AND_SETN,SETN,MGM_W0);


	and MGM_G2(ENABLE_D_AND_SETN,SETN,D);


	buf MGM_G3(ENABLE_SETN,SETN);


	not MGM_G4(MGM_W1,CLK);


	not MGM_G5(MGM_W2,D);


	and MGM_G6(ENABLE_NOT_CLK_AND_NOT_D,MGM_W2,MGM_W1);


	not MGM_G7(MGM_W3,CLK);


	and MGM_G8(ENABLE_NOT_CLK_AND_D,D,MGM_W3);


	not MGM_G9(MGM_W4,D);


	and MGM_G10(ENABLE_CLK_AND_NOT_D,MGM_W4,CLK);


	and MGM_G11(ENABLE_CLK_AND_D,D,CLK);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_SETN === 1'b1),
		negedge D &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_SETN === 1'b1),
		posedge D &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_SETN === 1'b1),
		posedge CLK &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_SETN === 1'b1),
		posedge CLK &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN,posedge CLK,1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN,posedge CLK,1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D === 1'b1)
		,1.0,0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFSNQ_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFSNQ_4_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFSNQ_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffsnq_4( CLK, D, SETN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffsnq_4( CLK, D, SETN, Q );
`endif // If not USE_POWER_PINS
input CLK, D, SETN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffsnq_func gf180mcu_fd_sc_mcu9t5v0__dffsnq_inst(.CLK(CLK),.D(D),.SETN(SETN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dffsnq_func gf180mcu_fd_sc_mcu9t5v0__dffsnq_inst(.CLK(CLK),.D(D),.SETN(SETN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(ENABLE_NOT_D_AND_SETN,SETN,MGM_W0);


	and MGM_G2(ENABLE_D_AND_SETN,SETN,D);


	buf MGM_G3(ENABLE_SETN,SETN);


	not MGM_G4(MGM_W1,CLK);


	not MGM_G5(MGM_W2,D);


	and MGM_G6(ENABLE_NOT_CLK_AND_NOT_D,MGM_W2,MGM_W1);


	not MGM_G7(MGM_W3,CLK);


	and MGM_G8(ENABLE_NOT_CLK_AND_D,D,MGM_W3);


	not MGM_G9(MGM_W4,D);


	and MGM_G10(ENABLE_CLK_AND_NOT_D,MGM_W4,CLK);


	and MGM_G11(ENABLE_CLK_AND_D,D,CLK);


	// spec_gates_end



   specify

	// specify_block_begin

	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_SETN === 1'b1),
		negedge D &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_SETN === 1'b1),
		posedge D &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_SETN === 1'b1),
		posedge CLK &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_SETN === 1'b1),
		posedge CLK &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN,posedge CLK,1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN,posedge CLK,1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D === 1'b1)
		,1.0,0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_SETN === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFSNQ_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DFFSNQ_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__DFFSNQ_FUNC_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffsnq_func( CLK, D, SETN, Q, VDD, VSS, VNW, VPW, notifier );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dffsnq_func( CLK, D, SETN, Q, notifier );
`endif // If not USE_POWER_PINS
input CLK, D, SETN, notifier;
output Q;

	not MGM_BG_0( MGM_C0, SETN );

	not MGM_BG_1( MGM_D0, D );

	gf180mcu_fd_sc_mcu9t5v0__udp_n_iq_ff( IQ1, MGM_C0, 1'b0, CLK, MGM_D0, notifier );

	not MGM_BG_2( Q, IQ1 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DFFSNQ_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DLYA_1_V
`define GF180MCU_FD_SC_MCU9T5V0__DLYA_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlya_1( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlya_1( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlya_func gf180mcu_fd_sc_mcu9t5v0__dlya_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlya_func gf180mcu_fd_sc_mcu9t5v0__dlya_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DLYA_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DLYA_2_V
`define GF180MCU_FD_SC_MCU9T5V0__DLYA_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlya_2( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlya_2( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlya_func gf180mcu_fd_sc_mcu9t5v0__dlya_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlya_func gf180mcu_fd_sc_mcu9t5v0__dlya_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DLYA_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DLYA_4_V
`define GF180MCU_FD_SC_MCU9T5V0__DLYA_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlya_4( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlya_4( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlya_func gf180mcu_fd_sc_mcu9t5v0__dlya_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlya_func gf180mcu_fd_sc_mcu9t5v0__dlya_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DLYA_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DLYA_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__DLYA_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlya_func( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlya_func( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

	buf MGM_BG_0( Z, I );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DLYA_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DLYB_1_V
`define GF180MCU_FD_SC_MCU9T5V0__DLYB_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyb_1( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyb_1( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlyb_func gf180mcu_fd_sc_mcu9t5v0__dlyb_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlyb_func gf180mcu_fd_sc_mcu9t5v0__dlyb_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DLYB_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DLYB_2_V
`define GF180MCU_FD_SC_MCU9T5V0__DLYB_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyb_2( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyb_2( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlyb_func gf180mcu_fd_sc_mcu9t5v0__dlyb_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlyb_func gf180mcu_fd_sc_mcu9t5v0__dlyb_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DLYB_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DLYB_4_V
`define GF180MCU_FD_SC_MCU9T5V0__DLYB_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyb_4( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyb_4( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlyb_func gf180mcu_fd_sc_mcu9t5v0__dlyb_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlyb_func gf180mcu_fd_sc_mcu9t5v0__dlyb_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DLYB_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DLYB_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__DLYB_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyb_func( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyb_func( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

	buf MGM_BG_0( Z, I );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DLYB_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DLYC_1_V
`define GF180MCU_FD_SC_MCU9T5V0__DLYC_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyc_1( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyc_1( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlyc_func gf180mcu_fd_sc_mcu9t5v0__dlyc_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlyc_func gf180mcu_fd_sc_mcu9t5v0__dlyc_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DLYC_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DLYC_2_V
`define GF180MCU_FD_SC_MCU9T5V0__DLYC_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyc_2( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyc_2( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlyc_func gf180mcu_fd_sc_mcu9t5v0__dlyc_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlyc_func gf180mcu_fd_sc_mcu9t5v0__dlyc_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DLYC_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DLYC_4_V
`define GF180MCU_FD_SC_MCU9T5V0__DLYC_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyc_4( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyc_4( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlyc_func gf180mcu_fd_sc_mcu9t5v0__dlyc_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlyc_func gf180mcu_fd_sc_mcu9t5v0__dlyc_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DLYC_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DLYC_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__DLYC_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyc_func( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyc_func( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

	buf MGM_BG_0( Z, I );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DLYC_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DLYD_1_V
`define GF180MCU_FD_SC_MCU9T5V0__DLYD_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyd_1( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyd_1( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlyd_func gf180mcu_fd_sc_mcu9t5v0__dlyd_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlyd_func gf180mcu_fd_sc_mcu9t5v0__dlyd_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DLYD_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DLYD_2_V
`define GF180MCU_FD_SC_MCU9T5V0__DLYD_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyd_2( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyd_2( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlyd_func gf180mcu_fd_sc_mcu9t5v0__dlyd_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlyd_func gf180mcu_fd_sc_mcu9t5v0__dlyd_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DLYD_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DLYD_4_V
`define GF180MCU_FD_SC_MCU9T5V0__DLYD_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyd_4( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyd_4( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlyd_func gf180mcu_fd_sc_mcu9t5v0__dlyd_inst(.I(I),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__dlyd_func gf180mcu_fd_sc_mcu9t5v0__dlyd_inst(.I(I),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> Z
	 (I => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DLYD_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__DLYD_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__DLYD_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyd_func( I, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__dlyd_func( I, Z );
`endif // If not USE_POWER_PINS
input I;
output Z;

	buf MGM_BG_0( Z, I );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__DLYD_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__ENDCAP_V
`define GF180MCU_FD_SC_MCU9T5V0__ENDCAP_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__endcap( VDD, VSS );
inout VDD, VSS;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__endcap(  );
`endif // If not USE_POWER_PINS

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__endcap_func gf180mcu_fd_sc_mcu9t5v0__endcap_inst(.VDD(VDD),.VSS(VSS));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__endcap_func gf180mcu_fd_sc_mcu9t5v0__endcap_inst();
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__ENDCAP_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__ENDCAP_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__ENDCAP_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__endcap_func( VDD, VSS );
inout VDD, VSS;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__endcap_func(  );
`endif // If not USE_POWER_PINS

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__ENDCAP_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__FILL_1_V
`define GF180MCU_FD_SC_MCU9T5V0__FILL_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fill_1( VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fill_1(  );
`endif // If not USE_POWER_PINS

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fill_func gf180mcu_fd_sc_mcu9t5v0__fill_inst(.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fill_func gf180mcu_fd_sc_mcu9t5v0__fill_inst();
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__FILL_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__FILL_2_V
`define GF180MCU_FD_SC_MCU9T5V0__FILL_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fill_2( VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fill_2(  );
`endif // If not USE_POWER_PINS

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fill_func gf180mcu_fd_sc_mcu9t5v0__fill_inst(.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fill_func gf180mcu_fd_sc_mcu9t5v0__fill_inst();
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__FILL_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__FILL_4_V
`define GF180MCU_FD_SC_MCU9T5V0__FILL_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fill_4( VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fill_4(  );
`endif // If not USE_POWER_PINS

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fill_func gf180mcu_fd_sc_mcu9t5v0__fill_inst(.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fill_func gf180mcu_fd_sc_mcu9t5v0__fill_inst();
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__FILL_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__FILL_8_V
`define GF180MCU_FD_SC_MCU9T5V0__FILL_8_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fill_8( VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fill_8(  );
`endif // If not USE_POWER_PINS

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fill_func gf180mcu_fd_sc_mcu9t5v0__fill_inst(.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fill_func gf180mcu_fd_sc_mcu9t5v0__fill_inst();
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__FILL_8_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__FILL_16_V
`define GF180MCU_FD_SC_MCU9T5V0__FILL_16_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fill_16( VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fill_16(  );
`endif // If not USE_POWER_PINS

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fill_func gf180mcu_fd_sc_mcu9t5v0__fill_inst(.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fill_func gf180mcu_fd_sc_mcu9t5v0__fill_inst();
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__FILL_16_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__FILL_32_V
`define GF180MCU_FD_SC_MCU9T5V0__FILL_32_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fill_32( VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fill_32(  );
`endif // If not USE_POWER_PINS

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fill_func gf180mcu_fd_sc_mcu9t5v0__fill_inst(.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fill_func gf180mcu_fd_sc_mcu9t5v0__fill_inst();
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__FILL_32_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__FILL_64_V
`define GF180MCU_FD_SC_MCU9T5V0__FILL_64_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fill_64( VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fill_64(  );
`endif // If not USE_POWER_PINS

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fill_func gf180mcu_fd_sc_mcu9t5v0__fill_inst(.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fill_func gf180mcu_fd_sc_mcu9t5v0__fill_inst();
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__FILL_64_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__FILL_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__FILL_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fill_func( VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fill_func(  );
`endif // If not USE_POWER_PINS

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__FILL_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__FILLCAP_4_V
`define GF180MCU_FD_SC_MCU9T5V0__FILLCAP_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fillcap_4( VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fillcap_4(  );
`endif // If not USE_POWER_PINS

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fillcap_func gf180mcu_fd_sc_mcu9t5v0__fillcap_inst(.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fillcap_func gf180mcu_fd_sc_mcu9t5v0__fillcap_inst();
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__FILLCAP_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__FILLCAP_8_V
`define GF180MCU_FD_SC_MCU9T5V0__FILLCAP_8_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fillcap_8( VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fillcap_8(  );
`endif // If not USE_POWER_PINS

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fillcap_func gf180mcu_fd_sc_mcu9t5v0__fillcap_inst(.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fillcap_func gf180mcu_fd_sc_mcu9t5v0__fillcap_inst();
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__FILLCAP_8_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__FILLCAP_16_V
`define GF180MCU_FD_SC_MCU9T5V0__FILLCAP_16_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fillcap_16( VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fillcap_16(  );
`endif // If not USE_POWER_PINS

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fillcap_func gf180mcu_fd_sc_mcu9t5v0__fillcap_inst(.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fillcap_func gf180mcu_fd_sc_mcu9t5v0__fillcap_inst();
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__FILLCAP_16_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__FILLCAP_32_V
`define GF180MCU_FD_SC_MCU9T5V0__FILLCAP_32_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fillcap_32( VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fillcap_32(  );
`endif // If not USE_POWER_PINS

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fillcap_func gf180mcu_fd_sc_mcu9t5v0__fillcap_inst(.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fillcap_func gf180mcu_fd_sc_mcu9t5v0__fillcap_inst();
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__FILLCAP_32_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__FILLCAP_64_V
`define GF180MCU_FD_SC_MCU9T5V0__FILLCAP_64_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fillcap_64( VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fillcap_64(  );
`endif // If not USE_POWER_PINS

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fillcap_func gf180mcu_fd_sc_mcu9t5v0__fillcap_inst(.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__fillcap_func gf180mcu_fd_sc_mcu9t5v0__fillcap_inst();
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__FILLCAP_64_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__FILLCAP_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__FILLCAP_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fillcap_func( VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__fillcap_func(  );
`endif // If not USE_POWER_PINS

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__FILLCAP_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__FILLTIE_V
`define GF180MCU_FD_SC_MCU9T5V0__FILLTIE_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__filltie( VDD, VSS );
inout VDD, VSS;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__filltie(  );
`endif // If not USE_POWER_PINS

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__filltie_func gf180mcu_fd_sc_mcu9t5v0__filltie_inst(.VDD(VDD),.VSS(VSS));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__filltie_func gf180mcu_fd_sc_mcu9t5v0__filltie_inst();
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__FILLTIE_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__FILLTIE_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__FILLTIE_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__filltie_func( VDD, VSS );
inout VDD, VSS;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__filltie_func(  );
`endif // If not USE_POWER_PINS

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__FILLTIE_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__HOLD_V
`define GF180MCU_FD_SC_MCU9T5V0__HOLD_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__hold( Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__hold( Z );
`endif // If not USE_POWER_PINS
inout Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__hold_func gf180mcu_fd_sc_mcu9t5v0__hold_inst(.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__hold_func gf180mcu_fd_sc_mcu9t5v0__hold_inst(.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__HOLD_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__HOLD_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__HOLD_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__hold_func( Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__hold_func( Z );
`endif // If not USE_POWER_PINS
inout Z;

	buf (weak0, weak1) MGM_BG_0( Z, MGM_WB_0 );

	buf MGM_BG_1( MGM_WB_0, Z );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__HOLD_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__ICGTN_1_V
`define GF180MCU_FD_SC_MCU9T5V0__ICGTN_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__icgtn_1( TE, E, CLKN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__icgtn_1( TE, E, CLKN, Q );
`endif // If not USE_POWER_PINS
input CLKN, E, TE;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__icgtn_func gf180mcu_fd_sc_mcu9t5v0__icgtn_inst(.TE(TE),.E(E),.CLKN(CLKN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__icgtn_func gf180mcu_fd_sc_mcu9t5v0__icgtn_inst(.TE(TE),.E(E),.CLKN(CLKN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,E);


	not MGM_G1(MGM_W1,TE);


	and MGM_G2(ENABLE_NOT_E_AND_NOT_TE,MGM_W1,MGM_W0);


	not MGM_G3(MGM_W2,E);


	and MGM_G4(ENABLE_NOT_E_AND_TE,TE,MGM_W2);


	not MGM_G5(MGM_W3,TE);


	and MGM_G6(ENABLE_E_AND_NOT_TE,MGM_W3,E);


	and MGM_G7(ENABLE_E_AND_TE,TE,E);


	// spec_gates_end



   specify

	// specify_block_begin

	if(E===1'b0 && TE===1'b1)
	// comb arc CLKN --> Q
	 (CLKN => Q) = (1.0,1.0);

	if(E===1'b1 && TE===1'b0)
	// comb arc CLKN --> Q
	 (CLKN => Q) = (1.0,1.0);

	if(E===1'b1 && TE===1'b1)
	// comb arc CLKN --> Q
	 (CLKN => Q) = (1.0,1.0);

	ifnone
	// comb arc CLKN --> Q
	 (CLKN => Q) = (1.0,1.0);

	if(E===1'b0 && TE===1'b0)
	// comb arc CLKN --> Q
	 (CLKN => Q) = (1.0,1.0);

	$width(posedge CLKN &&& (ENABLE_NOT_E_AND_NOT_TE === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_NOT_E_AND_TE === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_E_AND_NOT_TE === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_E_AND_TE === 1'b1)
		,1.0,0,notifier);

	// hold E-HL CLKN-HL
	$hold(negedge CLKN,negedge E,1.0,notifier);

	// hold E-LH CLKN-HL
	$hold(negedge CLKN,posedge E,1.0,notifier);

	// setup E-HL CLKN-HL
	$setup(negedge E,negedge CLKN,1.0,notifier);

	// setup E-LH CLKN-HL
	$setup(posedge E,negedge CLKN,1.0,notifier);

	// hold TE-HL CLKN-HL
	$hold(negedge CLKN,negedge TE,1.0,notifier);

	// hold TE-LH CLKN-HL
	$hold(negedge CLKN,posedge TE,1.0,notifier);

	// setup TE-HL CLKN-HL
	$setup(negedge TE,negedge CLKN,1.0,notifier);

	// setup TE-LH CLKN-HL
	$setup(posedge TE,negedge CLKN,1.0,notifier);

	// mpw CLKN_lh
	$width(posedge CLKN,1.0,0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__ICGTN_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__ICGTN_2_V
`define GF180MCU_FD_SC_MCU9T5V0__ICGTN_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__icgtn_2( TE, E, CLKN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__icgtn_2( TE, E, CLKN, Q );
`endif // If not USE_POWER_PINS
input CLKN, E, TE;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__icgtn_func gf180mcu_fd_sc_mcu9t5v0__icgtn_inst(.TE(TE),.E(E),.CLKN(CLKN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__icgtn_func gf180mcu_fd_sc_mcu9t5v0__icgtn_inst(.TE(TE),.E(E),.CLKN(CLKN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,E);


	not MGM_G1(MGM_W1,TE);


	and MGM_G2(ENABLE_NOT_E_AND_NOT_TE,MGM_W1,MGM_W0);


	not MGM_G3(MGM_W2,E);


	and MGM_G4(ENABLE_NOT_E_AND_TE,TE,MGM_W2);


	not MGM_G5(MGM_W3,TE);


	and MGM_G6(ENABLE_E_AND_NOT_TE,MGM_W3,E);


	and MGM_G7(ENABLE_E_AND_TE,TE,E);


	// spec_gates_end



   specify

	// specify_block_begin

	if(E===1'b0 && TE===1'b1)
	// comb arc CLKN --> Q
	 (CLKN => Q) = (1.0,1.0);

	if(E===1'b1 && TE===1'b0)
	// comb arc CLKN --> Q
	 (CLKN => Q) = (1.0,1.0);

	if(E===1'b1 && TE===1'b1)
	// comb arc CLKN --> Q
	 (CLKN => Q) = (1.0,1.0);

	ifnone
	// comb arc CLKN --> Q
	 (CLKN => Q) = (1.0,1.0);

	if(E===1'b0 && TE===1'b0)
	// comb arc CLKN --> Q
	 (CLKN => Q) = (1.0,1.0);

	$width(posedge CLKN &&& (ENABLE_NOT_E_AND_NOT_TE === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_NOT_E_AND_TE === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_E_AND_NOT_TE === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_E_AND_TE === 1'b1)
		,1.0,0,notifier);

	// hold E-HL CLKN-HL
	$hold(negedge CLKN,negedge E,1.0,notifier);

	// hold E-LH CLKN-HL
	$hold(negedge CLKN,posedge E,1.0,notifier);

	// setup E-HL CLKN-HL
	$setup(negedge E,negedge CLKN,1.0,notifier);

	// setup E-LH CLKN-HL
	$setup(posedge E,negedge CLKN,1.0,notifier);

	// hold TE-HL CLKN-HL
	$hold(negedge CLKN,negedge TE,1.0,notifier);

	// hold TE-LH CLKN-HL
	$hold(negedge CLKN,posedge TE,1.0,notifier);

	// setup TE-HL CLKN-HL
	$setup(negedge TE,negedge CLKN,1.0,notifier);

	// setup TE-LH CLKN-HL
	$setup(posedge TE,negedge CLKN,1.0,notifier);

	// mpw CLKN_lh
	$width(posedge CLKN,1.0,0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__ICGTN_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__ICGTN_4_V
`define GF180MCU_FD_SC_MCU9T5V0__ICGTN_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__icgtn_4( TE, E, CLKN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__icgtn_4( TE, E, CLKN, Q );
`endif // If not USE_POWER_PINS
input CLKN, E, TE;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__icgtn_func gf180mcu_fd_sc_mcu9t5v0__icgtn_inst(.TE(TE),.E(E),.CLKN(CLKN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__icgtn_func gf180mcu_fd_sc_mcu9t5v0__icgtn_inst(.TE(TE),.E(E),.CLKN(CLKN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,E);


	not MGM_G1(MGM_W1,TE);


	and MGM_G2(ENABLE_NOT_E_AND_NOT_TE,MGM_W1,MGM_W0);


	not MGM_G3(MGM_W2,E);


	and MGM_G4(ENABLE_NOT_E_AND_TE,TE,MGM_W2);


	not MGM_G5(MGM_W3,TE);


	and MGM_G6(ENABLE_E_AND_NOT_TE,MGM_W3,E);


	and MGM_G7(ENABLE_E_AND_TE,TE,E);


	// spec_gates_end



   specify

	// specify_block_begin

	if(E===1'b0 && TE===1'b1)
	// comb arc CLKN --> Q
	 (CLKN => Q) = (1.0,1.0);

	if(E===1'b1 && TE===1'b0)
	// comb arc CLKN --> Q
	 (CLKN => Q) = (1.0,1.0);

	if(E===1'b1 && TE===1'b1)
	// comb arc CLKN --> Q
	 (CLKN => Q) = (1.0,1.0);

	ifnone
	// comb arc CLKN --> Q
	 (CLKN => Q) = (1.0,1.0);

	if(E===1'b0 && TE===1'b0)
	// comb arc CLKN --> Q
	 (CLKN => Q) = (1.0,1.0);

	$width(posedge CLKN &&& (ENABLE_NOT_E_AND_NOT_TE === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_NOT_E_AND_TE === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_E_AND_NOT_TE === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLKN &&& (ENABLE_E_AND_TE === 1'b1)
		,1.0,0,notifier);

	// hold E-HL CLKN-HL
	$hold(negedge CLKN,negedge E,1.0,notifier);

	// hold E-LH CLKN-HL
	$hold(negedge CLKN,posedge E,1.0,notifier);

	// setup E-HL CLKN-HL
	$setup(negedge E,negedge CLKN,1.0,notifier);

	// setup E-LH CLKN-HL
	$setup(posedge E,negedge CLKN,1.0,notifier);

	// hold TE-HL CLKN-HL
	$hold(negedge CLKN,negedge TE,1.0,notifier);

	// hold TE-LH CLKN-HL
	$hold(negedge CLKN,posedge TE,1.0,notifier);

	// setup TE-HL CLKN-HL
	$setup(negedge TE,negedge CLKN,1.0,notifier);

	// setup TE-LH CLKN-HL
	$setup(posedge TE,negedge CLKN,1.0,notifier);

	// mpw CLKN_lh
	$width(posedge CLKN,1.0,0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__ICGTN_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__ICGTN_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__ICGTN_FUNC_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__icgtn_func( TE, E, CLKN, Q, VDD, VSS, VNW, VPW, notifier );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__icgtn_func( TE, E, CLKN, Q, notifier );
`endif // If not USE_POWER_PINS
input CLKN, E, TE, notifier;
output Q;

	or MGM_BG_0( MGM_D0, E, TE );

	gf180mcu_fd_sc_mcu9t5v0__udp_n_iq_latch( IQ3, 1'b0, 1'b0, CLKN, MGM_D0, notifier );

	wire IQ3_inv_for_gf180mcu_fd_sc_mcu9t5v0__icgtn_4;

	not MGM_BG_1( IQ3_inv_for_gf180mcu_fd_sc_mcu9t5v0__icgtn_4, IQ3 );

	or MGM_BG_2( Q, CLKN, IQ3_inv_for_gf180mcu_fd_sc_mcu9t5v0__icgtn_4 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__ICGTN_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__ICGTP_1_V
`define GF180MCU_FD_SC_MCU9T5V0__ICGTP_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__icgtp_1( TE, E, CLK, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__icgtp_1( TE, E, CLK, Q );
`endif // If not USE_POWER_PINS
input CLK, E, TE;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__icgtp_func gf180mcu_fd_sc_mcu9t5v0__icgtp_inst(.TE(TE),.E(E),.CLK(CLK),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__icgtp_func gf180mcu_fd_sc_mcu9t5v0__icgtp_inst(.TE(TE),.E(E),.CLK(CLK),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,E);


	not MGM_G1(MGM_W1,TE);


	and MGM_G2(ENABLE_NOT_E_AND_NOT_TE,MGM_W1,MGM_W0);


	not MGM_G3(MGM_W2,E);


	and MGM_G4(ENABLE_NOT_E_AND_TE,TE,MGM_W2);


	not MGM_G5(MGM_W3,TE);


	and MGM_G6(ENABLE_E_AND_NOT_TE,MGM_W3,E);


	and MGM_G7(ENABLE_E_AND_TE,TE,E);


	// spec_gates_end



   specify

	// specify_block_begin

	if(E===1'b0 && TE===1'b1)
	// comb arc CLK --> Q
	 (CLK => Q) = (1.0,1.0);

	if(E===1'b1 && TE===1'b0)
	// comb arc CLK --> Q
	 (CLK => Q) = (1.0,1.0);

	if(E===1'b1 && TE===1'b1)
	// comb arc CLK --> Q
	 (CLK => Q) = (1.0,1.0);

	ifnone
	// comb arc CLK --> Q
	 (CLK => Q) = (1.0,1.0);

	if(E===1'b0 && TE===1'b0)
	// comb arc CLK --> Q
	 (CLK => Q) = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_E_AND_NOT_TE === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_E_AND_TE === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_E_AND_NOT_TE === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_E_AND_TE === 1'b1)
		,1.0,0,notifier);

	// hold E-HL CLK-LH
	$hold(posedge CLK,negedge E,1.0,notifier);

	// hold E-LH CLK-LH
	$hold(posedge CLK,posedge E,1.0,notifier);

	// setup E-HL CLK-LH
	$setup(negedge E,posedge CLK,1.0,notifier);

	// setup E-LH CLK-LH
	$setup(posedge E,posedge CLK,1.0,notifier);

	// hold TE-HL CLK-LH
	$hold(posedge CLK,negedge TE,1.0,notifier);

	// hold TE-LH CLK-LH
	$hold(posedge CLK,posedge TE,1.0,notifier);

	// setup TE-HL CLK-LH
	$setup(negedge TE,posedge CLK,1.0,notifier);

	// setup TE-LH CLK-LH
	$setup(posedge TE,posedge CLK,1.0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__ICGTP_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__ICGTP_2_V
`define GF180MCU_FD_SC_MCU9T5V0__ICGTP_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__icgtp_2( TE, E, CLK, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__icgtp_2( TE, E, CLK, Q );
`endif // If not USE_POWER_PINS
input CLK, E, TE;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__icgtp_func gf180mcu_fd_sc_mcu9t5v0__icgtp_inst(.TE(TE),.E(E),.CLK(CLK),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__icgtp_func gf180mcu_fd_sc_mcu9t5v0__icgtp_inst(.TE(TE),.E(E),.CLK(CLK),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,E);


	not MGM_G1(MGM_W1,TE);


	and MGM_G2(ENABLE_NOT_E_AND_NOT_TE,MGM_W1,MGM_W0);


	not MGM_G3(MGM_W2,E);


	and MGM_G4(ENABLE_NOT_E_AND_TE,TE,MGM_W2);


	not MGM_G5(MGM_W3,TE);


	and MGM_G6(ENABLE_E_AND_NOT_TE,MGM_W3,E);


	and MGM_G7(ENABLE_E_AND_TE,TE,E);


	// spec_gates_end



   specify

	// specify_block_begin

	if(E===1'b0 && TE===1'b1)
	// comb arc CLK --> Q
	 (CLK => Q) = (1.0,1.0);

	if(E===1'b1 && TE===1'b0)
	// comb arc CLK --> Q
	 (CLK => Q) = (1.0,1.0);

	if(E===1'b1 && TE===1'b1)
	// comb arc CLK --> Q
	 (CLK => Q) = (1.0,1.0);

	ifnone
	// comb arc CLK --> Q
	 (CLK => Q) = (1.0,1.0);

	if(E===1'b0 && TE===1'b0)
	// comb arc CLK --> Q
	 (CLK => Q) = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_E_AND_NOT_TE === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_E_AND_TE === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_E_AND_NOT_TE === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_E_AND_TE === 1'b1)
		,1.0,0,notifier);

	// hold E-HL CLK-LH
	$hold(posedge CLK,negedge E,1.0,notifier);

	// hold E-LH CLK-LH
	$hold(posedge CLK,posedge E,1.0,notifier);

	// setup E-HL CLK-LH
	$setup(negedge E,posedge CLK,1.0,notifier);

	// setup E-LH CLK-LH
	$setup(posedge E,posedge CLK,1.0,notifier);

	// hold TE-HL CLK-LH
	$hold(posedge CLK,negedge TE,1.0,notifier);

	// hold TE-LH CLK-LH
	$hold(posedge CLK,posedge TE,1.0,notifier);

	// setup TE-HL CLK-LH
	$setup(negedge TE,posedge CLK,1.0,notifier);

	// setup TE-LH CLK-LH
	$setup(posedge TE,posedge CLK,1.0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__ICGTP_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__ICGTP_4_V
`define GF180MCU_FD_SC_MCU9T5V0__ICGTP_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__icgtp_4( TE, E, CLK, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__icgtp_4( TE, E, CLK, Q );
`endif // If not USE_POWER_PINS
input CLK, E, TE;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__icgtp_func gf180mcu_fd_sc_mcu9t5v0__icgtp_inst(.TE(TE),.E(E),.CLK(CLK),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__icgtp_func gf180mcu_fd_sc_mcu9t5v0__icgtp_inst(.TE(TE),.E(E),.CLK(CLK),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,E);


	not MGM_G1(MGM_W1,TE);


	and MGM_G2(ENABLE_NOT_E_AND_NOT_TE,MGM_W1,MGM_W0);


	not MGM_G3(MGM_W2,E);


	and MGM_G4(ENABLE_NOT_E_AND_TE,TE,MGM_W2);


	not MGM_G5(MGM_W3,TE);


	and MGM_G6(ENABLE_E_AND_NOT_TE,MGM_W3,E);


	and MGM_G7(ENABLE_E_AND_TE,TE,E);


	// spec_gates_end



   specify

	// specify_block_begin

	if(E===1'b0 && TE===1'b1)
	// comb arc CLK --> Q
	 (CLK => Q) = (1.0,1.0);

	if(E===1'b1 && TE===1'b0)
	// comb arc CLK --> Q
	 (CLK => Q) = (1.0,1.0);

	if(E===1'b1 && TE===1'b1)
	// comb arc CLK --> Q
	 (CLK => Q) = (1.0,1.0);

	ifnone
	// comb arc CLK --> Q
	 (CLK => Q) = (1.0,1.0);

	if(E===1'b0 && TE===1'b0)
	// comb arc CLK --> Q
	 (CLK => Q) = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_E_AND_NOT_TE === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_E_AND_TE === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_E_AND_NOT_TE === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_E_AND_TE === 1'b1)
		,1.0,0,notifier);

	// hold E-HL CLK-LH
	$hold(posedge CLK,negedge E,1.0,notifier);

	// hold E-LH CLK-LH
	$hold(posedge CLK,posedge E,1.0,notifier);

	// setup E-HL CLK-LH
	$setup(negedge E,posedge CLK,1.0,notifier);

	// setup E-LH CLK-LH
	$setup(posedge E,posedge CLK,1.0,notifier);

	// hold TE-HL CLK-LH
	$hold(posedge CLK,negedge TE,1.0,notifier);

	// hold TE-LH CLK-LH
	$hold(posedge CLK,posedge TE,1.0,notifier);

	// setup TE-HL CLK-LH
	$setup(negedge TE,posedge CLK,1.0,notifier);

	// setup TE-LH CLK-LH
	$setup(posedge TE,posedge CLK,1.0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__ICGTP_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__ICGTP_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__ICGTP_FUNC_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__icgtp_func( TE, E, CLK, Q, VDD, VSS, VNW, VPW, notifier );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__icgtp_func( TE, E, CLK, Q, notifier );
`endif // If not USE_POWER_PINS
input CLK, E, TE, notifier;
output Q;

	not MGM_BG_0( MGM_EN0, CLK );

	or MGM_BG_1( MGM_D0, E, TE );

	gf180mcu_fd_sc_mcu9t5v0__udp_n_iq_latch( IQ2, 1'b0, 1'b0, MGM_EN0, MGM_D0, notifier );

	and MGM_BG_2( Q, CLK, IQ2 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__ICGTP_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__INV_1_V
`define GF180MCU_FD_SC_MCU9T5V0__INV_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__inv_1( I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__inv_1( I, ZN );
`endif // If not USE_POWER_PINS
input I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__inv_func gf180mcu_fd_sc_mcu9t5v0__inv_inst(.I(I),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__inv_func gf180mcu_fd_sc_mcu9t5v0__inv_inst(.I(I),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__INV_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__INV_2_V
`define GF180MCU_FD_SC_MCU9T5V0__INV_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__inv_2( I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__inv_2( I, ZN );
`endif // If not USE_POWER_PINS
input I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__inv_func gf180mcu_fd_sc_mcu9t5v0__inv_inst(.I(I),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__inv_func gf180mcu_fd_sc_mcu9t5v0__inv_inst(.I(I),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__INV_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__INV_3_V
`define GF180MCU_FD_SC_MCU9T5V0__INV_3_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__inv_3( I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__inv_3( I, ZN );
`endif // If not USE_POWER_PINS
input I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__inv_func gf180mcu_fd_sc_mcu9t5v0__inv_inst(.I(I),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__inv_func gf180mcu_fd_sc_mcu9t5v0__inv_inst(.I(I),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__INV_3_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__INV_4_V
`define GF180MCU_FD_SC_MCU9T5V0__INV_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__inv_4( I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__inv_4( I, ZN );
`endif // If not USE_POWER_PINS
input I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__inv_func gf180mcu_fd_sc_mcu9t5v0__inv_inst(.I(I),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__inv_func gf180mcu_fd_sc_mcu9t5v0__inv_inst(.I(I),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__INV_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__INV_8_V
`define GF180MCU_FD_SC_MCU9T5V0__INV_8_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__inv_8( I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__inv_8( I, ZN );
`endif // If not USE_POWER_PINS
input I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__inv_func gf180mcu_fd_sc_mcu9t5v0__inv_inst(.I(I),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__inv_func gf180mcu_fd_sc_mcu9t5v0__inv_inst(.I(I),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__INV_8_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__INV_12_V
`define GF180MCU_FD_SC_MCU9T5V0__INV_12_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__inv_12( I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__inv_12( I, ZN );
`endif // If not USE_POWER_PINS
input I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__inv_func gf180mcu_fd_sc_mcu9t5v0__inv_inst(.I(I),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__inv_func gf180mcu_fd_sc_mcu9t5v0__inv_inst(.I(I),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__INV_12_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__INV_16_V
`define GF180MCU_FD_SC_MCU9T5V0__INV_16_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__inv_16( I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__inv_16( I, ZN );
`endif // If not USE_POWER_PINS
input I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__inv_func gf180mcu_fd_sc_mcu9t5v0__inv_inst(.I(I),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__inv_func gf180mcu_fd_sc_mcu9t5v0__inv_inst(.I(I),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__INV_16_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__INV_20_V
`define GF180MCU_FD_SC_MCU9T5V0__INV_20_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__inv_20( I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__inv_20( I, ZN );
`endif // If not USE_POWER_PINS
input I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__inv_func gf180mcu_fd_sc_mcu9t5v0__inv_inst(.I(I),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__inv_func gf180mcu_fd_sc_mcu9t5v0__inv_inst(.I(I),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__INV_20_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__INV_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__INV_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__inv_func( I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__inv_func( I, ZN );
`endif // If not USE_POWER_PINS
input I;
output ZN;

	not MGM_BG_0( ZN, I );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__INV_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__INVZ_1_V
`define GF180MCU_FD_SC_MCU9T5V0__INVZ_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__invz_1( EN, ZN, I, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__invz_1( EN, ZN, I );
`endif // If not USE_POWER_PINS
input EN, I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__invz_func gf180mcu_fd_sc_mcu9t5v0__invz_inst(.EN(EN),.ZN(ZN),.I(I),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__invz_func gf180mcu_fd_sc_mcu9t5v0__invz_inst(.EN(EN),.ZN(ZN),.I(I));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc EN --> ZN
	 (EN => ZN) = (1.0,1.0);

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__INVZ_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__INVZ_2_V
`define GF180MCU_FD_SC_MCU9T5V0__INVZ_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__invz_2( EN, ZN, I, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__invz_2( EN, ZN, I );
`endif // If not USE_POWER_PINS
input EN, I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__invz_func gf180mcu_fd_sc_mcu9t5v0__invz_inst(.EN(EN),.ZN(ZN),.I(I),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__invz_func gf180mcu_fd_sc_mcu9t5v0__invz_inst(.EN(EN),.ZN(ZN),.I(I));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc EN --> ZN
	 (EN => ZN) = (1.0,1.0);

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__INVZ_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__INVZ_3_V
`define GF180MCU_FD_SC_MCU9T5V0__INVZ_3_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__invz_3( EN, I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__invz_3( EN, I, ZN );
`endif // If not USE_POWER_PINS
input EN, I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__invz_func gf180mcu_fd_sc_mcu9t5v0__invz_inst(.EN(EN),.I(I),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__invz_func gf180mcu_fd_sc_mcu9t5v0__invz_inst(.EN(EN),.I(I),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc EN --> ZN
	 (EN => ZN) = (1.0,1.0);

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__INVZ_3_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__INVZ_4_V
`define GF180MCU_FD_SC_MCU9T5V0__INVZ_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__invz_4( EN, I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__invz_4( EN, I, ZN );
`endif // If not USE_POWER_PINS
input EN, I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__invz_func gf180mcu_fd_sc_mcu9t5v0__invz_inst(.EN(EN),.I(I),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__invz_func gf180mcu_fd_sc_mcu9t5v0__invz_inst(.EN(EN),.I(I),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc EN --> ZN
	 (EN => ZN) = (1.0,1.0);

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__INVZ_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__INVZ_8_V
`define GF180MCU_FD_SC_MCU9T5V0__INVZ_8_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__invz_8( EN, I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__invz_8( EN, I, ZN );
`endif // If not USE_POWER_PINS
input EN, I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__invz_func gf180mcu_fd_sc_mcu9t5v0__invz_inst(.EN(EN),.I(I),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__invz_func gf180mcu_fd_sc_mcu9t5v0__invz_inst(.EN(EN),.I(I),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc EN --> ZN
	 (EN => ZN) = (1.0,1.0);

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__INVZ_8_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__INVZ_12_V
`define GF180MCU_FD_SC_MCU9T5V0__INVZ_12_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__invz_12( EN, I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__invz_12( EN, I, ZN );
`endif // If not USE_POWER_PINS
input EN, I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__invz_func gf180mcu_fd_sc_mcu9t5v0__invz_inst(.EN(EN),.I(I),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__invz_func gf180mcu_fd_sc_mcu9t5v0__invz_inst(.EN(EN),.I(I),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc EN --> ZN
	 (EN => ZN) = (1.0,1.0);

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__INVZ_12_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__INVZ_16_V
`define GF180MCU_FD_SC_MCU9T5V0__INVZ_16_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__invz_16( EN, I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__invz_16( EN, I, ZN );
`endif // If not USE_POWER_PINS
input EN, I;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__invz_func gf180mcu_fd_sc_mcu9t5v0__invz_inst(.EN(EN),.I(I),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__invz_func gf180mcu_fd_sc_mcu9t5v0__invz_inst(.EN(EN),.I(I),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc EN --> ZN
	 (EN => ZN) = (1.0,1.0);

	// comb arc I --> ZN
	 (I => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__INVZ_16_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__INVZ_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__INVZ_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__invz_func( EN, I, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__invz_func( EN, I, ZN );
`endif // If not USE_POWER_PINS
input EN, I;
output ZN;

	wire MGM_WB_0;

	wire MGM_WB_1;

	wire I_inv_for_gf180mcu_fd_sc_mcu9t5v0__invz_16;

	not MGM_BG_0( I_inv_for_gf180mcu_fd_sc_mcu9t5v0__invz_16, I );

	and MGM_BG_1( MGM_WB_0, I_inv_for_gf180mcu_fd_sc_mcu9t5v0__invz_16, EN );

	not MGM_BG_2( MGM_WB_1, EN );

	bufif0 MGM_BG_3( ZN, MGM_WB_0,MGM_WB_1 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__INVZ_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__LATQ_1_V
`define GF180MCU_FD_SC_MCU9T5V0__LATQ_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latq_1( E, D, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latq_1( E, D, Q );
`endif // If not USE_POWER_PINS
input D, E;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latq_func gf180mcu_fd_sc_mcu9t5v0__latq_inst(.E(E),.D(D),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latq_func gf180mcu_fd_sc_mcu9t5v0__latq_inst(.E(E),.D(D),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(ENABLE_NOT_D,D);


	buf MGM_G1(ENABLE_D,D);


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc D --> Q
	 (D => Q) = (1.0,1.0);

	// seq arc E --> Q
	(posedge E => (Q : D))  = (1.0,1.0);

	// hold D-HL E-HL
	$hold(negedge E,negedge D,1.0,notifier);

	// hold D-LH E-HL
	$hold(negedge E,posedge D,1.0,notifier);

	// setup D-HL E-HL
	$setup(negedge D,negedge E,1.0,notifier);

	// setup D-LH E-HL
	$setup(posedge D,negedge E,1.0,notifier);

	$width(posedge E &&& (ENABLE_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(posedge E &&& (ENABLE_D === 1'b1)
		,1.0,0,notifier);

	// mpw E_lh
	$width(posedge E,1.0,0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__LATQ_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__LATQ_2_V
`define GF180MCU_FD_SC_MCU9T5V0__LATQ_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latq_2( E, D, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latq_2( E, D, Q );
`endif // If not USE_POWER_PINS
input D, E;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latq_func gf180mcu_fd_sc_mcu9t5v0__latq_inst(.E(E),.D(D),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latq_func gf180mcu_fd_sc_mcu9t5v0__latq_inst(.E(E),.D(D),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(ENABLE_NOT_D,D);


	buf MGM_G1(ENABLE_D,D);


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc D --> Q
	 (D => Q) = (1.0,1.0);

	// seq arc E --> Q
	(posedge E => (Q : D))  = (1.0,1.0);

	// hold D-HL E-HL
	$hold(negedge E,negedge D,1.0,notifier);

	// hold D-LH E-HL
	$hold(negedge E,posedge D,1.0,notifier);

	// setup D-HL E-HL
	$setup(negedge D,negedge E,1.0,notifier);

	// setup D-LH E-HL
	$setup(posedge D,negedge E,1.0,notifier);

	$width(posedge E &&& (ENABLE_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(posedge E &&& (ENABLE_D === 1'b1)
		,1.0,0,notifier);

	// mpw E_lh
	$width(posedge E,1.0,0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__LATQ_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__LATQ_4_V
`define GF180MCU_FD_SC_MCU9T5V0__LATQ_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latq_4( E, D, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latq_4( E, D, Q );
`endif // If not USE_POWER_PINS
input D, E;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latq_func gf180mcu_fd_sc_mcu9t5v0__latq_inst(.E(E),.D(D),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latq_func gf180mcu_fd_sc_mcu9t5v0__latq_inst(.E(E),.D(D),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(ENABLE_NOT_D,D);


	buf MGM_G1(ENABLE_D,D);


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc D --> Q
	 (D => Q) = (1.0,1.0);

	// seq arc E --> Q
	(posedge E => (Q : D))  = (1.0,1.0);

	// hold D-HL E-HL
	$hold(negedge E,negedge D,1.0,notifier);

	// hold D-LH E-HL
	$hold(negedge E,posedge D,1.0,notifier);

	// setup D-HL E-HL
	$setup(negedge D,negedge E,1.0,notifier);

	// setup D-LH E-HL
	$setup(posedge D,negedge E,1.0,notifier);

	$width(posedge E &&& (ENABLE_NOT_D === 1'b1)
		,1.0,0,notifier);

	$width(posedge E &&& (ENABLE_D === 1'b1)
		,1.0,0,notifier);

	// mpw E_lh
	$width(posedge E,1.0,0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__LATQ_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__LATQ_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__LATQ_FUNC_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latq_func( E, D, Q, VDD, VSS, VNW, VPW, notifier );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latq_func( E, D, Q, notifier );
`endif // If not USE_POWER_PINS
input D, E, notifier;
output Q;

	not MGM_BG_0( MGM_D0, D );

	gf180mcu_fd_sc_mcu9t5v0__udp_n_iq_latch( IQ1, 1'b0, 1'b0, E, MGM_D0, notifier );

	not MGM_BG_1( Q, IQ1 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__LATQ_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__LATRNQ_1_V
`define GF180MCU_FD_SC_MCU9T5V0__LATRNQ_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latrnq_1( E, RN, D, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latrnq_1( E, RN, D, Q );
`endif // If not USE_POWER_PINS
input D, E, RN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latrnq_func gf180mcu_fd_sc_mcu9t5v0__latrnq_inst(.E(E),.RN(RN),.D(D),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latrnq_func gf180mcu_fd_sc_mcu9t5v0__latrnq_inst(.E(E),.RN(RN),.D(D),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	buf MGM_G0(ENABLE_RN,RN);


	not MGM_G1(MGM_W0,D);


	and MGM_G2(ENABLE_NOT_D_AND_RN,RN,MGM_W0);


	and MGM_G3(ENABLE_D_AND_RN,RN,D);


	not MGM_G4(MGM_W1,D);


	not MGM_G5(MGM_W2,E);


	and MGM_G6(ENABLE_NOT_D_AND_NOT_E,MGM_W2,MGM_W1);


	not MGM_G7(MGM_W3,E);


	and MGM_G8(ENABLE_D_AND_NOT_E,MGM_W3,D);


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc D --> Q
	 (D => Q) = (1.0,1.0);

	// seq arc E --> Q
	(posedge E => (Q : D))  = (1.0,1.0);

	if(D===1'b0 && E===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	// hold D-HL E-HL
	$hold(negedge E &&& (ENABLE_RN === 1'b1),
		negedge D &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// hold D-LH E-HL
	$hold(negedge E &&& (ENABLE_RN === 1'b1),
		posedge D &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// setup D-HL E-HL
	$setup(negedge D &&& (ENABLE_RN === 1'b1),
		negedge E &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// setup D-LH E-HL
	$setup(posedge D &&& (ENABLE_RN === 1'b1),
		negedge E &&& (ENABLE_RN === 1'b1),1.0,notifier);

	$width(posedge E &&& (ENABLE_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(posedge E &&& (ENABLE_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	// recovery RN-LH E-HL
	$recovery(posedge RN,negedge E,1.0,notifier);

	// removal RN-LH E-HL
	$removal(posedge RN,negedge E,1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_D_AND_NOT_E === 1'b1)
		,1.0,0,notifier);

	// mpw E_lh
	$width(posedge E,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__LATRNQ_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__LATRNQ_2_V
`define GF180MCU_FD_SC_MCU9T5V0__LATRNQ_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latrnq_2( E, RN, D, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latrnq_2( E, RN, D, Q );
`endif // If not USE_POWER_PINS
input D, E, RN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latrnq_func gf180mcu_fd_sc_mcu9t5v0__latrnq_inst(.E(E),.RN(RN),.D(D),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latrnq_func gf180mcu_fd_sc_mcu9t5v0__latrnq_inst(.E(E),.RN(RN),.D(D),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	buf MGM_G0(ENABLE_RN,RN);


	not MGM_G1(MGM_W0,D);


	and MGM_G2(ENABLE_NOT_D_AND_RN,RN,MGM_W0);


	and MGM_G3(ENABLE_D_AND_RN,RN,D);


	not MGM_G4(MGM_W1,D);


	not MGM_G5(MGM_W2,E);


	and MGM_G6(ENABLE_NOT_D_AND_NOT_E,MGM_W2,MGM_W1);


	not MGM_G7(MGM_W3,E);


	and MGM_G8(ENABLE_D_AND_NOT_E,MGM_W3,D);


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc D --> Q
	 (D => Q) = (1.0,1.0);

	// seq arc E --> Q
	(posedge E => (Q : D))  = (1.0,1.0);

	if(D===1'b0 && E===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	// hold D-HL E-HL
	$hold(negedge E &&& (ENABLE_RN === 1'b1),
		negedge D &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// hold D-LH E-HL
	$hold(negedge E &&& (ENABLE_RN === 1'b1),
		posedge D &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// setup D-HL E-HL
	$setup(negedge D &&& (ENABLE_RN === 1'b1),
		negedge E &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// setup D-LH E-HL
	$setup(posedge D &&& (ENABLE_RN === 1'b1),
		negedge E &&& (ENABLE_RN === 1'b1),1.0,notifier);

	$width(posedge E &&& (ENABLE_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(posedge E &&& (ENABLE_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	// recovery RN-LH E-HL
	$recovery(posedge RN,negedge E,1.0,notifier);

	// removal RN-LH E-HL
	$removal(posedge RN,negedge E,1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_D_AND_NOT_E === 1'b1)
		,1.0,0,notifier);

	// mpw E_lh
	$width(posedge E,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__LATRNQ_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__LATRNQ_4_V
`define GF180MCU_FD_SC_MCU9T5V0__LATRNQ_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latrnq_4( E, RN, D, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latrnq_4( E, RN, D, Q );
`endif // If not USE_POWER_PINS
input D, E, RN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latrnq_func gf180mcu_fd_sc_mcu9t5v0__latrnq_inst(.E(E),.RN(RN),.D(D),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latrnq_func gf180mcu_fd_sc_mcu9t5v0__latrnq_inst(.E(E),.RN(RN),.D(D),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	buf MGM_G0(ENABLE_RN,RN);


	not MGM_G1(MGM_W0,D);


	and MGM_G2(ENABLE_NOT_D_AND_RN,RN,MGM_W0);


	and MGM_G3(ENABLE_D_AND_RN,RN,D);


	not MGM_G4(MGM_W1,D);


	not MGM_G5(MGM_W2,E);


	and MGM_G6(ENABLE_NOT_D_AND_NOT_E,MGM_W2,MGM_W1);


	not MGM_G7(MGM_W3,E);


	and MGM_G8(ENABLE_D_AND_NOT_E,MGM_W3,D);


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc D --> Q
	 (D => Q) = (1.0,1.0);

	// seq arc E --> Q
	(posedge E => (Q : D))  = (1.0,1.0);

	if(D===1'b0 && E===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	// hold D-HL E-HL
	$hold(negedge E &&& (ENABLE_RN === 1'b1),
		negedge D &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// hold D-LH E-HL
	$hold(negedge E &&& (ENABLE_RN === 1'b1),
		posedge D &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// setup D-HL E-HL
	$setup(negedge D &&& (ENABLE_RN === 1'b1),
		negedge E &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// setup D-LH E-HL
	$setup(posedge D &&& (ENABLE_RN === 1'b1),
		negedge E &&& (ENABLE_RN === 1'b1),1.0,notifier);

	$width(posedge E &&& (ENABLE_NOT_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(posedge E &&& (ENABLE_D_AND_RN === 1'b1)
		,1.0,0,notifier);

	// recovery RN-LH E-HL
	$recovery(posedge RN,negedge E,1.0,notifier);

	// removal RN-LH E-HL
	$removal(posedge RN,negedge E,1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_D_AND_NOT_E === 1'b1)
		,1.0,0,notifier);

	// mpw E_lh
	$width(posedge E,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__LATRNQ_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__LATRNQ_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__LATRNQ_FUNC_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latrnq_func( E, RN, D, Q, VDD, VSS, VNW, VPW, notifier );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latrnq_func( E, RN, D, Q, notifier );
`endif // If not USE_POWER_PINS
input D, E, RN, notifier;
output Q;

	not MGM_BG_0( MGM_C0, RN );

	gf180mcu_fd_sc_mcu9t5v0__udp_n_iq_latch( IQ2, MGM_C0, 1'b0, E, D, notifier );

	buf MGM_BG_1( Q, IQ2 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__LATRNQ_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__LATRSNQ_1_V
`define GF180MCU_FD_SC_MCU9T5V0__LATRSNQ_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latrsnq_1( E, RN, D, SETN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latrsnq_1( E, RN, D, SETN, Q );
`endif // If not USE_POWER_PINS
input D, E, RN, SETN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latrsnq_func gf180mcu_fd_sc_mcu9t5v0__latrsnq_inst(.E(E),.RN(RN),.D(D),.SETN(SETN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latrsnq_func gf180mcu_fd_sc_mcu9t5v0__latrsnq_inst(.E(E),.RN(RN),.D(D),.SETN(SETN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	and MGM_G0(ENABLE_RN_AND_SETN,SETN,RN);


	not MGM_G1(MGM_W0,D);


	and MGM_G2(MGM_W1,RN,MGM_W0);


	and MGM_G3(ENABLE_NOT_D_AND_RN_AND_SETN,SETN,MGM_W1);


	and MGM_G4(MGM_W2,RN,D);


	and MGM_G5(ENABLE_D_AND_RN_AND_SETN,SETN,MGM_W2);


	buf MGM_G6(ENABLE_SETN,SETN);


	not MGM_G7(MGM_W3,D);


	not MGM_G8(MGM_W4,E);


	and MGM_G9(MGM_W5,MGM_W4,MGM_W3);


	and MGM_G10(ENABLE_NOT_D_AND_NOT_E_AND_SETN,SETN,MGM_W5);


	not MGM_G11(MGM_W6,E);


	and MGM_G12(MGM_W7,MGM_W6,D);


	and MGM_G13(ENABLE_D_AND_NOT_E_AND_SETN,SETN,MGM_W7);


	not MGM_G14(MGM_W8,D);


	not MGM_G15(MGM_W9,E);


	and MGM_G16(ENABLE_NOT_D_AND_NOT_E,MGM_W9,MGM_W8);


	not MGM_G17(MGM_W10,E);


	and MGM_G18(ENABLE_D_AND_NOT_E,MGM_W10,D);


	buf MGM_G19(ENABLE_RN,RN);


	not MGM_G20(MGM_W11,D);


	not MGM_G21(MGM_W12,E);


	and MGM_G22(MGM_W13,MGM_W12,MGM_W11);


	and MGM_G23(ENABLE_NOT_D_AND_NOT_E_AND_RN,RN,MGM_W13);


	not MGM_G24(MGM_W14,E);


	and MGM_G25(MGM_W15,MGM_W14,D);


	and MGM_G26(ENABLE_D_AND_NOT_E_AND_RN,RN,MGM_W15);


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc D --> Q
	 (D => Q) = (1.0,1.0);

	// seq arc E --> Q
	(posedge E => (Q : D))  = (1.0,1.0);

	if(D===1'b0 && E===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(D===1'b0 && E===1'b0 && RN===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b0 && E===1'b1 && RN===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b0 && E===1'b1 && RN===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b0 && RN===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b1 && RN===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b0 && E===1'b0 && RN===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b0 && RN===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	// hold D-HL E-HL
	$hold(negedge E &&& (ENABLE_RN_AND_SETN === 1'b1),
		negedge D &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// hold D-LH E-HL
	$hold(negedge E &&& (ENABLE_RN_AND_SETN === 1'b1),
		posedge D &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// setup D-HL E-HL
	$setup(negedge D &&& (ENABLE_RN_AND_SETN === 1'b1),
		negedge E &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// setup D-LH E-HL
	$setup(posedge D &&& (ENABLE_RN_AND_SETN === 1'b1),
		negedge E &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	$width(posedge E &&& (ENABLE_NOT_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge E &&& (ENABLE_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// recovery RN-LH E-HL
	$recovery(posedge RN &&& (ENABLE_SETN === 1'b1),
		negedge E &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// removal RN-LH E-HL
	$removal(posedge RN &&& (ENABLE_SETN === 1'b1),
		negedge E &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_D_AND_NOT_E_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_D_AND_NOT_E_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),
		posedge RN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),
		posedge SETN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_D_AND_NOT_E === 1'b1),
		posedge RN &&& (ENABLE_D_AND_NOT_E === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_D_AND_NOT_E === 1'b1),
		posedge SETN &&& (ENABLE_D_AND_NOT_E === 1'b1),1.0,notifier);

	// recovery SETN-LH E-HL
	$recovery(posedge SETN &&& (ENABLE_RN === 1'b1),
		negedge E &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// removal SETN-LH E-HL
	$removal(posedge SETN &&& (ENABLE_RN === 1'b1),
		negedge E &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),
		posedge SETN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),
		posedge RN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_D_AND_NOT_E === 1'b1),
		posedge SETN &&& (ENABLE_D_AND_NOT_E === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_D_AND_NOT_E === 1'b1),
		posedge RN &&& (ENABLE_D_AND_NOT_E === 1'b1),1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_D_AND_NOT_E_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_D_AND_NOT_E_AND_RN === 1'b1)
		,1.0,0,notifier);

	// mpw E_lh
	$width(posedge E,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__LATRSNQ_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__LATRSNQ_2_V
`define GF180MCU_FD_SC_MCU9T5V0__LATRSNQ_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latrsnq_2( E, RN, D, SETN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latrsnq_2( E, RN, D, SETN, Q );
`endif // If not USE_POWER_PINS
input D, E, RN, SETN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latrsnq_func gf180mcu_fd_sc_mcu9t5v0__latrsnq_inst(.E(E),.RN(RN),.D(D),.SETN(SETN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latrsnq_func gf180mcu_fd_sc_mcu9t5v0__latrsnq_inst(.E(E),.RN(RN),.D(D),.SETN(SETN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	and MGM_G0(ENABLE_RN_AND_SETN,SETN,RN);


	not MGM_G1(MGM_W0,D);


	and MGM_G2(MGM_W1,RN,MGM_W0);


	and MGM_G3(ENABLE_NOT_D_AND_RN_AND_SETN,SETN,MGM_W1);


	and MGM_G4(MGM_W2,RN,D);


	and MGM_G5(ENABLE_D_AND_RN_AND_SETN,SETN,MGM_W2);


	buf MGM_G6(ENABLE_SETN,SETN);


	not MGM_G7(MGM_W3,D);


	not MGM_G8(MGM_W4,E);


	and MGM_G9(MGM_W5,MGM_W4,MGM_W3);


	and MGM_G10(ENABLE_NOT_D_AND_NOT_E_AND_SETN,SETN,MGM_W5);


	not MGM_G11(MGM_W6,E);


	and MGM_G12(MGM_W7,MGM_W6,D);


	and MGM_G13(ENABLE_D_AND_NOT_E_AND_SETN,SETN,MGM_W7);


	not MGM_G14(MGM_W8,D);


	not MGM_G15(MGM_W9,E);


	and MGM_G16(ENABLE_NOT_D_AND_NOT_E,MGM_W9,MGM_W8);


	not MGM_G17(MGM_W10,E);


	and MGM_G18(ENABLE_D_AND_NOT_E,MGM_W10,D);


	buf MGM_G19(ENABLE_RN,RN);


	not MGM_G20(MGM_W11,D);


	not MGM_G21(MGM_W12,E);


	and MGM_G22(MGM_W13,MGM_W12,MGM_W11);


	and MGM_G23(ENABLE_NOT_D_AND_NOT_E_AND_RN,RN,MGM_W13);


	not MGM_G24(MGM_W14,E);


	and MGM_G25(MGM_W15,MGM_W14,D);


	and MGM_G26(ENABLE_D_AND_NOT_E_AND_RN,RN,MGM_W15);


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc D --> Q
	 (D => Q) = (1.0,1.0);

	// seq arc E --> Q
	(posedge E => (Q : D))  = (1.0,1.0);

	if(D===1'b0 && E===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(D===1'b0 && E===1'b0 && RN===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b0 && E===1'b1 && RN===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b0 && E===1'b1 && RN===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b0 && RN===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b1 && RN===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b0 && E===1'b0 && RN===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b0 && RN===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	// hold D-HL E-HL
	$hold(negedge E &&& (ENABLE_RN_AND_SETN === 1'b1),
		negedge D &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// hold D-LH E-HL
	$hold(negedge E &&& (ENABLE_RN_AND_SETN === 1'b1),
		posedge D &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// setup D-HL E-HL
	$setup(negedge D &&& (ENABLE_RN_AND_SETN === 1'b1),
		negedge E &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// setup D-LH E-HL
	$setup(posedge D &&& (ENABLE_RN_AND_SETN === 1'b1),
		negedge E &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	$width(posedge E &&& (ENABLE_NOT_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge E &&& (ENABLE_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// recovery RN-LH E-HL
	$recovery(posedge RN &&& (ENABLE_SETN === 1'b1),
		negedge E &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// removal RN-LH E-HL
	$removal(posedge RN &&& (ENABLE_SETN === 1'b1),
		negedge E &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_D_AND_NOT_E_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_D_AND_NOT_E_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),
		posedge RN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),
		posedge SETN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_D_AND_NOT_E === 1'b1),
		posedge RN &&& (ENABLE_D_AND_NOT_E === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_D_AND_NOT_E === 1'b1),
		posedge SETN &&& (ENABLE_D_AND_NOT_E === 1'b1),1.0,notifier);

	// recovery SETN-LH E-HL
	$recovery(posedge SETN &&& (ENABLE_RN === 1'b1),
		negedge E &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// removal SETN-LH E-HL
	$removal(posedge SETN &&& (ENABLE_RN === 1'b1),
		negedge E &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),
		posedge SETN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),
		posedge RN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_D_AND_NOT_E === 1'b1),
		posedge SETN &&& (ENABLE_D_AND_NOT_E === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_D_AND_NOT_E === 1'b1),
		posedge RN &&& (ENABLE_D_AND_NOT_E === 1'b1),1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_D_AND_NOT_E_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_D_AND_NOT_E_AND_RN === 1'b1)
		,1.0,0,notifier);

	// mpw E_lh
	$width(posedge E,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__LATRSNQ_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__LATRSNQ_4_V
`define GF180MCU_FD_SC_MCU9T5V0__LATRSNQ_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latrsnq_4( E, RN, D, SETN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latrsnq_4( E, RN, D, SETN, Q );
`endif // If not USE_POWER_PINS
input D, E, RN, SETN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latrsnq_func gf180mcu_fd_sc_mcu9t5v0__latrsnq_inst(.E(E),.RN(RN),.D(D),.SETN(SETN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latrsnq_func gf180mcu_fd_sc_mcu9t5v0__latrsnq_inst(.E(E),.RN(RN),.D(D),.SETN(SETN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	and MGM_G0(ENABLE_RN_AND_SETN,SETN,RN);


	not MGM_G1(MGM_W0,D);


	and MGM_G2(MGM_W1,RN,MGM_W0);


	and MGM_G3(ENABLE_NOT_D_AND_RN_AND_SETN,SETN,MGM_W1);


	and MGM_G4(MGM_W2,RN,D);


	and MGM_G5(ENABLE_D_AND_RN_AND_SETN,SETN,MGM_W2);


	buf MGM_G6(ENABLE_SETN,SETN);


	not MGM_G7(MGM_W3,D);


	not MGM_G8(MGM_W4,E);


	and MGM_G9(MGM_W5,MGM_W4,MGM_W3);


	and MGM_G10(ENABLE_NOT_D_AND_NOT_E_AND_SETN,SETN,MGM_W5);


	not MGM_G11(MGM_W6,E);


	and MGM_G12(MGM_W7,MGM_W6,D);


	and MGM_G13(ENABLE_D_AND_NOT_E_AND_SETN,SETN,MGM_W7);


	not MGM_G14(MGM_W8,D);


	not MGM_G15(MGM_W9,E);


	and MGM_G16(ENABLE_NOT_D_AND_NOT_E,MGM_W9,MGM_W8);


	not MGM_G17(MGM_W10,E);


	and MGM_G18(ENABLE_D_AND_NOT_E,MGM_W10,D);


	buf MGM_G19(ENABLE_RN,RN);


	not MGM_G20(MGM_W11,D);


	not MGM_G21(MGM_W12,E);


	and MGM_G22(MGM_W13,MGM_W12,MGM_W11);


	and MGM_G23(ENABLE_NOT_D_AND_NOT_E_AND_RN,RN,MGM_W13);


	not MGM_G24(MGM_W14,E);


	and MGM_G25(MGM_W15,MGM_W14,D);


	and MGM_G26(ENABLE_D_AND_NOT_E_AND_RN,RN,MGM_W15);


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc D --> Q
	 (D => Q) = (1.0,1.0);

	// seq arc E --> Q
	(posedge E => (Q : D))  = (1.0,1.0);

	if(D===1'b0 && E===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(D===1'b0 && E===1'b0 && RN===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b0 && E===1'b1 && RN===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b0 && E===1'b1 && RN===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b0 && RN===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b1 && RN===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b0 && E===1'b0 && RN===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b0 && RN===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	// hold D-HL E-HL
	$hold(negedge E &&& (ENABLE_RN_AND_SETN === 1'b1),
		negedge D &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// hold D-LH E-HL
	$hold(negedge E &&& (ENABLE_RN_AND_SETN === 1'b1),
		posedge D &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// setup D-HL E-HL
	$setup(negedge D &&& (ENABLE_RN_AND_SETN === 1'b1),
		negedge E &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	// setup D-LH E-HL
	$setup(posedge D &&& (ENABLE_RN_AND_SETN === 1'b1),
		negedge E &&& (ENABLE_RN_AND_SETN === 1'b1),1.0,notifier);

	$width(posedge E &&& (ENABLE_NOT_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge E &&& (ENABLE_D_AND_RN_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// recovery RN-LH E-HL
	$recovery(posedge RN &&& (ENABLE_SETN === 1'b1),
		negedge E &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// removal RN-LH E-HL
	$removal(posedge RN &&& (ENABLE_SETN === 1'b1),
		negedge E &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_D_AND_NOT_E_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_D_AND_NOT_E_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),
		posedge RN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),
		posedge SETN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_D_AND_NOT_E === 1'b1),
		posedge RN &&& (ENABLE_D_AND_NOT_E === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_D_AND_NOT_E === 1'b1),
		posedge SETN &&& (ENABLE_D_AND_NOT_E === 1'b1),1.0,notifier);

	// recovery SETN-LH E-HL
	$recovery(posedge SETN &&& (ENABLE_RN === 1'b1),
		negedge E &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// removal SETN-LH E-HL
	$removal(posedge SETN &&& (ENABLE_RN === 1'b1),
		negedge E &&& (ENABLE_RN === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),
		posedge SETN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),
		posedge RN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_D_AND_NOT_E === 1'b1),
		posedge SETN &&& (ENABLE_D_AND_NOT_E === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_D_AND_NOT_E === 1'b1),
		posedge RN &&& (ENABLE_D_AND_NOT_E === 1'b1),1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_D_AND_NOT_E_AND_RN === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_D_AND_NOT_E_AND_RN === 1'b1)
		,1.0,0,notifier);

	// mpw E_lh
	$width(posedge E,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__LATRSNQ_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__LATRSNQ_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__LATRSNQ_FUNC_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latrsnq_func( E, RN, D, SETN, Q, VDD, VSS, VNW, VPW, notifier );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latrsnq_func( E, RN, D, SETN, Q, notifier );
`endif // If not USE_POWER_PINS
input D, E, RN, SETN, notifier;
output Q;

	not MGM_BG_0( MGM_P0, SETN );

	not MGM_BG_1( MGM_C0, RN );

	gf180mcu_fd_sc_mcu9t5v0__udp_hn_iq_latch( IQ2, MGM_C0, MGM_P0, E, D, notifier );

	buf MGM_BG_2( Q, IQ2 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__LATRSNQ_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__LATSNQ_1_V
`define GF180MCU_FD_SC_MCU9T5V0__LATSNQ_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latsnq_1( E, D, SETN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latsnq_1( E, D, SETN, Q );
`endif // If not USE_POWER_PINS
input D, E, SETN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latsnq_func gf180mcu_fd_sc_mcu9t5v0__latsnq_inst(.E(E),.D(D),.SETN(SETN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latsnq_func gf180mcu_fd_sc_mcu9t5v0__latsnq_inst(.E(E),.D(D),.SETN(SETN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	buf MGM_G0(ENABLE_SETN,SETN);


	not MGM_G1(MGM_W0,D);


	and MGM_G2(ENABLE_NOT_D_AND_SETN,SETN,MGM_W0);


	and MGM_G3(ENABLE_D_AND_SETN,SETN,D);


	not MGM_G4(MGM_W1,D);


	not MGM_G5(MGM_W2,E);


	and MGM_G6(ENABLE_NOT_D_AND_NOT_E,MGM_W2,MGM_W1);


	not MGM_G7(MGM_W3,E);


	and MGM_G8(ENABLE_D_AND_NOT_E,MGM_W3,D);


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc D --> Q
	 (D => Q) = (1.0,1.0);

	// seq arc E --> Q
	(posedge E => (Q : D))  = (1.0,1.0);

	if(D===1'b0 && E===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b0 && E===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	// hold D-HL E-HL
	$hold(negedge E &&& (ENABLE_SETN === 1'b1),
		negedge D &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// hold D-LH E-HL
	$hold(negedge E &&& (ENABLE_SETN === 1'b1),
		posedge D &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// setup D-HL E-HL
	$setup(negedge D &&& (ENABLE_SETN === 1'b1),
		negedge E &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// setup D-LH E-HL
	$setup(posedge D &&& (ENABLE_SETN === 1'b1),
		negedge E &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	$width(posedge E &&& (ENABLE_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge E &&& (ENABLE_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// recovery SETN-LH E-HL
	$recovery(posedge SETN,negedge E,1.0,notifier);

	// removal SETN-LH E-HL
	$removal(posedge SETN,negedge E,1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_D_AND_NOT_E === 1'b1)
		,1.0,0,notifier);

	// mpw E_lh
	$width(posedge E,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__LATSNQ_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__LATSNQ_2_V
`define GF180MCU_FD_SC_MCU9T5V0__LATSNQ_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latsnq_2( E, D, SETN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latsnq_2( E, D, SETN, Q );
`endif // If not USE_POWER_PINS
input D, E, SETN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latsnq_func gf180mcu_fd_sc_mcu9t5v0__latsnq_inst(.E(E),.D(D),.SETN(SETN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latsnq_func gf180mcu_fd_sc_mcu9t5v0__latsnq_inst(.E(E),.D(D),.SETN(SETN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	buf MGM_G0(ENABLE_SETN,SETN);


	not MGM_G1(MGM_W0,D);


	and MGM_G2(ENABLE_NOT_D_AND_SETN,SETN,MGM_W0);


	and MGM_G3(ENABLE_D_AND_SETN,SETN,D);


	not MGM_G4(MGM_W1,D);


	not MGM_G5(MGM_W2,E);


	and MGM_G6(ENABLE_NOT_D_AND_NOT_E,MGM_W2,MGM_W1);


	not MGM_G7(MGM_W3,E);


	and MGM_G8(ENABLE_D_AND_NOT_E,MGM_W3,D);


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc D --> Q
	 (D => Q) = (1.0,1.0);

	// seq arc E --> Q
	(posedge E => (Q : D))  = (1.0,1.0);

	if(D===1'b0 && E===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b0 && E===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	// hold D-HL E-HL
	$hold(negedge E &&& (ENABLE_SETN === 1'b1),
		negedge D &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// hold D-LH E-HL
	$hold(negedge E &&& (ENABLE_SETN === 1'b1),
		posedge D &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// setup D-HL E-HL
	$setup(negedge D &&& (ENABLE_SETN === 1'b1),
		negedge E &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// setup D-LH E-HL
	$setup(posedge D &&& (ENABLE_SETN === 1'b1),
		negedge E &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	$width(posedge E &&& (ENABLE_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge E &&& (ENABLE_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// recovery SETN-LH E-HL
	$recovery(posedge SETN,negedge E,1.0,notifier);

	// removal SETN-LH E-HL
	$removal(posedge SETN,negedge E,1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_D_AND_NOT_E === 1'b1)
		,1.0,0,notifier);

	// mpw E_lh
	$width(posedge E,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__LATSNQ_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__LATSNQ_4_V
`define GF180MCU_FD_SC_MCU9T5V0__LATSNQ_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latsnq_4( E, D, SETN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latsnq_4( E, D, SETN, Q );
`endif // If not USE_POWER_PINS
input D, E, SETN;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latsnq_func gf180mcu_fd_sc_mcu9t5v0__latsnq_inst(.E(E),.D(D),.SETN(SETN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__latsnq_func gf180mcu_fd_sc_mcu9t5v0__latsnq_inst(.E(E),.D(D),.SETN(SETN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	buf MGM_G0(ENABLE_SETN,SETN);


	not MGM_G1(MGM_W0,D);


	and MGM_G2(ENABLE_NOT_D_AND_SETN,SETN,MGM_W0);


	and MGM_G3(ENABLE_D_AND_SETN,SETN,D);


	not MGM_G4(MGM_W1,D);


	not MGM_G5(MGM_W2,E);


	and MGM_G6(ENABLE_NOT_D_AND_NOT_E,MGM_W2,MGM_W1);


	not MGM_G7(MGM_W3,E);


	and MGM_G8(ENABLE_D_AND_NOT_E,MGM_W3,D);


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc D --> Q
	 (D => Q) = (1.0,1.0);

	// seq arc E --> Q
	(posedge E => (Q : D))  = (1.0,1.0);

	if(D===1'b0 && E===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b0 && E===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(D===1'b1 && E===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	// hold D-HL E-HL
	$hold(negedge E &&& (ENABLE_SETN === 1'b1),
		negedge D &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// hold D-LH E-HL
	$hold(negedge E &&& (ENABLE_SETN === 1'b1),
		posedge D &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// setup D-HL E-HL
	$setup(negedge D &&& (ENABLE_SETN === 1'b1),
		negedge E &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	// setup D-LH E-HL
	$setup(posedge D &&& (ENABLE_SETN === 1'b1),
		negedge E &&& (ENABLE_SETN === 1'b1),1.0,notifier);

	$width(posedge E &&& (ENABLE_NOT_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	$width(posedge E &&& (ENABLE_D_AND_SETN === 1'b1)
		,1.0,0,notifier);

	// recovery SETN-LH E-HL
	$recovery(posedge SETN,negedge E,1.0,notifier);

	// removal SETN-LH E-HL
	$removal(posedge SETN,negedge E,1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_D_AND_NOT_E === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_D_AND_NOT_E === 1'b1)
		,1.0,0,notifier);

	// mpw E_lh
	$width(posedge E,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__LATSNQ_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__LATSNQ_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__LATSNQ_FUNC_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latsnq_func( E, D, SETN, Q, VDD, VSS, VNW, VPW, notifier );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__latsnq_func( E, D, SETN, Q, notifier );
`endif // If not USE_POWER_PINS
input D, E, SETN, notifier;
output Q;

	not MGM_BG_0( MGM_P0, SETN );

	gf180mcu_fd_sc_mcu9t5v0__udp_n_iq_latch( IQ2, 1'b0, MGM_P0, E, D, notifier );

	buf MGM_BG_1( Q, IQ2 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__LATSNQ_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__MUX2_1_V
`define GF180MCU_FD_SC_MCU9T5V0__MUX2_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__mux2_1( Z, I1, S, I0, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__mux2_1( Z, I1, S, I0 );
`endif // If not USE_POWER_PINS
input I0, I1, S;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__mux2_func gf180mcu_fd_sc_mcu9t5v0__mux2_inst(.Z(Z),.I1(I1),.S(S),.I0(I0),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__mux2_func gf180mcu_fd_sc_mcu9t5v0__mux2_inst(.Z(Z),.I1(I1),.S(S),.I0(I0));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(I1===1'b0)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b1)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	ifnone
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I0===1'b0)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b1)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	ifnone
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	ifnone
	// comb arc posedge S --> (Z:S)
	 (posedge S => (Z:S)) = (1.0,1.0);

	ifnone
	// comb arc negedge S --> (Z:S)
	 (negedge S => (Z:S)) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__MUX2_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__MUX2_2_V
`define GF180MCU_FD_SC_MCU9T5V0__MUX2_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__mux2_2( Z, I1, S, I0, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__mux2_2( Z, I1, S, I0 );
`endif // If not USE_POWER_PINS
input I0, I1, S;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__mux2_func gf180mcu_fd_sc_mcu9t5v0__mux2_inst(.Z(Z),.I1(I1),.S(S),.I0(I0),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__mux2_func gf180mcu_fd_sc_mcu9t5v0__mux2_inst(.Z(Z),.I1(I1),.S(S),.I0(I0));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(I1===1'b0)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b1)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	ifnone
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I0===1'b0)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b1)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	ifnone
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	ifnone
	// comb arc posedge S --> (Z:S)
	 (posedge S => (Z:S)) = (1.0,1.0);

	ifnone
	// comb arc negedge S --> (Z:S)
	 (negedge S => (Z:S)) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__MUX2_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__MUX2_4_V
`define GF180MCU_FD_SC_MCU9T5V0__MUX2_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__mux2_4( Z, I1, S, I0, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__mux2_4( Z, I1, S, I0 );
`endif // If not USE_POWER_PINS
input I0, I1, S;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__mux2_func gf180mcu_fd_sc_mcu9t5v0__mux2_inst(.Z(Z),.I1(I1),.S(S),.I0(I0),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__mux2_func gf180mcu_fd_sc_mcu9t5v0__mux2_inst(.Z(Z),.I1(I1),.S(S),.I0(I0));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(I1===1'b0)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b1)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	ifnone
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I0===1'b0)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b1)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	ifnone
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	ifnone
	// comb arc posedge S --> (Z:S)
	 (posedge S => (Z:S)) = (1.0,1.0);

	ifnone
	// comb arc negedge S --> (Z:S)
	 (negedge S => (Z:S)) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__MUX2_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__MUX2_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__MUX2_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__mux2_func( Z, I1, S, I0, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__mux2_func( Z, I1, S, I0 );
`endif // If not USE_POWER_PINS
input I0, I1, S;
output Z;

	wire Z_row1;

	and MGM_BG_0( Z_row1, I0, I1 );

	wire S_inv_for_gf180mcu_fd_sc_mcu9t5v0__mux2_2;

	not MGM_BG_1( S_inv_for_gf180mcu_fd_sc_mcu9t5v0__mux2_2, S );

	wire Z_row2;

	and MGM_BG_2( Z_row2, S_inv_for_gf180mcu_fd_sc_mcu9t5v0__mux2_2, I0 );

	wire Z_row3;

	and MGM_BG_3( Z_row3, I1, S );

	or MGM_BG_4( Z, Z_row1, Z_row2, Z_row3 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__MUX2_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__MUX4_1_V
`define GF180MCU_FD_SC_MCU9T5V0__MUX4_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__mux4_1( I2, S0, I3, Z, S1, I1, I0, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__mux4_1( I2, S0, I3, Z, S1, I1, I0 );
`endif // If not USE_POWER_PINS
input I0, I1, I2, I3, S0, S1;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__mux4_func gf180mcu_fd_sc_mcu9t5v0__mux4_inst(.I2(I2),.S0(S0),.I3(I3),.Z(Z),.S1(S1),.I1(I1),.I0(I0),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__mux4_func gf180mcu_fd_sc_mcu9t5v0__mux4_inst(.I2(I2),.S0(S0),.I3(I3),.Z(Z),.S1(S1),.I1(I1),.I0(I0));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(I1===1'b0 && I2===1'b0 && I3===1'b0)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b0 && I2===1'b0 && I3===1'b1)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b0 && I2===1'b1 && I3===1'b0)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b0 && I2===1'b1 && I3===1'b1)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b1 && I2===1'b0 && I3===1'b0)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b1 && I2===1'b0 && I3===1'b1)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b1 && I2===1'b1 && I3===1'b0)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b1 && I2===1'b1 && I3===1'b1)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	ifnone
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I2===1'b0 && I3===1'b0)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I2===1'b0 && I3===1'b1)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I2===1'b1 && I3===1'b0)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I2===1'b1 && I3===1'b1)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I2===1'b0 && I3===1'b0)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I2===1'b0 && I3===1'b1)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I2===1'b1 && I3===1'b0)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I2===1'b1 && I3===1'b1)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	ifnone
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I3===1'b0)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I3===1'b1)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I3===1'b0)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I3===1'b1)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I3===1'b0)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I3===1'b1)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I3===1'b0)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I3===1'b1)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	ifnone
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b0)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b1)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b0)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b1)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b0)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b1)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b0)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b1)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	ifnone
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b1 && I3===1'b0 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b1 && I3===1'b0 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b0 && I3===1'b0 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b0 && I3===1'b1 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b1 && I3===1'b0 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b1 && I3===1'b0 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b1 && I3===1'b1 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b1 && I3===1'b0 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	ifnone
	// comb arc posedge S0 --> (Z:S0)
	 (posedge S0 => (Z:S0)) = (1.0,1.0);

	ifnone
	// comb arc negedge S0 --> (Z:S0)
	 (negedge S0 => (Z:S0)) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b0 && I3===1'b1 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b0 && I3===1'b0 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b0 && I3===1'b1 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b0 && I3===1'b1 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b1 && I3===1'b0 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b1 && I3===1'b1 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b0 && I3===1'b1 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b0 && I3===1'b1 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b0 && I3===1'b0 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b1 && I3===1'b0 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b0 && I3===1'b0 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b0 && I3===1'b1 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b0 && I3===1'b0 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b0 && I3===1'b0 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b0 && I3===1'b1 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b1 && I3===1'b0 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	ifnone
	// comb arc posedge S1 --> (Z:S1)
	 (posedge S1 => (Z:S1)) = (1.0,1.0);

	ifnone
	// comb arc negedge S1 --> (Z:S1)
	 (negedge S1 => (Z:S1)) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b0 && I3===1'b1 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b1 && I3===1'b0 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b1 && I3===1'b1 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b1 && I3===1'b1 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b1 && I3===1'b0 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b1 && I3===1'b1 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b0 && I3===1'b1 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b1 && I3===1'b1 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__MUX4_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__MUX4_2_V
`define GF180MCU_FD_SC_MCU9T5V0__MUX4_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__mux4_2( I2, S0, I3, Z, S1, I1, I0, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__mux4_2( I2, S0, I3, Z, S1, I1, I0 );
`endif // If not USE_POWER_PINS
input I0, I1, I2, I3, S0, S1;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__mux4_func gf180mcu_fd_sc_mcu9t5v0__mux4_inst(.I2(I2),.S0(S0),.I3(I3),.Z(Z),.S1(S1),.I1(I1),.I0(I0),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__mux4_func gf180mcu_fd_sc_mcu9t5v0__mux4_inst(.I2(I2),.S0(S0),.I3(I3),.Z(Z),.S1(S1),.I1(I1),.I0(I0));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(I1===1'b0 && I2===1'b0 && I3===1'b0)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b0 && I2===1'b0 && I3===1'b1)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b0 && I2===1'b1 && I3===1'b0)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b0 && I2===1'b1 && I3===1'b1)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b1 && I2===1'b0 && I3===1'b0)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b1 && I2===1'b0 && I3===1'b1)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b1 && I2===1'b1 && I3===1'b0)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b1 && I2===1'b1 && I3===1'b1)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	ifnone
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I2===1'b0 && I3===1'b0)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I2===1'b0 && I3===1'b1)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I2===1'b1 && I3===1'b0)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I2===1'b1 && I3===1'b1)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I2===1'b0 && I3===1'b0)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I2===1'b0 && I3===1'b1)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I2===1'b1 && I3===1'b0)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I2===1'b1 && I3===1'b1)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	ifnone
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I3===1'b0)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I3===1'b1)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I3===1'b0)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I3===1'b1)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I3===1'b0)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I3===1'b1)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I3===1'b0)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I3===1'b1)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	ifnone
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b0)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b1)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b0)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b1)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b0)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b1)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b0)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b1)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	ifnone
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b1 && I3===1'b0 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b1 && I3===1'b0 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b0 && I3===1'b0 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b0 && I3===1'b1 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b1 && I3===1'b0 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b1 && I3===1'b0 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b1 && I3===1'b1 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b1 && I3===1'b0 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	ifnone
	// comb arc posedge S0 --> (Z:S0)
	 (posedge S0 => (Z:S0)) = (1.0,1.0);

	ifnone
	// comb arc negedge S0 --> (Z:S0)
	 (negedge S0 => (Z:S0)) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b0 && I3===1'b1 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b0 && I3===1'b0 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b0 && I3===1'b1 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b0 && I3===1'b1 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b1 && I3===1'b0 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b1 && I3===1'b1 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b0 && I3===1'b1 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b0 && I3===1'b1 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b0 && I3===1'b0 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b1 && I3===1'b0 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b0 && I3===1'b0 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b0 && I3===1'b1 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b0 && I3===1'b0 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b0 && I3===1'b0 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b0 && I3===1'b1 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b1 && I3===1'b0 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	ifnone
	// comb arc posedge S1 --> (Z:S1)
	 (posedge S1 => (Z:S1)) = (1.0,1.0);

	ifnone
	// comb arc negedge S1 --> (Z:S1)
	 (negedge S1 => (Z:S1)) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b0 && I3===1'b1 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b1 && I3===1'b0 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b1 && I3===1'b1 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b1 && I3===1'b1 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b1 && I3===1'b0 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b1 && I3===1'b1 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b0 && I3===1'b1 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b1 && I3===1'b1 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__MUX4_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__MUX4_4_V
`define GF180MCU_FD_SC_MCU9T5V0__MUX4_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__mux4_4( I2, S0, I3, Z, S1, I1, I0, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__mux4_4( I2, S0, I3, Z, S1, I1, I0 );
`endif // If not USE_POWER_PINS
input I0, I1, I2, I3, S0, S1;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__mux4_func gf180mcu_fd_sc_mcu9t5v0__mux4_inst(.I2(I2),.S0(S0),.I3(I3),.Z(Z),.S1(S1),.I1(I1),.I0(I0),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__mux4_func gf180mcu_fd_sc_mcu9t5v0__mux4_inst(.I2(I2),.S0(S0),.I3(I3),.Z(Z),.S1(S1),.I1(I1),.I0(I0));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(I1===1'b0 && I2===1'b0 && I3===1'b0)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b0 && I2===1'b0 && I3===1'b1)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b0 && I2===1'b1 && I3===1'b0)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b0 && I2===1'b1 && I3===1'b1)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b1 && I2===1'b0 && I3===1'b0)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b1 && I2===1'b0 && I3===1'b1)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b1 && I2===1'b1 && I3===1'b0)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I1===1'b1 && I2===1'b1 && I3===1'b1)
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	ifnone
	// comb arc I0 --> Z
	 (I0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I2===1'b0 && I3===1'b0)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I2===1'b0 && I3===1'b1)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I2===1'b1 && I3===1'b0)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I2===1'b1 && I3===1'b1)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I2===1'b0 && I3===1'b0)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I2===1'b0 && I3===1'b1)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I2===1'b1 && I3===1'b0)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I2===1'b1 && I3===1'b1)
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	ifnone
	// comb arc I1 --> Z
	 (I1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I3===1'b0)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I3===1'b1)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I3===1'b0)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I3===1'b1)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I3===1'b0)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I3===1'b1)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I3===1'b0)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I3===1'b1)
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	ifnone
	// comb arc I2 --> Z
	 (I2 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b0)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b1)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b0)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b1)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b0)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b1)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b0)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b1)
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	ifnone
	// comb arc I3 --> Z
	 (I3 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b1 && I3===1'b0 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b1 && I3===1'b0 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b0 && I3===1'b0 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b0 && I3===1'b1 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b1 && I3===1'b0 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b1 && I3===1'b0 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b1 && I3===1'b1 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b1 && I3===1'b0 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	ifnone
	// comb arc posedge S0 --> (Z:S0)
	 (posedge S0 => (Z:S0)) = (1.0,1.0);

	ifnone
	// comb arc negedge S0 --> (Z:S0)
	 (negedge S0 => (Z:S0)) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b0 && I3===1'b1 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b0 && I3===1'b0 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b0 && I3===1'b1 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b0 && I3===1'b1 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b1 && I3===1'b0 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b1 && I3===1'b1 && S1===1'b0)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b0 && I3===1'b1 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b0 && I3===1'b1 && S1===1'b1)
	// comb arc S0 --> Z
	 (S0 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b0 && I3===1'b0 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b1 && I3===1'b0 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b0 && I3===1'b0 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b0 && I3===1'b1 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b0 && I3===1'b0 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b0 && I3===1'b0 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b0 && I3===1'b1 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b1 && I2===1'b1 && I3===1'b0 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	ifnone
	// comb arc posedge S1 --> (Z:S1)
	 (posedge S1 => (Z:S1)) = (1.0,1.0);

	ifnone
	// comb arc negedge S1 --> (Z:S1)
	 (negedge S1 => (Z:S1)) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b0 && I3===1'b1 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b1 && I3===1'b0 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b1 && I3===1'b1 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b0 && I2===1'b1 && I3===1'b1 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b1 && I3===1'b0 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b0 && I1===1'b1 && I2===1'b1 && I3===1'b1 && S0===1'b0)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b0 && I3===1'b1 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	if(I0===1'b1 && I1===1'b0 && I2===1'b1 && I3===1'b1 && S0===1'b1)
	// comb arc S1 --> Z
	 (S1 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__MUX4_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__MUX4_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__MUX4_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__mux4_func( I2, S0, I3, Z, S1, I1, I0, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__mux4_func( I2, S0, I3, Z, S1, I1, I0 );
`endif // If not USE_POWER_PINS
input I0, I1, I2, I3, S0, S1;
output Z;

	wire S0_inv_for_gf180mcu_fd_sc_mcu9t5v0__mux4_4;

	not MGM_BG_0( S0_inv_for_gf180mcu_fd_sc_mcu9t5v0__mux4_4, S0 );

	wire S1_inv_for_gf180mcu_fd_sc_mcu9t5v0__mux4_4;

	not MGM_BG_1( S1_inv_for_gf180mcu_fd_sc_mcu9t5v0__mux4_4, S1 );

	wire Z_row1;

	and MGM_BG_2( Z_row1, S0_inv_for_gf180mcu_fd_sc_mcu9t5v0__mux4_4, S1_inv_for_gf180mcu_fd_sc_mcu9t5v0__mux4_4, I0 );

	wire Z_row2;

	and MGM_BG_3( Z_row2, S1_inv_for_gf180mcu_fd_sc_mcu9t5v0__mux4_4, I1, S0 );

	wire Z_row3;

	and MGM_BG_4( Z_row3, S0_inv_for_gf180mcu_fd_sc_mcu9t5v0__mux4_4, I2, S1 );

	wire Z_row4;

	and MGM_BG_5( Z_row4, I3, S0, S1 );

	or MGM_BG_6( Z, Z_row1, Z_row2, Z_row3, Z_row4 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__MUX4_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NAND2_1_V
`define GF180MCU_FD_SC_MCU9T5V0__NAND2_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand2_1( A2, ZN, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand2_1( A2, ZN, A1 );
`endif // If not USE_POWER_PINS
input A1, A2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nand2_func gf180mcu_fd_sc_mcu9t5v0__nand2_inst(.A2(A2),.ZN(ZN),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nand2_func gf180mcu_fd_sc_mcu9t5v0__nand2_inst(.A2(A2),.ZN(ZN),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NAND2_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NAND2_2_V
`define GF180MCU_FD_SC_MCU9T5V0__NAND2_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand2_2( A2, ZN, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand2_2( A2, ZN, A1 );
`endif // If not USE_POWER_PINS
input A1, A2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nand2_func gf180mcu_fd_sc_mcu9t5v0__nand2_inst(.A2(A2),.ZN(ZN),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nand2_func gf180mcu_fd_sc_mcu9t5v0__nand2_inst(.A2(A2),.ZN(ZN),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NAND2_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NAND2_4_V
`define GF180MCU_FD_SC_MCU9T5V0__NAND2_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand2_4( A2, ZN, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand2_4( A2, ZN, A1 );
`endif // If not USE_POWER_PINS
input A1, A2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nand2_func gf180mcu_fd_sc_mcu9t5v0__nand2_inst(.A2(A2),.ZN(ZN),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nand2_func gf180mcu_fd_sc_mcu9t5v0__nand2_inst(.A2(A2),.ZN(ZN),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NAND2_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NAND2_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__NAND2_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand2_func( A2, ZN, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand2_func( A2, ZN, A1 );
`endif // If not USE_POWER_PINS
input A1, A2;
output ZN;

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand2_1;

	not MGM_BG_0( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand2_1, A1 );

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand2_1;

	not MGM_BG_1( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand2_1, A2 );

	or MGM_BG_2( ZN, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand2_1, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand2_1 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NAND2_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NAND3_1_V
`define GF180MCU_FD_SC_MCU9T5V0__NAND3_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand3_1( A3, ZN, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand3_1( A3, ZN, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nand3_func gf180mcu_fd_sc_mcu9t5v0__nand3_inst(.A3(A3),.ZN(ZN),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nand3_func gf180mcu_fd_sc_mcu9t5v0__nand3_inst(.A3(A3),.ZN(ZN),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NAND3_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NAND3_2_V
`define GF180MCU_FD_SC_MCU9T5V0__NAND3_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand3_2( ZN, A3, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand3_2( ZN, A3, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nand3_func gf180mcu_fd_sc_mcu9t5v0__nand3_inst(.ZN(ZN),.A3(A3),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nand3_func gf180mcu_fd_sc_mcu9t5v0__nand3_inst(.ZN(ZN),.A3(A3),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NAND3_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NAND3_4_V
`define GF180MCU_FD_SC_MCU9T5V0__NAND3_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand3_4( A2, A3, ZN, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand3_4( A2, A3, ZN, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nand3_func gf180mcu_fd_sc_mcu9t5v0__nand3_inst(.A2(A2),.A3(A3),.ZN(ZN),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nand3_func gf180mcu_fd_sc_mcu9t5v0__nand3_inst(.A2(A2),.A3(A3),.ZN(ZN),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NAND3_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NAND3_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__NAND3_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand3_func( A2, A3, ZN, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand3_func( A2, A3, ZN, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output ZN;

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand3_4;

	not MGM_BG_0( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand3_4, A1 );

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand3_4;

	not MGM_BG_1( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand3_4, A2 );

	wire A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand3_4;

	not MGM_BG_2( A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand3_4, A3 );

	or MGM_BG_3( ZN, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand3_4, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand3_4, A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand3_4 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NAND3_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NAND4_1_V
`define GF180MCU_FD_SC_MCU9T5V0__NAND4_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand4_1( A4, ZN, A3, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand4_1( A4, ZN, A3, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3, A4;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nand4_func gf180mcu_fd_sc_mcu9t5v0__nand4_inst(.A4(A4),.ZN(ZN),.A3(A3),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nand4_func gf180mcu_fd_sc_mcu9t5v0__nand4_inst(.A4(A4),.ZN(ZN),.A3(A3),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	// comb arc A4 --> ZN
	 (A4 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NAND4_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NAND4_2_V
`define GF180MCU_FD_SC_MCU9T5V0__NAND4_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand4_2( ZN, A4, A3, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand4_2( ZN, A4, A3, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3, A4;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nand4_func gf180mcu_fd_sc_mcu9t5v0__nand4_inst(.ZN(ZN),.A4(A4),.A3(A3),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nand4_func gf180mcu_fd_sc_mcu9t5v0__nand4_inst(.ZN(ZN),.A4(A4),.A3(A3),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	// comb arc A4 --> ZN
	 (A4 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NAND4_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NAND4_4_V
`define GF180MCU_FD_SC_MCU9T5V0__NAND4_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand4_4( A3, ZN, A4, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand4_4( A3, ZN, A4, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3, A4;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nand4_func gf180mcu_fd_sc_mcu9t5v0__nand4_inst(.A3(A3),.ZN(ZN),.A4(A4),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nand4_func gf180mcu_fd_sc_mcu9t5v0__nand4_inst(.A3(A3),.ZN(ZN),.A4(A4),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	// comb arc A4 --> ZN
	 (A4 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NAND4_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NAND4_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__NAND4_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand4_func( A3, ZN, A4, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nand4_func( A3, ZN, A4, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3, A4;
output ZN;

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand4_4;

	not MGM_BG_0( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand4_4, A1 );

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand4_4;

	not MGM_BG_1( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand4_4, A2 );

	wire A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand4_4;

	not MGM_BG_2( A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand4_4, A3 );

	wire A4_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand4_4;

	not MGM_BG_3( A4_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand4_4, A4 );

	or MGM_BG_4( ZN, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand4_4, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand4_4, A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand4_4, A4_inv_for_gf180mcu_fd_sc_mcu9t5v0__nand4_4 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NAND4_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NOR2_1_V
`define GF180MCU_FD_SC_MCU9T5V0__NOR2_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor2_1( A2, ZN, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor2_1( A2, ZN, A1 );
`endif // If not USE_POWER_PINS
input A1, A2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nor2_func gf180mcu_fd_sc_mcu9t5v0__nor2_inst(.A2(A2),.ZN(ZN),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nor2_func gf180mcu_fd_sc_mcu9t5v0__nor2_inst(.A2(A2),.ZN(ZN),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NOR2_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NOR2_2_V
`define GF180MCU_FD_SC_MCU9T5V0__NOR2_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor2_2( A2, ZN, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor2_2( A2, ZN, A1 );
`endif // If not USE_POWER_PINS
input A1, A2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nor2_func gf180mcu_fd_sc_mcu9t5v0__nor2_inst(.A2(A2),.ZN(ZN),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nor2_func gf180mcu_fd_sc_mcu9t5v0__nor2_inst(.A2(A2),.ZN(ZN),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NOR2_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NOR2_4_V
`define GF180MCU_FD_SC_MCU9T5V0__NOR2_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor2_4( ZN, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor2_4( ZN, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nor2_func gf180mcu_fd_sc_mcu9t5v0__nor2_inst(.ZN(ZN),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nor2_func gf180mcu_fd_sc_mcu9t5v0__nor2_inst(.ZN(ZN),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NOR2_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NOR2_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__NOR2_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor2_func( ZN, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor2_func( ZN, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2;
output ZN;

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor2_4;

	not MGM_BG_0( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor2_4, A1 );

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor2_4;

	not MGM_BG_1( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor2_4, A2 );

	and MGM_BG_2( ZN, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor2_4, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor2_4 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NOR2_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NOR3_1_V
`define GF180MCU_FD_SC_MCU9T5V0__NOR3_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor3_1( A3, ZN, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor3_1( A3, ZN, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nor3_func gf180mcu_fd_sc_mcu9t5v0__nor3_inst(.A3(A3),.ZN(ZN),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nor3_func gf180mcu_fd_sc_mcu9t5v0__nor3_inst(.A3(A3),.ZN(ZN),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NOR3_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NOR3_2_V
`define GF180MCU_FD_SC_MCU9T5V0__NOR3_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor3_2( ZN, A3, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor3_2( ZN, A3, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nor3_func gf180mcu_fd_sc_mcu9t5v0__nor3_inst(.ZN(ZN),.A3(A3),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nor3_func gf180mcu_fd_sc_mcu9t5v0__nor3_inst(.ZN(ZN),.A3(A3),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NOR3_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NOR3_4_V
`define GF180MCU_FD_SC_MCU9T5V0__NOR3_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor3_4( A2, ZN, A3, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor3_4( A2, ZN, A3, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nor3_func gf180mcu_fd_sc_mcu9t5v0__nor3_inst(.A2(A2),.ZN(ZN),.A3(A3),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nor3_func gf180mcu_fd_sc_mcu9t5v0__nor3_inst(.A2(A2),.ZN(ZN),.A3(A3),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NOR3_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NOR3_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__NOR3_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor3_func( ZN, A3, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor3_func( ZN, A3, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output ZN;

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor3_2;

	not MGM_BG_0( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor3_2, A1 );

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor3_2;

	not MGM_BG_1( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor3_2, A2 );

	wire A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor3_2;

	not MGM_BG_2( A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor3_2, A3 );

	and MGM_BG_3( ZN, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor3_2, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor3_2, A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor3_2 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NOR3_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NOR4_1_V
`define GF180MCU_FD_SC_MCU9T5V0__NOR4_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor4_1( A4, ZN, A3, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor4_1( A4, ZN, A3, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3, A4;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nor4_func gf180mcu_fd_sc_mcu9t5v0__nor4_inst(.A4(A4),.ZN(ZN),.A3(A3),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nor4_func gf180mcu_fd_sc_mcu9t5v0__nor4_inst(.A4(A4),.ZN(ZN),.A3(A3),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	// comb arc A4 --> ZN
	 (A4 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NOR4_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NOR4_2_V
`define GF180MCU_FD_SC_MCU9T5V0__NOR4_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor4_2( A3, ZN, A4, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor4_2( A3, ZN, A4, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3, A4;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nor4_func gf180mcu_fd_sc_mcu9t5v0__nor4_inst(.A3(A3),.ZN(ZN),.A4(A4),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nor4_func gf180mcu_fd_sc_mcu9t5v0__nor4_inst(.A3(A3),.ZN(ZN),.A4(A4),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	// comb arc A4 --> ZN
	 (A4 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NOR4_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NOR4_4_V
`define GF180MCU_FD_SC_MCU9T5V0__NOR4_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor4_4( A3, ZN, A4, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor4_4( A3, ZN, A4, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3, A4;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nor4_func gf180mcu_fd_sc_mcu9t5v0__nor4_inst(.A3(A3),.ZN(ZN),.A4(A4),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__nor4_func gf180mcu_fd_sc_mcu9t5v0__nor4_inst(.A3(A3),.ZN(ZN),.A4(A4),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	// comb arc A4 --> ZN
	 (A4 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NOR4_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__NOR4_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__NOR4_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor4_func( A4, ZN, A3, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__nor4_func( A4, ZN, A3, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3, A4;
output ZN;

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor4_1;

	not MGM_BG_0( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor4_1, A1 );

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor4_1;

	not MGM_BG_1( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor4_1, A2 );

	wire A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor4_1;

	not MGM_BG_2( A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor4_1, A3 );

	wire A4_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor4_1;

	not MGM_BG_3( A4_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor4_1, A4 );

	and MGM_BG_4( ZN, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor4_1, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor4_1, A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor4_1, A4_inv_for_gf180mcu_fd_sc_mcu9t5v0__nor4_1 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__NOR4_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI21_1_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI21_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai21_1( A2, ZN, A1, B, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai21_1( A2, ZN, A1, B );
`endif // If not USE_POWER_PINS
input A1, A2, B;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai21_func gf180mcu_fd_sc_mcu9t5v0__oai21_inst(.A2(A2),.ZN(ZN),.A1(A1),.B(B),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai21_func gf180mcu_fd_sc_mcu9t5v0__oai21_inst(.A2(A2),.ZN(ZN),.A1(A1),.B(B));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	ifnone
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI21_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI21_2_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI21_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai21_2( B, ZN, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai21_2( B, ZN, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, B;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai21_func gf180mcu_fd_sc_mcu9t5v0__oai21_inst(.B(B),.ZN(ZN),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai21_func gf180mcu_fd_sc_mcu9t5v0__oai21_inst(.B(B),.ZN(ZN),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	ifnone
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI21_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI21_4_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI21_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai21_4( ZN, A2, A1, B, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai21_4( ZN, A2, A1, B );
`endif // If not USE_POWER_PINS
input A1, A2, B;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai21_func gf180mcu_fd_sc_mcu9t5v0__oai21_inst(.ZN(ZN),.A2(A2),.A1(A1),.B(B),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai21_func gf180mcu_fd_sc_mcu9t5v0__oai21_inst(.ZN(ZN),.A2(A2),.A1(A1),.B(B));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	ifnone
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI21_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI21_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI21_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai21_func( B, ZN, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai21_func( B, ZN, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, B;
output ZN;

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai21_2;

	not MGM_BG_0( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai21_2, A1 );

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai21_2;

	not MGM_BG_1( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai21_2, A2 );

	wire ZN_row1;

	and MGM_BG_2( ZN_row1, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai21_2, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai21_2 );

	wire B_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai21_2;

	not MGM_BG_3( B_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai21_2, B );

	or MGM_BG_4( ZN, ZN_row1, B_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai21_2 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI21_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI22_1_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI22_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai22_1( B2, B1, ZN, A1, A2, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai22_1( B2, B1, ZN, A1, A2 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai22_func gf180mcu_fd_sc_mcu9t5v0__oai22_inst(.B2(B2),.B1(B1),.ZN(ZN),.A1(A1),.A2(A2),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai22_func gf180mcu_fd_sc_mcu9t5v0__oai22_inst(.B2(B2),.B1(B1),.ZN(ZN),.A1(A1),.A2(A2));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI22_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI22_2_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI22_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai22_2( B2, B1, ZN, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai22_2( B2, B1, ZN, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai22_func gf180mcu_fd_sc_mcu9t5v0__oai22_inst(.B2(B2),.B1(B1),.ZN(ZN),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai22_func gf180mcu_fd_sc_mcu9t5v0__oai22_inst(.B2(B2),.B1(B1),.ZN(ZN),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI22_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI22_4_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI22_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai22_4( B2, ZN, B1, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai22_4( B2, ZN, B1, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai22_func gf180mcu_fd_sc_mcu9t5v0__oai22_inst(.B2(B2),.ZN(ZN),.B1(B1),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai22_func gf180mcu_fd_sc_mcu9t5v0__oai22_inst(.B2(B2),.ZN(ZN),.B1(B1),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI22_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI22_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI22_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai22_func( B2, B1, ZN, A1, A2, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai22_func( B2, B1, ZN, A1, A2 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2;
output ZN;

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai22_1;

	not MGM_BG_0( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai22_1, A1 );

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai22_1;

	not MGM_BG_1( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai22_1, A2 );

	wire ZN_row1;

	and MGM_BG_2( ZN_row1, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai22_1, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai22_1 );

	wire B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai22_1;

	not MGM_BG_3( B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai22_1, B1 );

	wire B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai22_1;

	not MGM_BG_4( B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai22_1, B2 );

	wire ZN_row2;

	and MGM_BG_5( ZN_row2, B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai22_1, B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai22_1 );

	or MGM_BG_6( ZN, ZN_row1, ZN_row2 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI22_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI31_1_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI31_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai31_1( B, ZN, A1, A2, A3, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai31_1( B, ZN, A1, A2, A3 );
`endif // If not USE_POWER_PINS
input A1, A2, A3, B;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai31_func gf180mcu_fd_sc_mcu9t5v0__oai31_inst(.B(B),.ZN(ZN),.A1(A1),.A2(A2),.A3(A3),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai31_func gf180mcu_fd_sc_mcu9t5v0__oai31_inst(.B(B),.ZN(ZN),.A1(A1),.A2(A2),.A3(A3));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && A3===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	ifnone
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI31_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI31_2_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI31_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai31_2( B, ZN, A3, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai31_2( B, ZN, A3, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3, B;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai31_func gf180mcu_fd_sc_mcu9t5v0__oai31_inst(.B(B),.ZN(ZN),.A3(A3),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai31_func gf180mcu_fd_sc_mcu9t5v0__oai31_inst(.B(B),.ZN(ZN),.A3(A3),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && A3===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	ifnone
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI31_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI31_4_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI31_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai31_4( A3, ZN, A2, A1, B, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai31_4( A3, ZN, A2, A1, B );
`endif // If not USE_POWER_PINS
input A1, A2, A3, B;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai31_func gf180mcu_fd_sc_mcu9t5v0__oai31_inst(.A3(A3),.ZN(ZN),.A2(A2),.A1(A1),.B(B),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai31_func gf180mcu_fd_sc_mcu9t5v0__oai31_inst(.A3(A3),.ZN(ZN),.A2(A2),.A1(A1),.B(B));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && A3===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	ifnone
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI31_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI31_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI31_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai31_func( B, ZN, A3, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai31_func( B, ZN, A3, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3, B;
output ZN;

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai31_2;

	not MGM_BG_0( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai31_2, A1 );

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai31_2;

	not MGM_BG_1( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai31_2, A2 );

	wire A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai31_2;

	not MGM_BG_2( A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai31_2, A3 );

	wire ZN_row1;

	and MGM_BG_3( ZN_row1, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai31_2, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai31_2, A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai31_2 );

	wire B_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai31_2;

	not MGM_BG_4( B_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai31_2, B );

	or MGM_BG_5( ZN, ZN_row1, B_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai31_2 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI31_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI32_1_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI32_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai32_1( A3, A2, A1, ZN, B1, B2, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai32_1( A3, A2, A1, ZN, B1, B2 );
`endif // If not USE_POWER_PINS
input A1, A2, A3, B1, B2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai32_func gf180mcu_fd_sc_mcu9t5v0__oai32_inst(.A3(A3),.A2(A2),.A1(A1),.ZN(ZN),.B1(B1),.B2(B2),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai32_func gf180mcu_fd_sc_mcu9t5v0__oai32_inst(.A3(A3),.A2(A2),.A1(A1),.ZN(ZN),.B1(B1),.B2(B2));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI32_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI32_2_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI32_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai32_2( A3, A2, A1, ZN, B2, B1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai32_2( A3, A2, A1, ZN, B2, B1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3, B1, B2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai32_func gf180mcu_fd_sc_mcu9t5v0__oai32_inst(.A3(A3),.A2(A2),.A1(A1),.ZN(ZN),.B2(B2),.B1(B1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai32_func gf180mcu_fd_sc_mcu9t5v0__oai32_inst(.A3(A3),.A2(A2),.A1(A1),.ZN(ZN),.B2(B2),.B1(B1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI32_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI32_4_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI32_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai32_4( A2, A3, A1, ZN, B2, B1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai32_4( A2, A3, A1, ZN, B2, B1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3, B1, B2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai32_func gf180mcu_fd_sc_mcu9t5v0__oai32_inst(.A2(A2),.A3(A3),.A1(A1),.ZN(ZN),.B2(B2),.B1(B1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai32_func gf180mcu_fd_sc_mcu9t5v0__oai32_inst(.A2(A2),.A3(A3),.A1(A1),.ZN(ZN),.B2(B2),.B1(B1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI32_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI32_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI32_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai32_func( A3, A2, A1, ZN, B2, B1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai32_func( A3, A2, A1, ZN, B2, B1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3, B1, B2;
output ZN;

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai32_2;

	not MGM_BG_0( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai32_2, A1 );

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai32_2;

	not MGM_BG_1( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai32_2, A2 );

	wire A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai32_2;

	not MGM_BG_2( A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai32_2, A3 );

	wire ZN_row1;

	and MGM_BG_3( ZN_row1, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai32_2, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai32_2, A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai32_2 );

	wire B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai32_2;

	not MGM_BG_4( B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai32_2, B1 );

	wire B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai32_2;

	not MGM_BG_5( B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai32_2, B2 );

	wire ZN_row2;

	and MGM_BG_6( ZN_row2, B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai32_2, B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai32_2 );

	or MGM_BG_7( ZN, ZN_row1, ZN_row2 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI32_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI33_1_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI33_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai33_1( B3, B2, B1, ZN, A1, A2, A3, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai33_1( B3, B2, B1, ZN, A1, A2, A3 );
`endif // If not USE_POWER_PINS
input A1, A2, A3, B1, B2, B3;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai33_func gf180mcu_fd_sc_mcu9t5v0__oai33_inst(.B3(B3),.B2(B2),.B1(B1),.ZN(ZN),.A1(A1),.A2(A2),.A3(A3),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai33_func gf180mcu_fd_sc_mcu9t5v0__oai33_inst(.B3(B3),.B2(B2),.B1(B1),.ZN(ZN),.A1(A1),.A2(A2),.A3(A3));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b0 && B3===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && B3===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && B3===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && B3===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && B3===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && B3===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && B3===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0 && B3===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && B3===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && B3===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && B3===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && B3===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && B3===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && B3===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0 && B3===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && B3===1'b0)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && B3===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && B3===1'b0)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && B3===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && B3===1'b0)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && B3===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && A3===1'b1)
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b0)
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b1)
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b0)
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b1)
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b0)
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b1)
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI33_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI33_2_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI33_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai33_2( B3, B2, B1, ZN, A3, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai33_2( B3, B2, B1, ZN, A3, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3, B1, B2, B3;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai33_func gf180mcu_fd_sc_mcu9t5v0__oai33_inst(.B3(B3),.B2(B2),.B1(B1),.ZN(ZN),.A3(A3),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai33_func gf180mcu_fd_sc_mcu9t5v0__oai33_inst(.B3(B3),.B2(B2),.B1(B1),.ZN(ZN),.A3(A3),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b0 && B3===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && B3===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && B3===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && B3===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && B3===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && B3===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && B3===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0 && B3===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && B3===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && B3===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && B3===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && B3===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && B3===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && B3===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0 && B3===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && B3===1'b0)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && B3===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && B3===1'b0)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && B3===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && B3===1'b0)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && B3===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && A3===1'b1)
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b0)
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b1)
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b0)
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b1)
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b0)
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b1)
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI33_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI33_4_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI33_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai33_4( B2, B3, B1, ZN, A1, A2, A3, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai33_4( B2, B3, B1, ZN, A1, A2, A3 );
`endif // If not USE_POWER_PINS
input A1, A2, A3, B1, B2, B3;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai33_func gf180mcu_fd_sc_mcu9t5v0__oai33_inst(.B2(B2),.B3(B3),.B1(B1),.ZN(ZN),.A1(A1),.A2(A2),.A3(A3),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai33_func gf180mcu_fd_sc_mcu9t5v0__oai33_inst(.B2(B2),.B3(B3),.B1(B1),.ZN(ZN),.A1(A1),.A2(A2),.A3(A3));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b0 && B3===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && B3===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && B3===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && B3===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && B3===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && B3===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && B3===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0 && B3===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && B3===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && B3===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && B3===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && B3===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && B3===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && B3===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b0 && B3===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && B3===1'b0)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && B3===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && B3===1'b0)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && B3===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && B3===1'b0)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && B3===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0 && A3===1'b1)
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b0)
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && A3===1'b1)
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b0)
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && A3===1'b1)
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b0)
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && A3===1'b1)
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B3 --> ZN
	 (B3 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI33_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI33_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI33_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai33_func( B3, B2, B1, ZN, A3, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai33_func( B3, B2, B1, ZN, A3, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, A3, B1, B2, B3;
output ZN;

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai33_2;

	not MGM_BG_0( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai33_2, A1 );

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai33_2;

	not MGM_BG_1( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai33_2, A2 );

	wire A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai33_2;

	not MGM_BG_2( A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai33_2, A3 );

	wire ZN_row1;

	and MGM_BG_3( ZN_row1, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai33_2, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai33_2, A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai33_2 );

	wire B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai33_2;

	not MGM_BG_4( B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai33_2, B1 );

	wire B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai33_2;

	not MGM_BG_5( B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai33_2, B2 );

	wire B3_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai33_2;

	not MGM_BG_6( B3_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai33_2, B3 );

	wire ZN_row2;

	and MGM_BG_7( ZN_row2, B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai33_2, B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai33_2, B3_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai33_2 );

	or MGM_BG_8( ZN, ZN_row1, ZN_row2 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI33_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI211_1_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI211_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai211_1( A2, ZN, A1, B, C, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai211_1( A2, ZN, A1, B, C );
`endif // If not USE_POWER_PINS
input A1, A2, B, C;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai211_func gf180mcu_fd_sc_mcu9t5v0__oai211_inst(.A2(A2),.ZN(ZN),.A1(A1),.B(B),.C(C),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai211_func gf180mcu_fd_sc_mcu9t5v0__oai211_inst(.A2(A2),.ZN(ZN),.A1(A1),.B(B),.C(C));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	ifnone
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	ifnone
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI211_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI211_2_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI211_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai211_2( ZN, A2, A1, B, C, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai211_2( ZN, A2, A1, B, C );
`endif // If not USE_POWER_PINS
input A1, A2, B, C;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai211_func gf180mcu_fd_sc_mcu9t5v0__oai211_inst(.ZN(ZN),.A2(A2),.A1(A1),.B(B),.C(C),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai211_func gf180mcu_fd_sc_mcu9t5v0__oai211_inst(.ZN(ZN),.A2(A2),.A1(A1),.B(B),.C(C));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	ifnone
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	ifnone
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI211_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI211_4_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI211_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai211_4( ZN, A2, A1, B, C, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai211_4( ZN, A2, A1, B, C );
`endif // If not USE_POWER_PINS
input A1, A2, B, C;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai211_func gf180mcu_fd_sc_mcu9t5v0__oai211_inst(.ZN(ZN),.A2(A2),.A1(A1),.B(B),.C(C),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai211_func gf180mcu_fd_sc_mcu9t5v0__oai211_inst(.ZN(ZN),.A2(A2),.A1(A1),.B(B),.C(C));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	ifnone
	// comb arc B --> ZN
	 (B => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	ifnone
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI211_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI211_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI211_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai211_func( A2, ZN, A1, B, C, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai211_func( A2, ZN, A1, B, C );
`endif // If not USE_POWER_PINS
input A1, A2, B, C;
output ZN;

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai211_1;

	not MGM_BG_0( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai211_1, A1 );

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai211_1;

	not MGM_BG_1( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai211_1, A2 );

	wire ZN_row1;

	and MGM_BG_2( ZN_row1, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai211_1, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai211_1 );

	wire B_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai211_1;

	not MGM_BG_3( B_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai211_1, B );

	wire C_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai211_1;

	not MGM_BG_4( C_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai211_1, C );

	or MGM_BG_5( ZN, ZN_row1, B_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai211_1, C_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai211_1 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI211_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI221_1_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI221_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai221_1( B2, B1, ZN, C, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai221_1( B2, B1, ZN, C, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2, C;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai221_func gf180mcu_fd_sc_mcu9t5v0__oai221_inst(.B2(B2),.B1(B1),.ZN(ZN),.C(C),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai221_func gf180mcu_fd_sc_mcu9t5v0__oai221_inst(.B2(B2),.B1(B1),.ZN(ZN),.C(C),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b1 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	ifnone
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI221_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI221_2_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI221_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai221_2( ZN, C, B2, B1, A1, A2, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai221_2( ZN, C, B2, B1, A1, A2 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2, C;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai221_func gf180mcu_fd_sc_mcu9t5v0__oai221_inst(.ZN(ZN),.C(C),.B2(B2),.B1(B1),.A1(A1),.A2(A2),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai221_func gf180mcu_fd_sc_mcu9t5v0__oai221_inst(.ZN(ZN),.C(C),.B2(B2),.B1(B1),.A1(A1),.A2(A2));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b1 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	ifnone
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI221_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI221_4_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI221_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai221_4( ZN, B1, B2, C, A1, A2, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai221_4( ZN, B1, B2, C, A1, A2 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2, C;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai221_func gf180mcu_fd_sc_mcu9t5v0__oai221_inst(.ZN(ZN),.B1(B1),.B2(B2),.C(C),.A1(A1),.A2(A2),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai221_func gf180mcu_fd_sc_mcu9t5v0__oai221_inst(.ZN(ZN),.B1(B1),.B2(B2),.C(C),.A1(A1),.A2(A2));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b1 && B2===1'b1)
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	ifnone
	// comb arc C --> ZN
	 (C => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI221_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI221_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI221_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai221_func( ZN, B1, B2, C, A1, A2, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai221_func( ZN, B1, B2, C, A1, A2 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2, C;
output ZN;

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai221_4;

	not MGM_BG_0( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai221_4, A1 );

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai221_4;

	not MGM_BG_1( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai221_4, A2 );

	wire ZN_row1;

	and MGM_BG_2( ZN_row1, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai221_4, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai221_4 );

	wire B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai221_4;

	not MGM_BG_3( B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai221_4, B1 );

	wire B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai221_4;

	not MGM_BG_4( B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai221_4, B2 );

	wire ZN_row2;

	and MGM_BG_5( ZN_row2, B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai221_4, B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai221_4 );

	wire C_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai221_4;

	not MGM_BG_6( C_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai221_4, C );

	or MGM_BG_7( ZN, ZN_row1, ZN_row2, C_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai221_4 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI221_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI222_1_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI222_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai222_1( C2, C1, ZN, B1, B2, A2, A1, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai222_1( C2, C1, ZN, B1, B2, A2, A1 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2, C1, C2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai222_func gf180mcu_fd_sc_mcu9t5v0__oai222_inst(.C2(C2),.C1(C1),.ZN(ZN),.B1(B1),.B2(B2),.A2(A2),.A1(A1),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai222_func gf180mcu_fd_sc_mcu9t5v0__oai222_inst(.C2(C2),.C1(C1),.ZN(ZN),.B1(B1),.B2(B2),.A2(A2),.A1(A1));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b1 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b1 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b1 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b1 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b1 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b1 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI222_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI222_2_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI222_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai222_2( ZN, C1, C2, B1, B2, A1, A2, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai222_2( ZN, C1, C2, B1, B2, A1, A2 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2, C1, C2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai222_func gf180mcu_fd_sc_mcu9t5v0__oai222_inst(.ZN(ZN),.C1(C1),.C2(C2),.B1(B1),.B2(B2),.A1(A1),.A2(A2),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai222_func gf180mcu_fd_sc_mcu9t5v0__oai222_inst(.ZN(ZN),.C1(C1),.C2(C2),.B1(B1),.B2(B2),.A1(A1),.A2(A2));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b1 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b1 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b1 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b1 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b1 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b1 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI222_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI222_4_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI222_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai222_4( ZN, C1, C2, B1, B2, A1, A2, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai222_4( ZN, C1, C2, B1, B2, A1, A2 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2, C1, C2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai222_func gf180mcu_fd_sc_mcu9t5v0__oai222_inst(.ZN(ZN),.C1(C1),.C2(C2),.B1(B1),.B2(B2),.A1(A1),.A2(A2),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__oai222_func gf180mcu_fd_sc_mcu9t5v0__oai222_inst(.ZN(ZN),.C1(C1),.C2(C2),.B1(B1),.B2(B2),.A1(A1),.A2(A2));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(B1===1'b0 && B2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b1 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b0 && B2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b0 && C1===1'b1 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(B1===1'b1 && B2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b1 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B1 --> ZN
	 (B1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b0 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b1 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && C1===1'b1 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && C1===1'b0 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && C1===1'b1 && C2===1'b0)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && C1===1'b1 && C2===1'b1)
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc B2 --> ZN
	 (B2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b1 && B2===1'b1)
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc C1 --> ZN
	 (C1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1 && B1===1'b1 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b0 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0 && B1===1'b1 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b0 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b1 && B2===1'b0)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1 && B1===1'b1 && B2===1'b1)
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc C2 --> ZN
	 (C2 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI222_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OAI222_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__OAI222_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai222_func( ZN, C1, C2, B1, B2, A1, A2, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__oai222_func( ZN, C1, C2, B1, B2, A1, A2 );
`endif // If not USE_POWER_PINS
input A1, A2, B1, B2, C1, C2;
output ZN;

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai222_2;

	not MGM_BG_0( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai222_2, A1 );

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai222_2;

	not MGM_BG_1( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai222_2, A2 );

	wire ZN_row1;

	and MGM_BG_2( ZN_row1, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai222_2, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai222_2 );

	wire B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai222_2;

	not MGM_BG_3( B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai222_2, B1 );

	wire B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai222_2;

	not MGM_BG_4( B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai222_2, B2 );

	wire ZN_row2;

	and MGM_BG_5( ZN_row2, B1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai222_2, B2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai222_2 );

	wire C1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai222_2;

	not MGM_BG_6( C1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai222_2, C1 );

	wire C2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai222_2;

	not MGM_BG_7( C2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai222_2, C2 );

	wire ZN_row3;

	and MGM_BG_8( ZN_row3, C1_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai222_2, C2_inv_for_gf180mcu_fd_sc_mcu9t5v0__oai222_2 );

	or MGM_BG_9( ZN, ZN_row1, ZN_row2, ZN_row3 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OAI222_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OR2_1_V
`define GF180MCU_FD_SC_MCU9T5V0__OR2_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or2_1( A1, A2, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or2_1( A1, A2, Z );
`endif // If not USE_POWER_PINS
input A1, A2;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__or2_func gf180mcu_fd_sc_mcu9t5v0__or2_inst(.A1(A1),.A2(A2),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__or2_func gf180mcu_fd_sc_mcu9t5v0__or2_inst(.A1(A1),.A2(A2),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OR2_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OR2_2_V
`define GF180MCU_FD_SC_MCU9T5V0__OR2_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or2_2( A1, A2, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or2_2( A1, A2, Z );
`endif // If not USE_POWER_PINS
input A1, A2;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__or2_func gf180mcu_fd_sc_mcu9t5v0__or2_inst(.A1(A1),.A2(A2),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__or2_func gf180mcu_fd_sc_mcu9t5v0__or2_inst(.A1(A1),.A2(A2),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OR2_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OR2_4_V
`define GF180MCU_FD_SC_MCU9T5V0__OR2_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or2_4( A2, A1, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or2_4( A2, A1, Z );
`endif // If not USE_POWER_PINS
input A1, A2;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__or2_func gf180mcu_fd_sc_mcu9t5v0__or2_inst(.A2(A2),.A1(A1),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__or2_func gf180mcu_fd_sc_mcu9t5v0__or2_inst(.A2(A2),.A1(A1),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OR2_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OR2_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__OR2_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or2_func( A1, A2, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or2_func( A1, A2, Z );
`endif // If not USE_POWER_PINS
input A1, A2;
output Z;

	or MGM_BG_0( Z, A1, A2 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OR2_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OR3_1_V
`define GF180MCU_FD_SC_MCU9T5V0__OR3_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or3_1( A1, A2, A3, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or3_1( A1, A2, A3, Z );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__or3_func gf180mcu_fd_sc_mcu9t5v0__or3_inst(.A1(A1),.A2(A2),.A3(A3),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__or3_func gf180mcu_fd_sc_mcu9t5v0__or3_inst(.A1(A1),.A2(A2),.A3(A3),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OR3_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OR3_2_V
`define GF180MCU_FD_SC_MCU9T5V0__OR3_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or3_2( A1, A2, A3, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or3_2( A1, A2, A3, Z );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__or3_func gf180mcu_fd_sc_mcu9t5v0__or3_inst(.A1(A1),.A2(A2),.A3(A3),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__or3_func gf180mcu_fd_sc_mcu9t5v0__or3_inst(.A1(A1),.A2(A2),.A3(A3),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OR3_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OR3_4_V
`define GF180MCU_FD_SC_MCU9T5V0__OR3_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or3_4( A3, A2, A1, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or3_4( A3, A2, A1, Z );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__or3_func gf180mcu_fd_sc_mcu9t5v0__or3_inst(.A3(A3),.A2(A2),.A1(A1),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__or3_func gf180mcu_fd_sc_mcu9t5v0__or3_inst(.A3(A3),.A2(A2),.A1(A1),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OR3_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OR3_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__OR3_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or3_func( A1, A2, A3, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or3_func( A1, A2, A3, Z );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output Z;

	or MGM_BG_0( Z, A1, A2, A3 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OR3_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OR4_1_V
`define GF180MCU_FD_SC_MCU9T5V0__OR4_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or4_1( A1, A2, A3, A4, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or4_1( A1, A2, A3, A4, Z );
`endif // If not USE_POWER_PINS
input A1, A2, A3, A4;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__or4_func gf180mcu_fd_sc_mcu9t5v0__or4_inst(.A1(A1),.A2(A2),.A3(A3),.A4(A4),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__or4_func gf180mcu_fd_sc_mcu9t5v0__or4_inst(.A1(A1),.A2(A2),.A3(A3),.A4(A4),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	// comb arc A4 --> Z
	 (A4 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OR4_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OR4_2_V
`define GF180MCU_FD_SC_MCU9T5V0__OR4_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or4_2( A1, A2, A3, A4, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or4_2( A1, A2, A3, A4, Z );
`endif // If not USE_POWER_PINS
input A1, A2, A3, A4;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__or4_func gf180mcu_fd_sc_mcu9t5v0__or4_inst(.A1(A1),.A2(A2),.A3(A3),.A4(A4),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__or4_func gf180mcu_fd_sc_mcu9t5v0__or4_inst(.A1(A1),.A2(A2),.A3(A3),.A4(A4),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	// comb arc A4 --> Z
	 (A4 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OR4_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OR4_4_V
`define GF180MCU_FD_SC_MCU9T5V0__OR4_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or4_4( A4, A3, A2, A1, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or4_4( A4, A3, A2, A1, Z );
`endif // If not USE_POWER_PINS
input A1, A2, A3, A4;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__or4_func gf180mcu_fd_sc_mcu9t5v0__or4_inst(.A4(A4),.A3(A3),.A2(A2),.A1(A1),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__or4_func gf180mcu_fd_sc_mcu9t5v0__or4_inst(.A4(A4),.A3(A3),.A2(A2),.A1(A1),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	// comb arc A4 --> Z
	 (A4 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OR4_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__OR4_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__OR4_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or4_func( A1, A2, A3, A4, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__or4_func( A1, A2, A3, A4, Z );
`endif // If not USE_POWER_PINS
input A1, A2, A3, A4;
output Z;

	or MGM_BG_0( Z, A1, A2, A3, A4 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__OR4_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__SDFFQ_1_V
`define GF180MCU_FD_SC_MCU9T5V0__SDFFQ_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffq_1( SE, SI, D, CLK, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffq_1( SE, SI, D, CLK, Q );
`endif // If not USE_POWER_PINS
input CLK, D, SE, SI;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffq_func gf180mcu_fd_sc_mcu9t5v0__sdffq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffq_func gf180mcu_fd_sc_mcu9t5v0__sdffq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	not MGM_G1(MGM_W1,SE);


	and MGM_G2(MGM_W2,MGM_W1,MGM_W0);


	not MGM_G3(MGM_W3,SI);


	and MGM_G4(ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W3,MGM_W2);


	not MGM_G5(MGM_W4,D);


	not MGM_G6(MGM_W5,SE);


	and MGM_G7(MGM_W6,MGM_W5,MGM_W4);


	and MGM_G8(ENABLE_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W6);


	not MGM_G9(MGM_W7,D);


	and MGM_G10(MGM_W8,SE,MGM_W7);


	not MGM_G11(MGM_W9,SI);


	and MGM_G12(ENABLE_NOT_D_AND_SE_AND_NOT_SI,MGM_W9,MGM_W8);


	not MGM_G13(MGM_W10,D);


	and MGM_G14(MGM_W11,SE,MGM_W10);


	and MGM_G15(ENABLE_NOT_D_AND_SE_AND_SI,SI,MGM_W11);


	not MGM_G16(MGM_W12,SE);


	and MGM_G17(MGM_W13,MGM_W12,D);


	not MGM_G18(MGM_W14,SI);


	and MGM_G19(ENABLE_D_AND_NOT_SE_AND_NOT_SI,MGM_W14,MGM_W13);


	not MGM_G20(MGM_W15,SE);


	and MGM_G21(MGM_W16,MGM_W15,D);


	and MGM_G22(ENABLE_D_AND_NOT_SE_AND_SI,SI,MGM_W16);


	and MGM_G23(MGM_W17,SE,D);


	not MGM_G24(MGM_W18,SI);


	and MGM_G25(ENABLE_D_AND_SE_AND_NOT_SI,MGM_W18,MGM_W17);


	and MGM_G26(MGM_W19,SE,D);


	and MGM_G27(ENABLE_D_AND_SE_AND_SI,SI,MGM_W19);


	not MGM_G28(MGM_W20,SE);


	not MGM_G29(MGM_W21,SI);


	and MGM_G30(ENABLE_NOT_SE_AND_NOT_SI,MGM_W21,MGM_W20);


	not MGM_G31(MGM_W22,SE);


	and MGM_G32(ENABLE_NOT_SE_AND_SI,SI,MGM_W22);


	not MGM_G33(MGM_W23,D);


	and MGM_G34(ENABLE_NOT_D_AND_SI,SI,MGM_W23);


	not MGM_G35(MGM_W24,SI);


	and MGM_G36(ENABLE_D_AND_NOT_SI,MGM_W24,D);


	not MGM_G37(MGM_W25,D);


	and MGM_G38(ENABLE_NOT_D_AND_SE,SE,MGM_W25);


	and MGM_G39(ENABLE_D_AND_SE,SE,D);


	// spec_gates_end



   specify

	// specify_block_begin

	if(D===1'b0 && SI===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SE))  = (1.0,1.0);

	if(SE===1'b0 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b0 && SI===1'b1 || D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SI))  = (1.0,1.0);

	ifnone
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),
		negedge D &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),
		posedge D &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_SI === 1'b1),
		negedge D &&& (ENABLE_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_SI === 1'b1),
		posedge D &&& (ENABLE_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SI === 1'b1),
		negedge SE &&& (ENABLE_NOT_D_AND_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SI === 1'b1),
		posedge SE &&& (ENABLE_NOT_D_AND_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_NOT_D_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_NOT_D_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SI === 1'b1),1.0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_NOT_SI === 1'b1),
		negedge SE &&& (ENABLE_D_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_NOT_SI === 1'b1),
		posedge SE &&& (ENABLE_D_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_D_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_D_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SE === 1'b1),
		negedge SI &&& (ENABLE_NOT_D_AND_SE === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SE === 1'b1),
		posedge SI &&& (ENABLE_NOT_D_AND_SE === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_NOT_D_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_NOT_D_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE === 1'b1),1.0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_SE === 1'b1),
		negedge SI &&& (ENABLE_D_AND_SE === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_SE === 1'b1),
		posedge SI &&& (ENABLE_D_AND_SE === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_D_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_D_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE === 1'b1),1.0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__SDFFQ_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__SDFFQ_2_V
`define GF180MCU_FD_SC_MCU9T5V0__SDFFQ_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffq_2( SE, SI, D, CLK, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffq_2( SE, SI, D, CLK, Q );
`endif // If not USE_POWER_PINS
input CLK, D, SE, SI;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffq_func gf180mcu_fd_sc_mcu9t5v0__sdffq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffq_func gf180mcu_fd_sc_mcu9t5v0__sdffq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	not MGM_G1(MGM_W1,SE);


	and MGM_G2(MGM_W2,MGM_W1,MGM_W0);


	not MGM_G3(MGM_W3,SI);


	and MGM_G4(ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W3,MGM_W2);


	not MGM_G5(MGM_W4,D);


	not MGM_G6(MGM_W5,SE);


	and MGM_G7(MGM_W6,MGM_W5,MGM_W4);


	and MGM_G8(ENABLE_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W6);


	not MGM_G9(MGM_W7,D);


	and MGM_G10(MGM_W8,SE,MGM_W7);


	not MGM_G11(MGM_W9,SI);


	and MGM_G12(ENABLE_NOT_D_AND_SE_AND_NOT_SI,MGM_W9,MGM_W8);


	not MGM_G13(MGM_W10,D);


	and MGM_G14(MGM_W11,SE,MGM_W10);


	and MGM_G15(ENABLE_NOT_D_AND_SE_AND_SI,SI,MGM_W11);


	not MGM_G16(MGM_W12,SE);


	and MGM_G17(MGM_W13,MGM_W12,D);


	not MGM_G18(MGM_W14,SI);


	and MGM_G19(ENABLE_D_AND_NOT_SE_AND_NOT_SI,MGM_W14,MGM_W13);


	not MGM_G20(MGM_W15,SE);


	and MGM_G21(MGM_W16,MGM_W15,D);


	and MGM_G22(ENABLE_D_AND_NOT_SE_AND_SI,SI,MGM_W16);


	and MGM_G23(MGM_W17,SE,D);


	not MGM_G24(MGM_W18,SI);


	and MGM_G25(ENABLE_D_AND_SE_AND_NOT_SI,MGM_W18,MGM_W17);


	and MGM_G26(MGM_W19,SE,D);


	and MGM_G27(ENABLE_D_AND_SE_AND_SI,SI,MGM_W19);


	not MGM_G28(MGM_W20,SE);


	not MGM_G29(MGM_W21,SI);


	and MGM_G30(ENABLE_NOT_SE_AND_NOT_SI,MGM_W21,MGM_W20);


	not MGM_G31(MGM_W22,SE);


	and MGM_G32(ENABLE_NOT_SE_AND_SI,SI,MGM_W22);


	not MGM_G33(MGM_W23,D);


	and MGM_G34(ENABLE_NOT_D_AND_SI,SI,MGM_W23);


	not MGM_G35(MGM_W24,SI);


	and MGM_G36(ENABLE_D_AND_NOT_SI,MGM_W24,D);


	not MGM_G37(MGM_W25,D);


	and MGM_G38(ENABLE_NOT_D_AND_SE,SE,MGM_W25);


	and MGM_G39(ENABLE_D_AND_SE,SE,D);


	// spec_gates_end



   specify

	// specify_block_begin

	if(D===1'b0 && SI===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SE))  = (1.0,1.0);

	if(SE===1'b0 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b0 && SI===1'b1 || D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SI))  = (1.0,1.0);

	ifnone
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),
		negedge D &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),
		posedge D &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_SI === 1'b1),
		negedge D &&& (ENABLE_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_SI === 1'b1),
		posedge D &&& (ENABLE_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SI === 1'b1),
		negedge SE &&& (ENABLE_NOT_D_AND_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SI === 1'b1),
		posedge SE &&& (ENABLE_NOT_D_AND_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_NOT_D_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_NOT_D_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SI === 1'b1),1.0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_NOT_SI === 1'b1),
		negedge SE &&& (ENABLE_D_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_NOT_SI === 1'b1),
		posedge SE &&& (ENABLE_D_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_D_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_D_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SE === 1'b1),
		negedge SI &&& (ENABLE_NOT_D_AND_SE === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SE === 1'b1),
		posedge SI &&& (ENABLE_NOT_D_AND_SE === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_NOT_D_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_NOT_D_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE === 1'b1),1.0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_SE === 1'b1),
		negedge SI &&& (ENABLE_D_AND_SE === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_SE === 1'b1),
		posedge SI &&& (ENABLE_D_AND_SE === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_D_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_D_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE === 1'b1),1.0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__SDFFQ_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__SDFFQ_4_V
`define GF180MCU_FD_SC_MCU9T5V0__SDFFQ_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffq_4( SE, SI, D, CLK, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffq_4( SE, SI, D, CLK, Q );
`endif // If not USE_POWER_PINS
input CLK, D, SE, SI;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffq_func gf180mcu_fd_sc_mcu9t5v0__sdffq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffq_func gf180mcu_fd_sc_mcu9t5v0__sdffq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	not MGM_G1(MGM_W1,SE);


	and MGM_G2(MGM_W2,MGM_W1,MGM_W0);


	not MGM_G3(MGM_W3,SI);


	and MGM_G4(ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W3,MGM_W2);


	not MGM_G5(MGM_W4,D);


	not MGM_G6(MGM_W5,SE);


	and MGM_G7(MGM_W6,MGM_W5,MGM_W4);


	and MGM_G8(ENABLE_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W6);


	not MGM_G9(MGM_W7,D);


	and MGM_G10(MGM_W8,SE,MGM_W7);


	not MGM_G11(MGM_W9,SI);


	and MGM_G12(ENABLE_NOT_D_AND_SE_AND_NOT_SI,MGM_W9,MGM_W8);


	not MGM_G13(MGM_W10,D);


	and MGM_G14(MGM_W11,SE,MGM_W10);


	and MGM_G15(ENABLE_NOT_D_AND_SE_AND_SI,SI,MGM_W11);


	not MGM_G16(MGM_W12,SE);


	and MGM_G17(MGM_W13,MGM_W12,D);


	not MGM_G18(MGM_W14,SI);


	and MGM_G19(ENABLE_D_AND_NOT_SE_AND_NOT_SI,MGM_W14,MGM_W13);


	not MGM_G20(MGM_W15,SE);


	and MGM_G21(MGM_W16,MGM_W15,D);


	and MGM_G22(ENABLE_D_AND_NOT_SE_AND_SI,SI,MGM_W16);


	and MGM_G23(MGM_W17,SE,D);


	not MGM_G24(MGM_W18,SI);


	and MGM_G25(ENABLE_D_AND_SE_AND_NOT_SI,MGM_W18,MGM_W17);


	and MGM_G26(MGM_W19,SE,D);


	and MGM_G27(ENABLE_D_AND_SE_AND_SI,SI,MGM_W19);


	not MGM_G28(MGM_W20,SE);


	not MGM_G29(MGM_W21,SI);


	and MGM_G30(ENABLE_NOT_SE_AND_NOT_SI,MGM_W21,MGM_W20);


	not MGM_G31(MGM_W22,SE);


	and MGM_G32(ENABLE_NOT_SE_AND_SI,SI,MGM_W22);


	not MGM_G33(MGM_W23,D);


	and MGM_G34(ENABLE_NOT_D_AND_SI,SI,MGM_W23);


	not MGM_G35(MGM_W24,SI);


	and MGM_G36(ENABLE_D_AND_NOT_SI,MGM_W24,D);


	not MGM_G37(MGM_W25,D);


	and MGM_G38(ENABLE_NOT_D_AND_SE,SE,MGM_W25);


	and MGM_G39(ENABLE_D_AND_SE,SE,D);


	// spec_gates_end



   specify

	// specify_block_begin

	if(D===1'b0 && SI===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SE))  = (1.0,1.0);

	if(SE===1'b0 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b0 && SI===1'b1 || D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SI))  = (1.0,1.0);

	ifnone
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),
		negedge D &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),
		posedge D &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_SI === 1'b1),
		negedge D &&& (ENABLE_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_SI === 1'b1),
		posedge D &&& (ENABLE_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SI === 1'b1),
		negedge SE &&& (ENABLE_NOT_D_AND_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SI === 1'b1),
		posedge SE &&& (ENABLE_NOT_D_AND_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_NOT_D_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_NOT_D_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SI === 1'b1),1.0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_NOT_SI === 1'b1),
		negedge SE &&& (ENABLE_D_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_NOT_SI === 1'b1),
		posedge SE &&& (ENABLE_D_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_D_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_D_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SE === 1'b1),
		negedge SI &&& (ENABLE_NOT_D_AND_SE === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SE === 1'b1),
		posedge SI &&& (ENABLE_NOT_D_AND_SE === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_NOT_D_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_NOT_D_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE === 1'b1),1.0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_SE === 1'b1),
		negedge SI &&& (ENABLE_D_AND_SE === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_SE === 1'b1),
		posedge SI &&& (ENABLE_D_AND_SE === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_D_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_D_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE === 1'b1),1.0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__SDFFQ_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__SDFFQ_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__SDFFQ_FUNC_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffq_func( SE, SI, D, CLK, Q, VDD, VSS, VNW, VPW, notifier );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffq_func( SE, SI, D, CLK, Q, notifier );
`endif // If not USE_POWER_PINS
input CLK, D, SE, SI, notifier;
output Q;

	wire D_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffq_4;

	not MGM_BG_0( D_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffq_4, D );

	wire SE_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffq_4;

	not MGM_BG_1( SE_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffq_4, SE );

	wire MGM_D0_row1;

	and MGM_BG_2( MGM_D0_row1, D_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffq_4, SE_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffq_4 );

	wire SI_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffq_4;

	not MGM_BG_3( SI_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffq_4, SI );

	wire MGM_D0_row2;

	and MGM_BG_4( MGM_D0_row2, D_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffq_4, SI_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffq_4 );

	wire MGM_D0_row3;

	and MGM_BG_5( MGM_D0_row3, SI_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffq_4, SE );

	or MGM_BG_6( MGM_D0, MGM_D0_row1, MGM_D0_row2, MGM_D0_row3 );

	gf180mcu_fd_sc_mcu9t5v0__udp_n_iq_ff( IQ1, 1'b0, 1'b0, CLK, MGM_D0, notifier );

	not MGM_BG_7( Q, IQ1 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__SDFFQ_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__SDFFRNQ_1_V
`define GF180MCU_FD_SC_MCU9T5V0__SDFFRNQ_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffrnq_1( SE, SI, D, CLK, RN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffrnq_1( SE, SI, D, CLK, RN, Q );
`endif // If not USE_POWER_PINS
input CLK, D, RN, SE, SI;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffrnq_func gf180mcu_fd_sc_mcu9t5v0__sdffrnq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.RN(RN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffrnq_func gf180mcu_fd_sc_mcu9t5v0__sdffrnq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.RN(RN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(MGM_W1,RN,MGM_W0);


	not MGM_G2(MGM_W2,SE);


	and MGM_G3(MGM_W3,MGM_W2,MGM_W1);


	not MGM_G4(MGM_W4,SI);


	and MGM_G5(ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI,MGM_W4,MGM_W3);


	not MGM_G6(MGM_W5,D);


	and MGM_G7(MGM_W6,RN,MGM_W5);


	not MGM_G8(MGM_W7,SE);


	and MGM_G9(MGM_W8,MGM_W7,MGM_W6);


	and MGM_G10(ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI,SI,MGM_W8);


	not MGM_G11(MGM_W9,D);


	and MGM_G12(MGM_W10,RN,MGM_W9);


	and MGM_G13(MGM_W11,SE,MGM_W10);


	not MGM_G14(MGM_W12,SI);


	and MGM_G15(ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W12,MGM_W11);


	not MGM_G16(MGM_W13,D);


	and MGM_G17(MGM_W14,RN,MGM_W13);


	and MGM_G18(MGM_W15,SE,MGM_W14);


	and MGM_G19(ENABLE_NOT_D_AND_RN_AND_SE_AND_SI,SI,MGM_W15);


	and MGM_G20(MGM_W16,RN,D);


	not MGM_G21(MGM_W17,SE);


	and MGM_G22(MGM_W18,MGM_W17,MGM_W16);


	not MGM_G23(MGM_W19,SI);


	and MGM_G24(ENABLE_D_AND_RN_AND_NOT_SE_AND_NOT_SI,MGM_W19,MGM_W18);


	and MGM_G25(MGM_W20,RN,D);


	not MGM_G26(MGM_W21,SE);


	and MGM_G27(MGM_W22,MGM_W21,MGM_W20);


	and MGM_G28(ENABLE_D_AND_RN_AND_NOT_SE_AND_SI,SI,MGM_W22);


	and MGM_G29(MGM_W23,RN,D);


	and MGM_G30(MGM_W24,SE,MGM_W23);


	not MGM_G31(MGM_W25,SI);


	and MGM_G32(ENABLE_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W25,MGM_W24);


	and MGM_G33(MGM_W26,RN,D);


	and MGM_G34(MGM_W27,SE,MGM_W26);


	and MGM_G35(ENABLE_D_AND_RN_AND_SE_AND_SI,SI,MGM_W27);


	not MGM_G36(MGM_W28,SE);


	and MGM_G37(MGM_W29,MGM_W28,RN);


	not MGM_G38(MGM_W30,SI);


	and MGM_G39(ENABLE_RN_AND_NOT_SE_AND_NOT_SI,MGM_W30,MGM_W29);


	not MGM_G40(MGM_W31,SE);


	and MGM_G41(MGM_W32,MGM_W31,RN);


	and MGM_G42(ENABLE_RN_AND_NOT_SE_AND_SI,SI,MGM_W32);


	not MGM_G43(MGM_W33,D);


	and MGM_G44(MGM_W34,SE,MGM_W33);


	and MGM_G45(ENABLE_NOT_D_AND_SE_AND_SI,SI,MGM_W34);


	not MGM_G46(MGM_W35,SE);


	and MGM_G47(MGM_W36,MGM_W35,D);


	not MGM_G48(MGM_W37,SI);


	and MGM_G49(ENABLE_D_AND_NOT_SE_AND_NOT_SI,MGM_W37,MGM_W36);


	not MGM_G50(MGM_W38,SE);


	and MGM_G51(MGM_W39,MGM_W38,D);


	and MGM_G52(ENABLE_D_AND_NOT_SE_AND_SI,SI,MGM_W39);


	and MGM_G53(MGM_W40,SE,D);


	and MGM_G54(ENABLE_D_AND_SE_AND_SI,SI,MGM_W40);


	not MGM_G55(MGM_W41,CLK);


	not MGM_G56(MGM_W42,D);


	and MGM_G57(MGM_W43,MGM_W42,MGM_W41);


	not MGM_G58(MGM_W44,SE);


	and MGM_G59(MGM_W45,MGM_W44,MGM_W43);


	not MGM_G60(MGM_W46,SI);


	and MGM_G61(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W46,MGM_W45);


	not MGM_G62(MGM_W47,CLK);


	not MGM_G63(MGM_W48,D);


	and MGM_G64(MGM_W49,MGM_W48,MGM_W47);


	not MGM_G65(MGM_W50,SE);


	and MGM_G66(MGM_W51,MGM_W50,MGM_W49);


	and MGM_G67(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W51);


	not MGM_G68(MGM_W52,CLK);


	not MGM_G69(MGM_W53,D);


	and MGM_G70(MGM_W54,MGM_W53,MGM_W52);


	and MGM_G71(MGM_W55,SE,MGM_W54);


	not MGM_G72(MGM_W56,SI);


	and MGM_G73(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI,MGM_W56,MGM_W55);


	not MGM_G74(MGM_W57,CLK);


	not MGM_G75(MGM_W58,D);


	and MGM_G76(MGM_W59,MGM_W58,MGM_W57);


	and MGM_G77(MGM_W60,SE,MGM_W59);


	and MGM_G78(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI,SI,MGM_W60);


	not MGM_G79(MGM_W61,CLK);


	and MGM_G80(MGM_W62,D,MGM_W61);


	not MGM_G81(MGM_W63,SE);


	and MGM_G82(MGM_W64,MGM_W63,MGM_W62);


	not MGM_G83(MGM_W65,SI);


	and MGM_G84(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI,MGM_W65,MGM_W64);


	not MGM_G85(MGM_W66,CLK);


	and MGM_G86(MGM_W67,D,MGM_W66);


	not MGM_G87(MGM_W68,SE);


	and MGM_G88(MGM_W69,MGM_W68,MGM_W67);


	and MGM_G89(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI,SI,MGM_W69);


	not MGM_G90(MGM_W70,CLK);


	and MGM_G91(MGM_W71,D,MGM_W70);


	and MGM_G92(MGM_W72,SE,MGM_W71);


	not MGM_G93(MGM_W73,SI);


	and MGM_G94(ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI,MGM_W73,MGM_W72);


	not MGM_G95(MGM_W74,CLK);


	and MGM_G96(MGM_W75,D,MGM_W74);


	and MGM_G97(MGM_W76,SE,MGM_W75);


	and MGM_G98(ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI,SI,MGM_W76);


	not MGM_G99(MGM_W77,D);


	and MGM_G100(MGM_W78,MGM_W77,CLK);


	not MGM_G101(MGM_W79,SE);


	and MGM_G102(MGM_W80,MGM_W79,MGM_W78);


	not MGM_G103(MGM_W81,SI);


	and MGM_G104(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W81,MGM_W80);


	not MGM_G105(MGM_W82,D);


	and MGM_G106(MGM_W83,MGM_W82,CLK);


	not MGM_G107(MGM_W84,SE);


	and MGM_G108(MGM_W85,MGM_W84,MGM_W83);


	and MGM_G109(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W85);


	not MGM_G110(MGM_W86,D);


	and MGM_G111(MGM_W87,MGM_W86,CLK);


	and MGM_G112(MGM_W88,SE,MGM_W87);


	not MGM_G113(MGM_W89,SI);


	and MGM_G114(ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI,MGM_W89,MGM_W88);


	not MGM_G115(MGM_W90,D);


	and MGM_G116(MGM_W91,MGM_W90,CLK);


	and MGM_G117(MGM_W92,SE,MGM_W91);


	and MGM_G118(ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI,SI,MGM_W92);


	and MGM_G119(MGM_W93,D,CLK);


	not MGM_G120(MGM_W94,SE);


	and MGM_G121(MGM_W95,MGM_W94,MGM_W93);


	not MGM_G122(MGM_W96,SI);


	and MGM_G123(ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI,MGM_W96,MGM_W95);


	and MGM_G124(MGM_W97,D,CLK);


	not MGM_G125(MGM_W98,SE);


	and MGM_G126(MGM_W99,MGM_W98,MGM_W97);


	and MGM_G127(ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI,SI,MGM_W99);


	and MGM_G128(MGM_W100,D,CLK);


	and MGM_G129(MGM_W101,SE,MGM_W100);


	not MGM_G130(MGM_W102,SI);


	and MGM_G131(ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI,MGM_W102,MGM_W101);


	and MGM_G132(MGM_W103,D,CLK);


	and MGM_G133(MGM_W104,SE,MGM_W103);


	and MGM_G134(ENABLE_CLK_AND_D_AND_SE_AND_SI,SI,MGM_W104);


	not MGM_G135(MGM_W105,D);


	and MGM_G136(MGM_W106,RN,MGM_W105);


	and MGM_G137(ENABLE_NOT_D_AND_RN_AND_SI,SI,MGM_W106);


	and MGM_G138(MGM_W107,RN,D);


	not MGM_G139(MGM_W108,SI);


	and MGM_G140(ENABLE_D_AND_RN_AND_NOT_SI,MGM_W108,MGM_W107);


	not MGM_G141(MGM_W109,D);


	and MGM_G142(MGM_W110,RN,MGM_W109);


	and MGM_G143(ENABLE_NOT_D_AND_RN_AND_SE,SE,MGM_W110);


	and MGM_G144(MGM_W111,RN,D);


	and MGM_G145(ENABLE_D_AND_RN_AND_SE,SE,MGM_W111);


	// spec_gates_end



   specify

	// specify_block_begin

	if(D===1'b0 && SI===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SE))  = (1.0,1.0);

	if(SE===1'b0 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b0 && SI===1'b1 || D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SI))  = (1.0,1.0);

	ifnone
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),
		negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),
		negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),
		posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_D_AND_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_D_AND_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),
		negedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),
		posedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),1.0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),
		negedge SE &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),
		posedge SE &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),
		negedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),
		posedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),
		negedge SI &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),
		posedge SI &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__SDFFRNQ_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__SDFFRNQ_2_V
`define GF180MCU_FD_SC_MCU9T5V0__SDFFRNQ_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffrnq_2( SE, SI, D, CLK, RN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffrnq_2( SE, SI, D, CLK, RN, Q );
`endif // If not USE_POWER_PINS
input CLK, D, RN, SE, SI;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffrnq_func gf180mcu_fd_sc_mcu9t5v0__sdffrnq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.RN(RN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffrnq_func gf180mcu_fd_sc_mcu9t5v0__sdffrnq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.RN(RN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(MGM_W1,RN,MGM_W0);


	not MGM_G2(MGM_W2,SE);


	and MGM_G3(MGM_W3,MGM_W2,MGM_W1);


	not MGM_G4(MGM_W4,SI);


	and MGM_G5(ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI,MGM_W4,MGM_W3);


	not MGM_G6(MGM_W5,D);


	and MGM_G7(MGM_W6,RN,MGM_W5);


	not MGM_G8(MGM_W7,SE);


	and MGM_G9(MGM_W8,MGM_W7,MGM_W6);


	and MGM_G10(ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI,SI,MGM_W8);


	not MGM_G11(MGM_W9,D);


	and MGM_G12(MGM_W10,RN,MGM_W9);


	and MGM_G13(MGM_W11,SE,MGM_W10);


	not MGM_G14(MGM_W12,SI);


	and MGM_G15(ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W12,MGM_W11);


	not MGM_G16(MGM_W13,D);


	and MGM_G17(MGM_W14,RN,MGM_W13);


	and MGM_G18(MGM_W15,SE,MGM_W14);


	and MGM_G19(ENABLE_NOT_D_AND_RN_AND_SE_AND_SI,SI,MGM_W15);


	and MGM_G20(MGM_W16,RN,D);


	not MGM_G21(MGM_W17,SE);


	and MGM_G22(MGM_W18,MGM_W17,MGM_W16);


	not MGM_G23(MGM_W19,SI);


	and MGM_G24(ENABLE_D_AND_RN_AND_NOT_SE_AND_NOT_SI,MGM_W19,MGM_W18);


	and MGM_G25(MGM_W20,RN,D);


	not MGM_G26(MGM_W21,SE);


	and MGM_G27(MGM_W22,MGM_W21,MGM_W20);


	and MGM_G28(ENABLE_D_AND_RN_AND_NOT_SE_AND_SI,SI,MGM_W22);


	and MGM_G29(MGM_W23,RN,D);


	and MGM_G30(MGM_W24,SE,MGM_W23);


	not MGM_G31(MGM_W25,SI);


	and MGM_G32(ENABLE_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W25,MGM_W24);


	and MGM_G33(MGM_W26,RN,D);


	and MGM_G34(MGM_W27,SE,MGM_W26);


	and MGM_G35(ENABLE_D_AND_RN_AND_SE_AND_SI,SI,MGM_W27);


	not MGM_G36(MGM_W28,SE);


	and MGM_G37(MGM_W29,MGM_W28,RN);


	not MGM_G38(MGM_W30,SI);


	and MGM_G39(ENABLE_RN_AND_NOT_SE_AND_NOT_SI,MGM_W30,MGM_W29);


	not MGM_G40(MGM_W31,SE);


	and MGM_G41(MGM_W32,MGM_W31,RN);


	and MGM_G42(ENABLE_RN_AND_NOT_SE_AND_SI,SI,MGM_W32);


	not MGM_G43(MGM_W33,D);


	and MGM_G44(MGM_W34,SE,MGM_W33);


	and MGM_G45(ENABLE_NOT_D_AND_SE_AND_SI,SI,MGM_W34);


	not MGM_G46(MGM_W35,SE);


	and MGM_G47(MGM_W36,MGM_W35,D);


	not MGM_G48(MGM_W37,SI);


	and MGM_G49(ENABLE_D_AND_NOT_SE_AND_NOT_SI,MGM_W37,MGM_W36);


	not MGM_G50(MGM_W38,SE);


	and MGM_G51(MGM_W39,MGM_W38,D);


	and MGM_G52(ENABLE_D_AND_NOT_SE_AND_SI,SI,MGM_W39);


	and MGM_G53(MGM_W40,SE,D);


	and MGM_G54(ENABLE_D_AND_SE_AND_SI,SI,MGM_W40);


	not MGM_G55(MGM_W41,CLK);


	not MGM_G56(MGM_W42,D);


	and MGM_G57(MGM_W43,MGM_W42,MGM_W41);


	not MGM_G58(MGM_W44,SE);


	and MGM_G59(MGM_W45,MGM_W44,MGM_W43);


	not MGM_G60(MGM_W46,SI);


	and MGM_G61(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W46,MGM_W45);


	not MGM_G62(MGM_W47,CLK);


	not MGM_G63(MGM_W48,D);


	and MGM_G64(MGM_W49,MGM_W48,MGM_W47);


	not MGM_G65(MGM_W50,SE);


	and MGM_G66(MGM_W51,MGM_W50,MGM_W49);


	and MGM_G67(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W51);


	not MGM_G68(MGM_W52,CLK);


	not MGM_G69(MGM_W53,D);


	and MGM_G70(MGM_W54,MGM_W53,MGM_W52);


	and MGM_G71(MGM_W55,SE,MGM_W54);


	not MGM_G72(MGM_W56,SI);


	and MGM_G73(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI,MGM_W56,MGM_W55);


	not MGM_G74(MGM_W57,CLK);


	not MGM_G75(MGM_W58,D);


	and MGM_G76(MGM_W59,MGM_W58,MGM_W57);


	and MGM_G77(MGM_W60,SE,MGM_W59);


	and MGM_G78(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI,SI,MGM_W60);


	not MGM_G79(MGM_W61,CLK);


	and MGM_G80(MGM_W62,D,MGM_W61);


	not MGM_G81(MGM_W63,SE);


	and MGM_G82(MGM_W64,MGM_W63,MGM_W62);


	not MGM_G83(MGM_W65,SI);


	and MGM_G84(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI,MGM_W65,MGM_W64);


	not MGM_G85(MGM_W66,CLK);


	and MGM_G86(MGM_W67,D,MGM_W66);


	not MGM_G87(MGM_W68,SE);


	and MGM_G88(MGM_W69,MGM_W68,MGM_W67);


	and MGM_G89(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI,SI,MGM_W69);


	not MGM_G90(MGM_W70,CLK);


	and MGM_G91(MGM_W71,D,MGM_W70);


	and MGM_G92(MGM_W72,SE,MGM_W71);


	not MGM_G93(MGM_W73,SI);


	and MGM_G94(ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI,MGM_W73,MGM_W72);


	not MGM_G95(MGM_W74,CLK);


	and MGM_G96(MGM_W75,D,MGM_W74);


	and MGM_G97(MGM_W76,SE,MGM_W75);


	and MGM_G98(ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI,SI,MGM_W76);


	not MGM_G99(MGM_W77,D);


	and MGM_G100(MGM_W78,MGM_W77,CLK);


	not MGM_G101(MGM_W79,SE);


	and MGM_G102(MGM_W80,MGM_W79,MGM_W78);


	not MGM_G103(MGM_W81,SI);


	and MGM_G104(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W81,MGM_W80);


	not MGM_G105(MGM_W82,D);


	and MGM_G106(MGM_W83,MGM_W82,CLK);


	not MGM_G107(MGM_W84,SE);


	and MGM_G108(MGM_W85,MGM_W84,MGM_W83);


	and MGM_G109(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W85);


	not MGM_G110(MGM_W86,D);


	and MGM_G111(MGM_W87,MGM_W86,CLK);


	and MGM_G112(MGM_W88,SE,MGM_W87);


	not MGM_G113(MGM_W89,SI);


	and MGM_G114(ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI,MGM_W89,MGM_W88);


	not MGM_G115(MGM_W90,D);


	and MGM_G116(MGM_W91,MGM_W90,CLK);


	and MGM_G117(MGM_W92,SE,MGM_W91);


	and MGM_G118(ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI,SI,MGM_W92);


	and MGM_G119(MGM_W93,D,CLK);


	not MGM_G120(MGM_W94,SE);


	and MGM_G121(MGM_W95,MGM_W94,MGM_W93);


	not MGM_G122(MGM_W96,SI);


	and MGM_G123(ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI,MGM_W96,MGM_W95);


	and MGM_G124(MGM_W97,D,CLK);


	not MGM_G125(MGM_W98,SE);


	and MGM_G126(MGM_W99,MGM_W98,MGM_W97);


	and MGM_G127(ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI,SI,MGM_W99);


	and MGM_G128(MGM_W100,D,CLK);


	and MGM_G129(MGM_W101,SE,MGM_W100);


	not MGM_G130(MGM_W102,SI);


	and MGM_G131(ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI,MGM_W102,MGM_W101);


	and MGM_G132(MGM_W103,D,CLK);


	and MGM_G133(MGM_W104,SE,MGM_W103);


	and MGM_G134(ENABLE_CLK_AND_D_AND_SE_AND_SI,SI,MGM_W104);


	not MGM_G135(MGM_W105,D);


	and MGM_G136(MGM_W106,RN,MGM_W105);


	and MGM_G137(ENABLE_NOT_D_AND_RN_AND_SI,SI,MGM_W106);


	and MGM_G138(MGM_W107,RN,D);


	not MGM_G139(MGM_W108,SI);


	and MGM_G140(ENABLE_D_AND_RN_AND_NOT_SI,MGM_W108,MGM_W107);


	not MGM_G141(MGM_W109,D);


	and MGM_G142(MGM_W110,RN,MGM_W109);


	and MGM_G143(ENABLE_NOT_D_AND_RN_AND_SE,SE,MGM_W110);


	and MGM_G144(MGM_W111,RN,D);


	and MGM_G145(ENABLE_D_AND_RN_AND_SE,SE,MGM_W111);


	// spec_gates_end



   specify

	// specify_block_begin

	if(D===1'b0 && SI===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SE))  = (1.0,1.0);

	if(SE===1'b0 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b0 && SI===1'b1 || D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SI))  = (1.0,1.0);

	ifnone
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),
		negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),
		negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),
		posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_D_AND_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_D_AND_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),
		negedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),
		posedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),1.0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),
		negedge SE &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),
		posedge SE &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),
		negedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),
		posedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),
		negedge SI &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),
		posedge SI &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__SDFFRNQ_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__SDFFRNQ_4_V
`define GF180MCU_FD_SC_MCU9T5V0__SDFFRNQ_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffrnq_4( SE, SI, D, CLK, RN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffrnq_4( SE, SI, D, CLK, RN, Q );
`endif // If not USE_POWER_PINS
input CLK, D, RN, SE, SI;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffrnq_func gf180mcu_fd_sc_mcu9t5v0__sdffrnq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.RN(RN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffrnq_func gf180mcu_fd_sc_mcu9t5v0__sdffrnq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.RN(RN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(MGM_W1,RN,MGM_W0);


	not MGM_G2(MGM_W2,SE);


	and MGM_G3(MGM_W3,MGM_W2,MGM_W1);


	not MGM_G4(MGM_W4,SI);


	and MGM_G5(ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI,MGM_W4,MGM_W3);


	not MGM_G6(MGM_W5,D);


	and MGM_G7(MGM_W6,RN,MGM_W5);


	not MGM_G8(MGM_W7,SE);


	and MGM_G9(MGM_W8,MGM_W7,MGM_W6);


	and MGM_G10(ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI,SI,MGM_W8);


	not MGM_G11(MGM_W9,D);


	and MGM_G12(MGM_W10,RN,MGM_W9);


	and MGM_G13(MGM_W11,SE,MGM_W10);


	not MGM_G14(MGM_W12,SI);


	and MGM_G15(ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W12,MGM_W11);


	not MGM_G16(MGM_W13,D);


	and MGM_G17(MGM_W14,RN,MGM_W13);


	and MGM_G18(MGM_W15,SE,MGM_W14);


	and MGM_G19(ENABLE_NOT_D_AND_RN_AND_SE_AND_SI,SI,MGM_W15);


	and MGM_G20(MGM_W16,RN,D);


	not MGM_G21(MGM_W17,SE);


	and MGM_G22(MGM_W18,MGM_W17,MGM_W16);


	not MGM_G23(MGM_W19,SI);


	and MGM_G24(ENABLE_D_AND_RN_AND_NOT_SE_AND_NOT_SI,MGM_W19,MGM_W18);


	and MGM_G25(MGM_W20,RN,D);


	not MGM_G26(MGM_W21,SE);


	and MGM_G27(MGM_W22,MGM_W21,MGM_W20);


	and MGM_G28(ENABLE_D_AND_RN_AND_NOT_SE_AND_SI,SI,MGM_W22);


	and MGM_G29(MGM_W23,RN,D);


	and MGM_G30(MGM_W24,SE,MGM_W23);


	not MGM_G31(MGM_W25,SI);


	and MGM_G32(ENABLE_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W25,MGM_W24);


	and MGM_G33(MGM_W26,RN,D);


	and MGM_G34(MGM_W27,SE,MGM_W26);


	and MGM_G35(ENABLE_D_AND_RN_AND_SE_AND_SI,SI,MGM_W27);


	not MGM_G36(MGM_W28,SE);


	and MGM_G37(MGM_W29,MGM_W28,RN);


	not MGM_G38(MGM_W30,SI);


	and MGM_G39(ENABLE_RN_AND_NOT_SE_AND_NOT_SI,MGM_W30,MGM_W29);


	not MGM_G40(MGM_W31,SE);


	and MGM_G41(MGM_W32,MGM_W31,RN);


	and MGM_G42(ENABLE_RN_AND_NOT_SE_AND_SI,SI,MGM_W32);


	not MGM_G43(MGM_W33,D);


	and MGM_G44(MGM_W34,SE,MGM_W33);


	and MGM_G45(ENABLE_NOT_D_AND_SE_AND_SI,SI,MGM_W34);


	not MGM_G46(MGM_W35,SE);


	and MGM_G47(MGM_W36,MGM_W35,D);


	not MGM_G48(MGM_W37,SI);


	and MGM_G49(ENABLE_D_AND_NOT_SE_AND_NOT_SI,MGM_W37,MGM_W36);


	not MGM_G50(MGM_W38,SE);


	and MGM_G51(MGM_W39,MGM_W38,D);


	and MGM_G52(ENABLE_D_AND_NOT_SE_AND_SI,SI,MGM_W39);


	and MGM_G53(MGM_W40,SE,D);


	and MGM_G54(ENABLE_D_AND_SE_AND_SI,SI,MGM_W40);


	not MGM_G55(MGM_W41,CLK);


	not MGM_G56(MGM_W42,D);


	and MGM_G57(MGM_W43,MGM_W42,MGM_W41);


	not MGM_G58(MGM_W44,SE);


	and MGM_G59(MGM_W45,MGM_W44,MGM_W43);


	not MGM_G60(MGM_W46,SI);


	and MGM_G61(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W46,MGM_W45);


	not MGM_G62(MGM_W47,CLK);


	not MGM_G63(MGM_W48,D);


	and MGM_G64(MGM_W49,MGM_W48,MGM_W47);


	not MGM_G65(MGM_W50,SE);


	and MGM_G66(MGM_W51,MGM_W50,MGM_W49);


	and MGM_G67(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W51);


	not MGM_G68(MGM_W52,CLK);


	not MGM_G69(MGM_W53,D);


	and MGM_G70(MGM_W54,MGM_W53,MGM_W52);


	and MGM_G71(MGM_W55,SE,MGM_W54);


	not MGM_G72(MGM_W56,SI);


	and MGM_G73(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI,MGM_W56,MGM_W55);


	not MGM_G74(MGM_W57,CLK);


	not MGM_G75(MGM_W58,D);


	and MGM_G76(MGM_W59,MGM_W58,MGM_W57);


	and MGM_G77(MGM_W60,SE,MGM_W59);


	and MGM_G78(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI,SI,MGM_W60);


	not MGM_G79(MGM_W61,CLK);


	and MGM_G80(MGM_W62,D,MGM_W61);


	not MGM_G81(MGM_W63,SE);


	and MGM_G82(MGM_W64,MGM_W63,MGM_W62);


	not MGM_G83(MGM_W65,SI);


	and MGM_G84(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI,MGM_W65,MGM_W64);


	not MGM_G85(MGM_W66,CLK);


	and MGM_G86(MGM_W67,D,MGM_W66);


	not MGM_G87(MGM_W68,SE);


	and MGM_G88(MGM_W69,MGM_W68,MGM_W67);


	and MGM_G89(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI,SI,MGM_W69);


	not MGM_G90(MGM_W70,CLK);


	and MGM_G91(MGM_W71,D,MGM_W70);


	and MGM_G92(MGM_W72,SE,MGM_W71);


	not MGM_G93(MGM_W73,SI);


	and MGM_G94(ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI,MGM_W73,MGM_W72);


	not MGM_G95(MGM_W74,CLK);


	and MGM_G96(MGM_W75,D,MGM_W74);


	and MGM_G97(MGM_W76,SE,MGM_W75);


	and MGM_G98(ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI,SI,MGM_W76);


	not MGM_G99(MGM_W77,D);


	and MGM_G100(MGM_W78,MGM_W77,CLK);


	not MGM_G101(MGM_W79,SE);


	and MGM_G102(MGM_W80,MGM_W79,MGM_W78);


	not MGM_G103(MGM_W81,SI);


	and MGM_G104(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W81,MGM_W80);


	not MGM_G105(MGM_W82,D);


	and MGM_G106(MGM_W83,MGM_W82,CLK);


	not MGM_G107(MGM_W84,SE);


	and MGM_G108(MGM_W85,MGM_W84,MGM_W83);


	and MGM_G109(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W85);


	not MGM_G110(MGM_W86,D);


	and MGM_G111(MGM_W87,MGM_W86,CLK);


	and MGM_G112(MGM_W88,SE,MGM_W87);


	not MGM_G113(MGM_W89,SI);


	and MGM_G114(ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI,MGM_W89,MGM_W88);


	not MGM_G115(MGM_W90,D);


	and MGM_G116(MGM_W91,MGM_W90,CLK);


	and MGM_G117(MGM_W92,SE,MGM_W91);


	and MGM_G118(ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI,SI,MGM_W92);


	and MGM_G119(MGM_W93,D,CLK);


	not MGM_G120(MGM_W94,SE);


	and MGM_G121(MGM_W95,MGM_W94,MGM_W93);


	not MGM_G122(MGM_W96,SI);


	and MGM_G123(ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI,MGM_W96,MGM_W95);


	and MGM_G124(MGM_W97,D,CLK);


	not MGM_G125(MGM_W98,SE);


	and MGM_G126(MGM_W99,MGM_W98,MGM_W97);


	and MGM_G127(ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI,SI,MGM_W99);


	and MGM_G128(MGM_W100,D,CLK);


	and MGM_G129(MGM_W101,SE,MGM_W100);


	not MGM_G130(MGM_W102,SI);


	and MGM_G131(ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI,MGM_W102,MGM_W101);


	and MGM_G132(MGM_W103,D,CLK);


	and MGM_G133(MGM_W104,SE,MGM_W103);


	and MGM_G134(ENABLE_CLK_AND_D_AND_SE_AND_SI,SI,MGM_W104);


	not MGM_G135(MGM_W105,D);


	and MGM_G136(MGM_W106,RN,MGM_W105);


	and MGM_G137(ENABLE_NOT_D_AND_RN_AND_SI,SI,MGM_W106);


	and MGM_G138(MGM_W107,RN,D);


	not MGM_G139(MGM_W108,SI);


	and MGM_G140(ENABLE_D_AND_RN_AND_NOT_SI,MGM_W108,MGM_W107);


	not MGM_G141(MGM_W109,D);


	and MGM_G142(MGM_W110,RN,MGM_W109);


	and MGM_G143(ENABLE_NOT_D_AND_RN_AND_SE,SE,MGM_W110);


	and MGM_G144(MGM_W111,RN,D);


	and MGM_G145(ENABLE_D_AND_RN_AND_SE,SE,MGM_W111);


	// spec_gates_end



   specify

	// specify_block_begin

	if(D===1'b0 && SI===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SE))  = (1.0,1.0);

	if(SE===1'b0 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b0 && SI===1'b1 || D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SI))  = (1.0,1.0);

	ifnone
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),
		negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),
		negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),
		posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_D_AND_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_D_AND_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),
		negedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),
		posedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SI === 1'b1),1.0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),
		negedge SE &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),
		posedge SE &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),
		negedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),
		posedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),
		negedge SI &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),
		posedge SI &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SE === 1'b1),1.0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__SDFFRNQ_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__SDFFRNQ_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__SDFFRNQ_FUNC_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffrnq_func( SE, SI, D, CLK, RN, Q, VDD, VSS, VNW, VPW, notifier );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffrnq_func( SE, SI, D, CLK, RN, Q, notifier );
`endif // If not USE_POWER_PINS
input CLK, D, RN, SE, SI, notifier;
output Q;

	not MGM_BG_0( MGM_P0, RN );

	wire D_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffrnq_1;

	not MGM_BG_1( D_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffrnq_1, D );

	wire SE_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffrnq_1;

	not MGM_BG_2( SE_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffrnq_1, SE );

	wire MGM_D0_row1;

	and MGM_BG_3( MGM_D0_row1, D_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffrnq_1, SE_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffrnq_1 );

	wire SI_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffrnq_1;

	not MGM_BG_4( SI_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffrnq_1, SI );

	wire MGM_D0_row2;

	and MGM_BG_5( MGM_D0_row2, D_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffrnq_1, SI_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffrnq_1 );

	wire MGM_D0_row3;

	and MGM_BG_6( MGM_D0_row3, SI_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffrnq_1, SE );

	or MGM_BG_7( MGM_D0, MGM_D0_row1, MGM_D0_row2, MGM_D0_row3 );

	gf180mcu_fd_sc_mcu9t5v0__udp_n_iq_ff( IQ1, 1'b0, MGM_P0, CLK, MGM_D0, notifier );

	not MGM_BG_8( Q, IQ1 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__SDFFRNQ_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__SDFFRSNQ_1_V
`define GF180MCU_FD_SC_MCU9T5V0__SDFFRSNQ_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_1( SE, SI, D, CLK, SETN, RN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_1( SE, SI, D, CLK, SETN, RN, Q );
`endif // If not USE_POWER_PINS
input CLK, D, RN, SE, SETN, SI;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_func gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.SETN(SETN),.RN(RN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_func gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.SETN(SETN),.RN(RN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(MGM_W1,RN,MGM_W0);


	not MGM_G2(MGM_W2,SE);


	and MGM_G3(MGM_W3,MGM_W2,MGM_W1);


	and MGM_G4(MGM_W4,SETN,MGM_W3);


	not MGM_G5(MGM_W5,SI);


	and MGM_G6(ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W5,MGM_W4);


	not MGM_G7(MGM_W6,D);


	and MGM_G8(MGM_W7,RN,MGM_W6);


	not MGM_G9(MGM_W8,SE);


	and MGM_G10(MGM_W9,MGM_W8,MGM_W7);


	and MGM_G11(MGM_W10,SETN,MGM_W9);


	and MGM_G12(ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W10);


	not MGM_G13(MGM_W11,D);


	and MGM_G14(MGM_W12,RN,MGM_W11);


	and MGM_G15(MGM_W13,SE,MGM_W12);


	and MGM_G16(MGM_W14,SETN,MGM_W13);


	not MGM_G17(MGM_W15,SI);


	and MGM_G18(ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI,MGM_W15,MGM_W14);


	not MGM_G19(MGM_W16,D);


	and MGM_G20(MGM_W17,RN,MGM_W16);


	and MGM_G21(MGM_W18,SE,MGM_W17);


	and MGM_G22(MGM_W19,SETN,MGM_W18);


	and MGM_G23(ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_SI,SI,MGM_W19);


	and MGM_G24(MGM_W20,RN,D);


	not MGM_G25(MGM_W21,SE);


	and MGM_G26(MGM_W22,MGM_W21,MGM_W20);


	and MGM_G27(MGM_W23,SETN,MGM_W22);


	not MGM_G28(MGM_W24,SI);


	and MGM_G29(ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W24,MGM_W23);


	and MGM_G30(MGM_W25,RN,D);


	not MGM_G31(MGM_W26,SE);


	and MGM_G32(MGM_W27,MGM_W26,MGM_W25);


	and MGM_G33(MGM_W28,SETN,MGM_W27);


	and MGM_G34(ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W28);


	and MGM_G35(MGM_W29,RN,D);


	and MGM_G36(MGM_W30,SE,MGM_W29);


	and MGM_G37(MGM_W31,SETN,MGM_W30);


	not MGM_G38(MGM_W32,SI);


	and MGM_G39(ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI,MGM_W32,MGM_W31);


	and MGM_G40(MGM_W33,RN,D);


	and MGM_G41(MGM_W34,SE,MGM_W33);


	and MGM_G42(MGM_W35,SETN,MGM_W34);


	and MGM_G43(ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_SI,SI,MGM_W35);


	not MGM_G44(MGM_W36,SE);


	and MGM_G45(MGM_W37,MGM_W36,RN);


	and MGM_G46(MGM_W38,SETN,MGM_W37);


	not MGM_G47(MGM_W39,SI);


	and MGM_G48(ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W39,MGM_W38);


	not MGM_G49(MGM_W40,SE);


	and MGM_G50(MGM_W41,MGM_W40,RN);


	and MGM_G51(MGM_W42,SETN,MGM_W41);


	and MGM_G52(ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W42);


	not MGM_G53(MGM_W43,D);


	and MGM_G54(MGM_W44,SE,MGM_W43);


	and MGM_G55(MGM_W45,SETN,MGM_W44);


	and MGM_G56(ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W45);


	not MGM_G57(MGM_W46,SE);


	and MGM_G58(MGM_W47,MGM_W46,D);


	and MGM_G59(MGM_W48,SETN,MGM_W47);


	not MGM_G60(MGM_W49,SI);


	and MGM_G61(ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W49,MGM_W48);


	not MGM_G62(MGM_W50,SE);


	and MGM_G63(MGM_W51,MGM_W50,D);


	and MGM_G64(MGM_W52,SETN,MGM_W51);


	and MGM_G65(ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W52);


	and MGM_G66(MGM_W53,SE,D);


	and MGM_G67(MGM_W54,SETN,MGM_W53);


	and MGM_G68(ENABLE_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W54);


	not MGM_G69(MGM_W55,CLK);


	not MGM_G70(MGM_W56,D);


	and MGM_G71(MGM_W57,MGM_W56,MGM_W55);


	not MGM_G72(MGM_W58,SE);


	and MGM_G73(MGM_W59,MGM_W58,MGM_W57);


	and MGM_G74(MGM_W60,SETN,MGM_W59);


	not MGM_G75(MGM_W61,SI);


	and MGM_G76(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W61,MGM_W60);


	not MGM_G77(MGM_W62,CLK);


	not MGM_G78(MGM_W63,D);


	and MGM_G79(MGM_W64,MGM_W63,MGM_W62);


	not MGM_G80(MGM_W65,SE);


	and MGM_G81(MGM_W66,MGM_W65,MGM_W64);


	and MGM_G82(MGM_W67,SETN,MGM_W66);


	and MGM_G83(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W67);


	not MGM_G84(MGM_W68,CLK);


	not MGM_G85(MGM_W69,D);


	and MGM_G86(MGM_W70,MGM_W69,MGM_W68);


	and MGM_G87(MGM_W71,SE,MGM_W70);


	and MGM_G88(MGM_W72,SETN,MGM_W71);


	not MGM_G89(MGM_W73,SI);


	and MGM_G90(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_NOT_SI,MGM_W73,MGM_W72);


	not MGM_G91(MGM_W74,CLK);


	not MGM_G92(MGM_W75,D);


	and MGM_G93(MGM_W76,MGM_W75,MGM_W74);


	and MGM_G94(MGM_W77,SE,MGM_W76);


	and MGM_G95(MGM_W78,SETN,MGM_W77);


	and MGM_G96(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W78);


	not MGM_G97(MGM_W79,CLK);


	and MGM_G98(MGM_W80,D,MGM_W79);


	not MGM_G99(MGM_W81,SE);


	and MGM_G100(MGM_W82,MGM_W81,MGM_W80);


	and MGM_G101(MGM_W83,SETN,MGM_W82);


	not MGM_G102(MGM_W84,SI);


	and MGM_G103(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W84,MGM_W83);


	not MGM_G104(MGM_W85,CLK);


	and MGM_G105(MGM_W86,D,MGM_W85);


	not MGM_G106(MGM_W87,SE);


	and MGM_G107(MGM_W88,MGM_W87,MGM_W86);


	and MGM_G108(MGM_W89,SETN,MGM_W88);


	and MGM_G109(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W89);


	not MGM_G110(MGM_W90,CLK);


	and MGM_G111(MGM_W91,D,MGM_W90);


	and MGM_G112(MGM_W92,SE,MGM_W91);


	and MGM_G113(MGM_W93,SETN,MGM_W92);


	not MGM_G114(MGM_W94,SI);


	and MGM_G115(ENABLE_NOT_CLK_AND_D_AND_SE_AND_SETN_AND_NOT_SI,MGM_W94,MGM_W93);


	not MGM_G116(MGM_W95,CLK);


	and MGM_G117(MGM_W96,D,MGM_W95);


	and MGM_G118(MGM_W97,SE,MGM_W96);


	and MGM_G119(MGM_W98,SETN,MGM_W97);


	and MGM_G120(ENABLE_NOT_CLK_AND_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W98);


	not MGM_G121(MGM_W99,D);


	and MGM_G122(MGM_W100,MGM_W99,CLK);


	not MGM_G123(MGM_W101,SE);


	and MGM_G124(MGM_W102,MGM_W101,MGM_W100);


	and MGM_G125(MGM_W103,SETN,MGM_W102);


	not MGM_G126(MGM_W104,SI);


	and MGM_G127(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W104,MGM_W103);


	not MGM_G128(MGM_W105,D);


	and MGM_G129(MGM_W106,MGM_W105,CLK);


	not MGM_G130(MGM_W107,SE);


	and MGM_G131(MGM_W108,MGM_W107,MGM_W106);


	and MGM_G132(MGM_W109,SETN,MGM_W108);


	and MGM_G133(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W109);


	not MGM_G134(MGM_W110,D);


	and MGM_G135(MGM_W111,MGM_W110,CLK);


	and MGM_G136(MGM_W112,SE,MGM_W111);


	and MGM_G137(MGM_W113,SETN,MGM_W112);


	not MGM_G138(MGM_W114,SI);


	and MGM_G139(ENABLE_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_NOT_SI,MGM_W114,MGM_W113);


	not MGM_G140(MGM_W115,D);


	and MGM_G141(MGM_W116,MGM_W115,CLK);


	and MGM_G142(MGM_W117,SE,MGM_W116);


	and MGM_G143(MGM_W118,SETN,MGM_W117);


	and MGM_G144(ENABLE_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W118);


	and MGM_G145(MGM_W119,D,CLK);


	not MGM_G146(MGM_W120,SE);


	and MGM_G147(MGM_W121,MGM_W120,MGM_W119);


	and MGM_G148(MGM_W122,SETN,MGM_W121);


	not MGM_G149(MGM_W123,SI);


	and MGM_G150(ENABLE_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W123,MGM_W122);


	and MGM_G151(MGM_W124,D,CLK);


	not MGM_G152(MGM_W125,SE);


	and MGM_G153(MGM_W126,MGM_W125,MGM_W124);


	and MGM_G154(MGM_W127,SETN,MGM_W126);


	and MGM_G155(ENABLE_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W127);


	and MGM_G156(MGM_W128,D,CLK);


	and MGM_G157(MGM_W129,SE,MGM_W128);


	and MGM_G158(MGM_W130,SETN,MGM_W129);


	not MGM_G159(MGM_W131,SI);


	and MGM_G160(ENABLE_CLK_AND_D_AND_SE_AND_SETN_AND_NOT_SI,MGM_W131,MGM_W130);


	and MGM_G161(MGM_W132,D,CLK);


	and MGM_G162(MGM_W133,SE,MGM_W132);


	and MGM_G163(MGM_W134,SETN,MGM_W133);


	and MGM_G164(ENABLE_CLK_AND_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W134);


	not MGM_G165(MGM_W135,CLK);


	not MGM_G166(MGM_W136,D);


	and MGM_G167(MGM_W137,MGM_W136,MGM_W135);


	not MGM_G168(MGM_W138,SE);


	and MGM_G169(MGM_W139,MGM_W138,MGM_W137);


	not MGM_G170(MGM_W140,SI);


	and MGM_G171(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W140,MGM_W139);


	not MGM_G172(MGM_W141,CLK);


	not MGM_G173(MGM_W142,D);


	and MGM_G174(MGM_W143,MGM_W142,MGM_W141);


	not MGM_G175(MGM_W144,SE);


	and MGM_G176(MGM_W145,MGM_W144,MGM_W143);


	and MGM_G177(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W145);


	not MGM_G178(MGM_W146,CLK);


	not MGM_G179(MGM_W147,D);


	and MGM_G180(MGM_W148,MGM_W147,MGM_W146);


	and MGM_G181(MGM_W149,SE,MGM_W148);


	not MGM_G182(MGM_W150,SI);


	and MGM_G183(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI,MGM_W150,MGM_W149);


	not MGM_G184(MGM_W151,CLK);


	not MGM_G185(MGM_W152,D);


	and MGM_G186(MGM_W153,MGM_W152,MGM_W151);


	and MGM_G187(MGM_W154,SE,MGM_W153);


	and MGM_G188(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI,SI,MGM_W154);


	not MGM_G189(MGM_W155,CLK);


	and MGM_G190(MGM_W156,D,MGM_W155);


	not MGM_G191(MGM_W157,SE);


	and MGM_G192(MGM_W158,MGM_W157,MGM_W156);


	not MGM_G193(MGM_W159,SI);


	and MGM_G194(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI,MGM_W159,MGM_W158);


	not MGM_G195(MGM_W160,CLK);


	and MGM_G196(MGM_W161,D,MGM_W160);


	not MGM_G197(MGM_W162,SE);


	and MGM_G198(MGM_W163,MGM_W162,MGM_W161);


	and MGM_G199(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI,SI,MGM_W163);


	not MGM_G200(MGM_W164,CLK);


	and MGM_G201(MGM_W165,D,MGM_W164);


	and MGM_G202(MGM_W166,SE,MGM_W165);


	not MGM_G203(MGM_W167,SI);


	and MGM_G204(ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI,MGM_W167,MGM_W166);


	not MGM_G205(MGM_W168,CLK);


	and MGM_G206(MGM_W169,D,MGM_W168);


	and MGM_G207(MGM_W170,SE,MGM_W169);


	and MGM_G208(ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI,SI,MGM_W170);


	not MGM_G209(MGM_W171,D);


	and MGM_G210(MGM_W172,MGM_W171,CLK);


	not MGM_G211(MGM_W173,SE);


	and MGM_G212(MGM_W174,MGM_W173,MGM_W172);


	not MGM_G213(MGM_W175,SI);


	and MGM_G214(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W175,MGM_W174);


	not MGM_G215(MGM_W176,D);


	and MGM_G216(MGM_W177,MGM_W176,CLK);


	not MGM_G217(MGM_W178,SE);


	and MGM_G218(MGM_W179,MGM_W178,MGM_W177);


	and MGM_G219(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W179);


	not MGM_G220(MGM_W180,D);


	and MGM_G221(MGM_W181,MGM_W180,CLK);


	and MGM_G222(MGM_W182,SE,MGM_W181);


	not MGM_G223(MGM_W183,SI);


	and MGM_G224(ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI,MGM_W183,MGM_W182);


	not MGM_G225(MGM_W184,D);


	and MGM_G226(MGM_W185,MGM_W184,CLK);


	and MGM_G227(MGM_W186,SE,MGM_W185);


	and MGM_G228(ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI,SI,MGM_W186);


	and MGM_G229(MGM_W187,D,CLK);


	not MGM_G230(MGM_W188,SE);


	and MGM_G231(MGM_W189,MGM_W188,MGM_W187);


	not MGM_G232(MGM_W190,SI);


	and MGM_G233(ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI,MGM_W190,MGM_W189);


	and MGM_G234(MGM_W191,D,CLK);


	not MGM_G235(MGM_W192,SE);


	and MGM_G236(MGM_W193,MGM_W192,MGM_W191);


	and MGM_G237(ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI,SI,MGM_W193);


	and MGM_G238(MGM_W194,D,CLK);


	and MGM_G239(MGM_W195,SE,MGM_W194);


	not MGM_G240(MGM_W196,SI);


	and MGM_G241(ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI,MGM_W196,MGM_W195);


	and MGM_G242(MGM_W197,D,CLK);


	and MGM_G243(MGM_W198,SE,MGM_W197);


	and MGM_G244(ENABLE_CLK_AND_D_AND_SE_AND_SI,SI,MGM_W198);


	not MGM_G245(MGM_W199,D);


	and MGM_G246(MGM_W200,RN,MGM_W199);


	and MGM_G247(MGM_W201,SETN,MGM_W200);


	and MGM_G248(ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI,SI,MGM_W201);


	and MGM_G249(MGM_W202,RN,D);


	and MGM_G250(MGM_W203,SETN,MGM_W202);


	not MGM_G251(MGM_W204,SI);


	and MGM_G252(ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI,MGM_W204,MGM_W203);


	not MGM_G253(MGM_W205,D);


	and MGM_G254(MGM_W206,RN,MGM_W205);


	not MGM_G255(MGM_W207,SE);


	and MGM_G256(MGM_W208,MGM_W207,MGM_W206);


	not MGM_G257(MGM_W209,SI);


	and MGM_G258(ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI,MGM_W209,MGM_W208);


	not MGM_G259(MGM_W210,D);


	and MGM_G260(MGM_W211,RN,MGM_W210);


	not MGM_G261(MGM_W212,SE);


	and MGM_G262(MGM_W213,MGM_W212,MGM_W211);


	and MGM_G263(ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI,SI,MGM_W213);


	not MGM_G264(MGM_W214,D);


	and MGM_G265(MGM_W215,RN,MGM_W214);


	and MGM_G266(MGM_W216,SE,MGM_W215);


	not MGM_G267(MGM_W217,SI);


	and MGM_G268(ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W217,MGM_W216);


	and MGM_G269(MGM_W218,RN,D);


	and MGM_G270(MGM_W219,SE,MGM_W218);


	not MGM_G271(MGM_W220,SI);


	and MGM_G272(ENABLE_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W220,MGM_W219);


	not MGM_G273(MGM_W221,CLK);


	not MGM_G274(MGM_W222,D);


	and MGM_G275(MGM_W223,MGM_W222,MGM_W221);


	and MGM_G276(MGM_W224,RN,MGM_W223);


	not MGM_G277(MGM_W225,SE);


	and MGM_G278(MGM_W226,MGM_W225,MGM_W224);


	not MGM_G279(MGM_W227,SI);


	and MGM_G280(ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI,MGM_W227,MGM_W226);


	not MGM_G281(MGM_W228,CLK);


	not MGM_G282(MGM_W229,D);


	and MGM_G283(MGM_W230,MGM_W229,MGM_W228);


	and MGM_G284(MGM_W231,RN,MGM_W230);


	not MGM_G285(MGM_W232,SE);


	and MGM_G286(MGM_W233,MGM_W232,MGM_W231);


	and MGM_G287(ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_SI,SI,MGM_W233);


	not MGM_G288(MGM_W234,CLK);


	not MGM_G289(MGM_W235,D);


	and MGM_G290(MGM_W236,MGM_W235,MGM_W234);


	and MGM_G291(MGM_W237,RN,MGM_W236);


	and MGM_G292(MGM_W238,SE,MGM_W237);


	not MGM_G293(MGM_W239,SI);


	and MGM_G294(ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W239,MGM_W238);


	not MGM_G295(MGM_W240,CLK);


	not MGM_G296(MGM_W241,D);


	and MGM_G297(MGM_W242,MGM_W241,MGM_W240);


	and MGM_G298(MGM_W243,RN,MGM_W242);


	and MGM_G299(MGM_W244,SE,MGM_W243);


	and MGM_G300(ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_SE_AND_SI,SI,MGM_W244);


	not MGM_G301(MGM_W245,CLK);


	and MGM_G302(MGM_W246,D,MGM_W245);


	and MGM_G303(MGM_W247,RN,MGM_W246);


	not MGM_G304(MGM_W248,SE);


	and MGM_G305(MGM_W249,MGM_W248,MGM_W247);


	not MGM_G306(MGM_W250,SI);


	and MGM_G307(ENABLE_NOT_CLK_AND_D_AND_RN_AND_NOT_SE_AND_NOT_SI,MGM_W250,MGM_W249);


	not MGM_G308(MGM_W251,CLK);


	and MGM_G309(MGM_W252,D,MGM_W251);


	and MGM_G310(MGM_W253,RN,MGM_W252);


	not MGM_G311(MGM_W254,SE);


	and MGM_G312(MGM_W255,MGM_W254,MGM_W253);


	and MGM_G313(ENABLE_NOT_CLK_AND_D_AND_RN_AND_NOT_SE_AND_SI,SI,MGM_W255);


	not MGM_G314(MGM_W256,CLK);


	and MGM_G315(MGM_W257,D,MGM_W256);


	and MGM_G316(MGM_W258,RN,MGM_W257);


	and MGM_G317(MGM_W259,SE,MGM_W258);


	not MGM_G318(MGM_W260,SI);


	and MGM_G319(ENABLE_NOT_CLK_AND_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W260,MGM_W259);


	not MGM_G320(MGM_W261,CLK);


	and MGM_G321(MGM_W262,D,MGM_W261);


	and MGM_G322(MGM_W263,RN,MGM_W262);


	and MGM_G323(MGM_W264,SE,MGM_W263);


	and MGM_G324(ENABLE_NOT_CLK_AND_D_AND_RN_AND_SE_AND_SI,SI,MGM_W264);


	not MGM_G325(MGM_W265,D);


	and MGM_G326(MGM_W266,MGM_W265,CLK);


	and MGM_G327(MGM_W267,RN,MGM_W266);


	not MGM_G328(MGM_W268,SE);


	and MGM_G329(MGM_W269,MGM_W268,MGM_W267);


	not MGM_G330(MGM_W270,SI);


	and MGM_G331(ENABLE_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI,MGM_W270,MGM_W269);


	not MGM_G332(MGM_W271,D);


	and MGM_G333(MGM_W272,MGM_W271,CLK);


	and MGM_G334(MGM_W273,RN,MGM_W272);


	not MGM_G335(MGM_W274,SE);


	and MGM_G336(MGM_W275,MGM_W274,MGM_W273);


	and MGM_G337(ENABLE_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_SI,SI,MGM_W275);


	not MGM_G338(MGM_W276,D);


	and MGM_G339(MGM_W277,MGM_W276,CLK);


	and MGM_G340(MGM_W278,RN,MGM_W277);


	and MGM_G341(MGM_W279,SE,MGM_W278);


	not MGM_G342(MGM_W280,SI);


	and MGM_G343(ENABLE_CLK_AND_NOT_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W280,MGM_W279);


	not MGM_G344(MGM_W281,D);


	and MGM_G345(MGM_W282,MGM_W281,CLK);


	and MGM_G346(MGM_W283,RN,MGM_W282);


	and MGM_G347(MGM_W284,SE,MGM_W283);


	and MGM_G348(ENABLE_CLK_AND_NOT_D_AND_RN_AND_SE_AND_SI,SI,MGM_W284);


	and MGM_G349(MGM_W285,D,CLK);


	and MGM_G350(MGM_W286,RN,MGM_W285);


	not MGM_G351(MGM_W287,SE);


	and MGM_G352(MGM_W288,MGM_W287,MGM_W286);


	not MGM_G353(MGM_W289,SI);


	and MGM_G354(ENABLE_CLK_AND_D_AND_RN_AND_NOT_SE_AND_NOT_SI,MGM_W289,MGM_W288);


	and MGM_G355(MGM_W290,D,CLK);


	and MGM_G356(MGM_W291,RN,MGM_W290);


	not MGM_G357(MGM_W292,SE);


	and MGM_G358(MGM_W293,MGM_W292,MGM_W291);


	and MGM_G359(ENABLE_CLK_AND_D_AND_RN_AND_NOT_SE_AND_SI,SI,MGM_W293);


	and MGM_G360(MGM_W294,D,CLK);


	and MGM_G361(MGM_W295,RN,MGM_W294);


	and MGM_G362(MGM_W296,SE,MGM_W295);


	not MGM_G363(MGM_W297,SI);


	and MGM_G364(ENABLE_CLK_AND_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W297,MGM_W296);


	and MGM_G365(MGM_W298,D,CLK);


	and MGM_G366(MGM_W299,RN,MGM_W298);


	and MGM_G367(MGM_W300,SE,MGM_W299);


	and MGM_G368(ENABLE_CLK_AND_D_AND_RN_AND_SE_AND_SI,SI,MGM_W300);


	not MGM_G369(MGM_W301,D);


	and MGM_G370(MGM_W302,RN,MGM_W301);


	and MGM_G371(MGM_W303,SE,MGM_W302);


	and MGM_G372(ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN,SETN,MGM_W303);


	and MGM_G373(MGM_W304,RN,D);


	and MGM_G374(MGM_W305,SE,MGM_W304);


	and MGM_G375(ENABLE_D_AND_RN_AND_SE_AND_SETN,SETN,MGM_W305);


	// spec_gates_end



   specify

	// specify_block_begin

	if(D===1'b0 && SI===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SE))  = (1.0,1.0);

	if(SE===1'b0 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b0 && SI===1'b1 || D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SI))  = (1.0,1.0);

	ifnone
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),
		negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_D_AND_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_D_AND_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),
		negedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),
		posedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),
		negedge SE &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),
		posedge SE &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		negedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		posedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		negedge SI &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		posedge SI &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__SDFFRSNQ_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__SDFFRSNQ_2_V
`define GF180MCU_FD_SC_MCU9T5V0__SDFFRSNQ_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_2( SE, SI, D, CLK, SETN, RN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_2( SE, SI, D, CLK, SETN, RN, Q );
`endif // If not USE_POWER_PINS
input CLK, D, RN, SE, SETN, SI;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_func gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.SETN(SETN),.RN(RN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_func gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.SETN(SETN),.RN(RN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(MGM_W1,RN,MGM_W0);


	not MGM_G2(MGM_W2,SE);


	and MGM_G3(MGM_W3,MGM_W2,MGM_W1);


	and MGM_G4(MGM_W4,SETN,MGM_W3);


	not MGM_G5(MGM_W5,SI);


	and MGM_G6(ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W5,MGM_W4);


	not MGM_G7(MGM_W6,D);


	and MGM_G8(MGM_W7,RN,MGM_W6);


	not MGM_G9(MGM_W8,SE);


	and MGM_G10(MGM_W9,MGM_W8,MGM_W7);


	and MGM_G11(MGM_W10,SETN,MGM_W9);


	and MGM_G12(ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W10);


	not MGM_G13(MGM_W11,D);


	and MGM_G14(MGM_W12,RN,MGM_W11);


	and MGM_G15(MGM_W13,SE,MGM_W12);


	and MGM_G16(MGM_W14,SETN,MGM_W13);


	not MGM_G17(MGM_W15,SI);


	and MGM_G18(ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI,MGM_W15,MGM_W14);


	not MGM_G19(MGM_W16,D);


	and MGM_G20(MGM_W17,RN,MGM_W16);


	and MGM_G21(MGM_W18,SE,MGM_W17);


	and MGM_G22(MGM_W19,SETN,MGM_W18);


	and MGM_G23(ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_SI,SI,MGM_W19);


	and MGM_G24(MGM_W20,RN,D);


	not MGM_G25(MGM_W21,SE);


	and MGM_G26(MGM_W22,MGM_W21,MGM_W20);


	and MGM_G27(MGM_W23,SETN,MGM_W22);


	not MGM_G28(MGM_W24,SI);


	and MGM_G29(ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W24,MGM_W23);


	and MGM_G30(MGM_W25,RN,D);


	not MGM_G31(MGM_W26,SE);


	and MGM_G32(MGM_W27,MGM_W26,MGM_W25);


	and MGM_G33(MGM_W28,SETN,MGM_W27);


	and MGM_G34(ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W28);


	and MGM_G35(MGM_W29,RN,D);


	and MGM_G36(MGM_W30,SE,MGM_W29);


	and MGM_G37(MGM_W31,SETN,MGM_W30);


	not MGM_G38(MGM_W32,SI);


	and MGM_G39(ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI,MGM_W32,MGM_W31);


	and MGM_G40(MGM_W33,RN,D);


	and MGM_G41(MGM_W34,SE,MGM_W33);


	and MGM_G42(MGM_W35,SETN,MGM_W34);


	and MGM_G43(ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_SI,SI,MGM_W35);


	not MGM_G44(MGM_W36,SE);


	and MGM_G45(MGM_W37,MGM_W36,RN);


	and MGM_G46(MGM_W38,SETN,MGM_W37);


	not MGM_G47(MGM_W39,SI);


	and MGM_G48(ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W39,MGM_W38);


	not MGM_G49(MGM_W40,SE);


	and MGM_G50(MGM_W41,MGM_W40,RN);


	and MGM_G51(MGM_W42,SETN,MGM_W41);


	and MGM_G52(ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W42);


	not MGM_G53(MGM_W43,D);


	and MGM_G54(MGM_W44,SE,MGM_W43);


	and MGM_G55(MGM_W45,SETN,MGM_W44);


	and MGM_G56(ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W45);


	not MGM_G57(MGM_W46,SE);


	and MGM_G58(MGM_W47,MGM_W46,D);


	and MGM_G59(MGM_W48,SETN,MGM_W47);


	not MGM_G60(MGM_W49,SI);


	and MGM_G61(ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W49,MGM_W48);


	not MGM_G62(MGM_W50,SE);


	and MGM_G63(MGM_W51,MGM_W50,D);


	and MGM_G64(MGM_W52,SETN,MGM_W51);


	and MGM_G65(ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W52);


	and MGM_G66(MGM_W53,SE,D);


	and MGM_G67(MGM_W54,SETN,MGM_W53);


	and MGM_G68(ENABLE_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W54);


	not MGM_G69(MGM_W55,CLK);


	not MGM_G70(MGM_W56,D);


	and MGM_G71(MGM_W57,MGM_W56,MGM_W55);


	not MGM_G72(MGM_W58,SE);


	and MGM_G73(MGM_W59,MGM_W58,MGM_W57);


	and MGM_G74(MGM_W60,SETN,MGM_W59);


	not MGM_G75(MGM_W61,SI);


	and MGM_G76(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W61,MGM_W60);


	not MGM_G77(MGM_W62,CLK);


	not MGM_G78(MGM_W63,D);


	and MGM_G79(MGM_W64,MGM_W63,MGM_W62);


	not MGM_G80(MGM_W65,SE);


	and MGM_G81(MGM_W66,MGM_W65,MGM_W64);


	and MGM_G82(MGM_W67,SETN,MGM_W66);


	and MGM_G83(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W67);


	not MGM_G84(MGM_W68,CLK);


	not MGM_G85(MGM_W69,D);


	and MGM_G86(MGM_W70,MGM_W69,MGM_W68);


	and MGM_G87(MGM_W71,SE,MGM_W70);


	and MGM_G88(MGM_W72,SETN,MGM_W71);


	not MGM_G89(MGM_W73,SI);


	and MGM_G90(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_NOT_SI,MGM_W73,MGM_W72);


	not MGM_G91(MGM_W74,CLK);


	not MGM_G92(MGM_W75,D);


	and MGM_G93(MGM_W76,MGM_W75,MGM_W74);


	and MGM_G94(MGM_W77,SE,MGM_W76);


	and MGM_G95(MGM_W78,SETN,MGM_W77);


	and MGM_G96(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W78);


	not MGM_G97(MGM_W79,CLK);


	and MGM_G98(MGM_W80,D,MGM_W79);


	not MGM_G99(MGM_W81,SE);


	and MGM_G100(MGM_W82,MGM_W81,MGM_W80);


	and MGM_G101(MGM_W83,SETN,MGM_W82);


	not MGM_G102(MGM_W84,SI);


	and MGM_G103(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W84,MGM_W83);


	not MGM_G104(MGM_W85,CLK);


	and MGM_G105(MGM_W86,D,MGM_W85);


	not MGM_G106(MGM_W87,SE);


	and MGM_G107(MGM_W88,MGM_W87,MGM_W86);


	and MGM_G108(MGM_W89,SETN,MGM_W88);


	and MGM_G109(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W89);


	not MGM_G110(MGM_W90,CLK);


	and MGM_G111(MGM_W91,D,MGM_W90);


	and MGM_G112(MGM_W92,SE,MGM_W91);


	and MGM_G113(MGM_W93,SETN,MGM_W92);


	not MGM_G114(MGM_W94,SI);


	and MGM_G115(ENABLE_NOT_CLK_AND_D_AND_SE_AND_SETN_AND_NOT_SI,MGM_W94,MGM_W93);


	not MGM_G116(MGM_W95,CLK);


	and MGM_G117(MGM_W96,D,MGM_W95);


	and MGM_G118(MGM_W97,SE,MGM_W96);


	and MGM_G119(MGM_W98,SETN,MGM_W97);


	and MGM_G120(ENABLE_NOT_CLK_AND_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W98);


	not MGM_G121(MGM_W99,D);


	and MGM_G122(MGM_W100,MGM_W99,CLK);


	not MGM_G123(MGM_W101,SE);


	and MGM_G124(MGM_W102,MGM_W101,MGM_W100);


	and MGM_G125(MGM_W103,SETN,MGM_W102);


	not MGM_G126(MGM_W104,SI);


	and MGM_G127(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W104,MGM_W103);


	not MGM_G128(MGM_W105,D);


	and MGM_G129(MGM_W106,MGM_W105,CLK);


	not MGM_G130(MGM_W107,SE);


	and MGM_G131(MGM_W108,MGM_W107,MGM_W106);


	and MGM_G132(MGM_W109,SETN,MGM_W108);


	and MGM_G133(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W109);


	not MGM_G134(MGM_W110,D);


	and MGM_G135(MGM_W111,MGM_W110,CLK);


	and MGM_G136(MGM_W112,SE,MGM_W111);


	and MGM_G137(MGM_W113,SETN,MGM_W112);


	not MGM_G138(MGM_W114,SI);


	and MGM_G139(ENABLE_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_NOT_SI,MGM_W114,MGM_W113);


	not MGM_G140(MGM_W115,D);


	and MGM_G141(MGM_W116,MGM_W115,CLK);


	and MGM_G142(MGM_W117,SE,MGM_W116);


	and MGM_G143(MGM_W118,SETN,MGM_W117);


	and MGM_G144(ENABLE_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W118);


	and MGM_G145(MGM_W119,D,CLK);


	not MGM_G146(MGM_W120,SE);


	and MGM_G147(MGM_W121,MGM_W120,MGM_W119);


	and MGM_G148(MGM_W122,SETN,MGM_W121);


	not MGM_G149(MGM_W123,SI);


	and MGM_G150(ENABLE_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W123,MGM_W122);


	and MGM_G151(MGM_W124,D,CLK);


	not MGM_G152(MGM_W125,SE);


	and MGM_G153(MGM_W126,MGM_W125,MGM_W124);


	and MGM_G154(MGM_W127,SETN,MGM_W126);


	and MGM_G155(ENABLE_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W127);


	and MGM_G156(MGM_W128,D,CLK);


	and MGM_G157(MGM_W129,SE,MGM_W128);


	and MGM_G158(MGM_W130,SETN,MGM_W129);


	not MGM_G159(MGM_W131,SI);


	and MGM_G160(ENABLE_CLK_AND_D_AND_SE_AND_SETN_AND_NOT_SI,MGM_W131,MGM_W130);


	and MGM_G161(MGM_W132,D,CLK);


	and MGM_G162(MGM_W133,SE,MGM_W132);


	and MGM_G163(MGM_W134,SETN,MGM_W133);


	and MGM_G164(ENABLE_CLK_AND_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W134);


	not MGM_G165(MGM_W135,CLK);


	not MGM_G166(MGM_W136,D);


	and MGM_G167(MGM_W137,MGM_W136,MGM_W135);


	not MGM_G168(MGM_W138,SE);


	and MGM_G169(MGM_W139,MGM_W138,MGM_W137);


	not MGM_G170(MGM_W140,SI);


	and MGM_G171(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W140,MGM_W139);


	not MGM_G172(MGM_W141,CLK);


	not MGM_G173(MGM_W142,D);


	and MGM_G174(MGM_W143,MGM_W142,MGM_W141);


	not MGM_G175(MGM_W144,SE);


	and MGM_G176(MGM_W145,MGM_W144,MGM_W143);


	and MGM_G177(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W145);


	not MGM_G178(MGM_W146,CLK);


	not MGM_G179(MGM_W147,D);


	and MGM_G180(MGM_W148,MGM_W147,MGM_W146);


	and MGM_G181(MGM_W149,SE,MGM_W148);


	not MGM_G182(MGM_W150,SI);


	and MGM_G183(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI,MGM_W150,MGM_W149);


	not MGM_G184(MGM_W151,CLK);


	not MGM_G185(MGM_W152,D);


	and MGM_G186(MGM_W153,MGM_W152,MGM_W151);


	and MGM_G187(MGM_W154,SE,MGM_W153);


	and MGM_G188(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI,SI,MGM_W154);


	not MGM_G189(MGM_W155,CLK);


	and MGM_G190(MGM_W156,D,MGM_W155);


	not MGM_G191(MGM_W157,SE);


	and MGM_G192(MGM_W158,MGM_W157,MGM_W156);


	not MGM_G193(MGM_W159,SI);


	and MGM_G194(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI,MGM_W159,MGM_W158);


	not MGM_G195(MGM_W160,CLK);


	and MGM_G196(MGM_W161,D,MGM_W160);


	not MGM_G197(MGM_W162,SE);


	and MGM_G198(MGM_W163,MGM_W162,MGM_W161);


	and MGM_G199(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI,SI,MGM_W163);


	not MGM_G200(MGM_W164,CLK);


	and MGM_G201(MGM_W165,D,MGM_W164);


	and MGM_G202(MGM_W166,SE,MGM_W165);


	not MGM_G203(MGM_W167,SI);


	and MGM_G204(ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI,MGM_W167,MGM_W166);


	not MGM_G205(MGM_W168,CLK);


	and MGM_G206(MGM_W169,D,MGM_W168);


	and MGM_G207(MGM_W170,SE,MGM_W169);


	and MGM_G208(ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI,SI,MGM_W170);


	not MGM_G209(MGM_W171,D);


	and MGM_G210(MGM_W172,MGM_W171,CLK);


	not MGM_G211(MGM_W173,SE);


	and MGM_G212(MGM_W174,MGM_W173,MGM_W172);


	not MGM_G213(MGM_W175,SI);


	and MGM_G214(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W175,MGM_W174);


	not MGM_G215(MGM_W176,D);


	and MGM_G216(MGM_W177,MGM_W176,CLK);


	not MGM_G217(MGM_W178,SE);


	and MGM_G218(MGM_W179,MGM_W178,MGM_W177);


	and MGM_G219(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W179);


	not MGM_G220(MGM_W180,D);


	and MGM_G221(MGM_W181,MGM_W180,CLK);


	and MGM_G222(MGM_W182,SE,MGM_W181);


	not MGM_G223(MGM_W183,SI);


	and MGM_G224(ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI,MGM_W183,MGM_W182);


	not MGM_G225(MGM_W184,D);


	and MGM_G226(MGM_W185,MGM_W184,CLK);


	and MGM_G227(MGM_W186,SE,MGM_W185);


	and MGM_G228(ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI,SI,MGM_W186);


	and MGM_G229(MGM_W187,D,CLK);


	not MGM_G230(MGM_W188,SE);


	and MGM_G231(MGM_W189,MGM_W188,MGM_W187);


	not MGM_G232(MGM_W190,SI);


	and MGM_G233(ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI,MGM_W190,MGM_W189);


	and MGM_G234(MGM_W191,D,CLK);


	not MGM_G235(MGM_W192,SE);


	and MGM_G236(MGM_W193,MGM_W192,MGM_W191);


	and MGM_G237(ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI,SI,MGM_W193);


	and MGM_G238(MGM_W194,D,CLK);


	and MGM_G239(MGM_W195,SE,MGM_W194);


	not MGM_G240(MGM_W196,SI);


	and MGM_G241(ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI,MGM_W196,MGM_W195);


	and MGM_G242(MGM_W197,D,CLK);


	and MGM_G243(MGM_W198,SE,MGM_W197);


	and MGM_G244(ENABLE_CLK_AND_D_AND_SE_AND_SI,SI,MGM_W198);


	not MGM_G245(MGM_W199,D);


	and MGM_G246(MGM_W200,RN,MGM_W199);


	and MGM_G247(MGM_W201,SETN,MGM_W200);


	and MGM_G248(ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI,SI,MGM_W201);


	and MGM_G249(MGM_W202,RN,D);


	and MGM_G250(MGM_W203,SETN,MGM_W202);


	not MGM_G251(MGM_W204,SI);


	and MGM_G252(ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI,MGM_W204,MGM_W203);


	not MGM_G253(MGM_W205,D);


	and MGM_G254(MGM_W206,RN,MGM_W205);


	not MGM_G255(MGM_W207,SE);


	and MGM_G256(MGM_W208,MGM_W207,MGM_W206);


	not MGM_G257(MGM_W209,SI);


	and MGM_G258(ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI,MGM_W209,MGM_W208);


	not MGM_G259(MGM_W210,D);


	and MGM_G260(MGM_W211,RN,MGM_W210);


	not MGM_G261(MGM_W212,SE);


	and MGM_G262(MGM_W213,MGM_W212,MGM_W211);


	and MGM_G263(ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI,SI,MGM_W213);


	not MGM_G264(MGM_W214,D);


	and MGM_G265(MGM_W215,RN,MGM_W214);


	and MGM_G266(MGM_W216,SE,MGM_W215);


	not MGM_G267(MGM_W217,SI);


	and MGM_G268(ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W217,MGM_W216);


	and MGM_G269(MGM_W218,RN,D);


	and MGM_G270(MGM_W219,SE,MGM_W218);


	not MGM_G271(MGM_W220,SI);


	and MGM_G272(ENABLE_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W220,MGM_W219);


	not MGM_G273(MGM_W221,CLK);


	not MGM_G274(MGM_W222,D);


	and MGM_G275(MGM_W223,MGM_W222,MGM_W221);


	and MGM_G276(MGM_W224,RN,MGM_W223);


	not MGM_G277(MGM_W225,SE);


	and MGM_G278(MGM_W226,MGM_W225,MGM_W224);


	not MGM_G279(MGM_W227,SI);


	and MGM_G280(ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI,MGM_W227,MGM_W226);


	not MGM_G281(MGM_W228,CLK);


	not MGM_G282(MGM_W229,D);


	and MGM_G283(MGM_W230,MGM_W229,MGM_W228);


	and MGM_G284(MGM_W231,RN,MGM_W230);


	not MGM_G285(MGM_W232,SE);


	and MGM_G286(MGM_W233,MGM_W232,MGM_W231);


	and MGM_G287(ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_SI,SI,MGM_W233);


	not MGM_G288(MGM_W234,CLK);


	not MGM_G289(MGM_W235,D);


	and MGM_G290(MGM_W236,MGM_W235,MGM_W234);


	and MGM_G291(MGM_W237,RN,MGM_W236);


	and MGM_G292(MGM_W238,SE,MGM_W237);


	not MGM_G293(MGM_W239,SI);


	and MGM_G294(ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W239,MGM_W238);


	not MGM_G295(MGM_W240,CLK);


	not MGM_G296(MGM_W241,D);


	and MGM_G297(MGM_W242,MGM_W241,MGM_W240);


	and MGM_G298(MGM_W243,RN,MGM_W242);


	and MGM_G299(MGM_W244,SE,MGM_W243);


	and MGM_G300(ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_SE_AND_SI,SI,MGM_W244);


	not MGM_G301(MGM_W245,CLK);


	and MGM_G302(MGM_W246,D,MGM_W245);


	and MGM_G303(MGM_W247,RN,MGM_W246);


	not MGM_G304(MGM_W248,SE);


	and MGM_G305(MGM_W249,MGM_W248,MGM_W247);


	not MGM_G306(MGM_W250,SI);


	and MGM_G307(ENABLE_NOT_CLK_AND_D_AND_RN_AND_NOT_SE_AND_NOT_SI,MGM_W250,MGM_W249);


	not MGM_G308(MGM_W251,CLK);


	and MGM_G309(MGM_W252,D,MGM_W251);


	and MGM_G310(MGM_W253,RN,MGM_W252);


	not MGM_G311(MGM_W254,SE);


	and MGM_G312(MGM_W255,MGM_W254,MGM_W253);


	and MGM_G313(ENABLE_NOT_CLK_AND_D_AND_RN_AND_NOT_SE_AND_SI,SI,MGM_W255);


	not MGM_G314(MGM_W256,CLK);


	and MGM_G315(MGM_W257,D,MGM_W256);


	and MGM_G316(MGM_W258,RN,MGM_W257);


	and MGM_G317(MGM_W259,SE,MGM_W258);


	not MGM_G318(MGM_W260,SI);


	and MGM_G319(ENABLE_NOT_CLK_AND_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W260,MGM_W259);


	not MGM_G320(MGM_W261,CLK);


	and MGM_G321(MGM_W262,D,MGM_W261);


	and MGM_G322(MGM_W263,RN,MGM_W262);


	and MGM_G323(MGM_W264,SE,MGM_W263);


	and MGM_G324(ENABLE_NOT_CLK_AND_D_AND_RN_AND_SE_AND_SI,SI,MGM_W264);


	not MGM_G325(MGM_W265,D);


	and MGM_G326(MGM_W266,MGM_W265,CLK);


	and MGM_G327(MGM_W267,RN,MGM_W266);


	not MGM_G328(MGM_W268,SE);


	and MGM_G329(MGM_W269,MGM_W268,MGM_W267);


	not MGM_G330(MGM_W270,SI);


	and MGM_G331(ENABLE_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI,MGM_W270,MGM_W269);


	not MGM_G332(MGM_W271,D);


	and MGM_G333(MGM_W272,MGM_W271,CLK);


	and MGM_G334(MGM_W273,RN,MGM_W272);


	not MGM_G335(MGM_W274,SE);


	and MGM_G336(MGM_W275,MGM_W274,MGM_W273);


	and MGM_G337(ENABLE_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_SI,SI,MGM_W275);


	not MGM_G338(MGM_W276,D);


	and MGM_G339(MGM_W277,MGM_W276,CLK);


	and MGM_G340(MGM_W278,RN,MGM_W277);


	and MGM_G341(MGM_W279,SE,MGM_W278);


	not MGM_G342(MGM_W280,SI);


	and MGM_G343(ENABLE_CLK_AND_NOT_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W280,MGM_W279);


	not MGM_G344(MGM_W281,D);


	and MGM_G345(MGM_W282,MGM_W281,CLK);


	and MGM_G346(MGM_W283,RN,MGM_W282);


	and MGM_G347(MGM_W284,SE,MGM_W283);


	and MGM_G348(ENABLE_CLK_AND_NOT_D_AND_RN_AND_SE_AND_SI,SI,MGM_W284);


	and MGM_G349(MGM_W285,D,CLK);


	and MGM_G350(MGM_W286,RN,MGM_W285);


	not MGM_G351(MGM_W287,SE);


	and MGM_G352(MGM_W288,MGM_W287,MGM_W286);


	not MGM_G353(MGM_W289,SI);


	and MGM_G354(ENABLE_CLK_AND_D_AND_RN_AND_NOT_SE_AND_NOT_SI,MGM_W289,MGM_W288);


	and MGM_G355(MGM_W290,D,CLK);


	and MGM_G356(MGM_W291,RN,MGM_W290);


	not MGM_G357(MGM_W292,SE);


	and MGM_G358(MGM_W293,MGM_W292,MGM_W291);


	and MGM_G359(ENABLE_CLK_AND_D_AND_RN_AND_NOT_SE_AND_SI,SI,MGM_W293);


	and MGM_G360(MGM_W294,D,CLK);


	and MGM_G361(MGM_W295,RN,MGM_W294);


	and MGM_G362(MGM_W296,SE,MGM_W295);


	not MGM_G363(MGM_W297,SI);


	and MGM_G364(ENABLE_CLK_AND_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W297,MGM_W296);


	and MGM_G365(MGM_W298,D,CLK);


	and MGM_G366(MGM_W299,RN,MGM_W298);


	and MGM_G367(MGM_W300,SE,MGM_W299);


	and MGM_G368(ENABLE_CLK_AND_D_AND_RN_AND_SE_AND_SI,SI,MGM_W300);


	not MGM_G369(MGM_W301,D);


	and MGM_G370(MGM_W302,RN,MGM_W301);


	and MGM_G371(MGM_W303,SE,MGM_W302);


	and MGM_G372(ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN,SETN,MGM_W303);


	and MGM_G373(MGM_W304,RN,D);


	and MGM_G374(MGM_W305,SE,MGM_W304);


	and MGM_G375(ENABLE_D_AND_RN_AND_SE_AND_SETN,SETN,MGM_W305);


	// spec_gates_end



   specify

	// specify_block_begin

	if(D===1'b0 && SI===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SE))  = (1.0,1.0);

	if(SE===1'b0 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b0 && SI===1'b1 || D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SI))  = (1.0,1.0);

	ifnone
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),
		negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_D_AND_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_D_AND_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),
		negedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),
		posedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),
		negedge SE &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),
		posedge SE &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		negedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		posedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		negedge SI &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		posedge SI &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__SDFFRSNQ_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__SDFFRSNQ_4_V
`define GF180MCU_FD_SC_MCU9T5V0__SDFFRSNQ_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_4( SE, SI, D, CLK, SETN, RN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_4( SE, SI, D, CLK, SETN, RN, Q );
`endif // If not USE_POWER_PINS
input CLK, D, RN, SE, SETN, SI;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_func gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.SETN(SETN),.RN(RN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_func gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.SETN(SETN),.RN(RN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	and MGM_G1(MGM_W1,RN,MGM_W0);


	not MGM_G2(MGM_W2,SE);


	and MGM_G3(MGM_W3,MGM_W2,MGM_W1);


	and MGM_G4(MGM_W4,SETN,MGM_W3);


	not MGM_G5(MGM_W5,SI);


	and MGM_G6(ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W5,MGM_W4);


	not MGM_G7(MGM_W6,D);


	and MGM_G8(MGM_W7,RN,MGM_W6);


	not MGM_G9(MGM_W8,SE);


	and MGM_G10(MGM_W9,MGM_W8,MGM_W7);


	and MGM_G11(MGM_W10,SETN,MGM_W9);


	and MGM_G12(ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W10);


	not MGM_G13(MGM_W11,D);


	and MGM_G14(MGM_W12,RN,MGM_W11);


	and MGM_G15(MGM_W13,SE,MGM_W12);


	and MGM_G16(MGM_W14,SETN,MGM_W13);


	not MGM_G17(MGM_W15,SI);


	and MGM_G18(ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI,MGM_W15,MGM_W14);


	not MGM_G19(MGM_W16,D);


	and MGM_G20(MGM_W17,RN,MGM_W16);


	and MGM_G21(MGM_W18,SE,MGM_W17);


	and MGM_G22(MGM_W19,SETN,MGM_W18);


	and MGM_G23(ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_SI,SI,MGM_W19);


	and MGM_G24(MGM_W20,RN,D);


	not MGM_G25(MGM_W21,SE);


	and MGM_G26(MGM_W22,MGM_W21,MGM_W20);


	and MGM_G27(MGM_W23,SETN,MGM_W22);


	not MGM_G28(MGM_W24,SI);


	and MGM_G29(ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W24,MGM_W23);


	and MGM_G30(MGM_W25,RN,D);


	not MGM_G31(MGM_W26,SE);


	and MGM_G32(MGM_W27,MGM_W26,MGM_W25);


	and MGM_G33(MGM_W28,SETN,MGM_W27);


	and MGM_G34(ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W28);


	and MGM_G35(MGM_W29,RN,D);


	and MGM_G36(MGM_W30,SE,MGM_W29);


	and MGM_G37(MGM_W31,SETN,MGM_W30);


	not MGM_G38(MGM_W32,SI);


	and MGM_G39(ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI,MGM_W32,MGM_W31);


	and MGM_G40(MGM_W33,RN,D);


	and MGM_G41(MGM_W34,SE,MGM_W33);


	and MGM_G42(MGM_W35,SETN,MGM_W34);


	and MGM_G43(ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_SI,SI,MGM_W35);


	not MGM_G44(MGM_W36,SE);


	and MGM_G45(MGM_W37,MGM_W36,RN);


	and MGM_G46(MGM_W38,SETN,MGM_W37);


	not MGM_G47(MGM_W39,SI);


	and MGM_G48(ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W39,MGM_W38);


	not MGM_G49(MGM_W40,SE);


	and MGM_G50(MGM_W41,MGM_W40,RN);


	and MGM_G51(MGM_W42,SETN,MGM_W41);


	and MGM_G52(ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W42);


	not MGM_G53(MGM_W43,D);


	and MGM_G54(MGM_W44,SE,MGM_W43);


	and MGM_G55(MGM_W45,SETN,MGM_W44);


	and MGM_G56(ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W45);


	not MGM_G57(MGM_W46,SE);


	and MGM_G58(MGM_W47,MGM_W46,D);


	and MGM_G59(MGM_W48,SETN,MGM_W47);


	not MGM_G60(MGM_W49,SI);


	and MGM_G61(ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W49,MGM_W48);


	not MGM_G62(MGM_W50,SE);


	and MGM_G63(MGM_W51,MGM_W50,D);


	and MGM_G64(MGM_W52,SETN,MGM_W51);


	and MGM_G65(ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W52);


	and MGM_G66(MGM_W53,SE,D);


	and MGM_G67(MGM_W54,SETN,MGM_W53);


	and MGM_G68(ENABLE_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W54);


	not MGM_G69(MGM_W55,CLK);


	not MGM_G70(MGM_W56,D);


	and MGM_G71(MGM_W57,MGM_W56,MGM_W55);


	not MGM_G72(MGM_W58,SE);


	and MGM_G73(MGM_W59,MGM_W58,MGM_W57);


	and MGM_G74(MGM_W60,SETN,MGM_W59);


	not MGM_G75(MGM_W61,SI);


	and MGM_G76(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W61,MGM_W60);


	not MGM_G77(MGM_W62,CLK);


	not MGM_G78(MGM_W63,D);


	and MGM_G79(MGM_W64,MGM_W63,MGM_W62);


	not MGM_G80(MGM_W65,SE);


	and MGM_G81(MGM_W66,MGM_W65,MGM_W64);


	and MGM_G82(MGM_W67,SETN,MGM_W66);


	and MGM_G83(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W67);


	not MGM_G84(MGM_W68,CLK);


	not MGM_G85(MGM_W69,D);


	and MGM_G86(MGM_W70,MGM_W69,MGM_W68);


	and MGM_G87(MGM_W71,SE,MGM_W70);


	and MGM_G88(MGM_W72,SETN,MGM_W71);


	not MGM_G89(MGM_W73,SI);


	and MGM_G90(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_NOT_SI,MGM_W73,MGM_W72);


	not MGM_G91(MGM_W74,CLK);


	not MGM_G92(MGM_W75,D);


	and MGM_G93(MGM_W76,MGM_W75,MGM_W74);


	and MGM_G94(MGM_W77,SE,MGM_W76);


	and MGM_G95(MGM_W78,SETN,MGM_W77);


	and MGM_G96(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W78);


	not MGM_G97(MGM_W79,CLK);


	and MGM_G98(MGM_W80,D,MGM_W79);


	not MGM_G99(MGM_W81,SE);


	and MGM_G100(MGM_W82,MGM_W81,MGM_W80);


	and MGM_G101(MGM_W83,SETN,MGM_W82);


	not MGM_G102(MGM_W84,SI);


	and MGM_G103(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W84,MGM_W83);


	not MGM_G104(MGM_W85,CLK);


	and MGM_G105(MGM_W86,D,MGM_W85);


	not MGM_G106(MGM_W87,SE);


	and MGM_G107(MGM_W88,MGM_W87,MGM_W86);


	and MGM_G108(MGM_W89,SETN,MGM_W88);


	and MGM_G109(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W89);


	not MGM_G110(MGM_W90,CLK);


	and MGM_G111(MGM_W91,D,MGM_W90);


	and MGM_G112(MGM_W92,SE,MGM_W91);


	and MGM_G113(MGM_W93,SETN,MGM_W92);


	not MGM_G114(MGM_W94,SI);


	and MGM_G115(ENABLE_NOT_CLK_AND_D_AND_SE_AND_SETN_AND_NOT_SI,MGM_W94,MGM_W93);


	not MGM_G116(MGM_W95,CLK);


	and MGM_G117(MGM_W96,D,MGM_W95);


	and MGM_G118(MGM_W97,SE,MGM_W96);


	and MGM_G119(MGM_W98,SETN,MGM_W97);


	and MGM_G120(ENABLE_NOT_CLK_AND_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W98);


	not MGM_G121(MGM_W99,D);


	and MGM_G122(MGM_W100,MGM_W99,CLK);


	not MGM_G123(MGM_W101,SE);


	and MGM_G124(MGM_W102,MGM_W101,MGM_W100);


	and MGM_G125(MGM_W103,SETN,MGM_W102);


	not MGM_G126(MGM_W104,SI);


	and MGM_G127(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W104,MGM_W103);


	not MGM_G128(MGM_W105,D);


	and MGM_G129(MGM_W106,MGM_W105,CLK);


	not MGM_G130(MGM_W107,SE);


	and MGM_G131(MGM_W108,MGM_W107,MGM_W106);


	and MGM_G132(MGM_W109,SETN,MGM_W108);


	and MGM_G133(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W109);


	not MGM_G134(MGM_W110,D);


	and MGM_G135(MGM_W111,MGM_W110,CLK);


	and MGM_G136(MGM_W112,SE,MGM_W111);


	and MGM_G137(MGM_W113,SETN,MGM_W112);


	not MGM_G138(MGM_W114,SI);


	and MGM_G139(ENABLE_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_NOT_SI,MGM_W114,MGM_W113);


	not MGM_G140(MGM_W115,D);


	and MGM_G141(MGM_W116,MGM_W115,CLK);


	and MGM_G142(MGM_W117,SE,MGM_W116);


	and MGM_G143(MGM_W118,SETN,MGM_W117);


	and MGM_G144(ENABLE_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W118);


	and MGM_G145(MGM_W119,D,CLK);


	not MGM_G146(MGM_W120,SE);


	and MGM_G147(MGM_W121,MGM_W120,MGM_W119);


	and MGM_G148(MGM_W122,SETN,MGM_W121);


	not MGM_G149(MGM_W123,SI);


	and MGM_G150(ENABLE_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W123,MGM_W122);


	and MGM_G151(MGM_W124,D,CLK);


	not MGM_G152(MGM_W125,SE);


	and MGM_G153(MGM_W126,MGM_W125,MGM_W124);


	and MGM_G154(MGM_W127,SETN,MGM_W126);


	and MGM_G155(ENABLE_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W127);


	and MGM_G156(MGM_W128,D,CLK);


	and MGM_G157(MGM_W129,SE,MGM_W128);


	and MGM_G158(MGM_W130,SETN,MGM_W129);


	not MGM_G159(MGM_W131,SI);


	and MGM_G160(ENABLE_CLK_AND_D_AND_SE_AND_SETN_AND_NOT_SI,MGM_W131,MGM_W130);


	and MGM_G161(MGM_W132,D,CLK);


	and MGM_G162(MGM_W133,SE,MGM_W132);


	and MGM_G163(MGM_W134,SETN,MGM_W133);


	and MGM_G164(ENABLE_CLK_AND_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W134);


	not MGM_G165(MGM_W135,CLK);


	not MGM_G166(MGM_W136,D);


	and MGM_G167(MGM_W137,MGM_W136,MGM_W135);


	not MGM_G168(MGM_W138,SE);


	and MGM_G169(MGM_W139,MGM_W138,MGM_W137);


	not MGM_G170(MGM_W140,SI);


	and MGM_G171(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W140,MGM_W139);


	not MGM_G172(MGM_W141,CLK);


	not MGM_G173(MGM_W142,D);


	and MGM_G174(MGM_W143,MGM_W142,MGM_W141);


	not MGM_G175(MGM_W144,SE);


	and MGM_G176(MGM_W145,MGM_W144,MGM_W143);


	and MGM_G177(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W145);


	not MGM_G178(MGM_W146,CLK);


	not MGM_G179(MGM_W147,D);


	and MGM_G180(MGM_W148,MGM_W147,MGM_W146);


	and MGM_G181(MGM_W149,SE,MGM_W148);


	not MGM_G182(MGM_W150,SI);


	and MGM_G183(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI,MGM_W150,MGM_W149);


	not MGM_G184(MGM_W151,CLK);


	not MGM_G185(MGM_W152,D);


	and MGM_G186(MGM_W153,MGM_W152,MGM_W151);


	and MGM_G187(MGM_W154,SE,MGM_W153);


	and MGM_G188(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI,SI,MGM_W154);


	not MGM_G189(MGM_W155,CLK);


	and MGM_G190(MGM_W156,D,MGM_W155);


	not MGM_G191(MGM_W157,SE);


	and MGM_G192(MGM_W158,MGM_W157,MGM_W156);


	not MGM_G193(MGM_W159,SI);


	and MGM_G194(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI,MGM_W159,MGM_W158);


	not MGM_G195(MGM_W160,CLK);


	and MGM_G196(MGM_W161,D,MGM_W160);


	not MGM_G197(MGM_W162,SE);


	and MGM_G198(MGM_W163,MGM_W162,MGM_W161);


	and MGM_G199(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI,SI,MGM_W163);


	not MGM_G200(MGM_W164,CLK);


	and MGM_G201(MGM_W165,D,MGM_W164);


	and MGM_G202(MGM_W166,SE,MGM_W165);


	not MGM_G203(MGM_W167,SI);


	and MGM_G204(ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI,MGM_W167,MGM_W166);


	not MGM_G205(MGM_W168,CLK);


	and MGM_G206(MGM_W169,D,MGM_W168);


	and MGM_G207(MGM_W170,SE,MGM_W169);


	and MGM_G208(ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI,SI,MGM_W170);


	not MGM_G209(MGM_W171,D);


	and MGM_G210(MGM_W172,MGM_W171,CLK);


	not MGM_G211(MGM_W173,SE);


	and MGM_G212(MGM_W174,MGM_W173,MGM_W172);


	not MGM_G213(MGM_W175,SI);


	and MGM_G214(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W175,MGM_W174);


	not MGM_G215(MGM_W176,D);


	and MGM_G216(MGM_W177,MGM_W176,CLK);


	not MGM_G217(MGM_W178,SE);


	and MGM_G218(MGM_W179,MGM_W178,MGM_W177);


	and MGM_G219(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W179);


	not MGM_G220(MGM_W180,D);


	and MGM_G221(MGM_W181,MGM_W180,CLK);


	and MGM_G222(MGM_W182,SE,MGM_W181);


	not MGM_G223(MGM_W183,SI);


	and MGM_G224(ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI,MGM_W183,MGM_W182);


	not MGM_G225(MGM_W184,D);


	and MGM_G226(MGM_W185,MGM_W184,CLK);


	and MGM_G227(MGM_W186,SE,MGM_W185);


	and MGM_G228(ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI,SI,MGM_W186);


	and MGM_G229(MGM_W187,D,CLK);


	not MGM_G230(MGM_W188,SE);


	and MGM_G231(MGM_W189,MGM_W188,MGM_W187);


	not MGM_G232(MGM_W190,SI);


	and MGM_G233(ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI,MGM_W190,MGM_W189);


	and MGM_G234(MGM_W191,D,CLK);


	not MGM_G235(MGM_W192,SE);


	and MGM_G236(MGM_W193,MGM_W192,MGM_W191);


	and MGM_G237(ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI,SI,MGM_W193);


	and MGM_G238(MGM_W194,D,CLK);


	and MGM_G239(MGM_W195,SE,MGM_W194);


	not MGM_G240(MGM_W196,SI);


	and MGM_G241(ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI,MGM_W196,MGM_W195);


	and MGM_G242(MGM_W197,D,CLK);


	and MGM_G243(MGM_W198,SE,MGM_W197);


	and MGM_G244(ENABLE_CLK_AND_D_AND_SE_AND_SI,SI,MGM_W198);


	not MGM_G245(MGM_W199,D);


	and MGM_G246(MGM_W200,RN,MGM_W199);


	and MGM_G247(MGM_W201,SETN,MGM_W200);


	and MGM_G248(ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI,SI,MGM_W201);


	and MGM_G249(MGM_W202,RN,D);


	and MGM_G250(MGM_W203,SETN,MGM_W202);


	not MGM_G251(MGM_W204,SI);


	and MGM_G252(ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI,MGM_W204,MGM_W203);


	not MGM_G253(MGM_W205,D);


	and MGM_G254(MGM_W206,RN,MGM_W205);


	not MGM_G255(MGM_W207,SE);


	and MGM_G256(MGM_W208,MGM_W207,MGM_W206);


	not MGM_G257(MGM_W209,SI);


	and MGM_G258(ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI,MGM_W209,MGM_W208);


	not MGM_G259(MGM_W210,D);


	and MGM_G260(MGM_W211,RN,MGM_W210);


	not MGM_G261(MGM_W212,SE);


	and MGM_G262(MGM_W213,MGM_W212,MGM_W211);


	and MGM_G263(ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI,SI,MGM_W213);


	not MGM_G264(MGM_W214,D);


	and MGM_G265(MGM_W215,RN,MGM_W214);


	and MGM_G266(MGM_W216,SE,MGM_W215);


	not MGM_G267(MGM_W217,SI);


	and MGM_G268(ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W217,MGM_W216);


	and MGM_G269(MGM_W218,RN,D);


	and MGM_G270(MGM_W219,SE,MGM_W218);


	not MGM_G271(MGM_W220,SI);


	and MGM_G272(ENABLE_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W220,MGM_W219);


	not MGM_G273(MGM_W221,CLK);


	not MGM_G274(MGM_W222,D);


	and MGM_G275(MGM_W223,MGM_W222,MGM_W221);


	and MGM_G276(MGM_W224,RN,MGM_W223);


	not MGM_G277(MGM_W225,SE);


	and MGM_G278(MGM_W226,MGM_W225,MGM_W224);


	not MGM_G279(MGM_W227,SI);


	and MGM_G280(ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI,MGM_W227,MGM_W226);


	not MGM_G281(MGM_W228,CLK);


	not MGM_G282(MGM_W229,D);


	and MGM_G283(MGM_W230,MGM_W229,MGM_W228);


	and MGM_G284(MGM_W231,RN,MGM_W230);


	not MGM_G285(MGM_W232,SE);


	and MGM_G286(MGM_W233,MGM_W232,MGM_W231);


	and MGM_G287(ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_SI,SI,MGM_W233);


	not MGM_G288(MGM_W234,CLK);


	not MGM_G289(MGM_W235,D);


	and MGM_G290(MGM_W236,MGM_W235,MGM_W234);


	and MGM_G291(MGM_W237,RN,MGM_W236);


	and MGM_G292(MGM_W238,SE,MGM_W237);


	not MGM_G293(MGM_W239,SI);


	and MGM_G294(ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W239,MGM_W238);


	not MGM_G295(MGM_W240,CLK);


	not MGM_G296(MGM_W241,D);


	and MGM_G297(MGM_W242,MGM_W241,MGM_W240);


	and MGM_G298(MGM_W243,RN,MGM_W242);


	and MGM_G299(MGM_W244,SE,MGM_W243);


	and MGM_G300(ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_SE_AND_SI,SI,MGM_W244);


	not MGM_G301(MGM_W245,CLK);


	and MGM_G302(MGM_W246,D,MGM_W245);


	and MGM_G303(MGM_W247,RN,MGM_W246);


	not MGM_G304(MGM_W248,SE);


	and MGM_G305(MGM_W249,MGM_W248,MGM_W247);


	not MGM_G306(MGM_W250,SI);


	and MGM_G307(ENABLE_NOT_CLK_AND_D_AND_RN_AND_NOT_SE_AND_NOT_SI,MGM_W250,MGM_W249);


	not MGM_G308(MGM_W251,CLK);


	and MGM_G309(MGM_W252,D,MGM_W251);


	and MGM_G310(MGM_W253,RN,MGM_W252);


	not MGM_G311(MGM_W254,SE);


	and MGM_G312(MGM_W255,MGM_W254,MGM_W253);


	and MGM_G313(ENABLE_NOT_CLK_AND_D_AND_RN_AND_NOT_SE_AND_SI,SI,MGM_W255);


	not MGM_G314(MGM_W256,CLK);


	and MGM_G315(MGM_W257,D,MGM_W256);


	and MGM_G316(MGM_W258,RN,MGM_W257);


	and MGM_G317(MGM_W259,SE,MGM_W258);


	not MGM_G318(MGM_W260,SI);


	and MGM_G319(ENABLE_NOT_CLK_AND_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W260,MGM_W259);


	not MGM_G320(MGM_W261,CLK);


	and MGM_G321(MGM_W262,D,MGM_W261);


	and MGM_G322(MGM_W263,RN,MGM_W262);


	and MGM_G323(MGM_W264,SE,MGM_W263);


	and MGM_G324(ENABLE_NOT_CLK_AND_D_AND_RN_AND_SE_AND_SI,SI,MGM_W264);


	not MGM_G325(MGM_W265,D);


	and MGM_G326(MGM_W266,MGM_W265,CLK);


	and MGM_G327(MGM_W267,RN,MGM_W266);


	not MGM_G328(MGM_W268,SE);


	and MGM_G329(MGM_W269,MGM_W268,MGM_W267);


	not MGM_G330(MGM_W270,SI);


	and MGM_G331(ENABLE_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI,MGM_W270,MGM_W269);


	not MGM_G332(MGM_W271,D);


	and MGM_G333(MGM_W272,MGM_W271,CLK);


	and MGM_G334(MGM_W273,RN,MGM_W272);


	not MGM_G335(MGM_W274,SE);


	and MGM_G336(MGM_W275,MGM_W274,MGM_W273);


	and MGM_G337(ENABLE_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_SI,SI,MGM_W275);


	not MGM_G338(MGM_W276,D);


	and MGM_G339(MGM_W277,MGM_W276,CLK);


	and MGM_G340(MGM_W278,RN,MGM_W277);


	and MGM_G341(MGM_W279,SE,MGM_W278);


	not MGM_G342(MGM_W280,SI);


	and MGM_G343(ENABLE_CLK_AND_NOT_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W280,MGM_W279);


	not MGM_G344(MGM_W281,D);


	and MGM_G345(MGM_W282,MGM_W281,CLK);


	and MGM_G346(MGM_W283,RN,MGM_W282);


	and MGM_G347(MGM_W284,SE,MGM_W283);


	and MGM_G348(ENABLE_CLK_AND_NOT_D_AND_RN_AND_SE_AND_SI,SI,MGM_W284);


	and MGM_G349(MGM_W285,D,CLK);


	and MGM_G350(MGM_W286,RN,MGM_W285);


	not MGM_G351(MGM_W287,SE);


	and MGM_G352(MGM_W288,MGM_W287,MGM_W286);


	not MGM_G353(MGM_W289,SI);


	and MGM_G354(ENABLE_CLK_AND_D_AND_RN_AND_NOT_SE_AND_NOT_SI,MGM_W289,MGM_W288);


	and MGM_G355(MGM_W290,D,CLK);


	and MGM_G356(MGM_W291,RN,MGM_W290);


	not MGM_G357(MGM_W292,SE);


	and MGM_G358(MGM_W293,MGM_W292,MGM_W291);


	and MGM_G359(ENABLE_CLK_AND_D_AND_RN_AND_NOT_SE_AND_SI,SI,MGM_W293);


	and MGM_G360(MGM_W294,D,CLK);


	and MGM_G361(MGM_W295,RN,MGM_W294);


	and MGM_G362(MGM_W296,SE,MGM_W295);


	not MGM_G363(MGM_W297,SI);


	and MGM_G364(ENABLE_CLK_AND_D_AND_RN_AND_SE_AND_NOT_SI,MGM_W297,MGM_W296);


	and MGM_G365(MGM_W298,D,CLK);


	and MGM_G366(MGM_W299,RN,MGM_W298);


	and MGM_G367(MGM_W300,SE,MGM_W299);


	and MGM_G368(ENABLE_CLK_AND_D_AND_RN_AND_SE_AND_SI,SI,MGM_W300);


	not MGM_G369(MGM_W301,D);


	and MGM_G370(MGM_W302,RN,MGM_W301);


	and MGM_G371(MGM_W303,SE,MGM_W302);


	and MGM_G372(ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN,SETN,MGM_W303);


	and MGM_G373(MGM_W304,RN,D);


	and MGM_G374(MGM_W305,SE,MGM_W304);


	and MGM_G375(ENABLE_D_AND_RN_AND_SE_AND_SETN,SETN,MGM_W305);


	// spec_gates_end



   specify

	// specify_block_begin

	if(D===1'b0 && SI===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SE))  = (1.0,1.0);

	if(SE===1'b0 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b0 && SI===1'b1 || D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SI))  = (1.0,1.0);

	ifnone
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SETN===1'b0 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SETN===1'b0 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SETN===1'b1 && SI===1'b0)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SETN===1'b1 && SI===1'b1)
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	ifnone
	// seq arc RN --> Q
	(RN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),
		negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// recovery RN-LH CLK-LH
	$recovery(posedge RN &&& (ENABLE_D_AND_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// removal RN-LH CLK-LH
	$removal(posedge RN &&& (ENABLE_D_AND_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold RN-LH SETN-LH
	$hold(posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup RN-LH SETN-LH
	$setup(posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),
		negedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),
		posedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),
		negedge SE &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),
		posedge SE &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SETN-LH RN-LH
	$hold(posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	// setup SETN-LH RN-LH
	$setup(posedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),
		posedge RN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1),1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_RN_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_RN_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_RN_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_RN_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		negedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		posedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		negedge SI &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		posedge SI &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// mpw RN_hl
	$width(negedge RN,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_RN_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_RN_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__SDFFRSNQ_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__SDFFRSNQ_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__SDFFRSNQ_FUNC_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_func( SE, SI, D, CLK, SETN, RN, Q, VDD, VSS, VNW, VPW, notifier );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_func( SE, SI, D, CLK, SETN, RN, Q, notifier );
`endif // If not USE_POWER_PINS
input CLK, D, RN, SE, SETN, SI, notifier;
output Q;

	not MGM_BG_0( MGM_P0, RN );

	not MGM_BG_1( MGM_C0, SETN );

	wire D_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_2;

	not MGM_BG_2( D_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_2, D );

	wire SE_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_2;

	not MGM_BG_3( SE_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_2, SE );

	wire MGM_D0_row1;

	and MGM_BG_4( MGM_D0_row1, D_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_2, SE_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_2 );

	wire SI_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_2;

	not MGM_BG_5( SI_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_2, SI );

	wire MGM_D0_row2;

	and MGM_BG_6( MGM_D0_row2, D_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_2, SI_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_2 );

	wire MGM_D0_row3;

	and MGM_BG_7( MGM_D0_row3, SI_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffrsnq_2, SE );

	or MGM_BG_8( MGM_D0, MGM_D0_row1, MGM_D0_row2, MGM_D0_row3 );

	gf180mcu_fd_sc_mcu9t5v0__udp_hn_iq_ff( IQ1, MGM_C0, MGM_P0, CLK, MGM_D0, notifier );

	not MGM_BG_9( Q, IQ1 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__SDFFRSNQ_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__SDFFSNQ_1_V
`define GF180MCU_FD_SC_MCU9T5V0__SDFFSNQ_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffsnq_1( SE, SI, D, CLK, SETN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffsnq_1( SE, SI, D, CLK, SETN, Q );
`endif // If not USE_POWER_PINS
input CLK, D, SE, SETN, SI;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffsnq_func gf180mcu_fd_sc_mcu9t5v0__sdffsnq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.SETN(SETN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffsnq_func gf180mcu_fd_sc_mcu9t5v0__sdffsnq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.SETN(SETN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	not MGM_G1(MGM_W1,SE);


	and MGM_G2(MGM_W2,MGM_W1,MGM_W0);


	and MGM_G3(MGM_W3,SETN,MGM_W2);


	not MGM_G4(MGM_W4,SI);


	and MGM_G5(ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W4,MGM_W3);


	not MGM_G6(MGM_W5,D);


	not MGM_G7(MGM_W6,SE);


	and MGM_G8(MGM_W7,MGM_W6,MGM_W5);


	and MGM_G9(MGM_W8,SETN,MGM_W7);


	and MGM_G10(ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W8);


	not MGM_G11(MGM_W9,D);


	and MGM_G12(MGM_W10,SE,MGM_W9);


	and MGM_G13(MGM_W11,SETN,MGM_W10);


	not MGM_G14(MGM_W12,SI);


	and MGM_G15(ENABLE_NOT_D_AND_SE_AND_SETN_AND_NOT_SI,MGM_W12,MGM_W11);


	not MGM_G16(MGM_W13,D);


	and MGM_G17(MGM_W14,SE,MGM_W13);


	and MGM_G18(MGM_W15,SETN,MGM_W14);


	and MGM_G19(ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W15);


	not MGM_G20(MGM_W16,SE);


	and MGM_G21(MGM_W17,MGM_W16,D);


	and MGM_G22(MGM_W18,SETN,MGM_W17);


	not MGM_G23(MGM_W19,SI);


	and MGM_G24(ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W19,MGM_W18);


	not MGM_G25(MGM_W20,SE);


	and MGM_G26(MGM_W21,MGM_W20,D);


	and MGM_G27(MGM_W22,SETN,MGM_W21);


	and MGM_G28(ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W22);


	and MGM_G29(MGM_W23,SE,D);


	and MGM_G30(MGM_W24,SETN,MGM_W23);


	not MGM_G31(MGM_W25,SI);


	and MGM_G32(ENABLE_D_AND_SE_AND_SETN_AND_NOT_SI,MGM_W25,MGM_W24);


	and MGM_G33(MGM_W26,SE,D);


	and MGM_G34(MGM_W27,SETN,MGM_W26);


	and MGM_G35(ENABLE_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W27);


	not MGM_G36(MGM_W28,SE);


	and MGM_G37(MGM_W29,SETN,MGM_W28);


	not MGM_G38(MGM_W30,SI);


	and MGM_G39(ENABLE_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W30,MGM_W29);


	not MGM_G40(MGM_W31,SE);


	and MGM_G41(MGM_W32,SETN,MGM_W31);


	and MGM_G42(ENABLE_NOT_SE_AND_SETN_AND_SI,SI,MGM_W32);


	not MGM_G43(MGM_W33,D);


	and MGM_G44(MGM_W34,SETN,MGM_W33);


	and MGM_G45(ENABLE_NOT_D_AND_SETN_AND_SI,SI,MGM_W34);


	and MGM_G46(MGM_W35,SETN,D);


	not MGM_G47(MGM_W36,SI);


	and MGM_G48(ENABLE_D_AND_SETN_AND_NOT_SI,MGM_W36,MGM_W35);


	not MGM_G49(MGM_W37,D);


	not MGM_G50(MGM_W38,SE);


	and MGM_G51(MGM_W39,MGM_W38,MGM_W37);


	not MGM_G52(MGM_W40,SI);


	and MGM_G53(ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W40,MGM_W39);


	not MGM_G54(MGM_W41,D);


	not MGM_G55(MGM_W42,SE);


	and MGM_G56(MGM_W43,MGM_W42,MGM_W41);


	and MGM_G57(ENABLE_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W43);


	not MGM_G58(MGM_W44,D);


	and MGM_G59(MGM_W45,SE,MGM_W44);


	not MGM_G60(MGM_W46,SI);


	and MGM_G61(ENABLE_NOT_D_AND_SE_AND_NOT_SI,MGM_W46,MGM_W45);


	and MGM_G62(MGM_W47,SE,D);


	not MGM_G63(MGM_W48,SI);


	and MGM_G64(ENABLE_D_AND_SE_AND_NOT_SI,MGM_W48,MGM_W47);


	not MGM_G65(MGM_W49,CLK);


	not MGM_G66(MGM_W50,D);


	and MGM_G67(MGM_W51,MGM_W50,MGM_W49);


	not MGM_G68(MGM_W52,SE);


	and MGM_G69(MGM_W53,MGM_W52,MGM_W51);


	not MGM_G70(MGM_W54,SI);


	and MGM_G71(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W54,MGM_W53);


	not MGM_G72(MGM_W55,CLK);


	not MGM_G73(MGM_W56,D);


	and MGM_G74(MGM_W57,MGM_W56,MGM_W55);


	not MGM_G75(MGM_W58,SE);


	and MGM_G76(MGM_W59,MGM_W58,MGM_W57);


	and MGM_G77(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W59);


	not MGM_G78(MGM_W60,CLK);


	not MGM_G79(MGM_W61,D);


	and MGM_G80(MGM_W62,MGM_W61,MGM_W60);


	and MGM_G81(MGM_W63,SE,MGM_W62);


	not MGM_G82(MGM_W64,SI);


	and MGM_G83(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI,MGM_W64,MGM_W63);


	not MGM_G84(MGM_W65,CLK);


	not MGM_G85(MGM_W66,D);


	and MGM_G86(MGM_W67,MGM_W66,MGM_W65);


	and MGM_G87(MGM_W68,SE,MGM_W67);


	and MGM_G88(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI,SI,MGM_W68);


	not MGM_G89(MGM_W69,CLK);


	and MGM_G90(MGM_W70,D,MGM_W69);


	not MGM_G91(MGM_W71,SE);


	and MGM_G92(MGM_W72,MGM_W71,MGM_W70);


	not MGM_G93(MGM_W73,SI);


	and MGM_G94(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI,MGM_W73,MGM_W72);


	not MGM_G95(MGM_W74,CLK);


	and MGM_G96(MGM_W75,D,MGM_W74);


	not MGM_G97(MGM_W76,SE);


	and MGM_G98(MGM_W77,MGM_W76,MGM_W75);


	and MGM_G99(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI,SI,MGM_W77);


	not MGM_G100(MGM_W78,CLK);


	and MGM_G101(MGM_W79,D,MGM_W78);


	and MGM_G102(MGM_W80,SE,MGM_W79);


	not MGM_G103(MGM_W81,SI);


	and MGM_G104(ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI,MGM_W81,MGM_W80);


	not MGM_G105(MGM_W82,CLK);


	and MGM_G106(MGM_W83,D,MGM_W82);


	and MGM_G107(MGM_W84,SE,MGM_W83);


	and MGM_G108(ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI,SI,MGM_W84);


	not MGM_G109(MGM_W85,D);


	and MGM_G110(MGM_W86,MGM_W85,CLK);


	not MGM_G111(MGM_W87,SE);


	and MGM_G112(MGM_W88,MGM_W87,MGM_W86);


	not MGM_G113(MGM_W89,SI);


	and MGM_G114(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W89,MGM_W88);


	not MGM_G115(MGM_W90,D);


	and MGM_G116(MGM_W91,MGM_W90,CLK);


	not MGM_G117(MGM_W92,SE);


	and MGM_G118(MGM_W93,MGM_W92,MGM_W91);


	and MGM_G119(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W93);


	not MGM_G120(MGM_W94,D);


	and MGM_G121(MGM_W95,MGM_W94,CLK);


	and MGM_G122(MGM_W96,SE,MGM_W95);


	not MGM_G123(MGM_W97,SI);


	and MGM_G124(ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI,MGM_W97,MGM_W96);


	not MGM_G125(MGM_W98,D);


	and MGM_G126(MGM_W99,MGM_W98,CLK);


	and MGM_G127(MGM_W100,SE,MGM_W99);


	and MGM_G128(ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI,SI,MGM_W100);


	and MGM_G129(MGM_W101,D,CLK);


	not MGM_G130(MGM_W102,SE);


	and MGM_G131(MGM_W103,MGM_W102,MGM_W101);


	not MGM_G132(MGM_W104,SI);


	and MGM_G133(ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI,MGM_W104,MGM_W103);


	and MGM_G134(MGM_W105,D,CLK);


	not MGM_G135(MGM_W106,SE);


	and MGM_G136(MGM_W107,MGM_W106,MGM_W105);


	and MGM_G137(ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI,SI,MGM_W107);


	and MGM_G138(MGM_W108,D,CLK);


	and MGM_G139(MGM_W109,SE,MGM_W108);


	not MGM_G140(MGM_W110,SI);


	and MGM_G141(ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI,MGM_W110,MGM_W109);


	and MGM_G142(MGM_W111,D,CLK);


	and MGM_G143(MGM_W112,SE,MGM_W111);


	and MGM_G144(ENABLE_CLK_AND_D_AND_SE_AND_SI,SI,MGM_W112);


	not MGM_G145(MGM_W113,D);


	and MGM_G146(MGM_W114,SE,MGM_W113);


	and MGM_G147(ENABLE_NOT_D_AND_SE_AND_SETN,SETN,MGM_W114);


	and MGM_G148(MGM_W115,SE,D);


	and MGM_G149(ENABLE_D_AND_SE_AND_SETN,SETN,MGM_W115);


	// spec_gates_end



   specify

	// specify_block_begin

	if(D===1'b0 && SI===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SE))  = (1.0,1.0);

	if(SE===1'b0 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b0 && SI===1'b1 || D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SI))  = (1.0,1.0);

	ifnone
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		negedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),
		negedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),
		negedge SE &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),
		posedge SE &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),
		negedge SE &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),
		posedge SE &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),
		negedge SI &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),
		posedge SI &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),
		negedge SI &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),
		posedge SI &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__SDFFSNQ_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__SDFFSNQ_2_V
`define GF180MCU_FD_SC_MCU9T5V0__SDFFSNQ_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffsnq_2( SE, SI, D, CLK, SETN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffsnq_2( SE, SI, D, CLK, SETN, Q );
`endif // If not USE_POWER_PINS
input CLK, D, SE, SETN, SI;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffsnq_func gf180mcu_fd_sc_mcu9t5v0__sdffsnq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.SETN(SETN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffsnq_func gf180mcu_fd_sc_mcu9t5v0__sdffsnq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.SETN(SETN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	not MGM_G1(MGM_W1,SE);


	and MGM_G2(MGM_W2,MGM_W1,MGM_W0);


	and MGM_G3(MGM_W3,SETN,MGM_W2);


	not MGM_G4(MGM_W4,SI);


	and MGM_G5(ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W4,MGM_W3);


	not MGM_G6(MGM_W5,D);


	not MGM_G7(MGM_W6,SE);


	and MGM_G8(MGM_W7,MGM_W6,MGM_W5);


	and MGM_G9(MGM_W8,SETN,MGM_W7);


	and MGM_G10(ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W8);


	not MGM_G11(MGM_W9,D);


	and MGM_G12(MGM_W10,SE,MGM_W9);


	and MGM_G13(MGM_W11,SETN,MGM_W10);


	not MGM_G14(MGM_W12,SI);


	and MGM_G15(ENABLE_NOT_D_AND_SE_AND_SETN_AND_NOT_SI,MGM_W12,MGM_W11);


	not MGM_G16(MGM_W13,D);


	and MGM_G17(MGM_W14,SE,MGM_W13);


	and MGM_G18(MGM_W15,SETN,MGM_W14);


	and MGM_G19(ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W15);


	not MGM_G20(MGM_W16,SE);


	and MGM_G21(MGM_W17,MGM_W16,D);


	and MGM_G22(MGM_W18,SETN,MGM_W17);


	not MGM_G23(MGM_W19,SI);


	and MGM_G24(ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W19,MGM_W18);


	not MGM_G25(MGM_W20,SE);


	and MGM_G26(MGM_W21,MGM_W20,D);


	and MGM_G27(MGM_W22,SETN,MGM_W21);


	and MGM_G28(ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W22);


	and MGM_G29(MGM_W23,SE,D);


	and MGM_G30(MGM_W24,SETN,MGM_W23);


	not MGM_G31(MGM_W25,SI);


	and MGM_G32(ENABLE_D_AND_SE_AND_SETN_AND_NOT_SI,MGM_W25,MGM_W24);


	and MGM_G33(MGM_W26,SE,D);


	and MGM_G34(MGM_W27,SETN,MGM_W26);


	and MGM_G35(ENABLE_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W27);


	not MGM_G36(MGM_W28,SE);


	and MGM_G37(MGM_W29,SETN,MGM_W28);


	not MGM_G38(MGM_W30,SI);


	and MGM_G39(ENABLE_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W30,MGM_W29);


	not MGM_G40(MGM_W31,SE);


	and MGM_G41(MGM_W32,SETN,MGM_W31);


	and MGM_G42(ENABLE_NOT_SE_AND_SETN_AND_SI,SI,MGM_W32);


	not MGM_G43(MGM_W33,D);


	and MGM_G44(MGM_W34,SETN,MGM_W33);


	and MGM_G45(ENABLE_NOT_D_AND_SETN_AND_SI,SI,MGM_W34);


	and MGM_G46(MGM_W35,SETN,D);


	not MGM_G47(MGM_W36,SI);


	and MGM_G48(ENABLE_D_AND_SETN_AND_NOT_SI,MGM_W36,MGM_W35);


	not MGM_G49(MGM_W37,D);


	not MGM_G50(MGM_W38,SE);


	and MGM_G51(MGM_W39,MGM_W38,MGM_W37);


	not MGM_G52(MGM_W40,SI);


	and MGM_G53(ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W40,MGM_W39);


	not MGM_G54(MGM_W41,D);


	not MGM_G55(MGM_W42,SE);


	and MGM_G56(MGM_W43,MGM_W42,MGM_W41);


	and MGM_G57(ENABLE_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W43);


	not MGM_G58(MGM_W44,D);


	and MGM_G59(MGM_W45,SE,MGM_W44);


	not MGM_G60(MGM_W46,SI);


	and MGM_G61(ENABLE_NOT_D_AND_SE_AND_NOT_SI,MGM_W46,MGM_W45);


	and MGM_G62(MGM_W47,SE,D);


	not MGM_G63(MGM_W48,SI);


	and MGM_G64(ENABLE_D_AND_SE_AND_NOT_SI,MGM_W48,MGM_W47);


	not MGM_G65(MGM_W49,CLK);


	not MGM_G66(MGM_W50,D);


	and MGM_G67(MGM_W51,MGM_W50,MGM_W49);


	not MGM_G68(MGM_W52,SE);


	and MGM_G69(MGM_W53,MGM_W52,MGM_W51);


	not MGM_G70(MGM_W54,SI);


	and MGM_G71(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W54,MGM_W53);


	not MGM_G72(MGM_W55,CLK);


	not MGM_G73(MGM_W56,D);


	and MGM_G74(MGM_W57,MGM_W56,MGM_W55);


	not MGM_G75(MGM_W58,SE);


	and MGM_G76(MGM_W59,MGM_W58,MGM_W57);


	and MGM_G77(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W59);


	not MGM_G78(MGM_W60,CLK);


	not MGM_G79(MGM_W61,D);


	and MGM_G80(MGM_W62,MGM_W61,MGM_W60);


	and MGM_G81(MGM_W63,SE,MGM_W62);


	not MGM_G82(MGM_W64,SI);


	and MGM_G83(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI,MGM_W64,MGM_W63);


	not MGM_G84(MGM_W65,CLK);


	not MGM_G85(MGM_W66,D);


	and MGM_G86(MGM_W67,MGM_W66,MGM_W65);


	and MGM_G87(MGM_W68,SE,MGM_W67);


	and MGM_G88(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI,SI,MGM_W68);


	not MGM_G89(MGM_W69,CLK);


	and MGM_G90(MGM_W70,D,MGM_W69);


	not MGM_G91(MGM_W71,SE);


	and MGM_G92(MGM_W72,MGM_W71,MGM_W70);


	not MGM_G93(MGM_W73,SI);


	and MGM_G94(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI,MGM_W73,MGM_W72);


	not MGM_G95(MGM_W74,CLK);


	and MGM_G96(MGM_W75,D,MGM_W74);


	not MGM_G97(MGM_W76,SE);


	and MGM_G98(MGM_W77,MGM_W76,MGM_W75);


	and MGM_G99(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI,SI,MGM_W77);


	not MGM_G100(MGM_W78,CLK);


	and MGM_G101(MGM_W79,D,MGM_W78);


	and MGM_G102(MGM_W80,SE,MGM_W79);


	not MGM_G103(MGM_W81,SI);


	and MGM_G104(ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI,MGM_W81,MGM_W80);


	not MGM_G105(MGM_W82,CLK);


	and MGM_G106(MGM_W83,D,MGM_W82);


	and MGM_G107(MGM_W84,SE,MGM_W83);


	and MGM_G108(ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI,SI,MGM_W84);


	not MGM_G109(MGM_W85,D);


	and MGM_G110(MGM_W86,MGM_W85,CLK);


	not MGM_G111(MGM_W87,SE);


	and MGM_G112(MGM_W88,MGM_W87,MGM_W86);


	not MGM_G113(MGM_W89,SI);


	and MGM_G114(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W89,MGM_W88);


	not MGM_G115(MGM_W90,D);


	and MGM_G116(MGM_W91,MGM_W90,CLK);


	not MGM_G117(MGM_W92,SE);


	and MGM_G118(MGM_W93,MGM_W92,MGM_W91);


	and MGM_G119(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W93);


	not MGM_G120(MGM_W94,D);


	and MGM_G121(MGM_W95,MGM_W94,CLK);


	and MGM_G122(MGM_W96,SE,MGM_W95);


	not MGM_G123(MGM_W97,SI);


	and MGM_G124(ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI,MGM_W97,MGM_W96);


	not MGM_G125(MGM_W98,D);


	and MGM_G126(MGM_W99,MGM_W98,CLK);


	and MGM_G127(MGM_W100,SE,MGM_W99);


	and MGM_G128(ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI,SI,MGM_W100);


	and MGM_G129(MGM_W101,D,CLK);


	not MGM_G130(MGM_W102,SE);


	and MGM_G131(MGM_W103,MGM_W102,MGM_W101);


	not MGM_G132(MGM_W104,SI);


	and MGM_G133(ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI,MGM_W104,MGM_W103);


	and MGM_G134(MGM_W105,D,CLK);


	not MGM_G135(MGM_W106,SE);


	and MGM_G136(MGM_W107,MGM_W106,MGM_W105);


	and MGM_G137(ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI,SI,MGM_W107);


	and MGM_G138(MGM_W108,D,CLK);


	and MGM_G139(MGM_W109,SE,MGM_W108);


	not MGM_G140(MGM_W110,SI);


	and MGM_G141(ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI,MGM_W110,MGM_W109);


	and MGM_G142(MGM_W111,D,CLK);


	and MGM_G143(MGM_W112,SE,MGM_W111);


	and MGM_G144(ENABLE_CLK_AND_D_AND_SE_AND_SI,SI,MGM_W112);


	not MGM_G145(MGM_W113,D);


	and MGM_G146(MGM_W114,SE,MGM_W113);


	and MGM_G147(ENABLE_NOT_D_AND_SE_AND_SETN,SETN,MGM_W114);


	and MGM_G148(MGM_W115,SE,D);


	and MGM_G149(ENABLE_D_AND_SE_AND_SETN,SETN,MGM_W115);


	// spec_gates_end



   specify

	// specify_block_begin

	if(D===1'b0 && SI===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SE))  = (1.0,1.0);

	if(SE===1'b0 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b0 && SI===1'b1 || D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SI))  = (1.0,1.0);

	ifnone
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		negedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),
		negedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),
		negedge SE &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),
		posedge SE &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),
		negedge SE &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),
		posedge SE &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),
		negedge SI &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),
		posedge SI &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),
		negedge SI &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),
		posedge SI &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__SDFFSNQ_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__SDFFSNQ_4_V
`define GF180MCU_FD_SC_MCU9T5V0__SDFFSNQ_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffsnq_4( SE, SI, D, CLK, SETN, Q, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffsnq_4( SE, SI, D, CLK, SETN, Q );
`endif // If not USE_POWER_PINS
input CLK, D, SE, SETN, SI;
output Q;
reg notifier;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffsnq_func gf180mcu_fd_sc_mcu9t5v0__sdffsnq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.SETN(SETN),.Q(Q),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW),.notifier(notifier));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__sdffsnq_func gf180mcu_fd_sc_mcu9t5v0__sdffsnq_inst(.SE(SE),.SI(SI),.D(D),.CLK(CLK),.SETN(SETN),.Q(Q),.notifier(notifier));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	not MGM_G0(MGM_W0,D);


	not MGM_G1(MGM_W1,SE);


	and MGM_G2(MGM_W2,MGM_W1,MGM_W0);


	and MGM_G3(MGM_W3,SETN,MGM_W2);


	not MGM_G4(MGM_W4,SI);


	and MGM_G5(ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W4,MGM_W3);


	not MGM_G6(MGM_W5,D);


	not MGM_G7(MGM_W6,SE);


	and MGM_G8(MGM_W7,MGM_W6,MGM_W5);


	and MGM_G9(MGM_W8,SETN,MGM_W7);


	and MGM_G10(ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W8);


	not MGM_G11(MGM_W9,D);


	and MGM_G12(MGM_W10,SE,MGM_W9);


	and MGM_G13(MGM_W11,SETN,MGM_W10);


	not MGM_G14(MGM_W12,SI);


	and MGM_G15(ENABLE_NOT_D_AND_SE_AND_SETN_AND_NOT_SI,MGM_W12,MGM_W11);


	not MGM_G16(MGM_W13,D);


	and MGM_G17(MGM_W14,SE,MGM_W13);


	and MGM_G18(MGM_W15,SETN,MGM_W14);


	and MGM_G19(ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W15);


	not MGM_G20(MGM_W16,SE);


	and MGM_G21(MGM_W17,MGM_W16,D);


	and MGM_G22(MGM_W18,SETN,MGM_W17);


	not MGM_G23(MGM_W19,SI);


	and MGM_G24(ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W19,MGM_W18);


	not MGM_G25(MGM_W20,SE);


	and MGM_G26(MGM_W21,MGM_W20,D);


	and MGM_G27(MGM_W22,SETN,MGM_W21);


	and MGM_G28(ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI,SI,MGM_W22);


	and MGM_G29(MGM_W23,SE,D);


	and MGM_G30(MGM_W24,SETN,MGM_W23);


	not MGM_G31(MGM_W25,SI);


	and MGM_G32(ENABLE_D_AND_SE_AND_SETN_AND_NOT_SI,MGM_W25,MGM_W24);


	and MGM_G33(MGM_W26,SE,D);


	and MGM_G34(MGM_W27,SETN,MGM_W26);


	and MGM_G35(ENABLE_D_AND_SE_AND_SETN_AND_SI,SI,MGM_W27);


	not MGM_G36(MGM_W28,SE);


	and MGM_G37(MGM_W29,SETN,MGM_W28);


	not MGM_G38(MGM_W30,SI);


	and MGM_G39(ENABLE_NOT_SE_AND_SETN_AND_NOT_SI,MGM_W30,MGM_W29);


	not MGM_G40(MGM_W31,SE);


	and MGM_G41(MGM_W32,SETN,MGM_W31);


	and MGM_G42(ENABLE_NOT_SE_AND_SETN_AND_SI,SI,MGM_W32);


	not MGM_G43(MGM_W33,D);


	and MGM_G44(MGM_W34,SETN,MGM_W33);


	and MGM_G45(ENABLE_NOT_D_AND_SETN_AND_SI,SI,MGM_W34);


	and MGM_G46(MGM_W35,SETN,D);


	not MGM_G47(MGM_W36,SI);


	and MGM_G48(ENABLE_D_AND_SETN_AND_NOT_SI,MGM_W36,MGM_W35);


	not MGM_G49(MGM_W37,D);


	not MGM_G50(MGM_W38,SE);


	and MGM_G51(MGM_W39,MGM_W38,MGM_W37);


	not MGM_G52(MGM_W40,SI);


	and MGM_G53(ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W40,MGM_W39);


	not MGM_G54(MGM_W41,D);


	not MGM_G55(MGM_W42,SE);


	and MGM_G56(MGM_W43,MGM_W42,MGM_W41);


	and MGM_G57(ENABLE_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W43);


	not MGM_G58(MGM_W44,D);


	and MGM_G59(MGM_W45,SE,MGM_W44);


	not MGM_G60(MGM_W46,SI);


	and MGM_G61(ENABLE_NOT_D_AND_SE_AND_NOT_SI,MGM_W46,MGM_W45);


	and MGM_G62(MGM_W47,SE,D);


	not MGM_G63(MGM_W48,SI);


	and MGM_G64(ENABLE_D_AND_SE_AND_NOT_SI,MGM_W48,MGM_W47);


	not MGM_G65(MGM_W49,CLK);


	not MGM_G66(MGM_W50,D);


	and MGM_G67(MGM_W51,MGM_W50,MGM_W49);


	not MGM_G68(MGM_W52,SE);


	and MGM_G69(MGM_W53,MGM_W52,MGM_W51);


	not MGM_G70(MGM_W54,SI);


	and MGM_G71(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W54,MGM_W53);


	not MGM_G72(MGM_W55,CLK);


	not MGM_G73(MGM_W56,D);


	and MGM_G74(MGM_W57,MGM_W56,MGM_W55);


	not MGM_G75(MGM_W58,SE);


	and MGM_G76(MGM_W59,MGM_W58,MGM_W57);


	and MGM_G77(ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W59);


	not MGM_G78(MGM_W60,CLK);


	not MGM_G79(MGM_W61,D);


	and MGM_G80(MGM_W62,MGM_W61,MGM_W60);


	and MGM_G81(MGM_W63,SE,MGM_W62);


	not MGM_G82(MGM_W64,SI);


	and MGM_G83(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI,MGM_W64,MGM_W63);


	not MGM_G84(MGM_W65,CLK);


	not MGM_G85(MGM_W66,D);


	and MGM_G86(MGM_W67,MGM_W66,MGM_W65);


	and MGM_G87(MGM_W68,SE,MGM_W67);


	and MGM_G88(ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI,SI,MGM_W68);


	not MGM_G89(MGM_W69,CLK);


	and MGM_G90(MGM_W70,D,MGM_W69);


	not MGM_G91(MGM_W71,SE);


	and MGM_G92(MGM_W72,MGM_W71,MGM_W70);


	not MGM_G93(MGM_W73,SI);


	and MGM_G94(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI,MGM_W73,MGM_W72);


	not MGM_G95(MGM_W74,CLK);


	and MGM_G96(MGM_W75,D,MGM_W74);


	not MGM_G97(MGM_W76,SE);


	and MGM_G98(MGM_W77,MGM_W76,MGM_W75);


	and MGM_G99(ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI,SI,MGM_W77);


	not MGM_G100(MGM_W78,CLK);


	and MGM_G101(MGM_W79,D,MGM_W78);


	and MGM_G102(MGM_W80,SE,MGM_W79);


	not MGM_G103(MGM_W81,SI);


	and MGM_G104(ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI,MGM_W81,MGM_W80);


	not MGM_G105(MGM_W82,CLK);


	and MGM_G106(MGM_W83,D,MGM_W82);


	and MGM_G107(MGM_W84,SE,MGM_W83);


	and MGM_G108(ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI,SI,MGM_W84);


	not MGM_G109(MGM_W85,D);


	and MGM_G110(MGM_W86,MGM_W85,CLK);


	not MGM_G111(MGM_W87,SE);


	and MGM_G112(MGM_W88,MGM_W87,MGM_W86);


	not MGM_G113(MGM_W89,SI);


	and MGM_G114(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI,MGM_W89,MGM_W88);


	not MGM_G115(MGM_W90,D);


	and MGM_G116(MGM_W91,MGM_W90,CLK);


	not MGM_G117(MGM_W92,SE);


	and MGM_G118(MGM_W93,MGM_W92,MGM_W91);


	and MGM_G119(ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI,SI,MGM_W93);


	not MGM_G120(MGM_W94,D);


	and MGM_G121(MGM_W95,MGM_W94,CLK);


	and MGM_G122(MGM_W96,SE,MGM_W95);


	not MGM_G123(MGM_W97,SI);


	and MGM_G124(ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI,MGM_W97,MGM_W96);


	not MGM_G125(MGM_W98,D);


	and MGM_G126(MGM_W99,MGM_W98,CLK);


	and MGM_G127(MGM_W100,SE,MGM_W99);


	and MGM_G128(ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI,SI,MGM_W100);


	and MGM_G129(MGM_W101,D,CLK);


	not MGM_G130(MGM_W102,SE);


	and MGM_G131(MGM_W103,MGM_W102,MGM_W101);


	not MGM_G132(MGM_W104,SI);


	and MGM_G133(ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI,MGM_W104,MGM_W103);


	and MGM_G134(MGM_W105,D,CLK);


	not MGM_G135(MGM_W106,SE);


	and MGM_G136(MGM_W107,MGM_W106,MGM_W105);


	and MGM_G137(ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI,SI,MGM_W107);


	and MGM_G138(MGM_W108,D,CLK);


	and MGM_G139(MGM_W109,SE,MGM_W108);


	not MGM_G140(MGM_W110,SI);


	and MGM_G141(ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI,MGM_W110,MGM_W109);


	and MGM_G142(MGM_W111,D,CLK);


	and MGM_G143(MGM_W112,SE,MGM_W111);


	and MGM_G144(ENABLE_CLK_AND_D_AND_SE_AND_SI,SI,MGM_W112);


	not MGM_G145(MGM_W113,D);


	and MGM_G146(MGM_W114,SE,MGM_W113);


	and MGM_G147(ENABLE_NOT_D_AND_SE_AND_SETN,SETN,MGM_W114);


	and MGM_G148(MGM_W115,SE,D);


	and MGM_G149(ENABLE_D_AND_SE_AND_SETN,SETN,MGM_W115);


	// spec_gates_end



   specify

	// specify_block_begin

	if(D===1'b0 && SI===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SE))  = (1.0,1.0);

	if(SE===1'b0 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b0 && SI===1'b1 || D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(D===1'b1 && SE===1'b1)
	// seq arc CLK --> Q
	(posedge CLK => (Q : SI))  = (1.0,1.0);

	ifnone
	// seq arc CLK --> Q
	(posedge CLK => (Q : D))  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b0 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b0 && D===1'b1 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b0 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b0 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SI===1'b0)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	if(CLK===1'b1 && D===1'b1 && SE===1'b1 && SI===1'b1)
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	ifnone
	// seq arc SETN --> Q
	(SETN => Q)  = (1.0,1.0);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		negedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold D-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),
		negedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// hold D-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup D-HL CLK-LH
	$setup(negedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup D-LH CLK-LH
	$setup(posedge D &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_SE_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),
		negedge SE &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),
		posedge SE &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SETN_AND_SI === 1'b1),1.0,notifier);

	// hold SE-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),
		negedge SE &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// hold SE-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),
		posedge SE &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-HL CLK-LH
	$setup(negedge SE &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// setup SE-LH CLK-LH
	$setup(posedge SE &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SETN_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_NOT_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// recovery SETN-LH CLK-LH
	$recovery(posedge SETN &&& (ENABLE_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	// removal SETN-LH CLK-LH
	$removal(posedge SETN &&& (ENABLE_D_AND_SE_AND_NOT_SI === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_NOT_SI === 1'b1),1.0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_NOT_CLK_AND_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_NOT_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_NOT_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_NOT_SI === 1'b1)
		,1.0,0,notifier);

	$width(negedge SETN &&& (ENABLE_CLK_AND_D_AND_SE_AND_SI === 1'b1)
		,1.0,0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),
		negedge SI &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),
		posedge SI &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// hold SI-HL CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),
		negedge SI &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// hold SI-LH CLK-LH
	$hold(posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),
		posedge SI &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-HL CLK-LH
	$setup(negedge SI &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// setup SI-LH CLK-LH
	$setup(posedge SI &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),
		posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN === 1'b1),1.0,notifier);

	// mpw CLK_lh
	$width(posedge CLK,1.0,0,notifier);

	// mpw CLK_hl
	$width(negedge CLK,1.0,0,notifier);

	// mpw SETN_hl
	$width(negedge SETN,1.0,0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_NOT_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_NOT_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_NOT_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK &&& (ENABLE_D_AND_SE_AND_SETN_AND_SI === 1'b1)
		,1.0,notifier);

	// period CLK
	$period(posedge CLK,1.0,notifier);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__SDFFSNQ_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__SDFFSNQ_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__SDFFSNQ_FUNC_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffsnq_func( SE, SI, D, CLK, SETN, Q, VDD, VSS, VNW, VPW, notifier );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__sdffsnq_func( SE, SI, D, CLK, SETN, Q, notifier );
`endif // If not USE_POWER_PINS
input CLK, D, SE, SETN, SI, notifier;
output Q;

	not MGM_BG_0( MGM_C0, SETN );

	wire D_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffsnq_1;

	not MGM_BG_1( D_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffsnq_1, D );

	wire SE_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffsnq_1;

	not MGM_BG_2( SE_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffsnq_1, SE );

	wire MGM_D0_row1;

	and MGM_BG_3( MGM_D0_row1, D_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffsnq_1, SE_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffsnq_1 );

	wire SI_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffsnq_1;

	not MGM_BG_4( SI_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffsnq_1, SI );

	wire MGM_D0_row2;

	and MGM_BG_5( MGM_D0_row2, D_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffsnq_1, SI_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffsnq_1 );

	wire MGM_D0_row3;

	and MGM_BG_6( MGM_D0_row3, SI_inv_for_gf180mcu_fd_sc_mcu9t5v0__sdffsnq_1, SE );

	or MGM_BG_7( MGM_D0, MGM_D0_row1, MGM_D0_row2, MGM_D0_row3 );

	gf180mcu_fd_sc_mcu9t5v0__udp_n_iq_ff( IQ1, MGM_C0, 1'b0, CLK, MGM_D0, notifier );

	not MGM_BG_8( Q, IQ1 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__SDFFSNQ_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__TIEH_V
`define GF180MCU_FD_SC_MCU9T5V0__TIEH_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__tieh( Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__tieh( Z );
`endif // If not USE_POWER_PINS
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__tieh_func gf180mcu_fd_sc_mcu9t5v0__tieh_inst(.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__tieh_func gf180mcu_fd_sc_mcu9t5v0__tieh_inst(.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__TIEH_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__TIEH_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__TIEH_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__tieh_func( Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__tieh_func( Z );
`endif // If not USE_POWER_PINS
output Z;

	assign Z = 1'b1;

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__TIEH_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__TIEL_V
`define GF180MCU_FD_SC_MCU9T5V0__TIEL_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__tiel( ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__tiel( ZN );
`endif // If not USE_POWER_PINS
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__tiel_func gf180mcu_fd_sc_mcu9t5v0__tiel_inst(.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__tiel_func gf180mcu_fd_sc_mcu9t5v0__tiel_inst(.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__TIEL_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__TIEL_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__TIEL_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__tiel_func( ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__tiel_func( ZN );
`endif // If not USE_POWER_PINS
output ZN;

	assign ZN = 1'b0;

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__TIEL_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__XNOR2_1_V
`define GF180MCU_FD_SC_MCU9T5V0__XNOR2_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xnor2_1( A2, A1, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xnor2_1( A2, A1, ZN );
`endif // If not USE_POWER_PINS
input A1, A2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xnor2_func gf180mcu_fd_sc_mcu9t5v0__xnor2_inst(.A2(A2),.A1(A1),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xnor2_func gf180mcu_fd_sc_mcu9t5v0__xnor2_inst(.A2(A2),.A1(A1),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	ifnone
	// comb arc posedge A1 --> (ZN:A1)
	 (posedge A1 => (ZN:A1)) = (1.0,1.0);

	ifnone
	// comb arc negedge A1 --> (ZN:A1)
	 (negedge A1 => (ZN:A1)) = (1.0,1.0);

	ifnone
	// comb arc posedge A2 --> (ZN:A2)
	 (posedge A2 => (ZN:A2)) = (1.0,1.0);

	ifnone
	// comb arc negedge A2 --> (ZN:A2)
	 (negedge A2 => (ZN:A2)) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__XNOR2_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__XNOR2_2_V
`define GF180MCU_FD_SC_MCU9T5V0__XNOR2_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xnor2_2( A2, A1, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xnor2_2( A2, A1, ZN );
`endif // If not USE_POWER_PINS
input A1, A2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xnor2_func gf180mcu_fd_sc_mcu9t5v0__xnor2_inst(.A2(A2),.A1(A1),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xnor2_func gf180mcu_fd_sc_mcu9t5v0__xnor2_inst(.A2(A2),.A1(A1),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	ifnone
	// comb arc posedge A1 --> (ZN:A1)
	 (posedge A1 => (ZN:A1)) = (1.0,1.0);

	ifnone
	// comb arc negedge A1 --> (ZN:A1)
	 (negedge A1 => (ZN:A1)) = (1.0,1.0);

	ifnone
	// comb arc posedge A2 --> (ZN:A2)
	 (posedge A2 => (ZN:A2)) = (1.0,1.0);

	ifnone
	// comb arc negedge A2 --> (ZN:A2)
	 (negedge A2 => (ZN:A2)) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__XNOR2_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__XNOR2_4_V
`define GF180MCU_FD_SC_MCU9T5V0__XNOR2_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xnor2_4( A2, A1, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xnor2_4( A2, A1, ZN );
`endif // If not USE_POWER_PINS
input A1, A2;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xnor2_func gf180mcu_fd_sc_mcu9t5v0__xnor2_inst(.A2(A2),.A1(A1),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xnor2_func gf180mcu_fd_sc_mcu9t5v0__xnor2_inst(.A2(A2),.A1(A1),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	ifnone
	// comb arc posedge A1 --> (ZN:A1)
	 (posedge A1 => (ZN:A1)) = (1.0,1.0);

	ifnone
	// comb arc negedge A1 --> (ZN:A1)
	 (negedge A1 => (ZN:A1)) = (1.0,1.0);

	ifnone
	// comb arc posedge A2 --> (ZN:A2)
	 (posedge A2 => (ZN:A2)) = (1.0,1.0);

	ifnone
	// comb arc negedge A2 --> (ZN:A2)
	 (negedge A2 => (ZN:A2)) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__XNOR2_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__XNOR2_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__XNOR2_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xnor2_func( A2, A1, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xnor2_func( A2, A1, ZN );
`endif // If not USE_POWER_PINS
input A1, A2;
output ZN;

	wire ZN_row1;

	and MGM_BG_0( ZN_row1, A1, A2 );

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__xnor2_4;

	not MGM_BG_1( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__xnor2_4, A1 );

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__xnor2_4;

	not MGM_BG_2( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__xnor2_4, A2 );

	wire ZN_row2;

	and MGM_BG_3( ZN_row2, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__xnor2_4, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__xnor2_4 );

	or MGM_BG_4( ZN, ZN_row1, ZN_row2 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__XNOR2_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__XNOR3_1_V
`define GF180MCU_FD_SC_MCU9T5V0__XNOR3_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xnor3_1( A2, A1, A3, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xnor3_1( A2, A1, A3, ZN );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xnor3_func gf180mcu_fd_sc_mcu9t5v0__xnor3_inst(.A2(A2),.A1(A1),.A3(A3),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xnor3_func gf180mcu_fd_sc_mcu9t5v0__xnor3_inst(.A2(A2),.A1(A1),.A3(A3),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(A2===1'b0 && A3===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(A2===1'b1 && A3===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc posedge A1 --> (ZN:A1)
	 (posedge A1 => (ZN:A1)) = (1.0,1.0);

	ifnone
	// comb arc negedge A1 --> (ZN:A1)
	 (negedge A1 => (ZN:A1)) = (1.0,1.0);

	if(A2===1'b0 && A3===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(A2===1'b1 && A3===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A3===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A3===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc posedge A2 --> (ZN:A2)
	 (posedge A2 => (ZN:A2)) = (1.0,1.0);

	ifnone
	// comb arc negedge A2 --> (ZN:A2)
	 (negedge A2 => (ZN:A2)) = (1.0,1.0);

	if(A1===1'b0 && A3===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A3===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	ifnone
	// comb arc posedge A3 --> (ZN:A3)
	 (posedge A3 => (ZN:A3)) = (1.0,1.0);

	ifnone
	// comb arc negedge A3 --> (ZN:A3)
	 (negedge A3 => (ZN:A3)) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__XNOR3_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__XNOR3_2_V
`define GF180MCU_FD_SC_MCU9T5V0__XNOR3_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xnor3_2( A2, A1, A3, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xnor3_2( A2, A1, A3, ZN );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xnor3_func gf180mcu_fd_sc_mcu9t5v0__xnor3_inst(.A2(A2),.A1(A1),.A3(A3),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xnor3_func gf180mcu_fd_sc_mcu9t5v0__xnor3_inst(.A2(A2),.A1(A1),.A3(A3),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(A2===1'b0 && A3===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(A2===1'b1 && A3===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc posedge A1 --> (ZN:A1)
	 (posedge A1 => (ZN:A1)) = (1.0,1.0);

	ifnone
	// comb arc negedge A1 --> (ZN:A1)
	 (negedge A1 => (ZN:A1)) = (1.0,1.0);

	if(A2===1'b0 && A3===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(A2===1'b1 && A3===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A3===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A3===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc posedge A2 --> (ZN:A2)
	 (posedge A2 => (ZN:A2)) = (1.0,1.0);

	ifnone
	// comb arc negedge A2 --> (ZN:A2)
	 (negedge A2 => (ZN:A2)) = (1.0,1.0);

	if(A1===1'b0 && A3===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A3===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	ifnone
	// comb arc posedge A3 --> (ZN:A3)
	 (posedge A3 => (ZN:A3)) = (1.0,1.0);

	ifnone
	// comb arc negedge A3 --> (ZN:A3)
	 (negedge A3 => (ZN:A3)) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__XNOR3_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__XNOR3_4_V
`define GF180MCU_FD_SC_MCU9T5V0__XNOR3_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xnor3_4( A2, A1, A3, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xnor3_4( A2, A1, A3, ZN );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output ZN;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xnor3_func gf180mcu_fd_sc_mcu9t5v0__xnor3_inst(.A2(A2),.A1(A1),.A3(A3),.ZN(ZN),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xnor3_func gf180mcu_fd_sc_mcu9t5v0__xnor3_inst(.A2(A2),.A1(A1),.A3(A3),.ZN(ZN));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(A2===1'b0 && A3===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(A2===1'b1 && A3===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	ifnone
	// comb arc posedge A1 --> (ZN:A1)
	 (posedge A1 => (ZN:A1)) = (1.0,1.0);

	ifnone
	// comb arc negedge A1 --> (ZN:A1)
	 (negedge A1 => (ZN:A1)) = (1.0,1.0);

	if(A2===1'b0 && A3===1'b1)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(A2===1'b1 && A3===1'b0)
	// comb arc A1 --> ZN
	 (A1 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A3===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A3===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	ifnone
	// comb arc posedge A2 --> (ZN:A2)
	 (posedge A2 => (ZN:A2)) = (1.0,1.0);

	ifnone
	// comb arc negedge A2 --> (ZN:A2)
	 (negedge A2 => (ZN:A2)) = (1.0,1.0);

	if(A1===1'b0 && A3===1'b1)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A3===1'b0)
	// comb arc A2 --> ZN
	 (A2 => ZN) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	ifnone
	// comb arc posedge A3 --> (ZN:A3)
	 (posedge A3 => (ZN:A3)) = (1.0,1.0);

	ifnone
	// comb arc negedge A3 --> (ZN:A3)
	 (negedge A3 => (ZN:A3)) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc A3 --> ZN
	 (A3 => ZN) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__XNOR3_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__XNOR3_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__XNOR3_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xnor3_func( A2, A1, A3, ZN, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xnor3_func( A2, A1, A3, ZN );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output ZN;

	wire A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__xnor3_4;

	not MGM_BG_0( A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__xnor3_4, A3 );

	wire ZN_row1;

	and MGM_BG_1( ZN_row1, A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__xnor3_4, A1, A2 );

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__xnor3_4;

	not MGM_BG_2( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__xnor3_4, A2 );

	wire ZN_row2;

	and MGM_BG_3( ZN_row2, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__xnor3_4, A1, A3 );

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__xnor3_4;

	not MGM_BG_4( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__xnor3_4, A1 );

	wire ZN_row3;

	and MGM_BG_5( ZN_row3, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__xnor3_4, A2, A3 );

	wire ZN_row4;

	and MGM_BG_6( ZN_row4, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__xnor3_4, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__xnor3_4, A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__xnor3_4 );

	or MGM_BG_7( ZN, ZN_row1, ZN_row2, ZN_row3, ZN_row4 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__XNOR3_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__XOR2_1_V
`define GF180MCU_FD_SC_MCU9T5V0__XOR2_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xor2_1( A2, A1, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xor2_1( A2, A1, Z );
`endif // If not USE_POWER_PINS
input A1, A2;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xor2_func gf180mcu_fd_sc_mcu9t5v0__xor2_inst(.A2(A2),.A1(A1),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xor2_func gf180mcu_fd_sc_mcu9t5v0__xor2_inst(.A2(A2),.A1(A1),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	ifnone
	// comb arc posedge A1 --> (Z:A1)
	 (posedge A1 => (Z:A1)) = (1.0,1.0);

	ifnone
	// comb arc negedge A1 --> (Z:A1)
	 (negedge A1 => (Z:A1)) = (1.0,1.0);

	ifnone
	// comb arc posedge A2 --> (Z:A2)
	 (posedge A2 => (Z:A2)) = (1.0,1.0);

	ifnone
	// comb arc negedge A2 --> (Z:A2)
	 (negedge A2 => (Z:A2)) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__XOR2_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__XOR2_2_V
`define GF180MCU_FD_SC_MCU9T5V0__XOR2_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xor2_2( A2, A1, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xor2_2( A2, A1, Z );
`endif // If not USE_POWER_PINS
input A1, A2;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xor2_func gf180mcu_fd_sc_mcu9t5v0__xor2_inst(.A2(A2),.A1(A1),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xor2_func gf180mcu_fd_sc_mcu9t5v0__xor2_inst(.A2(A2),.A1(A1),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	ifnone
	// comb arc posedge A1 --> (Z:A1)
	 (posedge A1 => (Z:A1)) = (1.0,1.0);

	ifnone
	// comb arc negedge A1 --> (Z:A1)
	 (negedge A1 => (Z:A1)) = (1.0,1.0);

	ifnone
	// comb arc posedge A2 --> (Z:A2)
	 (posedge A2 => (Z:A2)) = (1.0,1.0);

	ifnone
	// comb arc negedge A2 --> (Z:A2)
	 (negedge A2 => (Z:A2)) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__XOR2_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__XOR2_4_V
`define GF180MCU_FD_SC_MCU9T5V0__XOR2_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xor2_4( A2, A1, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xor2_4( A2, A1, Z );
`endif // If not USE_POWER_PINS
input A1, A2;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xor2_func gf180mcu_fd_sc_mcu9t5v0__xor2_inst(.A2(A2),.A1(A1),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xor2_func gf180mcu_fd_sc_mcu9t5v0__xor2_inst(.A2(A2),.A1(A1),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	ifnone
	// comb arc posedge A1 --> (Z:A1)
	 (posedge A1 => (Z:A1)) = (1.0,1.0);

	ifnone
	// comb arc negedge A1 --> (Z:A1)
	 (negedge A1 => (Z:A1)) = (1.0,1.0);

	ifnone
	// comb arc posedge A2 --> (Z:A2)
	 (posedge A2 => (Z:A2)) = (1.0,1.0);

	ifnone
	// comb arc negedge A2 --> (Z:A2)
	 (negedge A2 => (Z:A2)) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__XOR2_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__XOR2_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__XOR2_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xor2_func( A2, A1, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xor2_func( A2, A1, Z );
`endif // If not USE_POWER_PINS
input A1, A2;
output Z;

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__xor2_1;

	not MGM_BG_0( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__xor2_1, A2 );

	wire Z_row1;

	and MGM_BG_1( Z_row1, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__xor2_1, A1 );

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__xor2_1;

	not MGM_BG_2( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__xor2_1, A1 );

	wire Z_row2;

	and MGM_BG_3( Z_row2, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__xor2_1, A2 );

	or MGM_BG_4( Z, Z_row1, Z_row2 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__XOR2_FUNC_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__XOR3_1_V
`define GF180MCU_FD_SC_MCU9T5V0__XOR3_1_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xor3_1( A2, A1, A3, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xor3_1( A2, A1, A3, Z );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xor3_func gf180mcu_fd_sc_mcu9t5v0__xor3_inst(.A2(A2),.A1(A1),.A3(A3),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xor3_func gf180mcu_fd_sc_mcu9t5v0__xor3_inst(.A2(A2),.A1(A1),.A3(A3),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(A2===1'b0 && A3===1'b1)
	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	if(A2===1'b1 && A3===1'b0)
	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	ifnone
	// comb arc posedge A1 --> (Z:A1)
	 (posedge A1 => (Z:A1)) = (1.0,1.0);

	ifnone
	// comb arc negedge A1 --> (Z:A1)
	 (negedge A1 => (Z:A1)) = (1.0,1.0);

	if(A2===1'b0 && A3===1'b0)
	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	if(A2===1'b1 && A3===1'b1)
	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	if(A1===1'b0 && A3===1'b1)
	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	if(A1===1'b1 && A3===1'b0)
	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	ifnone
	// comb arc posedge A2 --> (Z:A2)
	 (posedge A2 => (Z:A2)) = (1.0,1.0);

	ifnone
	// comb arc negedge A2 --> (Z:A2)
	 (negedge A2 => (Z:A2)) = (1.0,1.0);

	if(A1===1'b0 && A3===1'b0)
	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	if(A1===1'b1 && A3===1'b1)
	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	ifnone
	// comb arc posedge A3 --> (Z:A3)
	 (posedge A3 => (Z:A3)) = (1.0,1.0);

	ifnone
	// comb arc negedge A3 --> (Z:A3)
	 (negedge A3 => (Z:A3)) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__XOR3_1_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__XOR3_2_V
`define GF180MCU_FD_SC_MCU9T5V0__XOR3_2_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xor3_2( A2, A1, A3, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xor3_2( A2, A1, A3, Z );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xor3_func gf180mcu_fd_sc_mcu9t5v0__xor3_inst(.A2(A2),.A1(A1),.A3(A3),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xor3_func gf180mcu_fd_sc_mcu9t5v0__xor3_inst(.A2(A2),.A1(A1),.A3(A3),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(A2===1'b0 && A3===1'b1)
	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	if(A2===1'b1 && A3===1'b0)
	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	ifnone
	// comb arc posedge A1 --> (Z:A1)
	 (posedge A1 => (Z:A1)) = (1.0,1.0);

	ifnone
	// comb arc negedge A1 --> (Z:A1)
	 (negedge A1 => (Z:A1)) = (1.0,1.0);

	if(A2===1'b0 && A3===1'b0)
	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	if(A2===1'b1 && A3===1'b1)
	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	if(A1===1'b0 && A3===1'b1)
	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	if(A1===1'b1 && A3===1'b0)
	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	ifnone
	// comb arc posedge A2 --> (Z:A2)
	 (posedge A2 => (Z:A2)) = (1.0,1.0);

	ifnone
	// comb arc negedge A2 --> (Z:A2)
	 (negedge A2 => (Z:A2)) = (1.0,1.0);

	if(A1===1'b0 && A3===1'b0)
	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	if(A1===1'b1 && A3===1'b1)
	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	ifnone
	// comb arc posedge A3 --> (Z:A3)
	 (posedge A3 => (Z:A3)) = (1.0,1.0);

	ifnone
	// comb arc negedge A3 --> (Z:A3)
	 (negedge A3 => (Z:A3)) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__XOR3_2_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__XOR3_4_V
`define GF180MCU_FD_SC_MCU9T5V0__XOR3_4_V


`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xor3_4( A2, A1, A3, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xor3_4( A2, A1, A3, Z );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output Z;

`ifdef USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xor3_func gf180mcu_fd_sc_mcu9t5v0__xor3_inst(.A2(A2),.A1(A1),.A3(A3),.Z(Z),.VDD(VDD),.VSS(VSS),.VNW(VNW),.VPW(VPW));
`else // If not USE_POWER_PINS
  gf180mcu_fd_sc_mcu9t5v0__xor3_func gf180mcu_fd_sc_mcu9t5v0__xor3_inst(.A2(A2),.A1(A1),.A3(A3),.Z(Z));
`endif // If not USE_POWER_PINS

`ifndef FUNCTIONAL
	// spec_gates_begin


	// spec_gates_end



   specify

	// specify_block_begin

	if(A2===1'b0 && A3===1'b1)
	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	if(A2===1'b1 && A3===1'b0)
	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	ifnone
	// comb arc posedge A1 --> (Z:A1)
	 (posedge A1 => (Z:A1)) = (1.0,1.0);

	ifnone
	// comb arc negedge A1 --> (Z:A1)
	 (negedge A1 => (Z:A1)) = (1.0,1.0);

	if(A2===1'b0 && A3===1'b0)
	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	if(A2===1'b1 && A3===1'b1)
	// comb arc A1 --> Z
	 (A1 => Z) = (1.0,1.0);

	if(A1===1'b0 && A3===1'b1)
	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	if(A1===1'b1 && A3===1'b0)
	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	ifnone
	// comb arc posedge A2 --> (Z:A2)
	 (posedge A2 => (Z:A2)) = (1.0,1.0);

	ifnone
	// comb arc negedge A2 --> (Z:A2)
	 (negedge A2 => (Z:A2)) = (1.0,1.0);

	if(A1===1'b0 && A3===1'b0)
	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	if(A1===1'b1 && A3===1'b1)
	// comb arc A2 --> Z
	 (A2 => Z) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b1)
	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b0)
	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	ifnone
	// comb arc posedge A3 --> (Z:A3)
	 (posedge A3 => (Z:A3)) = (1.0,1.0);

	ifnone
	// comb arc negedge A3 --> (Z:A3)
	 (negedge A3 => (Z:A3)) = (1.0,1.0);

	if(A1===1'b0 && A2===1'b0)
	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	if(A1===1'b1 && A2===1'b1)
	// comb arc A3 --> Z
	 (A3 => Z) = (1.0,1.0);

	// specify_block_end

   endspecify

   `endif

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__XOR3_4_V


//--------EOF---------

// Copyright 2022 GlobalFoundries PDK Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

`ifndef GF180MCU_FD_SC_MCU9T5V0__XOR3_FUNC_V
`define GF180MCU_FD_SC_MCU9T5V0__XOR3_FUNC_V

`ifdef USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xor3_func( A2, A1, A3, Z, VDD, VSS, VNW, VPW );
inout VDD, VSS, VNW, VPW;
`else // If not USE_POWER_PINS
module gf180mcu_fd_sc_mcu9t5v0__xor3_func( A2, A1, A3, Z );
`endif // If not USE_POWER_PINS
input A1, A2, A3;
output Z;

	wire Z_row1;

	and MGM_BG_0( Z_row1, A1, A2, A3 );

	wire A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__xor3_4;

	not MGM_BG_1( A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__xor3_4, A2 );

	wire A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__xor3_4;

	not MGM_BG_2( A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__xor3_4, A3 );

	wire Z_row2;

	and MGM_BG_3( Z_row2, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__xor3_4, A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__xor3_4, A1 );

	wire A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__xor3_4;

	not MGM_BG_4( A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__xor3_4, A1 );

	wire Z_row3;

	and MGM_BG_5( Z_row3, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__xor3_4, A3_inv_for_gf180mcu_fd_sc_mcu9t5v0__xor3_4, A2 );

	wire Z_row4;

	and MGM_BG_6( Z_row4, A1_inv_for_gf180mcu_fd_sc_mcu9t5v0__xor3_4, A2_inv_for_gf180mcu_fd_sc_mcu9t5v0__xor3_4, A3 );

	or MGM_BG_7( Z, Z_row1, Z_row2, Z_row3, Z_row4 );

endmodule
`endif // GF180MCU_FD_SC_MCU9T5V0__XOR3_FUNC_V


//--------EOF---------

