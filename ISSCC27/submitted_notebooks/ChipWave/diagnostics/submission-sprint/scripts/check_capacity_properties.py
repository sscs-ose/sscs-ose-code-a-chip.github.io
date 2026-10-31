"""Bounded public-interface properties, independently of the reference internals."""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from study_protocol import digest, write_json

ROOT = Path(__file__).resolve().parents[1]


MEMORY_GROUPS = ("reset","acceptance","response_0","response_1","request_hold")


def harness(task, legal_memory=False, group="all"):
    interface = json.loads((task/"agent/spec/interface.json").read_text())
    declarations, names = [], []
    for port in interface["ports"]:
        name, width, direction = port["name"], port["width"], port["direction"]
        names.append(name)
        if name == "clk":
            continue
        declarations.append(("(* anyseq *) reg " if direction == "in" else "wire ")
                            + (f"[{width-1}:0] " if width > 1 else "") + name+";")
    if task.name.startswith("A"):
        if group!="all":
            raise ValueError("Property decomposition currently targets memory interfaces")
        assumptions = """
 if(past_valid && rst_n && $past(rst_n) && !cancel_valid && !$past(cancel_valid))begin
  if($past(cmd_valid && !cmd_ready))begin
   assume(cmd_valid);assume({cmd_id,cmd_len}==$past({cmd_id,cmd_len}));
  end
  if($past(data_valid && !data_ready))begin
   assume(data_valid);assume({data_id,data_a,data_b}==$past({data_id,data_a,data_b}));
  end
 end
"""
        properties = """
 if(!rst_n)begin assert(!cmd_ready);assert(!data_ready);assert(!rsp_valid);end
 if(cmd_ready)begin assert(cmd_len>=1);assert(cmd_len<=64);end
 if(past_valid && rst_n && $past(rst_n) && !cancel_valid && !$past(cancel_valid)
    && $past(rsp_valid && !rsp_ready))begin
  assert(rsp_valid);assert({rsp_id,rsp_data}==$past({rsp_id,rsp_data}));
 end
"""
    else:
        assumptions = """
 if(past_valid && rst_n && $past(rst_n) && !flush && !$past(flush))begin
  for(integer c=0;c<2;c=c+1)
   if($past(req_valid[c] && !req_ready[c]))begin
    assume(req_valid[c]);
    assume({req_write[c],req_addr[32*c+:32],req_wdata[32*c+:32],req_wstrb[4*c+:4],req_id[8*c+:8]}
     ==$past({req_write[c],req_addr[32*c+:32],req_wdata[32*c+:32],req_wstrb[4*c+:4],req_id[8*c+:8]}));
   end
 end
"""
        memory_properties = dict(reset="""
 if(!rst_n || flush)begin assert(req_ready==0);assert(rsp_valid==0);assert(!m_req_valid);end
""", acceptance="""
 assert(req_ready!=2'b11);
 if(|req_ready)assert(m_req_valid && m_req_ready);
 if(m_req_valid && m_req_ready)assert(|req_ready);
 for(integer c=0;c<2;c=c+1)begin
  if(req_ready[c])begin
   assert(req_valid[c]);
   assert({m_req_addr,m_req_write,m_req_wdata,m_req_wstrb}==
    {req_addr[32*c+:32],req_write[c],req_wdata[32*c+:32],req_wstrb[4*c+:4]});
  end
 end
""", request_hold="""
 if(past_valid && rst_n && $past(rst_n) && !flush && !$past(flush)
    && $past(m_req_valid && !m_req_ready))begin
  assert(m_req_valid);
  assert({m_req_tag,m_req_addr,m_req_write,m_req_wdata,m_req_wstrb}==
   $past({m_req_tag,m_req_addr,m_req_write,m_req_wdata,m_req_wstrb}));
 end
""")
        for client in range(2):
            memory_properties["response_"+str(client)] = """
 for(integer c=CLIENT;c<=CLIENT;c=c+1)begin
  if(past_valid && rst_n && $past(rst_n) && !flush && !$past(flush)
     && $past(rsp_valid[c] && !rsp_ready[c]))begin
   assert(rsp_valid[c]);
   assert({rsp_id[8*c+:8],rsp_rdata[32*c+:32],rsp_err[c]}==
    $past({rsp_id[8*c+:8],rsp_rdata[32*c+:32],rsp_err[c]}));
  end
 end
""".replace("CLIENT",str(client))
        properties = "".join(memory_properties[name] for name in MEMORY_GROUPS) if group=="all" else memory_properties[group]
    environment = ""
    if legal_memory:
        if task.name not in ("B1", "B2"):
            raise ValueError("Memory environment applies only to memory tasks")
        environment = """
reg [3:0] external_pending=0;
always @(posedge clk)begin
 if(!rst_n)external_pending<=0;
 else begin
  if(m_rsp_valid)assume(external_pending[m_rsp_tag] ||
    (m_req_valid && m_req_ready && m_req_tag==m_rsp_tag));
  if(m_rsp_valid && m_rsp_ready)external_pending[m_rsp_tag]<=0;
  if(m_req_valid && m_req_ready)external_pending[m_req_tag]<=1;
  if(past_valid && $past(rst_n) && $past(m_rsp_valid && !m_rsp_ready))begin
   assume(m_rsp_valid);
   assume({m_rsp_tag,m_rsp_rdata,m_rsp_err}==$past({m_rsp_tag,m_rsp_rdata,m_rsp_err}));
  end
 end
end
"""
    return (
        "module capacity_properties(input clk, output reg seen_output=0);\n"
        +"\n".join(declarations)+"\n"+interface["top"]+" dut("
        +",".join(f".{name}({name})" for name in names)+");\n"
        "reg past_valid=0;\nalways @(posedge clk)begin\n"
        " if(!past_valid)assume(!rst_n);\n past_valid<=1;\n"
        " if(rst_n && |rsp_valid)seen_output<=1;\n"+assumptions+properties+"\nend\n"+environment+"endmodule\n")


