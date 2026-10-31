"""Exclude transient build links while retaining source/archive safety checks."""
from pathlib import Path
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch
import subprocess
import tempfile
import hashlib
import json
import export_snapshot
from chip_nebula.taskgraph.domain import Artifact, ArtifactContent, ArtifactProducer

with tempfile.TemporaryDirectory() as temp:
    project = Path(temp) / 'project'
    (project / 'rtl').mkdir(parents=True)
    (project / 'build/libs').mkdir(parents=True)
    source = b'module dut; endmodule\n'
    (project / 'rtl/dut.sv').write_bytes(source)
    (project / 'build/libs/libatomic.so').symlink_to('/not-an-exported-dependency')
    for args in [('init', '-q'), ('add', '.'), ('-c', 'user.name=test', '-c', 'user.email=test@invalid', 'commit', '-qm', 'fixture')]:
        subprocess.run(['git', *args], cwd=project, check=True)
    def artifact():
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=project).decode().strip()
        tree = subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=project).decode().strip()
        return Artifact('fixture', 'rtl.integration', 1, ArtifactProducer('fixture', 'fixture', 'fixture', 'fixture', 1),
                        ArtifactContent('git', commit, tree, ('rtl',)), {})
    @contextmanager
    def store(*args):
        yield SimpleNamespace(task_state=lambda _: SimpleNamespace(value='satisfied'),
            deliveries=lambda _: {'integration': SimpleNamespace(artifact_id='fixture')},
            get_artifact=lambda _: artifact())
    with patch.object(export_snapshot, 'StaticTaskGraphStore', store):
        out = Path(temp) / 'export'
        export_snapshot.export(project, 'fixture', 'integration', 'integration', out)
        assert (out / 'rtl/dut.sv').read_bytes() == source and not (out / 'build').exists()
        record = json.loads((out / 'selected-delivery.json').read_text())
        assert record['exported_source_sha256']['rtl/dut.sv'] == hashlib.sha256(source).hexdigest()
        (project / 'rtl/escape.sv').symlink_to('/unsafe-source-link')
        subprocess.run(['git', 'add', '.'], cwd=project, check=True)
        subprocess.run(['git', '-c', 'user.name=test', '-c', 'user.email=test@invalid', 'commit', '-qm', 'unsafe fixture'], cwd=project, check=True)
        try:
            export_snapshot.export(project, 'fixture', 'integration', 'integration', Path(temp) / 'unsafe')
        except ValueError:
            pass
        else:
            raise AssertionError('Unsafe source symlink accepted')
print('SOURCE_EXPORT_PASS: build links excluded, RTL bytes/hashes preserved, source symlinks still rejected')

# Completed extension summaries belong in drafts even while another cohort is running.
import export_study_results
from study_protocol import preregistration, write_json

with tempfile.TemporaryDirectory() as temp:
    source=Path(temp)/'study';source.mkdir()
    write_json(source/'protocol.json',preregistration())
    completed={'finished':True,'rows':[{'rank_eligible':False}]}
    write_json(source/'representatives/summary.json',completed)
    write_json(source/'representatives/selection.json',{'integrations':[{'cell':'fixture'}]})
    write_json(source/'high-frequency/selection.json',{'choices':[{'name':'fixture'}]})
    evidence=source/'representatives/fixture/physical/evidence/sentinel.txt'
    evidence.parent.mkdir(parents=True);evidence.write_text('physical evidence\n')
    with patch.object(export_study_results,'graph'):
        draft=Path(temp)/'draft';export_study_results.export(source,draft,foundations=True)
        assert json.loads((draft/'representatives/summary.json').read_text())==completed
        assert (draft/'high-frequency/selection.json').is_file()
        assert not (draft/'high-frequency/summary.json').exists()
        assert not (draft/'representatives/fixture').exists()
        assert not json.loads((draft/'export-manifest.json').read_text())['complete']
        full=Path(temp)/'full';export_study_results.export(source,full)
        assert (full/'representatives/fixture/physical/evidence/sentinel.txt').read_bytes()==evidence.read_bytes()
print('STUDY_DRAFT_EXPORT_PASS: completed summaries retained, unfinished outcomes absent, heavy evidence deferred to full export')
