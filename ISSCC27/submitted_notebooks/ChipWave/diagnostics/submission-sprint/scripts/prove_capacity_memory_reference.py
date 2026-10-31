"""Prove reference memory safety with explicit queue invariants, no RTL changes."""
import json
import argparse
import re
import subprocess
import time
from pathlib import Path

from check_capacity_properties import harness
from study_protocol import digest, write_json

ROOT=Path(__file__).resolve().parents[1]
INVARIANTS="""
// Proof-only inductive invariants; the original reference source is unchanged.
always @(posedge clk)if(rst_n)begin
 assert(count[0]+count[1]<=SLOTS);
 assert((done & ~used)==0);
 assert((discard & ~used)==0);
 assert((discard & done)==0);
 if(locked)assert(!used[locked_slot]);
 if(locked && !flush)assert(req_valid[locked_client]);
 for(integer c=0;c<2;c=c+1)begin
  assert(count[c]<=SLOTS);
  assert(tail[c]==((head[c]+count[c])%SLOTS));
  for(integer i=0;i<SLOTS;i=i+1)if(i<count[c])begin
   assert(used[queue[c][(head[c]+i)%SLOTS]]);
   assert(!discard[queue[c][(head[c]+i)%SLOTS]]);
   assert(owner[queue[c][(head[c]+i)%SLOTS]]==c);
   for(integer j=0;j<SLOTS;j=j+1)if(i<j && j<count[c])
    assert(queue[c][(head[c]+i)%SLOTS]!=queue[c][(head[c]+j)%SLOTS]);
  end
 end
 for(integer s=0;s<SLOTS;s=s+1)if(used[s] && !discard[s])begin
  assert((count[0]>0 && queue[0][head[0]]==s) ||
         (count[0]>1 && queue[0][(head[0]+1)%SLOTS]==s) ||
         (count[0]>2 && queue[0][(head[0]+2)%SLOTS]==s) ||
         (count[0]>3 && queue[0][(head[0]+3)%SLOTS]==s) ||
         (count[1]>0 && queue[1][head[1]]==s) ||
         (count[1]>1 && queue[1][(head[1]+1)%SLOTS]==s) ||
         (count[1]>2 && queue[1][(head[1]+2)%SLOTS]==s) ||
         (count[1]>3 && queue[1][(head[1]+3)%SLOTS]==s));
 end
end
"""


def prove(revision=None):
    if revision and not re.fullmatch(r"[a-z0-9-]+",revision):
        raise ValueError("Unsafe proof revision")
    task=ROOT/"tasks/B2";out=task/"qualification"/("inductive-queue-invariants"+("-"+revision if revision else ""))
    if out.exists():
        raise ValueError("Existing proof attempt retained")
    out.mkdir()
    reference=task/"grader/reference.sv"
    original_hash=digest(reference)
    source=reference.read_text()
    assert source.count("endmodule")==1
    instrumented=out/"reference-with-assertions.sv"
    instrumented.write_text(source.replace("endmodule",INVARIANTS+"\nendmodule"))
    bench=out/"properties.sv";bench.write_text(harness(task,True))
    script=out/"prepare.ys"
    script.write_text(f"read_verilog -formal -sv {instrumented} {bench}\n"
        "prep -top capacity_properties -flatten\nasync2sync\nmemory_map\nopt_clean\ndffunmap\n"
        f"write_smt2 -wires {out/'design.smt2'}\n")
    start=time.monotonic()
    with (out/"prepare.log").open("w") as log:
        subprocess.run(["yosys","-Q","-T","-s",str(script)],stdout=log,stderr=subprocess.STDOUT,
                       check=True,timeout=120)
    results={}
    for label,flags in (("base",[]),("induction",["-i"])):
        with (out/(label+".log")).open("w") as log:
            result=subprocess.run(["yosys-smtbmc","-s","z3","-t","6","--timeout","120",
                "--dump-vcd",str(out/(label+"-counterexample.vcd")),*flags,str(out/"design.smt2")],
                stdout=log,stderr=subprocess.STDOUT,timeout=150)
        text=(out/(label+".log")).read_text()
        results[label]=dict(passed=result.returncode==0 and "Status: PASSED" in text,
                            timed_out="timeout" in text.lower(),exit_code=result.returncode)
    unchanged=digest(reference)==original_hash
    report=dict(passed=unchanged and all(r["passed"] for r in results.values()),results=results,
        source_sha256=original_hash,instrumented_sha256=digest(instrumented),
        interface_harness_sha256=digest(bench),original_reference_unchanged=unchanged,
        scope="Reference-only inductive queue invariants plus all public memory-interface safety assertions; not a progress proof",
        elapsed_seconds=time.monotonic()-start,model_calls=0,physical_attempts=0)
    write_json(out/"qualification.json",report)
    print(json.dumps(report),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision")
    prove(parser.parse_args().revision)
