"""Exercise existing sandbox with canaries, without starting a model or EDA."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from capacity_workflows import configuration, repair_context
from study_portability import sandbox_command
from study_protocol import write_json


def check():
    with tempfile.TemporaryDirectory(prefix="capacity-isolation-") as temp:
        root = Path(temp)
        project, private = root / "project", root / "private"
        work = project / "workspace"
        (work / "spec").mkdir(parents=True)
        (work / "rtl").mkdir()
        private.mkdir()
        (work / "spec/task.md").write_text("frozen")
        grader = root / "hidden-grader.txt"
        grader.write_text("reference canary")
        other = root / "other-trial.txt"
        other.write_text("other-trial canary")
        control = project / "quota.json"
        control.write_text('{"limit":2}')
        probe = f"""
from pathlib import Path
assert not Path({str(grader)!r}).exists()
assert not Path({str(other)!r}).exists()
for p in [Path('spec/task.md'), Path({str(control)!r})]:
    try: p.write_text('tamper')
    except OSError: pass
    else: raise AssertionError('Protected file writable: '+str(p))
Path('rtl/probe.sv').write_text('module probe; endmodule')
assert Path('rtl/probe.sv').read_text()=='module probe; endmodule'
print('ISOLATION_PASS')
"""
        result = subprocess.run(sandbox_command(project, work, private,
                                [sys.executable, "-c", probe]), text=True,
                                capture_output=True, timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "ISOLATION_PASS" in result.stdout
    c2, c3 = configuration("C2"), configuration("C3")
    assert c2["expert_materials"] == c3["expert_materials"]
    assert [p["phase"] for p in c2["phases"]] == [p["phase"] for p in c3["phases"]]
    assert len({p["context"] for p in c2["phases"]}) == 1
    assert len({p["context"] for p in c3["phases"]}) == 3
    assert len({p["context"] for p in configuration("C6")["phases"]}) == 6
    for workflow in ("C0", "C1", "C2", "C3", "C6"):
        assert repair_context(workflow, 1)["physical_retry_allowed"]
        assert not repair_context(workflow, 2)["physical_retry_allowed"]
    return dict(passed=True, model_calls=0, physical_runs=0,
                checks=["real bwrap hidden grader/other trial canaries",
                        "read-only task/control", "writable designated RTL",
                        "phase/context declarations", "physical repair quota branch"],
                not_qualified=["complete illegal-tool enforcement",
                               "live workflow/context execution", "live usage/source association"])


if __name__ == "__main__":
    result = check()
    write_json(Path(__file__).resolve().parents[1] / "checks/zero-model-isolation.json", result)
    print(json.dumps(result))
