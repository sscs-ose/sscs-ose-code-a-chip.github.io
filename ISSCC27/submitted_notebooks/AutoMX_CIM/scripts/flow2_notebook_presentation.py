"""Readable cell output: measurements, commands and tool logs."""
import json
import re


def public_values(value):
    if isinstance(value,dict):
        return {k:public_values(v) for k,v in value.items() if not any(word in k.lower() for word in ('sha256','sha_256','digest','hash'))}
    if isinstance(value,(list,tuple)):return [public_values(v) for v in value]
    return value


def pretty(value,**options):
    return json.dumps(public_values(value),**options)
