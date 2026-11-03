"""Locate native tools for an isolated replay without assuming the author's paths."""
from pathlib import Path
import hashlib
import os
import shutil
import sys


def case_root(experiment):
    override=os.environ.get('CHIPNEBULA_CASE_ROOT')
    if override:return Path(override).expanduser().resolve()
    root=Path(experiment).resolve()
    for parent in (root,*root.parents):
        if (parent/'runtime/src/chip_nebula/__init__.py').is_file() and (parent/'toolchain/orfs/source-manifest.json').is_file():
            return parent
    return root.parents[1]/'CodeAChip_Submission/ISSCC27/submitted_notebooks/ChipNebula_CPU'


def private_context(experiment,study,trial=None):
    identity=hashlib.sha256(str(Path(experiment).resolve()).encode()).hexdigest()[:20]
    root=Path('/tmp')/('chipnebula-'+study+'-'+str(os.getuid())+'-'+identity)
    return root/trial if trial is not None else root


def sandbox_command(project, workspace, private_home, command, readonly=()):
    project,workspace,private_home=(Path(path).resolve() for path in (project,workspace,private_home))
    if not workspace.is_relative_to(project) or private_home.is_relative_to(project):
        raise ValueError('Workspace must belong to the trial; private context must remain outside it')
    executable=os.environ.get('CHIP_STUDY_CODEX_BINARY') or shutil.which('codex-real')
    if not executable:
        standalone=Path.home()/'.codex/packages/standalone/current/bin/codex'
        executable=str(standalone) if standalone.is_file() else shutil.which('codex')
    if not executable:
        raise ValueError('Set CHIP_STUDY_CODEX_BINARY to the recorded standalone Codex executable')
    binary=Path(executable).resolve()
    if not binary.is_file() or binary.name!='codex' or binary.is_relative_to(private_home):
        raise ValueError('Use the real standalone Codex binary and its companion files, not the study wrapper')
    roots={Path(sys.prefix).resolve(),Path(sys.base_prefix).resolve()}
    aliases={}
    python_link=Path(sys.executable)
    for _ in range(40):
        for parent in python_link.parents:
            if parent.is_symlink():aliases[parent]=parent.resolve()
        if not python_link.is_symlink():break
        target=python_link.readlink()
        python_link=target if target.is_absolute() else Path(os.path.normpath(python_link.parent/target))
    paths=[str(Path(sys.executable).parent)]
    for name in ('python3','iverilog','vvp','verilator','git','make','gcc','g++'):
        found=shutil.which(name)
        if found:
            tool=Path(found).resolve();roots.add(tool.parent.parent);paths.append(str(tool.parent))
    args=['bwrap','--unshare-user','--unshare-pid','--unshare-ipc','--die-with-parent',
          '--new-session','--proc','/proc','--dev','/dev','--tmpfs','/tmp']
    roots.update(Path(path) for path in ('/usr','/bin','/sbin','/lib','/lib64','/etc'))
    for root in sorted(roots,key=lambda path:(len(path.parts),str(path))):
        if not root.exists():continue
        resolved=root.resolve()
        if project.is_relative_to(resolved) or private_home.is_relative_to(resolved):
            raise ValueError('A tool root would expose the experiment/context parent: '+str(root))
        args+=['--ro-bind',str(resolved),str(resolved)]
        if root.is_symlink():args+=['--symlink',str(resolved),str(root)]
    for alias,target in aliases.items():
        if not any(alias.is_relative_to(root.resolve()) for root in roots) and alias not in roots:
            args+=['--symlink',str(target),str(alias)]
    args+=['--ro-bind',str(project),str(project),'--bind',str(workspace),str(workspace),
           '--bind',str(private_home),str(Path.home()/'.codex')]
    for relative in ('spec','context','ip','tools','.nebula_inputs',*readonly):
        path=workspace/relative
        if path.exists():args+=['--ro-bind',str(path),str(path)]
    if os.environ.get('CHIP_STUDY_CHECK_SOCKET'):
        args+=['--dir','/run','--ro-bind',os.environ['CHIP_STUDY_CHECK_SOCKET'],'/run/study-check.sock']
    bundled_bwrap=binary.parent.parent/'codex-resources/bwrap'
    if bundled_bwrap.is_file():
        args+=['--dir','/codex-resources','--ro-bind',str(bundled_bwrap),'/codex-resources/bwrap']
    args+=['--dir','/tools','--ro-bind',str(binary.parent),'/tools',
           '--setenv','PATH',':'.join(dict.fromkeys([*paths,'/usr/bin','/bin'])),
           '--setenv','GIT_OPTIONAL_LOCKS','0','--unsetenv','PYTHONPATH',
           '--chdir',str(workspace),'--',*command]
    return args
