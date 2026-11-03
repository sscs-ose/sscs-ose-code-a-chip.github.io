#!/usr/bin/env python3
"""Hash every GDS record byte, replacing only library/cell timestamps with zero."""
import argparse
import hashlib
import io
import json
import struct
from pathlib import Path


def digest(stream):
    result = hashlib.sha256()
    timestamps = 0
    while True:
        header = stream.read(4)
        if not header:
            break
        if len(header) != 4:
            raise ValueError('Truncated GDS record header')
        size, kind, datatype = struct.unpack('>HBB', header)
        if size < 4 or size % 2:
            raise ValueError('Invalid GDS record length')
        body = stream.read(size-4)
        if len(body) != size-4:
            raise ValueError('Truncated GDS record body')
        if kind in (1, 5):
            if datatype != 2 or size != 28:
                raise ValueError('Invalid BGNLIB/BGNSTR timestamp record')
            body = bytes(24)
            timestamps += 1
        result.update(header)
        result.update(body)
    return dict(sha256=result.hexdigest(), timestamp_records=timestamps)


def self_check():
    header = struct.pack('>HBB',28,1,2)
    assert digest(io.BytesIO(header+bytes(24))) == digest(io.BytesIO(header+b'\x01'*24))
    try:
        digest(io.BytesIO(header+b'\x01'))
    except ValueError:
        pass
    else:
        raise AssertionError('Truncated input must fail')


if __name__ == '__main__':
    self_check()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('gds',type=Path)
    with parser.parse_args().gds.open('rb') as stream:
        print(json.dumps(digest(stream),indent=2))