def check(name, depth=12, solver="sat", legal_memory=False, timeout=120, group="all"):
    task = ROOT/"tasks"/name
    if solver not in ("sat", "smt"):
        raise ValueError("Unknown bounded solver")
    if not 1 <= timeout <= 900:
        raise ValueError("Preparation solver timeout must be between 1 and 900 seconds")
    out = task/"qualification"/(f"properties-depth{depth}"+("-smt" if solver == "smt" else "")
                               +("-legal-memory" if legal_memory else "")
                               +(f"-timeout{timeout}" if timeout != 120 else "")
                               +("-"+group if group!="all" else ""))
    if out.exists():
        raise ValueError("Prior bounded-property evidence retained")
    out.mkdir()
    source = task/"grader/reference.sv"
    bench = out/"properties.sv"
    body = harness(task, legal_memory, group)
    if solver == "smt":
        body = body.replace(" if(rst_n && |rsp_valid)seen_output<=1;",
                            " if(rst_n && |rsp_valid)seen_output<=1;\n cover(seen_output);")
    bench.write_text(body)
    script = out/"check.ys"
    prefix = (
        f"read_verilog -formal -sv {source} {bench}\n"
        "prep -top capacity_properties -flatten\n"
        "async2sync\nmemory_map\nopt_clean\ndffunmap\n")
    script.write_text(prefix + (
        f"sat -seq {depth} -set-assumes -prove-asserts -verify -timeout {timeout}\n"
        f"sat -seq {depth} -set-assumes -set-at {depth} seen_output 1 -show seen_output -timeout {timeout}\n"
        if solver == "sat" else f"write_smt2 -wires {out/'design.smt2'}\n"))
    start = time.monotonic()
    with (out/"solver.log").open("w") as log:
        result = subprocess.run(["yosys", "-Q", "-T", "-s", str(script)],
                                stdout=log, stderr=subprocess.STDOUT, timeout=2*timeout+60)
    log = (out/"solver.log").read_text()
    proof = result.returncode == 0 and "SAT proof finished - no model found: SUCCESS!" in log
    reachable = "SAT solving finished - model found:" in log
    code = result.returncode
    timed_out = "TIMEOUT" in log
    if solver == "smt" and result.returncode == 0:
        outcomes = {}
        for label, flags in (("safety", []), ("reachability", ["-c"])):
            path = out/(label+".log")
            with path.open("w") as handle:
                solved = subprocess.run(["yosys-smtbmc", "-s", "z3", "-t", str(depth),
                    "--timeout", str(timeout), *flags, str(out/"design.smt2")],
                    stdout=handle, stderr=subprocess.STDOUT, timeout=timeout+30)
            text = path.read_text()
            outcomes[label] = solved.returncode == 0 and "Status: PASSED" in text
            timed_out |= "timeout" in text.lower()
            if solved.returncode:
                code = solved.returncode
        proof, reachable = outcomes["safety"], outcomes["reachability"]
    report = dict(task=name, passed=proof and reachable, bounded_depth=depth,
        safety_passed=proof, result_reachable=reachable, elapsed_seconds=time.monotonic()-start,
        source_sha256=digest(source), harness_sha256=digest(bench), solver_script_sha256=digest(script),
        properties="Reset suppression, legal accepts, request attribution and backpressure stability",
        scope="Bounded safety only; no unbounded correctness or 128/512-cycle progress proof",
        environment=("Public memory contract: responses require an accepted request; no duplicate response; "
                     "response held under backpressure; reset clears external pipeline"
                     if legal_memory else "Unrestricted downstream memory response inputs"),
        solver=solver, property_group=group, solver_timeout_seconds=timeout, solver_timed_out=timed_out,
        exit_code=code, model_calls=0, physical_attempts=0)
    write_json(out/"qualification.json", report)
    print(json.dumps(report), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, choices=("A1", "A2", "B1", "B2"))
    parser.add_argument("--solver", choices=("sat", "smt"), default="sat")
    parser.add_argument("--legal-memory", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--group",choices=("all",*MEMORY_GROUPS),default="all")
    args = parser.parse_args()
    raise SystemExit(0 if check(args.task, solver=args.solver, legal_memory=args.legal_memory,
                               timeout=args.timeout,group=args.group)["passed"] else 1)
