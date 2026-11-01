"""Finite saved-job checks for the explicit 2x2 PE, collector and post nodes.

Ordinary-program independent integer references; no RTL is inspected to choose
expected behavior. Repeated jobs preserve original GUI arithmetic inputs.
"""
from __future__ import annotations

import copy
import json
import re

from .context import build_node_context
from .domain import DomainError
from .verification import content_hash, object_hash

TEMPLATE = "npu2-original-job-datapath-v1"
KINDS = {"npu2_pe_original_job": ("npu2-pe00", "npu2-pe01", "npu2-pe10", "npu2-pe11"),
         "npu2_collector_original_job": ("npu2-collector",), "npu2_post_original_job": ("npu2-post",)}
STREAMS = {
    "npu2_pe_original_job": {"pair_data": ("input", 18, False), "sum_data": ("output", 32, True)},
    "npu2_collector_original_job": {**{"sum" + lane: ("input", 32, True) for lane in ("00", "01", "10", "11")}, "acc_data": ("output", 32, True)},
    "npu2_post_original_job": {"post_config": ("input", 65, False), "acc_data": ("input", 32, True), "result_data": ("output", 32, True)},
}

EXPECTED_NODES = json.loads(r'''{
  "npu2-pe00": {
    "behavior": "Dedicated output-stationary MAC for C[0][0]. pair_data carries signed8 a[7:0], signed8 b[15:8], first[16], last[17]. Sign-extend the signed16 product to signed32. On an input transfer with first=1 replace the accumulator with that product; otherwise add the product modulo 2^32. first is data, never a reset pin. If last=1 publish the updated sum once in a registered output slot and hold output valid/data until accepted. first && last supports K=1. While an output is pending, accept no new pair; no same-cycle output-consume/new-pair replacement. Intermediate products do not emit partial output responses. Synchronous high reset clears accumulator, output valid and pending state. Each job has K input transfers and one final sum transfer.",
    "constraints": {
      "latency_cycles": 1,
      "protocol": "valid_ready",
      "row": 0,
      "column": 0,
      "accumulator_bits": 32
    },
    "ports": [
      {
        "id": "npu2-pe00-pair_data",
        "name": "pair_data",
        "direction": "input",
        "width": 18,
        "signed": false,
        "protocol": "valid_ready",
        "clock": "clk",
        "reset": "rst"
      },
      {
        "id": "npu2-pe00-sum_data",
        "name": "sum_data",
        "direction": "output",
        "width": 32,
        "signed": true,
        "protocol": "valid_ready",
        "clock": "clk",
        "reset": "rst"
      }
    ]
  },
  "npu2-pe01": {
    "behavior": "Dedicated output-stationary MAC for C[0][1]. pair_data carries signed8 a[7:0], signed8 b[15:8], first[16], last[17]. Sign-extend the signed16 product to signed32. On an input transfer with first=1 replace the accumulator with that product; otherwise add the product modulo 2^32. first is data, never a reset pin. If last=1 publish the updated sum once in a registered output slot and hold output valid/data until accepted. first && last supports K=1. While an output is pending, accept no new pair; no same-cycle output-consume/new-pair replacement. Intermediate products do not emit partial output responses. Synchronous high reset clears accumulator, output valid and pending state. Each job has K input transfers and one final sum transfer.",
    "constraints": {
      "latency_cycles": 1,
      "protocol": "valid_ready",
      "row": 0,
      "column": 1,
      "accumulator_bits": 32
    },
    "ports": [
      {
        "id": "npu2-pe01-pair_data",
        "name": "pair_data",
        "direction": "input",
        "width": 18,
        "signed": false,
        "protocol": "valid_ready",
        "clock": "clk",
        "reset": "rst"
      },
      {
        "id": "npu2-pe01-sum_data",
        "name": "sum_data",
        "direction": "output",
        "width": 32,
        "signed": true,
        "protocol": "valid_ready",
        "clock": "clk",
        "reset": "rst"
      }
    ]
  },
  "npu2-pe10": {
    "behavior": "Dedicated output-stationary MAC for C[1][0]. pair_data carries signed8 a[7:0], signed8 b[15:8], first[16], last[17]. Sign-extend the signed16 product to signed32. On an input transfer with first=1 replace the accumulator with that product; otherwise add the product modulo 2^32. first is data, never a reset pin. If last=1 publish the updated sum once in a registered output slot and hold output valid/data until accepted. first && last supports K=1. While an output is pending, accept no new pair; no same-cycle output-consume/new-pair replacement. Intermediate products do not emit partial output responses. Synchronous high reset clears accumulator, output valid and pending state. Each job has K input transfers and one final sum transfer.",
    "constraints": {
      "latency_cycles": 1,
      "protocol": "valid_ready",
      "row": 1,
      "column": 0,
      "accumulator_bits": 32
    },
    "ports": [
      {
        "id": "npu2-pe10-pair_data",
        "name": "pair_data",
        "direction": "input",
        "width": 18,
        "signed": false,
        "protocol": "valid_ready",
        "clock": "clk",
        "reset": "rst"
      },
      {
        "id": "npu2-pe10-sum_data",
        "name": "sum_data",
        "direction": "output",
        "width": 32,
        "signed": true,
        "protocol": "valid_ready",
        "clock": "clk",
        "reset": "rst"
      }
    ]
  },
  "npu2-pe11": {
    "behavior": "Dedicated output-stationary MAC for C[1][1]. pair_data carries signed8 a[7:0], signed8 b[15:8], first[16], last[17]. Sign-extend the signed16 product to signed32. On an input transfer with first=1 replace the accumulator with that product; otherwise add the product modulo 2^32. first is data, never a reset pin. If last=1 publish the updated sum once in a registered output slot and hold output valid/data until accepted. first && last supports K=1. While an output is pending, accept no new pair; no same-cycle output-consume/new-pair replacement. Intermediate products do not emit partial output responses. Synchronous high reset clears accumulator, output valid and pending state. Each job has K input transfers and one final sum transfer.",
    "constraints": {
      "latency_cycles": 1,
      "protocol": "valid_ready",
      "row": 1,
      "column": 1,
      "accumulator_bits": 32
    },
    "ports": [
      {
        "id": "npu2-pe11-pair_data",
        "name": "pair_data",
        "direction": "input",
        "width": 18,
        "signed": false,
        "protocol": "valid_ready",
        "clock": "clk",
        "reset": "rst"
      },
      {
        "id": "npu2-pe11-sum_data",
        "name": "sum_data",
        "direction": "output",
        "width": 32,
        "signed": true,
        "protocol": "valid_ready",
        "clock": "clk",
        "reset": "rst"
      }
    ]
  },
  "npu2-collector": {
    "behavior": "Four separate input streams, one combinational valid/ready output stream. Start at lane00 after reset and visit 00,01,10,11. Present acc_data/valid from only the current lane; propagate downstream ready only to that lane. All other input ready signals remain low. Advance on the actual acc_data valid && ready transfer; after lane11 wrap to lane00 for the next job. Do not drain, reorder or drop another lane's result early. The selected PE holds its registered final sum during downstream stall. Reset gates all valids/readies and returns selection to lane00. No new job may start before Job control sees four final external outputs.",
    "constraints": {
      "latency_cycles": 0,
      "protocol": "valid_ready",
      "lane_order": [
        "00",
        "01",
        "10",
        "11"
      ]
    },
    "ports": [
      {
        "id": "npu2-collector-sum00",
        "name": "sum00",
        "direction": "input",
        "width": 32,
        "signed": true,
        "protocol": "valid_ready",
        "clock": "clk",
        "reset": "rst"
      },
      {
        "id": "npu2-collector-sum01",
        "name": "sum01",
        "direction": "input",
        "width": 32,
        "signed": true,
        "protocol": "valid_ready",
        "clock": "clk",
        "reset": "rst"
      },
      {
        "id": "npu2-collector-sum10",
        "name": "sum10",
        "direction": "input",
        "width": 32,
        "signed": true,
        "protocol": "valid_ready",
        "clock": "clk",
        "reset": "rst"
      },
      {
        "id": "npu2-collector-sum11",
        "name": "sum11",
        "direction": "input",
        "width": 32,
        "signed": true,
        "protocol": "valid_ready",
        "clock": "clk",
        "reset": "rst"
      },
      {
        "id": "npu2-collector-acc_data",
        "name": "acc_data",
        "direction": "output",
        "width": 32,
        "signed": true,
        "protocol": "valid_ready",
        "clock": "clk",
        "reset": "rst"
      }
    ]
  },
  "npu2-post": {
    "behavior": "post_config[0]=ReLU, [32:1]=signed bias0, [64:33]=signed bias1. Latch configuration only between jobs when no output is pending and the four-result index is at zero. Process exactly four row-major acc_data transfers per configuration, applying bias for column index (result_index modulo2). Compute signed32 wrapped=(acc_data+bias[column]) modulo2^32, then output zero if ReLU and signed wrapped<0, otherwise wrapped. One registered result slot, stable while stalled. Support output consume/input replacement in the same cycle; do not accept acc_data when unconfigured or while a configuration transfer is pending. After the fourth accepted acc_data, require a fresh configuration before any fifth value. Reset clears configuration flag, result index and output valid.",
    "constraints": {
      "latency_cycles": 1,
      "protocol": "valid_ready",
      "outputs_per_job": 4
    },
    "ports": [
      {
        "id": "npu2-post-post_config",
        "name": "post_config",
        "direction": "input",
        "width": 65,
        "signed": false,
        "protocol": "valid_ready",
        "clock": "clk",
        "reset": "rst"
      },
      {
        "id": "npu2-post-acc_data",
        "name": "acc_data",
        "direction": "input",
        "width": 32,
        "signed": true,
        "protocol": "valid_ready",
        "clock": "clk",
        "reset": "rst"
      },
      {
        "id": "npu2-post-result_data",
        "name": "result_data",
        "direction": "output",
        "width": 32,
        "signed": true,
        "protocol": "valid_ready",
        "clock": "clk",
        "reset": "rst"
      }
    ]
  }
}''')
EXPECTED_EDGES = json.loads(r'''{
  "npu2-pe00": [
    {
      "id": "npu2-edge-pair-00",
      "source": {
        "node_id": "npu2-dispatcher",
        "port_id": "npu2-dispatcher-pair00"
      },
      "target": {
        "node_id": "npu2-pe00",
        "port_id": "npu2-pe00-pair_data"
      },
      "protocol": "valid_ready",
      "behavior": "Dedicated lane00 stream; signed A(row0,k) and B(k,col0) with first/last bits, independent handshake."
    },
    {
      "id": "npu2-edge-sum-00",
      "source": {
        "node_id": "npu2-pe00",
        "port_id": "npu2-pe00-sum_data"
      },
      "target": {
        "node_id": "npu2-collector",
        "port_id": "npu2-collector-sum00"
      },
      "protocol": "valid_ready",
      "behavior": "Exactly one signed32 final MAC sum for C[0][0] per job; held until row-major collector selects this lane."
    }
  ],
  "npu2-pe01": [
    {
      "id": "npu2-edge-pair-01",
      "source": {
        "node_id": "npu2-dispatcher",
        "port_id": "npu2-dispatcher-pair01"
      },
      "target": {
        "node_id": "npu2-pe01",
        "port_id": "npu2-pe01-pair_data"
      },
      "protocol": "valid_ready",
      "behavior": "Dedicated lane01 stream; signed A(row0,k) and B(k,col1) with first/last bits, independent handshake."
    },
    {
      "id": "npu2-edge-sum-01",
      "source": {
        "node_id": "npu2-pe01",
        "port_id": "npu2-pe01-sum_data"
      },
      "target": {
        "node_id": "npu2-collector",
        "port_id": "npu2-collector-sum01"
      },
      "protocol": "valid_ready",
      "behavior": "Exactly one signed32 final MAC sum for C[0][1] per job; held until row-major collector selects this lane."
    }
  ],
  "npu2-pe10": [
    {
      "id": "npu2-edge-pair-10",
      "source": {
        "node_id": "npu2-dispatcher",
        "port_id": "npu2-dispatcher-pair10"
      },
      "target": {
        "node_id": "npu2-pe10",
        "port_id": "npu2-pe10-pair_data"
      },
      "protocol": "valid_ready",
      "behavior": "Dedicated lane10 stream; signed A(row1,k) and B(k,col0) with first/last bits, independent handshake."
    },
    {
      "id": "npu2-edge-sum-10",
      "source": {
        "node_id": "npu2-pe10",
        "port_id": "npu2-pe10-sum_data"
      },
      "target": {
        "node_id": "npu2-collector",
        "port_id": "npu2-collector-sum10"
      },
      "protocol": "valid_ready",
      "behavior": "Exactly one signed32 final MAC sum for C[1][0] per job; held until row-major collector selects this lane."
    }
  ],
  "npu2-pe11": [
    {
      "id": "npu2-edge-pair-11",
      "source": {
        "node_id": "npu2-dispatcher",
        "port_id": "npu2-dispatcher-pair11"
      },
      "target": {
        "node_id": "npu2-pe11",
        "port_id": "npu2-pe11-pair_data"
      },
      "protocol": "valid_ready",
      "behavior": "Dedicated lane11 stream; signed A(row1,k) and B(k,col1) with first/last bits, independent handshake."
    },
    {
      "id": "npu2-edge-sum-11",
      "source": {
        "node_id": "npu2-pe11",
        "port_id": "npu2-pe11-sum_data"
      },
      "target": {
        "node_id": "npu2-collector",
        "port_id": "npu2-collector-sum11"
      },
      "protocol": "valid_ready",
      "behavior": "Exactly one signed32 final MAC sum for C[1][1] per job; held until row-major collector selects this lane."
    }
  ],
  "npu2-collector": [
    {
      "id": "npu2-edge-sum-00",
      "source": {
        "node_id": "npu2-pe00",
        "port_id": "npu2-pe00-sum_data"
      },
      "target": {
        "node_id": "npu2-collector",
        "port_id": "npu2-collector-sum00"
      },
      "protocol": "valid_ready",
      "behavior": "Exactly one signed32 final MAC sum for C[0][0] per job; held until row-major collector selects this lane."
    },
    {
      "id": "npu2-edge-sum-01",
      "source": {
        "node_id": "npu2-pe01",
        "port_id": "npu2-pe01-sum_data"
      },
      "target": {
        "node_id": "npu2-collector",
        "port_id": "npu2-collector-sum01"
      },
      "protocol": "valid_ready",
      "behavior": "Exactly one signed32 final MAC sum for C[0][1] per job; held until row-major collector selects this lane."
    },
    {
      "id": "npu2-edge-sum-10",
      "source": {
        "node_id": "npu2-pe10",
        "port_id": "npu2-pe10-sum_data"
      },
      "target": {
        "node_id": "npu2-collector",
        "port_id": "npu2-collector-sum10"
      },
      "protocol": "valid_ready",
      "behavior": "Exactly one signed32 final MAC sum for C[1][0] per job; held until row-major collector selects this lane."
    },
    {
      "id": "npu2-edge-sum-11",
      "source": {
        "node_id": "npu2-pe11",
        "port_id": "npu2-pe11-sum_data"
      },
      "target": {
        "node_id": "npu2-collector",
        "port_id": "npu2-collector-sum11"
      },
      "protocol": "valid_ready",
      "behavior": "Exactly one signed32 final MAC sum for C[1][1] per job; held until row-major collector selects this lane."
    },
    {
      "id": "npu2-edge-collected-sum",
      "source": {
        "node_id": "npu2-collector",
        "port_id": "npu2-collector-acc_data"
      },
      "target": {
        "node_id": "npu2-post",
        "port_id": "npu2-post-acc_data"
      },
      "protocol": "valid_ready",
      "behavior": "Four final sums in 00,01,10,11 order; signed32; advance lane only on transfer."
    }
  ],
  "npu2-post": [
    {
      "id": "npu2-edge-post-config",
      "source": {
        "node_id": "npu2-control",
        "port_id": "npu2-control-post_config"
      },
      "target": {
        "node_id": "npu2-post",
        "port_id": "npu2-post-post_config"
      },
      "protocol": "valid_ready",
      "behavior": "Exactly the saved ReLU and two signed column biases; independent handshake before RUN."
    },
    {
      "id": "npu2-edge-collected-sum",
      "source": {
        "node_id": "npu2-collector",
        "port_id": "npu2-collector-acc_data"
      },
      "target": {
        "node_id": "npu2-post",
        "port_id": "npu2-post-acc_data"
      },
      "protocol": "valid_ready",
      "behavior": "Four final sums in 00,01,10,11 order; signed32; advance lane only on transfer."
    },
    {
      "id": "npu2-edge-post-result",
      "source": {
        "node_id": "npu2-post",
        "port_id": "npu2-post-result_data"
      },
      "target": {
        "node_id": "npu2-fifo",
        "port_id": "npu2-fifo-result_data"
      },
      "protocol": "valid_ready",
      "behavior": "Four bias-adjusted and optionally ReLU-clamped signed32 values in the same row-major order."
    }
  ]
}''')


