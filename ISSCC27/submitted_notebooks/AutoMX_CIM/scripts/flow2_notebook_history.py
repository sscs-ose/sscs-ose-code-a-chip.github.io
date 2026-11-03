"""Historical evidence reader; embedded in full in the combined notebook."""
from pathlib import Path
import hashlib
import json
import re
from IPython.display import Markdown,display

REPLAY_RECORDS={}
REFERENCE_ONLY=False


def file_hash(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def summarize_values(value,depth=0):
    if depth>3:return '<details retained in source report>'
    if isinstance(value,dict):
        return {k:summarize_values(v,depth+1) for k,v in value.items() if not any(token in k.lower() for token in ('sha256','hash','digest')) and k not in ('intervals','measurements','decks','jobs','cases','points','screens','evidence','scope','scope_warning','conclusion','qualification','fabrication_ready','not_signoff','status','assessment','limitations','not_measured','warnings')}
    if isinstance(value,list):
        if len(value)>12:return {'entries':len(value),'first_entries':[summarize_values(v,depth+1) for v in value[:3]]}
        return [summarize_values(v,depth+1) for v in value]
    return value


def review_reports(root,paths,*,label='',show_log=True):
    """Read saved measurements; preserve negative, missing and stale results."""
    root=Path(root);rows=[]
    if REFERENCE_ONLY:
        rows=[{'path':relative,'state':'REFERENCE_ONLY'} for relative in paths]
        REPLAY_RECORDS[label]=rows
        return rows
    print('\nHISTORICAL EVIDENCE REPLAY:',label,'— no new simulator measurement')
    for relative in paths:
        path=root/relative
        display(Markdown(f'**Report:** [{relative}]({relative})'))
        if not path.is_file():
            print('MISSING / NOT MEASURED at this path; not PASS');rows.append({'path':relative,'state':'MISSING'});continue
        if path.suffix.lower()!='.json':
            print('Tài liệu nguồn đã lưu:',path);rows.append({'path':relative,'sha256':file_hash(path),'state':'DOCUMENT'});continue
        try:data=json.loads(path.read_text())
        except (ValueError,OSError) as error:
            print('UNREADABLE:',error);rows.append({'path':relative,'state':'UNREADABLE'});continue
        if not isinstance(data,dict):
            print('Saved JSON data (not a PASS receipt):',json.dumps(summarize_values(data),indent=2,ensure_ascii=False)[:2200])
            rows.append({'path':relative,'sha256':file_hash(path),'state':'SAVED_JSON_DATA','recorded_status':None});continue
        print('Saved measurement timestamp:',data.get('timestamp_utc','not recorded'))
        keys=('format','stage','completed_sims','planned_sims','completed_new_sims','planned_new_sims','metrics',
              'summary','analysis','selected_feature','failures')
        details={k:summarize_values(data[k]) for k in keys if k in data}
        if not details:details={'source_report':relative,'fields_available':len(data)}
        print(json.dumps(details,indent=2,ensure_ascii=False)[:11000])
        refs=[]
        def scan(value):
            if isinstance(value,dict):
                if isinstance(value.get('path'),str) and re.fullmatch('[0-9a-f]{64}',str(value.get('sha256',''))):refs.append(value)
                for child in value.values():scan(child)
            elif isinstance(value,list):
                for child in value:scan(child)
        scan({k:data[k] for k in ('views','inputs','sources','logs') if k in data})
        verified=0;problems=[]
        for ref in refs:
            artifact=Path(ref['path']);artifact=artifact if artifact.is_absolute() else root/artifact
            if not artifact.is_file():problems.append({'path':str(artifact),'state':'MISSING'})
            elif file_hash(artifact)!=ref['sha256']:problems.append({'path':str(artifact),'state':'HASH_CHANGED'})
            else:verified+=1
        print('Source files checked:',verified,'| issues:',len(problems))
        for issue in problems[:8]:print(issue)
        if show_log:
            candidates=[]
            for entry in data.get('logs',[]):
                value=entry.get('path') if isinstance(entry,dict) else entry
                if isinstance(value,str):candidates.append(root/value)
            candidates.extend(sorted(path.parent.glob('*.log'))[:1])
            for log in candidates:
                if log.is_file():
                    lines=log.read_text(errors='replace').splitlines()
                    print('SAVED NATIVE LOG (historical):',log,'\n'+'\n'.join(lines[:4]+['...']+lines[-10:]));break
        rows.append({'path':relative,'sha256':file_hash(path),'recorded_status':data.get('status'),
            'state':'REPLAY_WITH_SOURCE_ISSUES' if problems else 'REPLAY','verified_refs':verified,'source_issues':problems})
    REPLAY_RECORDS[label]=rows
    return rows


def plot_saved_transfer(root,relative,title):
    """Render actual measured interval envelopes, never a synthetic transfer fit."""
    if REFERENCE_ONLY:return
    import matplotlib.pyplot as plt
    path=Path(root)/relative
    if not path.is_file():print('No saved transfer report:',relative);return
    data=json.loads(path.read_text());found=[]
    def find(value):
        if isinstance(value,dict):
            if isinstance(value.get('columns'),list) and value['columns'] and 'intervals' in value['columns'][0]:found.append(value['columns'])
            for child in value.values():find(child)
        elif isinstance(value,list):
            for child in value:find(child)
    find(data.get('analysis',{}))
    if not found:print('No measured interval envelopes in',relative);return
    cols=found[0];fig,axes=plt.subplots(1,len(cols),figsize=(12,3),layout='constrained',squeeze=False)
    for ax,col in zip(axes[0],cols):
        intervals=sorted(col['intervals'],key=lambda row:row['sum'])
        x=[row['sum'] for row in intervals];lo=[row['min_diff_v']*1000 for row in intervals];hi=[row['max_diff_v']*1000 for row in intervals]
        ax.fill_between(x,lo,hi,alpha=.3);ax.plot(x,lo,'.-',lw=.7);ax.plot(x,hi,'.-',lw=.7)
        ax.set_title('Column '+str(col['column']));ax.set_xlabel('Measured integer sum');ax.set_ylabel('Differential / mV');ax.grid(alpha=.2)
    fig.suptitle(title+' — saved measurement envelopes');plt.show();plt.close(fig)
