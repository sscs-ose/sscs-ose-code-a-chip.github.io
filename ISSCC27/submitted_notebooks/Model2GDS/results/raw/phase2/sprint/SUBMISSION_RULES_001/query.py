"""Read pinned official rules, preserving response identity and factual fields."""
from datetime import datetime, timezone
import hashlib
import json
import re
import urllib.request

COMMIT = 'a502a6ba01260d3492df9137dddae0bb5fabeb3c'
BASE = 'https://raw.githubusercontent.com/sscs-ose/sscs-ose-code-a-chip.github.io/' + COMMIT + '/'
expected = {'README.md': 'df0d6f0a00b9b45e53f90027b112e345bfcfbbbb2ec273f23c5a8963e21e10f3',
            'howtoapply.md': '1c62abbb8b6527934a0b0fb4dc058dec0fce49096d26e14734c08f96c220f599'}
records, texts = [], {}
for name in expected:
    url = BASE + name
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Model2GDS-rule-check'}), timeout=45) as response:
        body = response.read()
        record = {'url': url, 'status': response.status, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(),
                  'http_date': response.headers.get('Date'), 'etag': response.headers.get('ETag')}
    if record['sha256'] != expected[name]:
        raise ValueError('Pinned official source bytes differ: ' + name)
    records.append(record)
    texts[name] = body.decode('utf-8')
readme, guide = texts['README.md'], texts['howtoapply.md']
fields = {
    'contest_year_2027': 'ISSCC 2027' in readme,
    'deadline': re.search(r'October 31st, 2026, 11:59 AM Pacific Time', readme).group(),
    'project_folder': re.search(r'ISSCC27/submitted_notebooks/<project_name>/', readme).group(),
    'license_example': re.search(r'Apache License 2\.0', readme).group(),
    'educational_project_supported': 'educational project' in readme,
    'layout_encouraged_not_required': 'encouraged but not required' in readme,
    'notebook_required': 'openly licensed Jupyter notebook' in readme,
    'methodology_results_reproduction_required': all(word in readme for word in ('methodology', 'results', 'reproducibility instructions')),
    'representative_required': 'designate one representative' in readme,
    'guide_older_year': 'ISSCC26' in guide,
    'guide_old_deadline': 'November 27, 2025' in guide,
    'guide_team_at_top': 'team members' in guide.lower(),
    'guide_references': 'references' in guide.lower(),
    'guide_versions': 'versions' in guide.lower(),
}
issue_url = 'https://api.github.com/repos/sscs-ose/sscs-ose-code-a-chip.github.io/issues/194'
with urllib.request.urlopen(urllib.request.Request(issue_url, headers={'User-Agent': 'Model2GDS-rule-check'}), timeout=45) as response:
    body = response.read()
    issue = json.loads(body)
    issue_record = {'url': issue_url, 'http_status': response.status, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(),
                    'number': issue['number'], 'state': issue['state'], 'comments': issue['comments'], 'updated_at': issue['updated_at']}
result = {'status': 'PASS', 'queried_at': datetime.now(timezone.utc).isoformat(), 'official_commit': COMMIT,
          'responses': records, 'factual_fields': fields, 'deadline_issue': issue_record,
          'internal_deadline_policy': 'Preserve earlier October 9 conservative project planning; no frozen document is rewritten.',
          'scope': 'Official rule/source verification only. No eligibility decision, public submission, EDA or research result.'}
print(json.dumps(result, indent=2, sort_keys=True))
