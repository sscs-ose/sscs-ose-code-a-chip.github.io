"""Pure proposal checks shared by the protected evaluator and isolated roles."""
import json

from study_protocol import config_tuple


def validate_configuration(configuration, observations):
    selected = config_tuple(configuration)
    if selected in {config_tuple(row['configuration']) for row in observations}:
        raise ValueError('Previously tried configuration; choose another frozen-domain tuple')


def proposal_file(workspace):
    path = workspace/'proposal/candidate.json'
    if path.is_symlink() or path.stat().st_size > 65536:
        raise ValueError('Invalid candidate file')
    document = json.loads(path.read_text())
    if set(document) != {'configuration', 'rationale'} or not isinstance(document['rationale'], str):
        raise ValueError('Candidate file needs configuration and a string rationale')
    return document


def validate_local(workspace):
    observations = [json.loads((workspace/'context/baseline.json').read_text())]
    for path in sorted((workspace/'.nebula_inputs').rglob('artifact.json')):
        artifact = json.loads(path.read_text())
        if artifact['type'] == 'ppa.evaluation.report':
            observations.extend(artifact['payload']['history'])
    document = proposal_file(workspace)
    validate_configuration(document['configuration'], observations)
    return document
