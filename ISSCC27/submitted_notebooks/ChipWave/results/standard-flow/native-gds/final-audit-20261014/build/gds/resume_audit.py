import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[2]
out = root / "build/gds"
def digest(data):
    return hashlib.sha256(data).hexdigest()
def read(name):
    return json.loads((out / name).read_text())
def git(*args):
    return subprocess.check_output(["git", *args], cwd=root)

# Reuse requires unchanged owner bytes, including the full physical snapshot.
inputs = []
for record in sorted((root / ".nebula_inputs").glob("*/artifact.json")):
    artifact = json.loads(record.read_text())
    if artifact["type"] == "specification.source":
        continue
    content = artifact["content"]
    count = 0
    for path in content["paths"]:
        tree = git("ls-tree", "-r", content["commit"], "--", path).decode()
        for row in tree.splitlines():
            metadata, name = row.split("\t", 1)
            mode, kind, oid = metadata.split()
            assert kind == "blob" and mode in ("100644", "100755"), name
            data = (root / name).read_bytes()
            assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == oid, name
            count += 1
    inputs.append(dict(record=str(record.relative_to(root)), record_sha256=digest(record.read_bytes()),
                       commit=content["commit"], files_checked=count))
assert len(inputs) == 4, "Unexpected captured input set"
tools = read("tool_identity.json")
subprocess.run([tools["klayout_requested"], "-b", "-r", str(out / "reuse_tool_probe.py")], cwd=root, check=True)
klayout = read("current_klayout_identity.json")
assert klayout["sha256"] == read("klayout_runtime_identity.json")["actual_executable_sha256"]
identity_files = {tools["openroad_resolved"]: tools["openroad_sha256"],
                  tools["klayout_resolved"]: tools["klayout_wrapper_sha256"]}
resources = read("resources.json")
for view in resources["views"]:
    identity_files[view["path"]] = view["sha256"]
identity_files[resources["flow"] + "/util/def2stream.py"] = resources["def2stream_sha256"]
for path, expected in identity_files.items():
    assert digest(Path(path).read_bytes()) == expected, path
snapshot = read("current_input_snapshot.json")
for path, expected in snapshot["files"].items():
    assert digest((root / path).read_bytes()) == expected, path

# Existing Git owner objects close lost capture paths; no owner result is rerun.
origins = {"authorized-root-project-delivery": "08c8b22cebbafda6fba41cb6229baeb91ff1cc2a",
           "artifact-0b514721fd8641408ffcec0d7f4350ec": "506aa56bf42544a1f38b5a12f5b66bd76acc286b"}
report = read("project_acceptance.json")
paths = {row["original_path"]: row["sha256"] for row in read("resume_validation.json")["archive"]} if (out / "resume_validation.json").exists() else {}
for check in report["checks"]:
    for path, expected in check.get("evidence_sha256", {}).items():
        if path.startswith(".nebula_inputs/"):
            paths[path] = expected
native = read("delivery_synthesis_revalidation.json")["delivery"]
for name, expected in native["rtl_sha256"].items():
    paths[".nebula_inputs/authorized-root-project-delivery/delivery/standard-project/" + name] = expected
paths[".nebula_inputs/authorized-root-project-delivery/delivery/standard-project/spec/acceptance.md"] = digest((root / "spec/acceptance.md").read_bytes())
archive = []
for old_path, expected in sorted(paths.items()):
    _, artifact_id, source_path = old_path.split("/", 2)
    commit = origins[artifact_id]
    data = git("show", commit + ":" + source_path)
    assert digest(data) == expected, old_path
    target = out / "evidence" / artifact_id / source_path
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert target.read_bytes() == data, target
    else:
        target.write_bytes(data)
    archive.append(dict(original_path=old_path, archived_path=str(target.relative_to(root)),
                        artifact_id=artifact_id, commit=commit, source_path=source_path,
                        git_blob=git("rev-parse", commit + ":" + source_path).decode().strip(),
                        bytes=len(data), sha256=expected))
assert (out / "nebula_cpu_npu_top.gds").stat().st_size == 21239988
assert digest((out / "nebula_cpu_npu_top.gds").read_bytes()) == read("reuse_validation.json")["gds_sha256"]
assert report["verdict"] == "failed" and report["physical_export_acceptance"]["verdict"] == "passed"
assert next(c for c in report["checks"] if c["id"] == "AC-RESOURCES")["verdict"] == "failed"
result = dict(schema_version=1, status="passed", audit_scope="Evidence retrievability and exact reuse binding only; whole-project acceptance remains failed",
              prior_attempt="attempt-cf266b46df624d72941221bc4ba42d7e", prior_workspace_commit="54b95bdc7a4ba97ad74bc6ce5711f85c8efb0d7d",
              snapshot_id=snapshot["snapshot_id"], input_artifacts=inputs, unchanged_physical_files=len(snapshot["files"]), unchanged_tools_and_resources=identity_files, qualified_container_klayout=klayout,
              archive=archive, new_owner_results=False, design_checks_rerun=False,
              owner_power_adoption="build/gds/power_area_adoption.json", owner_results_origin="Source-qualified PnR receipt adopted separately; no owner execution by this script",
              historical_operator_evidence="build/gds/operator_feedback.json",
              blocking_checks=report["blocking_checks"], project_verdict="failed")
(out / "resume_validation.json").write_text(json.dumps(result, indent=2) + "\n")
print("RESUME_SOURCE_BINDING_AND_NATIVE_RETRIEVABILITY_PASS", len(archive))
