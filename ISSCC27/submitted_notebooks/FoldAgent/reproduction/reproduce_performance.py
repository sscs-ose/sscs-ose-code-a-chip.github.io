"""Portable entry for the original 162-case paired experiment; default is input checking."""
from pathlib import Path
import argparse,hashlib,json,os,random,sys
import performance
ROOT=Path(__file__).resolve().parents[1]
def check_inputs():
    sources=json.loads((ROOT/"sources.json").read_text())
    for name,item in sources.items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==item["sha256"],name
    reports=[json.loads((ROOT/"evidence"/name).read_text()) for name in
             ["reference-performance.json","P0-performance.json"]]
    tb=performance.testbench((ROOT/"design/verif/tb_lb.sv").read_text())
    checker="sha256:"+hashlib.sha256(tb.encode()).hexdigest()
    assert tb==(ROOT/"reproduction/tb_folding_perf.sv").read_text()
    hashes=[checker]
    for seed in [11,23,37]:
        for kind in ["ready","latency"]:
            hashes.append(performance.digest(ROOT/f"reproduction/stimulus/{kind}-{seed}.hex"))
        rng=random.Random(seed)
        x=[rng.randrange(-128,128) for _ in range(64)]
        w=[[rng.randrange(-128,128) for _ in range(8)] for _ in range(64)]
        for k in [4,16,64]:
            expected=[sum(x[i]*w[i][j] for i in range(k)) for j in range(8)]
            vector=" ".join(map(str,[*x,*[v for row in w for v in row],*expected]))+"\n"
            assert vector==(ROOT/f"reproduction/vectors/vectors-{seed}-{k}.txt").read_text()
            hashes.append("sha256:"+hashlib.sha256(vector.encode()).hexdigest())
    workload=hashlib.sha256("".join(hashes).encode()).hexdigest()
    for report,rtl in zip(reports,["reproduction/reference/rtl/lb_feedback.sv","design/rtl/lb_feedback.sv"]):
        assert performance.digest(ROOT/rtl)==report["rtl_digest"]
        assert checker==report["checker_digest"] and workload==report["workload_digest"]
    sys.path.insert(0,str(ROOT))
    import review
    assert len(review.compare_performance(*reports))==162
    return dict(status="passed",checker_digest=checker,workload_digest=workload,
                generated_vectors_verified=9,stored_event_files_verified=6,simulations_run=0)
def run(output):
    check_inputs()
    output=output.resolve()
    output.mkdir(parents=True,exist_ok=False)
    os.environ.setdefault("IVERILOG_EXE","iverilog")
    os.environ.setdefault("VVP_EXE","vvp")
    # Both designs use the identical original checker and stored event schedules.
    reference=performance.measure(ROOT/"design",ROOT/"reproduction/reference/rtl/lb_feedback.sv",
        output/"reference",event_directory=ROOT/"reproduction/stimulus")
    candidate=performance.measure(ROOT/"design",ROOT/"design/rtl/lb_feedback.sv",
        output/"two-tier",event_directory=ROOT/"reproduction/stimulus",reference=reference)
    sys.path.insert(0,str(ROOT))
    import review
    pairs=review.compare_performance(reference,candidate)
    performance.save(output/"comparison.json",dict(pairs=pairs,comparison=candidate["comparison"]))
    assert candidate["verdict"]=="passed",candidate["comparison"]
    # Record departures from the archived experiment explicitly, even for a faster result.
    for current,name in [(reference,"reference-performance.json"),(candidate,"P0-performance.json")]:
        old=json.loads((ROOT/"evidence"/name).read_text())
        fields=("K","mapping","seed","profile","output_stall","completion_cycles","supply_cycles","useful_bytes","max_latency_cycles")
        assert [[c[k] for k in fields] for c in current["cases"]]==[[c[k] for k in fields] for c in old["cases"]],name
    print("Both 162-case measurements match the archived metrics.")
if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run",type=Path,metavar="NEW_OUTPUT_DIR",help="explicitly run 324 RTL simulations; directory must be new")
    args=ap.parse_args()
    if args.run:run(args.run)
    else:print(json.dumps(check_inputs(),indent=2))
