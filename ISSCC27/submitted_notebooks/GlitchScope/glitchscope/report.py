from __future__ import annotations
import csv, json
from pathlib import Path
from .model import fs_to_ps

def write_results(outdir, trace, pulses, final_state, lineages=None, lineage_edges=None):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)

    with (out/"events.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["event_id","time_fs","time_ps","epoch","net","old","new","source","parent_event_ids"])
        for e in sorted(trace, key=lambda x:(x.time_fs,x.event_id)):
            w.writerow([e.event_id,e.time_fs,f"{fs_to_ps(e.time_fs):.3f}",
                        e.epoch_id,e.net,e.old_value,e.new_value,
                        e.source_instance,";".join(map(str,e.parent_event_ids))])

    with (out/"glitches.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["glitch_id","epoch","net","start_fs","end_fs","width_fs","width_ps","polarity"])
        for p in pulses:
            w.writerow([p.pulse_id,p.epoch_id,p.net,p.start_fs,p.end_fs,p.width_fs,
                        f"{fs_to_ps(p.width_fs):.3f}",p.polarity])

    if lineages is not None:
        with (out/"lineages.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["glitch_id","epoch","net","classification","root_ids","source_instance",
                        "start_fs","end_fs","width_fs","width_ps","polarity"])
            for g in lineages:
                w.writerow([g.glitch_id,g.epoch_id,g.net,g.classification,
                            ";".join(g.root_ids),g.source_instance,
                            g.start_fs,g.end_fs,g.width_fs,
                            f"{fs_to_ps(g.width_fs):.3f}",g.polarity])

        payload = [{
            "glitch_id":g.glitch_id, "epoch":g.epoch_id, "net":g.net,
            "classification":g.classification, "root_ids":list(g.root_ids),
            "source_instance":g.source_instance, "start_fs":g.start_fs,
            "end_fs":g.end_fs, "width_fs":g.width_fs, "polarity":g.polarity
        } for g in lineages]
        (out/"lineages.json").write_text(json.dumps(payload, indent=2, sort_keys=True))

    if lineage_edges is not None:
        with (out/"lineage_edges.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["root_id","origin_net","descendant_net","descendant_glitch_id"])
            for e in lineage_edges:
                w.writerow([e.root_id,e.origin_net,e.descendant_net,e.descendant_glitch_id])

    summary = {
        "status":"PASS",
        "num_trace_events":len(trace),
        "num_glitch_pulses":len(pulses),
        "final_outputs":final_state,
    }
    if lineages is not None:
        summary["num_generated"] = sum(g.classification=="GENERATED" for g in lineages)
        summary["num_propagated"] = sum(g.classification=="PROPAGATED" for g in lineages)
        summary["num_merged"] = sum(g.classification=="MERGED" for g in lineages)
    (out/"summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
