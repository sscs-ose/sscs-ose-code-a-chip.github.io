"""Audit the authorized project-root publication and bind reused DUT evidence."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys

def digest(data):
    return hashlib.sha256(data).hexdigest()

def check_delivery(root):
    records = [json.loads(p.read_text()) for p in root.glob('.nebula_inputs/*/artifact.json')]
    artifact = next(a for a in records if a['id']=='authorized-root-project-delivery')
    integration = next(a for a in records if a['id']=='artifact-2f225eabd33249d79dbc17a7b73ec146')
    plan = next(a['payload'] for a in records if a['id']=='artifact-478b595695d0419e81e4d77e864a23d7')
    resource = root/'.nebula_inputs'/artifact['id']
    manifest_path = resource/'project-delivery.manifest.json'
    manifest_bytes = manifest_path.read_bytes()
    assert manifest_bytes == subprocess.check_output(
        ['git','show',artifact['content']['commit']+':project-delivery.manifest.json'])
    manifest = json.loads(manifest_bytes)
    project = resource/manifest['project_root']
    assert project == resource/'delivery/standard-project'
    assert (project/'project-delivery.manifest.json').read_bytes() == manifest_bytes
    files = []
    for name, expected in sorted(manifest['content_files_sha256'].items()):
        relative = PurePosixPath(name)
        assert not relative.is_absolute() and '..' not in relative.parts, name
        path = project/name
        assert stat.S_ISREG(path.lstat().st_mode), name
        assert path.resolve().is_relative_to(project.resolve()), name
        data = path.read_bytes()
        assert digest(data) == expected, name
        files.append({'path':name,'bytes':len(data),'sha256':digest(data),'matched':True})
    actual = {str(p.relative_to(project)) for p in project.rglob('*') if p.is_file()}
    assert actual == set(manifest['content_files_sha256']) | {'project-delivery.manifest.json'}
    source = (root/'spec/source-contract.md').read_bytes()
    acceptance = (root/'spec/acceptance.md').read_bytes()
    assert digest(source) == plan['plan']['input_file_sha256']['spec/source-contract.md']
    assert digest(acceptance) == plan['plan']['input_file_sha256']['spec/acceptance.md']
    contract_path = project/'t09-base-contract.md'
    contract = contract_path.read_bytes()
    suffix = b''.join(source.splitlines(keepends=True)[18:])
    expected_hash = '1021e4b88446ed12c7b6a3cc6f46847f16a44c70a47660fff24f5f91ca778958'
    assert contract == suffix and len(contract) == 6930 and digest(contract) == expected_hash
    assert manifest['root_contract']['path'] == 't09-base-contract.md'
    assert manifest['root_contract']['bytes'] == len(contract)
    assert manifest['root_contract']['sha256'] == digest(contract)
    assert manifest['root_contract']['source_sha256'] == digest(source)
    assert (resource/'t09-base-contract.md').read_bytes() == contract
    companion = project/manifest['companion_acceptance']['path']
    assert companion == project/'spec/acceptance.md'
    assert companion.read_bytes() == acceptance
    assert digest(acceptance) == manifest['companion_acceptance']['sha256']
    assert manifest['selected_integration_artifact'] == integration['id']
    assert manifest['selected_integration_commit'] == integration['content']['commit']
    selected = json.loads((project/'selected-delivery.json').read_text())
    assert {key:selected.get(key) for key in integration} == integration
    assert selected['exported_source_sha256'] == manifest['rtl_sha256']
    previous = json.loads((root/'reports/verification/candidate-view.json').read_text())
    assert previous['rtl_commit'] == integration['content']['commit']
    assert set(manifest['rtl_sha256']) == {r['source'] for r in previous['sources']}
    rtl = []
    for entry in previous['sources']:
        name = entry['source']
        frozen = subprocess.check_output(['git','show',integration['content']['commit']+':'+name])
        assert (root/name).read_bytes() == (project/name).read_bytes() == frozen, name
        assert digest(frozen) == entry['sha256'] == manifest['rtl_sha256'][name], name
        rtl.append({'path':name,'sha256':digest(frozen),'formal_snapshot_equal':True,
                    'published_view_equal':True,'prior_verified_source_equal':True})
    for name in ['spec/draft.specir','spec/contracts.json','spec/provenance.json','spec/questions.json',
                 'integration/design.f','integration/dependencies.lock.json']:
        if name == 'integration/dependencies.lock.json':
            assert (project/name).read_bytes() == subprocess.check_output(
                ['git','show',integration['content']['commit']+':'+name]), name
        else:
            assert (project/name).read_bytes() == (root/name).read_bytes(), name
    fixed = resource/'verification/fixed_common'
    fixed_manifest = json.loads((fixed/'fixed-files.json').read_text())
    previous_fixed = json.loads((root/'reports/verification/fixed-final.json').read_text())
    assert digest((fixed/'fixed-files.json').read_bytes()) == previous_fixed['manifest_sha256']
    assert len(fixed_manifest) == previous_fixed['files']
    for name, expected in fixed_manifest.items():
        assert digest((fixed/name).read_bytes()) == expected, name
    return {'check':'AC-DELIVERY','contract_id':'SPEC_AUTHORITY','verdict':'passed',
        'scope':'authorized complete project delivery; original selected rtl.integration unchanged',
        'path':str(contract_path.relative_to(root)),'file_type':'regular','bytes':len(contract),
        'sha256':digest(contract),'source': 'spec/source-contract.md lines19 through EOF',
        'source_sha256':digest(source),'byte_equal':True,
        'companion_acceptance_sha256':digest(acceptance),'companion_byte_equal':True,
        'manifest':str(manifest_path.relative_to(root)),'manifest_sha256':digest(manifest_bytes),
        'actor':manifest['actor'],'artifact_digest':artifact['digest'],
        'manifest_files':files,'rtl_source_binding':rtl,'fixed_files_validated':len(fixed_manifest),
        'fixed_manifest_sha256':previous_fixed['manifest_sha256'],
        'original_integration_omission_retained':'t09-base-contract.md is absent from the original rtl.integration content paths; operator publication supplies that project dependency separately.',
        'reason':'Actual operator-delivered root file, source suffix, companion and full manifest agree; qualified functional evidence is reused by exact DUT/spec/checker binding.',
        'tool_versions':{'delivery_audit_python':sys.version},
        'commands':['python3 -B verification/write_report.py --refresh-delivery']}

if __name__ == '__main__':
    print(json.dumps(check_delivery(Path.cwd()),indent=2))
