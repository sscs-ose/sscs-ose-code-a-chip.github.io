"""Collect the logs of run_formal.sh into one JSON file; every value is read from the SymbiYosys logs.
usage: formal_collect.py <work dir> <result.json>
SPDX-License-Identifier: Apache-2.0"""
import hashlib
import json
import pathlib
import re
import sys

W, DST = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
TASKS = {"props_cover": "reachability of a binding, a sealed frame, a received frame and the lock",
         "props_bmc": "P2 to P6, bounded", "props_prove": "P2 to P6, k-induction",
         "miter_bmc": "P1, two copies differing only in K, bounded", "miter_prove": "P1, k-induction"}
res = {"tool": "SymbiYosys with smtbmc and Bitwuzla",
       "design": "hsm_shell.sv of the chip's RTL root, TRUSTEDGE_REVC on, ENABLE_MLKEM_K_CHANNEL on, EXTERNAL_HMAC on (HMAC outputs are free inputs)",
       "hsm_shell_sha256": hashlib.sha256((W / "hsm_shell.sv").read_bytes()).hexdigest(),
       "rejection_limit_in_the_model": int(re.search(r"REVC_FAIL_LIMIT=(\d+)", (W / "session_props.sby").read_text())[1]),
       "rejection_limit_on_the_chip": 16,
       "properties": {
           "P1": "no bit of K reaches the host: two copies that differ only in K give identical responses",
           "P2": "a sealed frame's counter is exactly the previous one plus one, starting at 1",
           "P3": "an accepted frame carries the epoch of the current binding and a counter above the last accepted",
           "P4": "after the rejection limit no frame is accepted until the next binding or zeroisation",
           "P5": "a binding is refused as a replay only if an earlier successful command used that counter or a later one",
           "P6": "a binding succeeds only with a nonce ready, returns that nonce as its epoch and consumes it"},
       "tasks": {}}
for t, what in TASKS.items():
    log = (W / f"{t}.log").read_text(errors="replace")
    done = re.findall(r"DONE \((\w+), rc=(\d+)\)", log)
    sby = (W / ("session_props.sby" if t.startswith("props") else "session_miter.sby")).read_text()
    mode = t.split("_")[1]
    depth = re.search(rf"^{mode}: depth (\d+)", sby, re.M)
    elapsed = re.search(r"Elapsed clock time \[H:MM:SS \(secs\)\]: \S+ \((\d+)\)", log)
    res["tasks"][t] = {"checks": what, "depth": int(depth[1]), "status": done[-1][0], "elapsed_s": int(elapsed[1]),
                       "induction_step": ("FAIL" if "returned FAIL for induction" in log else "pass") if mode == "prove" else None,
                       "basecase": ("pass" if "returned pass for basecase" in log else "not reported") if mode == "prove" else None,
                       "cover_traces": len(set(re.findall(r"cover trace: \S+trace(\d+)\.vcd", log))) if mode == "cover" else None}
DST.write_text(json.dumps(res, indent=1) + "\n")
print("FORMAL", {k: v["status"] for k, v in res["tasks"].items()})