def _require(value, message, code="unsupported_npu2_datapath_contract"):
    if not value:
        raise DomainError(code, message)


def _recognize(contract):
    _require(type(contract) is dict and set(contract) == {"kind", "version", "source_node", "source_job", "source_edges", "settings", "global_integration", "design_intent"}, "A complete saved datapath graph/job contract is required.")
    kind = contract["kind"]
    _require(kind in KINDS and type(contract["version"]) is int and contract["version"] == 1, "Unsupported saved datapath contract version.")
    node = contract["source_node"]
    _require(type(node) is dict and node.get("id") in KINDS[kind], "The saved node does not match this datapath family.")
    expected = EXPECTED_NODES[node["id"]]
    _require(node.get("parent_id") is None and node.get("verification") is None and all(object_hash(node.get(key)) == object_hash(value) for key, value in expected.items()), "Only the unchanged saved datapath behavior, constraints and exact public graph ports are supported.")
    _require(type(node.get("module_name")) is str and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", node["module_name"]), "A valid saved module name is required.")
    _require(object_hash(contract["source_edges"]) == object_hash(EXPECTED_EDGES[node["id"]]), "The original incident datapath edges and their language are required.")
    settings = contract["settings"]
    _require(type(settings) is dict and all(settings.get(key) == value for key, value in {"clock_name": "clk", "reset_name": "rst", "reset_active": "high", "reset_kind": "synchronous", "rtl_language": "verilog_2005"}.items()), "The saved shared clock and synchronous high reset are required.")
    intent = contract["design_intent"]
    _require(type(intent) is dict and all(type(intent.get(key)) is int and intent[key] == value for key, value in {"matrix_rows": 2, "matrix_columns": 2, "operand_bits": 8, "accumulator_bits": 32, "k_min": 1, "k_max": 8, "pe_instances": 4}.items()), "The explicit four-PE 2x2 dimensions are required.")
    integration = contract["global_integration"]
    _require(type(integration) is dict and integration.get("numerical_contract") == "C[r,c] = signed32(sum_k(signed8(A[r,k])*signed8(B[k,c])) + signed32(bias[c])); ReLU, if configured, applies after the signed32 wrap." and integration.get("reset_contract") == "Synchronous high reset cancels all in-flight transfers and clears arithmetic/control/output state; operand register bank bytes are retained. No power-loss retention claim.", "The saved numerical and shared reset contracts are required.")
    job = contract["source_job"]
    _require(type(job) is dict and set(job) == {"id", "k", "A", "B", "bias", "relu", "scope"} and type(job["id"]) is str and bool(job["id"]) and type(job["scope"]) is str and type(job["k"]) is int and 1 <= job["k"] <= 8 and type(job["relu"]) is bool, "Exactly one supported original matrix job is required.")
    k = job["k"]
    _require(type(job["A"]) is list and len(job["A"]) == 2 and all(type(row) is list and len(row) == k for row in job["A"]) and type(job["B"]) is list and len(job["B"]) == k and all(type(row) is list and len(row) == 2 for row in job["B"]) and all(type(value) is int and -128 <= value <= 127 for matrix in (job["A"], job["B"]) for row in matrix for value in row) and type(job["bias"]) is list and len(job["bias"]) == 2 and all(type(value) is int and -(1 << 31) <= value < (1 << 31) for value in job["bias"]), "Saved matrix dimensions, signed operands and two signed biases must match the job.")
    return contract


def physical_ports(kind):
    _require(kind in STREAMS, "Unsupported datapath kind.")
    ports = {"clk": ("input", 1, False), "rst": ("input", 1, False)}
    for name, (direction, width, signed) in STREAMS[kind].items():
        ports[name] = direction, width, signed
        ports[name + "_valid"] = direction, 1, False
        ports[name + "_ready"] = "output" if direction == "input" else "input", 1, False
    return ports


def projected_job(job):
    sums = [sum(job["A"][row][k] * job["B"][k][column] for k in range(job["k"])) & 0xffffffff for row in range(2) for column in range(2)]
    results = []
    for lane, value in enumerate(sums):
        value = (value + job["bias"][lane % 2]) & 0xffffffff
        results.append(0 if job["relu"] and value & 0x80000000 else value)
    return {"sums": sums, "results": results, "post_config": int(job["relu"]) | ((job["bias"][0] & 0xffffffff) << 1) | ((job["bias"][1] & 0xffffffff) << 33)}


def pair_packets(contract):
    job, constraints = contract["source_job"], contract["source_node"]["constraints"]
    row, column = constraints["row"], constraints["column"]
    return [(job["A"][row][k] & 255) | ((job["B"][k][column] & 255) << 8) | (int(k == 0) << 16) | (int(k == job["k"] - 1) << 17) for k in range(job["k"])]


def _initial(kind):
    if kind == "npu2_pe_original_job":
        return {"accumulator": 0, "valid": 0, "data": 0}
    if kind == "npu2_collector_original_job":
        return {"lane": 0}
    return {"configured": 0, "index": 0, "config": 0, "valid": 0, "data": 0}


def _outputs(kind, state, vector):
    if kind == "npu2_pe_original_job":
        return {"pair_data_ready": int(not state["valid"]), "sum_data_valid": state["valid"], "sum_data": state["data"]}
    if kind == "npu2_collector_original_job":
        lane = ("00", "01", "10", "11")[state["lane"]]
        return {"acc_data_valid": int(not vector["reset"] and vector["sum" + lane + "_valid"]), "acc_data": vector["sum" + lane], **{"sum" + other + "_ready": int(not vector["reset"] and other == lane and vector["acc_data_ready"]) for other in ("00", "01", "10", "11")}}
    return {"post_config_ready": int(not state["configured"] and not state["valid"] and state["index"] == 0), "acc_data_ready": int(state["configured"] and (not state["valid"] or vector["result_data_ready"]) and not vector["post_config_valid"]), "result_data_valid": state["valid"], "result_data": state["data"]}


def _step(kind, state, vector):
    before = _outputs(kind, state, vector)
    transfers = {name + "_transfer": int(not vector["reset"] and (vector[name + "_valid"] if direction == "input" else before[name + "_valid"]) and (before[name + "_ready"] if direction == "input" else vector[name + "_ready"])) for name, (direction, _, _) in STREAMS[kind].items()}
    after = copy.deepcopy(state)
    arithmetic = {}
    if vector["reset"]:
        after = _initial(kind)
    elif kind == "npu2_pe_original_job":
        if transfers["pair_data_transfer"]:
            packet = vector["pair_data"]
            a, b = packet & 255, (packet >> 8) & 255
            a, b = a - 256 if a & 128 else a, b - 256 if b & 128 else b
            product = a * b
            accumulator = (product if packet & 0x10000 else state["accumulator"] + product) & 0xffffffff
            after["accumulator"] = accumulator
            arithmetic = {"a": a, "b": b, "signed_product": product, "accumulator": accumulator}
            if packet & 0x20000:
                after.update(data=accumulator, valid=1)
        elif transfers["sum_data_transfer"]:
            after["valid"] = 0
    elif kind == "npu2_collector_original_job":
        if transfers["acc_data_transfer"]:
            after["lane"] = (state["lane"] + 1) % 4
    else:
        if transfers["post_config_transfer"]:
            after.update(configured=1, index=0, config=vector["post_config"])
        if transfers["acc_data_transfer"]:
            column = state["index"] % 2
            bias = (state["config"] >> (1 + 32 * column)) & 0xffffffff
            unwrapped = vector["acc_data"] + bias
            wrapped = unwrapped & 0xffffffff
            data = 0 if state["config"] & 1 and wrapped & 0x80000000 else wrapped
            after.update(valid=1, data=data, index=(state["index"] + 1) % 4, configured=int(state["index"] < 3))
            signed_acc = vector["acc_data"] - (1 << 32) if vector["acc_data"] & 0x80000000 else vector["acc_data"]
            signed_bias = bias - (1 << 32) if bias & 0x80000000 else bias
            arithmetic = {"column": column, "bias_bits": bias, "unwrapped_bit_pattern_sum": unwrapped, "signed_sum": signed_acc + signed_bias, "signed_overflow": int(not -(1 << 31) <= signed_acc + signed_bias < (1 << 31)), "wrapped": wrapped, "result": data}
        elif transfers["result_data_transfer"]:
            after["valid"] = 0
    return after, before, _outputs(kind, after, vector), transfers, arithmetic


def reference_trace(kind, vectors):
    state, trace = _initial(kind), []
    for cycle, vector in enumerate(vectors):
        next_state, before, after, transfers, arithmetic = _step(kind, state, vector)
        trace.append({"cycle": cycle, "stimulus": copy.deepcopy(vector), "before": before, "after": after, **transfers, "reference_bookkeeping": copy.deepcopy(state), "arithmetic": arithmetic})
        state = next_state
    return trace


def expand_vectors(contract):
    _recognize(contract)
    kind, job = contract["kind"], contract["source_job"]
    projection = projected_job(job)
    vectors, state = [], _initial(kind)
    def base(**changes):
        vector = {"reset": 0, "reset_pulse_before_edge": 0}
        for name, (direction, _, _) in STREAMS[kind].items():
            vector.update({name: 0, name + "_valid": 0} if direction == "input" else {name + "_ready": 0})
        if kind == "npu2_collector_original_job":
            vector.update({"sum" + lane: projection["sums"][index] for index, lane in enumerate(("00", "01", "10", "11"))})
        elif kind == "npu2_post_original_job":
            vector["post_config"] = projection["post_config"]
            vector["acc_data"] = projection["sums"][0]
        vector.update(changes)
        return vector
    def add(label, **changes):
        nonlocal state
        _require(len(vectors) < 512, "Finite saved-job recipe exceeded its bound.")
        vector = base(**changes); vector["label"] = label
        state, before, after, transfers, arithmetic = _step(kind, state, vector)
        vectors.append(vector)
        return transfers
    add("initial_reset", reset=1)
    if kind == "npu2_pe_original_job":
        pairs = pair_packets(contract)
        add("cancel_partial_or_pending", pair_data=pairs[0], pair_data_valid=1)
        add("cancel_stall")
        add("reset_cancels_partial_or_pending", reset=1)
        for job_index in range(2):
            start = 1 if job_index else 0
            for index in range(start, len(pairs)):
                add("original_pair_" + str(index), pair_data=pairs[index], pair_data_valid=1)
                if index < len(pairs) - 1:
                    add("intermediate_must_not_emit")
            if job_index == 0:
                for stall in range(3):
                    add("pending_blocks_next_original_pair", pair_data=pairs[0], pair_data_valid=1, reset_pulse_before_edge=int(stall == 1))
                add("consume_without_replacement", pair_data=pairs[0], pair_data_valid=1, sum_data_ready=1)
                add("next_job_first_after_consume", pair_data=pairs[0], pair_data_valid=1)
            else:
                for _ in range(2):
                    add("hold_final_sum")
                add("consume_final_sum", sum_data_ready=1)
        add("final_reset", reset=1)
    elif kind == "npu2_collector_original_job":
        add("reset_gates_all_lanes", reset=1, acc_data_ready=1, **{"sum" + lane + "_valid": 1 for lane in ("00", "01", "10", "11")})
        for _ in range(2):
            add("other_lanes_cannot_pass_missing_00", acc_data_ready=1, sum01_valid=1, sum10_valid=1, sum11_valid=1)
        for job_index in range(2):
            offered = {"sum" + lane + "_valid": 1 for lane in ("00", "01", "10", "11")}
            for lane in ("00", "01", "10", "11"):
                for stall in range(2):
                    add("selected_" + lane + "_stall", reset_pulse_before_edge=int(lane == "01" and stall == 0), **offered)
                add("ordered_" + lane + "_transfer", acc_data_ready=1, **offered)
                offered["sum" + lane + "_valid"] = 0
        add("cancel_mid_order_00", acc_data_ready=1, sum00_valid=1)
        add("reset_returns_lane00", reset=1, acc_data_ready=1, sum01_valid=1)
        add("after_reset_wait00", acc_data_ready=1, sum01_valid=1)
        add("restart00", acc_data_ready=1, sum00_valid=1, sum01_valid=1)
        add("restart01", acc_data_ready=1, sum01_valid=1)
    else:
        add("unconfigured_blocks_acc", acc_data_valid=1)
        add("initial_configuration_blocks_held_acc", post_config_valid=1, acc_data_valid=1)
        add("first_original_acc", acc_data_valid=1)
        add("pending_result_nonclocked_reset_pulse", reset_pulse_before_edge=1)
        add("midjob_config_blocked", post_config_valid=1)
        add("midjob_config_still_blocked", post_config_valid=1)
        add("reset_cancels_configuration_and_pending_result", reset=1, post_config_valid=1)
        add("no_stale_configuration", acc_data_valid=1)
        for round_index in range(2):
            add("fresh_original_configuration", post_config_valid=1, acc_data_valid=1)
            index = consumed = cycle = 0
            while consumed < 4:
                transfers = add("original_row_major_job_" + str(round_index), acc_data=projection["sums"][index] if index < 4 else projection["sums"][0], acc_data_valid=1, result_data_ready=(0, 0, 1, 1, 1)[cycle % 5])
                index += transfers["acc_data_transfer"]
                consumed += transfers["result_data_transfer"]
                cycle += 1
            _require(index == 4, "Exactly four original sums must be accepted under each configuration.")
            add("fifth_acc_rejected_without_fresh_config", acc_data_valid=1, result_data_ready=1)
        add("final_reset_cancels_held_fifth", reset=1, acc_data_valid=1)
    for _ in range(3):
        add("final_quiet")
    return vectors


def asserted(kind, values, vector, after=False):
    if vector["reset"] and kind != "npu2_collector_original_job":
        if not after:
            return {}
        return {("sum_data" if kind == "npu2_pe_original_job" else "result_data") + "_valid": 0}
    result = {}
    for name, (direction, _, _) in STREAMS[kind].items():
        if direction == "input":
            result[name + "_ready"] = values[name + "_ready"]
        else:
            result[name + "_valid"] = values[name + "_valid"]
            if values[name + "_valid"]:
                result[name] = values[name]
    return result


def assertion_spec(kind, values, vector, phase, allow_wait=None):
    """Shared actual TB assertions and S07 fact projection; no stronger claim."""
    exact = asserted(kind, values, vector, after=phase == "after")
    known = []
    for name, value in list(exact.items()):
        required_replacement = (kind == "npu2_post_original_job" and name == "acc_data_ready" and phase == "before"
                                and values["result_data_valid"] and vector["result_data_ready"] and vector["acc_data_valid"])
        if name == allow_wait or (name.endswith("_ready") and value == 1 and kind != "npu2_collector_original_job" and not required_replacement):
            known.append(name)
            del exact[name]
    return exact, known


def datapath_asserted_trace(plan):
    result = []
    for item in plan["reference_trace"]:
        vector = item["stimulus"]
        before, known_before = assertion_spec(plan["kind"], item["before"], vector, "before")
        after, known_after = assertion_spec(plan["kind"], item["after"], vector, "after")
        result.append({"cycle": item["cycle"], "stimulus": copy.deepcopy(vector),
                       **{key: value for key, value in item.items() if key.endswith("_transfer")},
                       "asserted_before": before if item["cycle"] else None, "asserted_after": after,
                       "known_bit_before": known_before if item["cycle"] else [], "known_bit_after": known_after})
    return result


def testbench(kind, module_name, trace, vector_hash):
    ports = physical_ports(kind)
    lines = [chr(96) + "timescale 1ns/1ps", "module hullcirq_contract_tb;", "reg clk;"]
    for name, (direction, width, _) in ports.items():
        if name != "clk":
            lines.append(f"{'reg' if direction == 'input' else 'wire'} {'' if width == 1 else f'[{width-1}:0] '}{name};")
    lines += [f"{module_name} dut (" + ", ".join(f".{name}({name})" for name in ports) + ");", "integer attempt; reg accepted;"]
    def checks(values, vector, cycle, phase, allow_wait=None):
        result = []
        exact, known = assertion_spec(kind, values, vector, phase, allow_wait)
        for name in known:
            result.append(f'if ({name} !== 0 && {name} !== 1) begin $display("HULLCIRQ_FAIL cycle={cycle} {phase} unknown {name}"); $finish; end')
        for name, value in exact.items():
            width = ports[name][1]
            expected = f"{width}'h{value:x}"
            result.append(f'if ({name} !== {expected}) begin $display("HULLCIRQ_FAIL cycle={cycle} {phase} signal={name} expected=%h actual=%h",{expected},{name}); $finish; end')
        return result
    lines += ["initial begin", "clk=0;"]
    for item in trace:
        cycle, vector = item["cycle"], item["stimulus"]
        lines += [f"// Saved GUI job recipe {cycle}: {vector['label']}", "clk=0;"]
        for name, (direction, width, _) in ports.items():
            if direction == "input" and name != "clk":
                lines.append(f"{name}={width}'h{vector['reset' if name == 'rst' else name]:x};")
        if vector["reset_pulse_before_edge"]:
            lines += ["// Pulse rst without a clock: synchronous state must survive after deassertion.", "#1; rst=1; #1;"]
            if kind == "npu2_collector_original_job":
                gated = dict(item["before"])
                gated.update({name: 0 for name in gated if name.endswith(("_ready", "_valid"))})
                gated_vector = dict(vector, reset=1)
                lines += checks(gated, gated_vector, cycle, "during nonclocked reset")
            lines += ["rst=0; #1;"] + checks(item["before"], vector, cycle, "after nonclocked reset")
        waits = [name for name, (direction, _, _) in STREAMS[kind].items() if direction == "input" and item[name + "_transfer"]]
        any_output = any(item[name + "_transfer"] for name, (direction, _, _) in STREAMS[kind].items() if direction == "output")
        wait_name = waits[0] + "_ready" if len(waits) == 1 and not any_output and kind != "npu2_collector_original_job" else None
        if wait_name:
            lines += ["// Hold source-job offer until actual acceptance; 64 is only a finite harness progress bound.", "accepted=0; begin: wait_" + str(cycle), "for(attempt=0;attempt<64;attempt=attempt+1) begin", "#4;"]
            lines += checks(item["before"], vector, cycle, "before", wait_name)
            lines += [f"accepted=({wait_name} === 1'b1); #1; clk=1; #1;", "if (accepted) begin"]
            lines += checks(item["after"], vector, cycle, "after")
            lines += ["#4; clk=0; disable wait_" + str(cycle) + "; end"]
            lines += checks(item["before"], vector, cycle, "waiting", wait_name)
            lines += ["#4; clk=0; end", f'$display("HULLCIRQ_FAIL cycle={cycle} finite harness acceptance bound reached"); $finish;', "end"]
        else:
            lines += ["#4;"]
            if cycle:
                lines += checks(item["before"], vector, cycle, "before")
            lines += ["#1; clk=1; #1;"] + checks(item["after"], vector, cycle, "after") + ["#4; clk=0;"]
    lines += [f'$display("HULLCIRQ_PASS vectors={len(trace)} vector_hash={vector_hash}");', "$finish;", "end", "endmodule", ""]
    return "\n".join(lines)


def _plan(contract, node_input_hash):
    _recognize(contract)
    kind = contract["kind"]
    vectors = expand_vectors(contract)
    trace = reference_trace(kind, vectors)
    vector_hash = object_hash(vectors)
    tb = testbench(kind, contract["source_node"]["module_name"], trace, vector_hash)
    output = next(name for name, (direction, _, _) in STREAMS[kind].items() if direction == "output")
    coverage = {name + "_transfers": sum(item[name + "_transfer"] for item in trace) for name in STREAMS[kind]}
    coverage.update(nonclocked_reset_pulse_checks=sum(v["reset_pulse_before_edge"] for v in vectors), reset_cycles=sum(v["reset"] for v in vectors), output_stall_cycles=sum(not v["stimulus"]["reset"] and v["before"][output + "_valid"] and not v["stimulus"][output + "_ready"] for v in trace), source_job_k=contract["source_job"]["k"], source_job_relu=contract["source_job"]["relu"], source_job_sums=projected_job(contract["source_job"])["sums"], source_job_results=projected_job(contract["source_job"])["results"])
    if kind == "npu2_pe_original_job":
        coverage["negative_product_transfers"] = sum(v["arithmetic"].get("signed_product", 0) < 0 for v in trace)
        coverage["no_same_cycle_replacement_checks"] = sum(v["sum_data_transfer"] and v["stimulus"]["pair_data_valid"] for v in trace)
        coverage["complete_original_jobs"] = 2
    elif kind == "npu2_post_original_job":
        coverage["same_cycle_replacement_transfers"] = sum(v["result_data_transfer"] and v["acc_data_transfer"] for v in trace)
        coverage["unconfigured_offer_rejections"] = sum(not v["stimulus"]["reset"] and not v["reference_bookkeeping"]["configured"] and v["stimulus"]["acc_data_valid"] and not v["acc_data_transfer"] for v in trace)
        coverage["complete_original_jobs"] = 2
        coverage["signed_overflow_transfers"] = sum(v["arithmetic"].get("signed_overflow", 0) for v in trace)
        coverage["wrapped_addition_transfers"] = sum(v["arithmetic"].get("unwrapped_bit_pattern_sum", 0) > 0xffffffff for v in trace)
        coverage["relu_clamped_transfers"] = sum(v["arithmetic"].get("result") == 0 and bool(v["arithmetic"].get("wrapped", 0) & 0x80000000) and bool(v["reference_bookkeeping"]["config"] & 1) for v in trace)
    else:
        coverage["complete_original_jobs"] = 2
        coverage["reset_returns_first_lane"] = 1
    return {"kind": kind, "version": 1, "source_node_id": contract["source_node"]["id"], "module_name": contract["source_node"]["module_name"], "node_input_hash": node_input_hash, "contract": copy.deepcopy(contract), "contract_hash": object_hash(contract), "expanded_vectors": vectors, "vector_hash": vector_hash, "reference_trace": trace, "reference_trace_hash": object_hash(trace), "testbench": tb, "testbench_sha256": content_hash(tb), "vector_count": len(vectors), "testbench_template_version": TEMPLATE,
            "initialization_origin": "first_saved_job_projection_vector_asserting_synchronous_reset", "stimulus_origin": "original_design.verification_jobs[0]_and_exact_saved_datapath_node_edges_contract", "reference_origin": "ordinary_program_independent_signed_integer_and_handshake_state_machines", "testbench_origin": "ordinary_program_from_saved_job_projection_and_independent_reference", "stimulus_timing": "saved_job_recipe_with_actual_handshake_waits_when_no_other_transfer_is_pending", "coverage": coverage, "signal_checks": [name for name, (direction, _, _) in physical_ports(kind).items() if direction == "output"],
            "limits": ["Finite projection and handshake replays of the one original saved 2x2 matrix job only; not exhaustive or formal.", "Recipe trace is an earliest-acceptance independent reference, not an observed DUT waveform or cycle count.", "Each eligible source offer waits at most 64 actual clocks, a finite harness bound, not a circuit timeout requirement.", "Only active output payloads are compared. PE/post combinational reset gating is not required by their synchronous-reset specifications.", "Original K, operands, bias and ReLU mode are preserved; unexercised values, overflow or ReLU modes are not proven.", "No cross-node integration, full-NPU completion, timing, PDK, physical DRC/LVS or post-layout verification is claimed."]}


def build_datapath_plan(design, node_id, template_version=None):
    _require(template_version in (None, TEMPLATE), "Unsupported 2x2 datapath testbench template.", "unsupported_verification_template")
    kind = next((kind for kind, ids in KINDS.items() if node_id in ids), None)
    _require(kind is not None, "Select one supported saved explicit 2x2 datapath node.")
    nodes = [node for node in design.get("nodes", []) if node.get("id") == node_id]
    jobs = design.get("verification_jobs")
    _require(len(nodes) == 1 and type(jobs) is list and len(jobs) == 1, "One saved node and one original matrix job are required.")
    contract = {"kind": kind, "version": 1, "source_node": copy.deepcopy(nodes[0]), "source_job": copy.deepcopy(jobs[0]), "source_edges": copy.deepcopy([edge for edge in design.get("edges", []) if any(edge.get(side, {}).get("node_id") == node_id for side in ("source", "target"))]), **{key: copy.deepcopy(design.get(key)) for key in ("settings", "global_integration", "design_intent")}}
    _recognize(contract)
    context = build_node_context(design, "verification-source", node_id)
    ports = {port["name"]: (port["direction"], port["width"], port["signed"]) for port in context["interface"]["ports"]}
    _require(ports == physical_ports(kind), "The expanded public interface must match the exact saved datapath streams.", "invalid_verification_interface")
    return _plan(contract, context["node_input_hash"])


def validate_datapath_plan(plan):
    try:
        valid = object_hash(plan) == object_hash(_plan(plan["contract"], plan["node_input_hash"]))
    except (KeyError, TypeError, ValueError, AttributeError, DomainError):
        valid = False
    _require(valid, "Frozen 2x2 original-job datapath evidence is inconsistent.", "invalid_verification_plan")
