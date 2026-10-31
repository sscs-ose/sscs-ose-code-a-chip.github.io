"""Exercise adapter trust boundaries and existing public dispatch without models."""
import json
import tempfile
import sys
import shlex
import time
from pathlib import Path
from unittest.mock import patch

from chip_nebula.models.task_manifest import AgentResult, TaskManifest
from capacity_context import ControlledCodexAdapter, IsolatedCodexAdapter
from capacity_runtime import adapter_arguments, run
from study_protocol import write_json


def check():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp); work=root/"project/work";work.mkdir(parents=True)
        config=dict(record=str(root/"record"), private=str(root/"private"),
                    project=str(root/"project"), workspace=str(work),model="gpt-6-luna")
        args=["exec","--json","--dangerously-bypass-approvals-and-sandbox","--skip-git-repo-check",
              "--cd",str(work),"--model","gpt-6-luna","--config",'model_reasoning_effort="high"']
        assert adapter_arguments(args+["-"],config) is None
        assert adapter_arguments(args+["resume","abc-def","-"],config) == "abc-def"
        for invalid in (args+["--sandbox","danger-full-access","-"],args+["resume","../../other","-"],
                        [*args[:7],"gpt-6.1-sol",*args[8:],"-"]):
            try:adapter_arguments(invalid,config)
            except ValueError:pass
            else:raise AssertionError("Unapproved native invocation accepted")
        for extra in (dict(limit=1_000_001),dict(active_seconds=5401),dict(writable=["spec"]),dict(scored=True)):
            try:run(dict(config,**extra),"must not call a model")
            except ValueError:pass
            else:raise AssertionError("Invalid protocol boundary accepted")
        adapter=ControlledCodexAdapter(root/"private",dict(record=str(root/"record")))
        task=TaskManifest(task_id="check",feature_id="fixture",stage="review",assigned_agent="reviewer",
            description="fixture",model="gpt-6-luna",reasoning_effort="high",
            write_paths=["tests/**","reports/**","build/**"])
        def fake(instance, manifest, workspace, project_root=None):
            saved=json.loads((root/"record/adapter-invocation.json").read_text())
            assert saved["writable"] == ["tests","reports","build"]
            assert saved["model"] == "gpt-6-luna"
            assert saved["stage"] == "review" and saved["role"] == "reviewer"
            wrapper=(root/"record/adapter-bin/codex").read_text()
            assert "exec "+shlex.quote(sys.executable)+" " in wrapper
            return AgentResult(success=True,session_id="abc-def")
        with patch.object(IsolatedCodexAdapter,"execute",fake):
            assert adapter.execute(task,work,project_root=root/"project").success
        # Changing role/worktree cannot reset the shared active-time clock.
        clock_record=root/"clock-record";clock_record.mkdir()
        clock=dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                   start=time.monotonic()-20, physical_seconds=10, active_limit=5,
                   token_limit=100, model='gpt-6-luna')
        write_json(clock_record/'clock.json',clock)
        expired=dict(config,record=str(clock_record),limit=100,active_seconds=5)
        with patch('capacity_runtime.subprocess.Popen') as launch:
            for stage in ('implementation','verification'):
                try:run(dict(expired,stage=stage),'must not launch')
                except ValueError as error:assert 'exhausted' in str(error)
                else:raise AssertionError('Role reset exhausted clock')
            launch.assert_not_called()
        assert json.loads((clock_record/'clock.json').read_text())==clock
    report=dict(passed=True,model_calls=0,physical_runs=0,
        checks=["frozen adapter arguments", "model/permission escalation rejection",
                "protocol ceiling rejection", "unqualified formal invocation rejection",
                "public adapter review-role scope", "cumulative active-time exhaustion across roles"])
    write_json(Path(__file__).resolve().parents[1]/"checks/runtime-boundaries.json",report)
    return report


if __name__=="__main__":
    print(json.dumps(check()))
