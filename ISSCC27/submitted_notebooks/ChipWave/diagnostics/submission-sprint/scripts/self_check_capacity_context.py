"""Verify actual public dispatch plumbing without calling a model."""
import json
import tempfile
from pathlib import Path

from chip_nebula.models.task_manifest import AgentResult, TaskManifest
from capacity_context import ContextPool, IsolatedCodexAdapter
from study_protocol import write_json


def check():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        calls = []
        class Fake:
            def execute(self, task, workspace, project_root=None):
                calls.append((task.assigned_agent, task.session_id))
                identity = task.session_id or ("a"*8 if task.assigned_agent=="engineer" else "b"*8)
                return AgentResult(success=True, session_id=identity)
        pool = ContextPool(root/"private", root/"contexts.json", "gpt-6-luna")
        pool.adapters["codex"] = Fake()
        def task(role, stage):
            return TaskManifest(task_id=stage,feature_id="fixture",stage=stage,assigned_agent=role,
                                description="fixture",model="gpt-6-luna",reasoning_effort="high")
        pool.dispatch(task("engineer","implementation"),root)
        pool.dispatch(task("engineer","verification"),root)
        pool.dispatch(task("verifier","review"),root)
        pool = ContextPool(root/"private", root/"contexts.json", "gpt-6-luna")
        pool.adapters["codex"] = Fake()
        pool.dispatch(task("engineer","revision"),root)
        assert calls == [("engineer",""),("engineer","aaaaaaaa"),
                         ("verifier",""),("engineer","aaaaaaaa")]
        adapter = IsolatedCodexAdapter(root/"private")
        try: adapter._session_exists("aaaaaaaa")
        except ValueError: pass
        else: raise AssertionError("Missing resumed context was silently reset")
        saved=root/"private/sessions/2026/10/21/rollout-aaaaaaaa.jsonl"
        saved.parent.mkdir(parents=True);saved.write_text('{"fixture":true}\n')
        assert adapter._session_exists("aaaaaaaa")
        before=saved.read_bytes()
        adapter._append_session_message("aaaaaaaa","must not edit scientific evidence")
        assert saved.read_bytes()==before
    return dict(passed=True,model_calls=0,checks=["same role reused across phases",
        "independent roles separated","durable context mapping","private-session lookup",
        "missing context rejects silent restart","no synthetic transcript events"],
        live_context_resume_qualified=False)


if __name__=="__main__":
    result=check()
    write_json(Path(__file__).resolve().parents[1]/"checks/context-dispatch.json",result)
    print(json.dumps(result))
