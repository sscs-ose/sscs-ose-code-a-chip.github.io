"""Prefer native response accounting, which includes remote compaction costs."""
import json

from capacity_meter import FIELDS, InvalidMeasurement


def validate(usage):
    if not isinstance(usage,dict) or any(type(usage.get(k)) is not int or usage[k]<0 for k in FIELDS):
        raise InvalidMeasurement("Invalid native usage record")
    if (usage.get("total_tokens") != usage["input_tokens"]+usage["output_tokens"]
        or usage["cached_input_tokens"]>usage["input_tokens"]
        or usage["reasoning_output_tokens"]>usage["output_tokens"]):
        raise InvalidMeasurement("Inconsistent native usage record")
    return usage


class NativeUsage:
    def __init__(self):
        self.latest = None
        self.records = {}
        self.session = None
        self.compactions = set()

    def observe(self,kind,payload):
        if kind=="session_meta":
            self.session=payload.get("id")
        if kind=="token_usage_record":
            if payload.get("session_id")!=self.session:
                raise InvalidMeasurement("Response usage belongs to another session")
            identity=payload.get("response_id")
            if not isinstance(identity,str) or not identity:
                raise InvalidMeasurement("Missing response usage identity")
            usage=validate(payload.get("usage"))
            cumulative=validate(payload.get("thread_token_usage"))
            fingerprint=json.dumps(payload,sort_keys=True)
            if identity in self.records:
                if self.records[identity]!=fingerprint:
                    raise InvalidMeasurement("Response usage identity changed")
                return self.latest
            if self.latest is not None and any(
                    cumulative[k]-self.latest[k]!=usage[k] for k in FIELDS):
                raise InvalidMeasurement("Response and cumulative usage disagree")
            if self.latest is None and any(cumulative[k]!=usage[k] for k in FIELDS):
                raise InvalidMeasurement("Initial response accounting is incomplete")
            self.records[identity]=fingerprint
            self.latest=cumulative
            return cumulative
        if kind=="compacted":
            identity=payload.get("compaction_response_id")
            if not identity or identity not in self.records:
                raise InvalidMeasurement("Compaction has no independently recorded response usage")
            self.compactions.add(identity)
        if kind=="event_msg" and payload.get("type")=="token_count":
            ui=validate((payload.get("info") or {}).get("total_token_usage"))
            if self.latest is not None:
                if any(ui[k]>self.latest[k] for k in FIELDS):
                    raise InvalidMeasurement("Response accounting is missing UI-reported usage")
                return self.latest
            return ui
        return None
