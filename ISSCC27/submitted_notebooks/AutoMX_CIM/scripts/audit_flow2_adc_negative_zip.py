#!/usr/bin/env python3
"""Read the received timeout waveform; never launches SPICE or edits evidence."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from zipfile import ZipFile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.flow2_waveforms import read_raw, sample
from scripts import flow2_adc_finish_profile as profile
from scripts import flow2_integration_common as common


def inspect(root, archive):
    root,archive=Path(root).resolve(),Path(archive).resolve()
    digest=sha256(archive.read_bytes()).hexdigest()
    work=root/"build/flow2_adc_negative_zip_audit"/digest[:16]
    work.mkdir(parents=True,exist_ok=True)
    with ZipFile(archive) as z:
        if z.testzip():raise ValueError("corrupt ADC diagnostic ZIP")
        receipt=json.loads(z.read("attempt_001/receipt.json"))
        segment=receipt["observed_segments"][-1]
        name=Path(segment["path"]).name
        if not __import__('re').fullmatch(r"segment_\d+\.raw",name):raise ValueError("invalid raw name")
        raw=z.read("attempt_001/"+name)
        log=z.read("attempt_001/native.log")
        circuit=z.read("attempt_001/circuit.spice")
        for data,expected in ((raw,segment["sha256"]),(log,receipt["log"]["sha256"]),
                              (circuit,receipt["staged_inputs"][0]["staged"]["sha256"])):
            if sha256(data).hexdigest()!=expected:raise ValueError("raw/log/deck receipt mismatch")
        dest=work/name
        if dest.exists() and dest.read_bytes()!=raw:raise FileExistsError("audit raw differs")
        if not dest.exists():dest.write_bytes(raw)
    vectors=read_raw(dest);t=vectors['time'];mask=t>=22e-9
    profile.validate_sources(vectors,'conversion',.9,-.1)
    stimulus={n:sample(vectors,n,at) for n,at in (('v(ainp)',15e-9),('v(ainn)',15e-9),('v(rst_n)',15e-9),('v(start)',25e-9))}
    if (abs(stimulus['v(ainp)']-.85)>1e-5 or abs(stimulus['v(ainn)']-.95)>1e-5 or
        min(stimulus['v(rst_n)'],stimulus['v(start)'])<1.62):raise ValueError('negative-case stimulus/handshake mismatch')
    report={"format":"automx-cim-adc-negative-partial-raw-review-v1","archive_sha256":digest,
        "receipt_returncode":receipt['returncode'],"raw_sha256":segment['sha256'],
        "raw_points":len(t),"stop_ns":float(t[-1])*1e9,"signals":{},"verified_stimulus":stimulus,
        "evidence":"ZIP CRC plus receipt-matched raw/log/deck; source model/network not present in this ZIP"}
    for key in ("v(eoc)","v(eoc_osr)","v(adc_clk_dig)","v(adc_clk_comp)","v(adc_clk_ena)"):
        a=vectors[key];rising=np.flatnonzero((a[:-1]<.9)&(a[1:]>=.9)&(t[1:]>22e-9))+1
        report["signals"][key]={"minimum_after_start_v":float(min(a[mask])),"maximum_after_start_v":float(max(a[mask])),
            "rising_edge_count":len(rising),"first_edges_ns":[float(t[i])*1e9 for i in rising[:4]]}
    report["result_bits_remain_low"]=all(float(max(vectors[f'v(result_{i})'][mask]))<.18 for i in range(16))
    report["conclusion"]=("CLOCK_ACTIVE_NO_EOC_THROUGH_SAVED_WINDOW" if
        report['signals']['v(adc_clk_dig)']['rising_edge_count']>0 and
        report['signals']['v(eoc_osr)']['rising_edge_count']==0 else "INSPECT_COMPLETION_WAVEFORMS")
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('archive',type=Path);a=p.parse_args();r=inspect(a.root,a.archive)
    common._save(a.root/'docs/flow2_adc_negative_raw_review_20261020.json',r)
    print(json.dumps(r,indent=2))
