"""Run the same baseline, candidate and verification sequence for every design."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
from time import perf_counter
import numpy as np
from .project import ROOT
from .measure import measure
from .design import read_design,verify,map_devices
from .circuit import mesh,solve
from .sensitivity import calibrate
from .system import assemble
from .prediction import predict
from .actions import discover,widen,resistance_changes,node_nets
from .metric_policy import evaluate_metrics,constraint_report


def write(path,value):
    path.write_text(json.dumps(value,indent=2)+"\n")


def score(values,project):
    return sum(m["objective"] for m in evaluate_metrics(values,project).values())


def baseline(project,folder):
    write(folder/"project.json",project)
    design=read_design(project,folder/"input")
    verify(project,project["layout"],folder/"verification",folder/"input/reference.spice")
    mapping=map_devices(project,design,folder/"verification")
    network=mesh(project,folder/"verification/layout.gds",mapping)
    node_nets(network,design)
    state=solve(design,network,folder/"baseline")
    measured,gradient,system=calibrate(project,folder/"baseline",folder/"calibration")
    write(folder/"baseline.json",measured)
    return design,mapping,measured,gradient,system


def restore(project,folder):
    state=json.loads((folder/"baseline/summary.json").read_text())
    network=json.loads((folder/"baseline/network.json").read_text())
    system=assemble(network,state,project)
    data=np.load(folder/"calibration/gradients.npz")
    system["Ydc"]=data["Ydc"];system["baseline"]=json.loads((folder/"baseline.json").read_text())
    mapping=map_devices(project,state["design"],folder/"verification")
    return state["design"],mapping,system["baseline"],data["dmetric_dR"],system


def candidates(project,folder,design,mapping,measured,gradient,system):
    source=folder/"verification/layout.oas"
    actions=discover(project,source,system["network"],design)
    write(folder/"actions.json",actions)
    names=list(project["metrics"]);reference=measured["metrics"];J0=score(reference,project)
    rows=[]
    for action in actions["actions"]:
        changes=resistance_changes(system["network"],action)
        delta=gradient[list(changes)].T@np.array(list(changes.values())) if changes else np.zeros(len(names))
        first={name:reference[name]+float(delta[k]) for k,name in enumerate(names)}
        rows.append({"id":action["id"],"geometry":action,"first_order_values":first,
                     "first_order_benefit":J0-score(first,project),"status":"first_order"})
    rows.sort(key=lambda r:r["first_order_benefit"],reverse=True)
    count=project["refine_count"];selected=rows if count is None else rows[:count]
    for row in selected:
        started=perf_counter()
        name=row["id"];target=folder/"candidates"/name;target.mkdir(parents=True)
        widen(project,source,target/"candidate.oas",row["geometry"])
        try:
            verify(project,target/"candidate.oas",target/"verification",folder/"input/reference.spice")
            network=mesh(project,target/"verification/layout.gds",mapping)
            prediction=predict(project,folder/"baseline",target/"prediction",network,system)
            values=prediction["values"];benefit=J0-score(values,project)
            row.update(status="predicted" if prediction["usable"] else "needs_verification",
                       predicted_values=values,prediction=prediction,predicted_benefit=benefit,
                       benefit_per_area=benefit/row["geometry"]["added_area_um2"],
                       predicted_constraints=constraint_report(values,reference,project))
            print(name,"predicted",values,flush=True)
        except (ValueError,RuntimeError,subprocess.CalledProcessError) as error:
            row.update(status="rejected",reason=str(error))
            print(name,"rejected:",error,flush=True)
        row["prediction_seconds"]=perf_counter()-started

    write(folder/"predictions.json",rows)
    return rows


def verify_candidate(project,folder,row,design,mapping,reference):
    target=folder/"candidates"/row["id"]
    network=mesh(project,target/"verification/layout.gds",mapping)
    state=solve(design,network,target/"measured")
    actual,_=measure(project,target/"measured",target/"AC_measurement")
    values=actual["metrics"]
    errors={}
    for name,spec in project["metrics"].items():
        error=abs(values[name]-row["predicted_values"][name])
        change=abs(values[name]-reference[name])
        floor=spec.get("prediction_absolute_tolerance",.001 if spec["measurement"]=="gain_dB" else 1e3)
        limit=max(floor,.03*change)
        errors[name]={"absolute":error,"change_relative":error/change if change>floor else None,
                      "acceptance_limit":limit,"passed":error<=limit}
    row.update(status="verified",measured_values=values,measured_benefit=score(reference,project)-score(values,project),
               measured_constraints=constraint_report(values,reference,project),prediction_errors=errors,
               source_currents_A=state["source_currents_A"],power_W=state["power_W"],bode_file=actual["bode_file"])
    print(row["id"],"ngspice",values,flush=True)


def fingerprints(project):
    files=[*Path(__file__).parent.glob("*.py"),ROOT/"scripts/perfpdn.py",
           Path(project["project_file"]),Path(project["layout"]),Path(project["testbench"]),
           *Path(project["testbench"]).parent.glob("*.sch"),*Path(project["testbench"]).parent.glob("*.sym"),
           ROOT/"config/pdk.lock.json",ROOT/"config/ngspice.lock.json",ROOT/"uv.lock"]
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def run(project,folder=None,baseline_only=False,resume=False,verify_all=False):
    started=perf_counter()
    folder=Path(folder).resolve() if folder else ROOT/"output"/project["name"]/"unified"/datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    folder.mkdir(parents=True,exist_ok=resume)
    hashes=fingerprints(project)
    if resume:
        saved=json.loads((folder/"project.json").read_text())
        proof=json.loads((folder/"provenance.json").read_text())
        if saved!=project or proof["source_sha256"]!=hashes:
            raise ValueError("Resume requires unchanged project inputs and shared source files.")
        if (folder/"candidates").exists():
            raise ValueError("Resume accepts a baseline-only analysis; choose a new output for another study.")
        design,mapping,measured,gradient,system=restore(project,folder)
    else:
        write(folder/"provenance.json",{"source_sha256":hashes,"state":"running"})
        design,mapping,measured,gradient,system=baseline(project,folder)
    print("Baseline:",measured["metrics"],flush=True)
    baseline_seconds=perf_counter()-started
    rows=[] if baseline_only else candidates(project,folder,design,mapping,measured,gradient,system)
    if rows and not any("predicted_values" in r for r in rows):
        raise ValueError(f"No finite candidate prediction succeeded; inspect {folder/'predictions.json'}.")
    eligible=[r for r in rows if "predicted_values" in r and r["predicted_benefit"]>0 and r["predicted_constraints"]["passed"]]
    eligible.sort(key=lambda r:r["predicted_benefit"],reverse=True)

    verification_rows=[r for r in rows if "predicted_values" in r] if verify_all else eligible[:project["verification_count"]]
    for row in verification_rows:
        tick=perf_counter()
        try:
            verify_candidate(project,folder,row,design,mapping,measured["metrics"])
        except (ValueError,RuntimeError,subprocess.CalledProcessError,subprocess.TimeoutExpired) as error:
            row.update(status="verification_failed",verification_error=str(error))
            print(row["id"],"verification failed:",error,flush=True)
        row["verification_seconds"]=perf_counter()-tick
    accepted=[r for r in rows if r["status"]=="verified" and r["measured_constraints"]["passed"] and r["measured_benefit"]>0]
    best=max(accepted,key=lambda r:r["measured_benefit"])["id"] if accepted else "unchanged"
    result={"baseline":measured,"baseline_DC":system["state"],"candidates":rows,"selected":best,
            "selection_scope":"largest measured benefit among verified individual alternatives",
            "verification_mode":"all_refined" if verify_all else "ranked",
            "verification_coverage":{"requested":len(verification_rows),
                                     "measured":sum(r["status"]=="verified" for r in rows)},
            "prediction_coverage":{"generated":len(rows),"refined":sum("predicted_values" in r for r in rows)},
            "baseline_seconds":baseline_seconds,"total_seconds":perf_counter()-started,"project":project}
    write(folder/"results.json",result)
    changed=hashes!=fingerprints(project)
    write(folder/"provenance.json",{"source_sha256":hashes,"state":"complete","source_changed_during_run":changed})
    if changed:raise ValueError("Source files changed during this run; results were saved but latest.json was not updated.")
    if eligible and not any(r["status"]=="verified" for r in eligible):
        raise ValueError("No selected candidate completed native verification; inspect results.json.")
    write(folder.parent/"latest.json",{"directory":str(folder)})
    from .plots import plot
    plot(folder)
    print("Selected:",best,"\nResults:",folder,flush=True)
    return folder
