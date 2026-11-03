"""Common proposal validation, available in isolated agent workspaces."""
import json
from study_protocol import config_tuple


def key(document):
    configuration=document['configuration'];actions=document['rtl_actions']
    values=config_tuple(configuration)
    if set(actions)!={'operand_isolation','reduce_width'} or any(type(v) is not bool for v in actions.values()):
        raise ValueError('Both shared RTL action switches must be booleans')
    return (*values,actions['operand_isolation'],actions['reduce_width'])


def validate(document, observations, allowed):
    if set(document)!={'configuration','rtl_actions','rationale'} or not isinstance(document['rationale'],str) or not document['rationale'].strip():
        raise ValueError('Provide configuration, rtl_actions and a report-grounded rationale')
    selected=key(document)
    if document['rtl_actions'] not in allowed:
        raise ValueError('RTL action combination lacks correctness qualification')
    seen={key(dict(configuration=row['configuration'],rtl_actions=row.get('rtl_actions',dict(operand_isolation=False,reduce_width=False))))
          for row in observations}
    if selected in seen:raise ValueError('Candidate has already been tried in this session')
    return document


def local(workspace):
    path=workspace/'proposal/candidate.json'
    if path.is_symlink() or path.stat().st_size>65536:raise ValueError('Unsafe candidate file')
    document=json.loads(path.read_text());observations=[json.loads((workspace/'context/baseline.json').read_text())]
    for path in (workspace/'.nebula_inputs').rglob('artifact.json'):
        artifact=json.loads(path.read_text())
        if artifact['type'] in ('ppa.route.report','ppa.evaluation.report'):
            observations.extend(artifact['payload'].get('history',[]))
    allowed=json.loads((workspace/'context/protocol.json').read_text())['allowed_rtl_actions']
    return validate(document,observations,allowed)
