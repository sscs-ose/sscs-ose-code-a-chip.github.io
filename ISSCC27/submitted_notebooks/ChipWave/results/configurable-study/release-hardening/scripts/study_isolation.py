"""Filesystem isolation for study model processes; credentials stay outside releases."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def prepare_credentials(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(destination, 0o700)
    # Preserve login locally; do not copy the operator's projects, sessions or plugins.
    original = Path.home() / '.codex'
    auth = original / 'auth.json'
    if not (destination / 'auth.json').exists() and auth.is_file():
        shutil.copy2(auth, destination / 'auth.json')
        os.chmod(destination / 'auth.json', 0o600)
    import tomllib
    config = original / 'config.toml'
    settings = tomllib.loads(config.read_text()) if config.exists() else {}

    def toml(value):
        if isinstance(value, str): return json.dumps(value)
        if isinstance(value, bool): return str(value).lower()
        if isinstance(value, dict): return '{' + ', '.join(json.dumps(k) + '=' + toml(v) for k, v in value.items()) + '}'
        if isinstance(value, list): return '[' + ', '.join(toml(v) for v in value) + ']'
        return str(value)

    transport = ('model_provider', 'model_providers', 'chatgpt_base_url', 'cli_auth_credentials_store', 'force_login_method')
    lines = [key + '=' + toml(settings[key]) for key in transport if key in settings]
    lines += ['[features]', 'multi_agent=false']
    (destination / 'config.toml').write_text('\n'.join(lines) + '\n')


from study_portability import sandbox_command


def wrapper(arguments):
    try:
        index = arguments.index('--cd')
        workspace = Path(arguments[index + 1])
    except (ValueError, IndexError):
        raise ValueError('Study adapter must specify --cd explicitly')
    project = Path(os.environ['CHIP_STUDY_PROJECT'])
    private_home = Path(os.environ['CHIP_STUDY_PRIVATE_HOME'])
    readonly = json.loads(os.environ.get('CHIP_STUDY_READONLY', '[]'))
    command = ['/tools/codex', *arguments]
    return subprocess.call(sandbox_command(project, workspace, private_home, command, readonly))


if __name__ == '__main__':
    raise SystemExit(wrapper(sys.argv[1:]))
