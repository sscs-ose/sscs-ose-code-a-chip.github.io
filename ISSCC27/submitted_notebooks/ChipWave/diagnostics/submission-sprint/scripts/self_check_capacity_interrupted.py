"""A normal budget stop preserves earlier witnessed snapshots, not partial edits."""
import json
from pathlib import Path

from capacity_meter import InvalidMeasurement
from qualify_capacity_events import associate
from study_protocol import write_json

ROOT=Path(__file__).resolve().parents[1]


def check():
    fixture=ROOT/"checks/native-router-probe-v4"
    events=json.loads((fixture/"event-order.json").read_text())
    hooks=json.loads((fixture/"hook-observations.json").read_text())
    extended=events+[dict(kind="response_item",subtype="custom_tool_call",call_id="interrupted-final")]
    kept=associate(extended,hooks,interrupted=True)
    assert len(kept.state["snapshots"])==4
    for stream,allowed in ((extended,False),([r for r in extended if not (
        r.get("subtype")=="custom_tool_call_output" and
        r.get("call_id")==hooks[0]["parent_call_id"])],True)):
        try:
            associate(stream,hooks,interrupted=allowed)
        except InvalidMeasurement:
            pass
        else:
            raise AssertionError("Missing output accepted outside a single terminal interruption")
    report=dict(passed=True,model_calls=0,physical_runs=0,
        checks=["earlier four complete snapshots survive terminal interruption",
                "normal exits still require complete calls", "missing earlier output rejected"])
    write_json(ROOT/"checks/interrupted-source-prefix.json",report)
    return report


if __name__=="__main__":
    print(json.dumps(check()))
