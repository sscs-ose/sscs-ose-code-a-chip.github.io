"""Protected campaign-wide physical launch accounting; never replace a scored run."""
from __future__ import annotations

import datetime
import fcntl
import json
import os
from pathlib import Path

from study_protocol import write_json


def reserve(campaign, category, identity, output):
    campaign, output = Path(campaign).resolve(), Path(output).resolve()
    if not output.is_relative_to(campaign) or output.exists():
        raise ValueError('New physical output must be inside this campaign')
    path = campaign / 'launch-ledger.json'
    with (campaign / '.launch-ledger.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        document = json.loads(path.read_text())
        limits = document['limits']
        if category not in ('reference', 'demonstration', 'common_baseline', 'ppa', 'high_frequency', 'preformal_calibration', 'reference_supplement'):
            raise ValueError('Unknown physical budget category')
        if category == 'reference_supplement':
            authority=campaign/'budget-amendment.json'
            if not authority.exists() or not json.loads(authority.read_text()).get('owner_approved'):
                raise ValueError('A reference supplement requires explicit owner budget authorization')
        launches = document['launches']
        if any(row['identity'] == identity or row['output'] == str(output.relative_to(campaign)) for row in launches):
            raise ValueError('A prior launch is retained; do not retry it')
        if sum(row['category'] == category for row in launches) >= limits.get(category, 0):
            raise ValueError('Category launch budget exhausted')
        if len(launches) >= limits['absolute_total']:
            raise ValueError('Campaign physical budget exhausted')
        if category == 'preformal_calibration' and (campaign / 'ppa/formal-freeze.json').exists():
            raise ValueError('Calibration cannot rescue formal searches')
        record = dict(category=category, identity=identity, output=str(output.relative_to(campaign)),
                      allocated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      pid=os.getpid(), status='allocated')
        launches.append(record)
        write_json(path, document)
        return record


def finish(campaign, identity, *, status, evidence):
    campaign = Path(campaign).resolve()
    with (campaign / '.launch-ledger.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        document = json.loads((campaign / 'launch-ledger.json').read_text())
        record = next(row for row in document['launches'] if row['identity'] == identity)
        if record['status'] != 'allocated':
            raise ValueError('Terminal launch records are immutable')
        record.update(status=status, evidence=evidence, finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        write_json(campaign / 'launch-ledger.json', document)
