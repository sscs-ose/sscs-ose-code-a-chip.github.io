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
    settings = tomllib.loads((original / 'config.toml').read_text())

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


def sandbox_command(project, workspace, private_home, command, readonly=()):
    project, workspace, private_home = (Path(p).resolve() for p in (project, workspace, private_home))
    if not workspace.is_relative_to(project):
        raise ValueError('Agent workspace must belong to this trial')
    if private_home.is_relative_to(project):
        raise ValueError('Credentials must remain outside project exports')
    args = ['bwrap', '--unshare-user', '--unshare-pid', '--unshare-ipc', '--die-with-parent',
            '--new-session', '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp']
    for name in ('/usr', '/bin', '/sbin', '/lib', '/lib64', '/etc', '/opt/rh',
                 '/tmp/chipnebula-pinned-tools', '/tmp/chipnebula-public-repro-user37',
                 str(Path(sys.executable).resolve().parent.parent),
                 str(Path.home() / '.local/share/uv/python')):
        path = Path(name)
        if path.exists(): args += ['--ro-bind', str(path.resolve()), str(path.resolve())]
        if path.is_symlink(): args += ['--symlink', str(path.resolve()), str(path)]
    args += ['--ro-bind', str(project), str(project), '--bind', str(workspace), str(workspace),
             '--bind', str(private_home), str(Path.home() / '.codex')]
    for relative in ('spec', 'ip', 'tools', '.nebula_inputs', *readonly):
        path = workspace / relative
        if path.exists(): args += ['--ro-bind', str(path), str(path)]
    if os.environ.get('CHIP_STUDY_CHECK_SOCKET'):
        args += ['--dir', '/run', '--ro-bind', os.environ['CHIP_STUDY_CHECK_SOCKET'], '/run/study-check.sock']
    binary = Path(shutil.which('codex-real') or '/home/asic03/.codex/packages/standalone/current/bin/codex').resolve()
    args += ['--dir', '/tools', '--ro-bind', str(binary.parent), '/tools',
             '--setenv', 'PATH', '/tmp/chipnebula-public-repro-user37/bin:/tmp/chipnebula-pinned-tools/bin:/opt/rh/gcc-toolset-13/root/usr/bin:/usr/bin:/bin',
             '--setenv', 'GIT_OPTIONAL_LOCKS', '0', '--unsetenv', 'PYTHONPATH',
             '--chdir', str(workspace), '--', *command]
    return args


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
