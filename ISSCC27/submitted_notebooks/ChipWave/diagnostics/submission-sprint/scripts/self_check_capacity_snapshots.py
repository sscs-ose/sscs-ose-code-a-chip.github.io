"""Replay real nested hooks against a shared ledger without making model calls."""
import json
import tempfile
import shutil
from pathlib import Path

from capacity_live_usage import LiveUsage
from capacity_snapshots import associate_captures
from study_protocol import write_json

ROOT = Path(__file__).resolve().parents[1]


def check():
    probe = ROOT/"checks/native-router-probe-v4"
    result = json.loads((probe/"result.json").read_text())
    assert result["passed"]
    with tempfile.TemporaryDirectory() as directory:
        record = Path(directory)/"usage.json"
        observer = LiveUsage(result["private_diagnostics"], record, result["model"])
        # A prior independent role used 321 Tokens; source scoring must include it.
        usage = dict(input_tokens=300, cached_input_tokens=0, output_tokens=21,
                     reasoning_output_tokens=0,total_tokens=321)
        observer.ledger.record("earlier-role", "fixture", usage)
        observer.poll()
        captures = Path(directory)/"captures"
        shutil.copytree(probe/"tools/snapshots", captures)
        empty = json.loads(next(captures.glob("*/capture.json")).read_text())
        empty.update(call_id="empty-before-rtl", source_sha256={})
        write_json(captures/"empty"/"capture.json", empty)
        assert associate_captures(observer, captures) == 4
        assert not any(s["id"] == "empty-before-rtl" for s in observer.ledger.state["snapshots"])
        expected = json.loads((probe/"associated-usage.json").read_text())["snapshots"]
        actual = observer.ledger.state["snapshots"]
        assert [r["tokens"] for r in actual] == [r["tokens"]+321 for r in expected]
        assert observer.ledger.summary()["actual_tokens"] == result["actual_logical_tokens"]+321
        assert associate_captures(observer, probe/"tools/snapshots") == 0
        resumed = LiveUsage(result["private_diagnostics"], record, result["model"])
        resumed.poll()
        assert associate_captures(resumed, probe/"tools/snapshots") == 0
        assert resumed.ledger.state["snapshots"] == actual
    report = dict(passed=True, model_calls=0, physical_runs=0, real_captures=4,
        checks=["real code-mode parent/child IDs", "prior-role Tokens included",
                "empty pre-RTL captures cannot score or invalidate later RTL", "idempotent replay", "durable observer restart"],
        scope="Recorded live serial captures plus synthetic prior-role cost; multi-role live qualification recorded separately")
    write_json(ROOT/"checks/shared-source-association.json", report)
    return report


if __name__ == "__main__":
    print(json.dumps(check()))
