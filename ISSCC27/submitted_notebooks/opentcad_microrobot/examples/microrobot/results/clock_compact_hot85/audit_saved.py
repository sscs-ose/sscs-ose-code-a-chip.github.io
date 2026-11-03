"""Audit the saved run only; normalize JSON arrays without changing frozen execution provenance."""
import json
import run_hot85

original_inputs=run_hot85.inputs
def normalized_inputs():
    original,changed,proof=original_inputs()
    return original,changed,json.loads(json.dumps(proof))

run_hot85.inputs=normalized_inputs
run_hot85.audit()
metrics_path=run_hot85.DEST/'metrics.json'
metrics=json.loads(metrics_path.read_text())
metrics['nominal_reference_assumptions']=metrics.pop('assumptions')
run_hot85.dump(metrics_path,metrics)
run_hot85.refresh_manifest()
