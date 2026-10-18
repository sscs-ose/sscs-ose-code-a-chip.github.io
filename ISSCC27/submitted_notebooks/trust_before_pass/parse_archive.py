"""Parser for archived CACE text. Apache-2.0."""
import re

def parse(path):
    root={'blocks':[], 'fields':{}, 'raw':[]}; stack=[root]
    for no,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1):
        s=line.strip()
        if not s or s.startswith('#'): continue
        if re.fullmatch(r'[\w]+\s*\{',s):
            b={'kind':s.split()[0], 'line':no,'blocks':[],'fields':{},'raw':[]}
            stack[-1]['blocks'].append(b);stack.append(b)
        elif s=='}': stack.pop()
        elif s=='+':
            old=stack.pop(); b={'kind':old['kind'],'line':no,'blocks':[],'fields':{},'raw':[]}
            stack[-1]['blocks'].append(b);stack.append(b)
        elif re.match(r'^\S+:\s+',s):
            k,v=re.split(r':\s+',s,maxsplit=1);stack[-1]['fields'][k]=v
        else: stack[-1]['raw'].append(s)
    assert len(stack)==1
    return root
