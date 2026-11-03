"""Return specification-only buffer/post/FIFO projections; never mutate live data."""
from __future__ import annotations

import copy


BEHAVIORS = {
    "node-buffer": (
        "Register banks A[64],B[64] unsigned8 storedbytes. load_data16: byte[7:0],addr[13:8],bank[14](A0/B1),reserved15=0. "
        "read_request16: Aaddr[5:0],Baddr[13:8],reserved[7:6]/[15:14]=0. read_response16 low8=A/high8=B. "
        "One response slot. load_data_ready=!rst&&!response_valid&&load_data[15]==0. "
        "read_request_ready=!rst&&!response_valid&&!load_data_valid&&reserved_read_bits==0. Load has priority. "
        "Accepted load writes exactly one bank/address. Accepted read registers packed operands and asserts response_valid next cycle. "
        "Hold response/data under stall; accepted response clears valid. No same-cycle response consume/read replacement. "
        "Synchronous high rst cancels pending response and gates all ready/valid low; it MUST NOT reset either stored bank. "
        "No initial memory values are assumed; only loaded addresses may be read. Physical memory retention is not claimed."
    ),
    "node-post": (
        "Registered signed32 bias/ReLU output, row-major column counter0..3. post_config129 packs ReLU[0],four signed32biases[1+32*c+:32]. "
        "post_config_ready=!rst&&!out_valid&&column==0. Accepted config latches allbits,sets configured1,column0. "
        "acc_data_ready=!rst&&configured&&(!out_valid||result_data_ready)&&!post_config_valid. "
        "Accepted acc_data adds selected bias[column] modulo2^32,then zeroes result if configReLU and signed wrappedsum<0. "
        "Register result_data/valid; advance column modulo4 per accepted acc_data. "
        "Simultaneous oldoutput consume/newinput accept replaces slot; output consume without replacement clears valid. "
        "Hold result_data/valid under stall. No input before configuration; reconfigure only between rows after slotempty. "
        "Synchronous high rst clears configured,column,outputvalid and gates all ready/valid low. Metadata routing/final PE sum selection is global work."
    ),
    "node-fifo": (
        "Depth2 signed32 FIFO, preserve accepted result_data order. output_data_valid=!rst&&(count>0); "
        "result_data_ready=!rst&&((count<2)||(output_data_ready&&output_data_valid)). "
        "output_data is current head only meaningful while valid; hold head under stall. "
        "Support full simultaneous pop+push, empty push (no combinational bypass), circular pointer wrap; count changes bypush-minuspop. "
        "Synchronous high rst empties queue/resets pointers/count and gates ready/valid low. "
        "No need clear memorybits. FIFO doesn't identify job boundaries/count16; globalcontrol counts accepted finaloutputs."
        " Raw output_transfer=output_data_valid&&output_data_ready is the exact accepted-output pulse,including consecutivecycles; sendtojobcontrol."
    ),
}
KINDS = {"node-buffer": "npu_buffer_stream", "node-post": "npu_post_stream", "node-fifo": "npu_fifo_stream"}


def build_proposal(design):
    """Preserve all source data/ports/edges; concretize only these three nodes."""
    proposal = copy.deepcopy(design)
    if len(proposal.get("verification_jobs", [])) != 1:
        raise ValueError("This continuation requires exactly the preserved original GUI job.")
    source_job = proposal["verification_jobs"][0]
    for node in proposal["nodes"]:
        if node["id"] not in KINDS:
            continue
        node["behavior"] = BEHAVIORS[node["id"]]
        node["test_expectations"] = (
            "Same exact original GUI matrix job via saved original_job_projection_v1 independent recipe. "
            "Frozen inputs/reference/TB must match RTL and synthesized netlist. Check valid/ready,payload onlyvalid,stalls,resetcancel,ordering. "
            "Buffer loads originalbytes once then reads afterreset; post uses16 independent matrixsums/bias,sourceReLUmode unchanged; FIFO uses16 finalsourcejobresults. "
            "No internal-state observation/fullNPU/exhaustive claim."
        )
        node["verification"] = {"kind": KINDS[node["id"]], "version": 1, "source_job": copy.deepcopy(source_job),
                                "exercise": {"kind": "original_job_projection_v1"}}
        if node["id"] == "node-fifo":
            node["constraints"]["depth"] = 2
            node["ports"] = [port for port in node["ports"] if port["name"] != "output_transfer"]
            node["ports"].append({"id": "port-fifo-output_transfer", "name": "output_transfer", "direction": "output", "width": 1,
                                  "signed": False, "protocol": "raw", "clock": "clk", "reset": "rst",
                                  "sideband": {"kind": "pulse", "associated_port_id": "port-fifo-output_data"}})
    return proposal
