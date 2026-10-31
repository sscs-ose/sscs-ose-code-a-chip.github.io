from pathlib import Path
import subprocess,json,hashlib,re,os,time
from datetime import datetime,timezone
run=Path(__file__).resolve().parent
package=run/"ChipNebula-3D-review-v3-20261030"
workspace=run.parents[1]
bindir=workspace/".tools/chipnebula-sky130/bin"
env={"PATH":str(bindir)+":/usr/bin:/bin","LANG":"C.UTF-8","LC_ALL":"C.UTF-8",
     "PYTHONNOUSERSITE":"1","PYTHONDONTWRITEBYTECODE":"1",
     "IVERILOG_EXE":str(bindir/"iverilog"),"VVP_EXE":str(bindir/"vvp"),
     "SKY130_TT_LIB":str(run/"dependencies/sky130_fd_sc_hd__tt_025C_1v80.lib"),
     "STA_OUTPUT":str(run/"joint")}
expected_lib=json.loads((package/"physical/library-requirement.json").read_text())["sha256"]
assert hashlib.sha256(Path(env["SKY130_TT_LIB"]).read_bytes()).hexdigest()==expected_lib
(run/"joint").mkdir()
accepted=json.loads((package/"evidence/L1-acceptance.json").read_text())["joint"]["cases"]
results={}
for case in ["min","nominal","max"]:
    cmd=[str(bindir/"sta"),"-exit",str(package/"physical"/(case+".tcl"))]
    start=time.monotonic();log=run/"joint"/(case+".log")
    with log.open("w") as out:proc=subprocess.run(cmd,cwd=package,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=120)
    raw=log.read_text()
    assert proc.returncode==0 and not re.search(r"^Error[: ]",raw,re.M),case
    sta=re.search(r"STACKLINK_STA setup_ns=(\S+) hold_ns=(\S+) instances=(\d+)",raw)
    erc=re.search(r"STACKLINK_ERC slew=(\d+) capacitance=(\d+) fanout=(\d+) setup=(\d+) hold=(\d+)",raw)
    assert sta and erc and all(int(v)==0 for v in erc.groups()),case
    setup,hold=float(sta[1]),float(sta[2])
    assert abs(setup-accepted[case]["setup_ns"])<1e-8 and abs(hold-accepted[case]["hold_ns"])<1e-8,case
    classes=re.findall(r"^CLOSURE_PATH_CLASS (.+)$",raw,re.M)
    assert set(classes)=={"L0->L0","L0->L1","L1->L0","L1->L1","L0->L1->L0","L1->L0->L1"}
    results[case]=dict(status="passed",setup_ns=setup,hold_ns=hold,ERC=list(map(int,erc.groups())),
        path_classes=classes,seconds=time.monotonic()-start,log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
        command=cmd)
    (run/"joint/result.json").write_text(json.dumps(results,indent=2)+"\n")
    print("Joint STA",case,"matches accepted values",flush=True)
cmd=[str(run/"python/bin/python"),str(package/"reproduction/reproduce_performance.py"),"--run",str(run/"paired")]
start=time.monotonic()
with (run/"performance-driver.log").open("w") as out:
    proc=subprocess.run(cmd,cwd=package,env=env,stdout=out,stderr=subprocess.STDOUT)
receipt=dict(command=cmd,returncode=proc.returncode,seconds=time.monotonic()-start,
    finished_at=datetime.now(timezone.utc).isoformat())
(run/"performance-driver.receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
assert proc.returncode==0,(run/"performance-driver.log").read_text()
print("324 RTL simulations completed and all archived metrics matched",flush=True)
