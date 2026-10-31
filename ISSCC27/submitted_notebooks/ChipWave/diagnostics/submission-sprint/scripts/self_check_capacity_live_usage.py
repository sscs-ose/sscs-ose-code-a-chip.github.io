"""Exercise real process stopping against synthetic native transcript events."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from capacity_live_usage import LiveUsage
from capacity_meter import InvalidMeasurement
from study_protocol import write_json

MODEL = "gpt-6-luna"


def events(session, tokens):
    return [
        dict(type="session_meta", payload=dict(id=session)),
        dict(type="turn_context", payload=dict(model=MODEL, effort="high")),
        dict(type="event_msg", payload=dict(type="token_count", info=dict(total_token_usage=dict(
            input_tokens=tokens, cached_input_tokens=0, output_tokens=0,
            reasoning_output_tokens=0, total_tokens=tokens))))]


def encode(rows):
    return "".join(json.dumps(row)+"\n" for row in rows)


def check():
    with tempfile.TemporaryDirectory(prefix="capacity-live-usage-") as tmp:
        root = Path(tmp)
        private = root/"private"
        sessions = private/"sessions"
        sessions.mkdir(parents=True)
        path = sessions/"first.jsonl"
        path.write_text(encode(events("role-a", 30)))
        meter = LiveUsage(private, root/"usage.json", MODEL, limit=100)
        assert meter.poll()["actual_tokens"] == 30
        assert meter.poll()["actual_tokens"] == 30
        resumed = LiveUsage(private, root/"usage.json", MODEL, limit=100)
        assert resumed.poll()["actual_tokens"] == 30
        with path.open("a") as f:
            f.write(encode([events("role-a", 60)[-1]]))
        assert resumed.poll()["actual_tokens"] == 60
        (sessions/"second.jsonl").write_text(encode(events("role-b", 25)))
        assert resumed.poll()["actual_tokens"] == 85
        with path.open("a") as f:
            f.write(encode([events("role-a", 80)[-1]])[:-1])
        assert resumed.poll()["actual_tokens"] == 85
        with path.open("a") as f:
            f.write("\n")
        summary = resumed.poll()
        assert summary["actual_tokens"] == 105 and summary["overshoot_tokens"] == 5
        assert not summary["dispatch_allowed"]
        path.write_text(encode(events("role-a", 1)))
        try:
            LiveUsage(private, root/"usage.json", MODEL, limit=100).poll()
        except InvalidMeasurement:
            pass
        else:
            raise AssertionError("Truncated native evidence accepted")

        live = root/"stoppable"
        (live/"sessions").mkdir(parents=True)
        target = live/"sessions/native.jsonl"
        child = subprocess.Popen([sys.executable, "-c",
            "import pathlib,time;pathlib.Path("+repr(str(target))+").write_text("
            +repr(encode(events("process", 120)))+");time.sleep(60)"], start_new_session=True)
        control = LiveUsage(live, root/"stopped-usage.json", MODEL, limit=100)
        report = control.wait(child)
        assert report["reason"] == "token_budget" and report["actual_tokens"] == 120, report
        assert child.poll() is not None and report["wall_seconds"] < 10
        for label, content in (
            ("missing", encode(events("bad", 0)[:2])),
            ("partial", encode(events("bad", 1))+'{"type":'),
            ("reset", encode(events("bad", 20)+[events("bad", 10)[-1]])),
            ("identity", encode(events("bad", 1)).replace(MODEL, "unapproved-model")),
            ("resume_missing", encode(events("bad", 1)+[events("bad", 1)[1]])),
            ("unmetered_compaction", encode(events("bad",1)+[
                dict(type="compacted",payload=dict(compaction_response_id="missing"))])),
        ):
            folder = root/label
            (folder/"sessions").mkdir(parents=True)
            (folder/"sessions/native.jsonl").write_text(content)
            observer = LiveUsage(folder, root/(label+".json"), MODEL)
            try:
                observer.finish()
            except InvalidMeasurement:
                pass
            else:
                raise AssertionError("Invalid native transcript accepted: "+label)
    result = dict(passed=True, model_calls=0, physical_attempts=0,
        checks=["same-session resume idempotence", "cross-role incremental sum", "partial event wait",
                "unmetered compaction rejected", "actual process-group budget stop",
                "overshoot retained", "truncation/counter-reset/missing-usage/model mismatch rejected"],
        scope="Synthetic native events and real process termination; live Codex/tool coupling still pending")
    write_json(Path(__file__).resolve().parents[1]/"checks/live-usage-controller.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(check()))
