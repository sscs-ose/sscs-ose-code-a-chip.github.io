"""Create a static, local reading copy of the executed submission notebook."""
from pathlib import Path
import html
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', lambda m: '<img loading="lazy" alt="'+html.escape(m[1],quote=True)+'" src="'+html.escape(m[2],quote=True)+'">', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', lambda m: '<a href="'+html.escape(m[2],quote=True)+'">'+m[1]+'</a>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    return text


def markdown(source):
    lines=source.splitlines()
    out=[]
    i=0
    paragraph=[]
    def flush():
        if paragraph:
            out.append('<p>'+inline(' '.join(paragraph))+'</p>')
            paragraph.clear()
    while i<len(lines):
        line=lines[i]
        if line.startswith('```'):
            flush(); block=[]; i+=1
            while i<len(lines) and not lines[i].startswith('```'):
                block.append(lines[i]);i+=1
            out.append('<pre>'+html.escape('\n'.join(block))+'</pre>')
        elif line.startswith('|') and i+1<len(lines) and re.match(r'^\|[\s:|\-]+\|$',lines[i+1]):
            flush()
            rows=[line];i+=2
            while i<len(lines) and lines[i].startswith('|'):
                rows.append(lines[i]);i+=1
            cells=lambda s:[inline(x.strip()) for x in s.strip().strip('|').split('|')]
            out.append('<div class="table-scroll"><table><thead><tr>'+''.join('<th>'+x+'</th>' for x in cells(rows[0]))+'</tr></thead><tbody>')
            out.extend('<tr>'+''.join('<td>'+x+'</td>' for x in cells(row))+'</tr>' for row in rows[1:])
            out.append('</tbody></table></div>')
            continue
        elif re.match(r'^#{1,6} ',line):
            flush(); level=len(line)-len(line.lstrip('#'))
            label=line[level+1:]
            out.append(f'<h{level}>'+inline(label)+f'</h{level}>')
        elif re.match(r'^(?:\d+\.|[-*]) ',line):
            flush(); items=[]; ordered=bool(re.match(r'^\d+\.',line))
            while i<len(lines) and re.match(r'^(?:\d+\.|[-*]) ',lines[i]):
                items.append(re.sub(r'^(?:\d+\.|[-*]) ','',lines[i]));i+=1
            tag='ol' if ordered else 'ul'
            out.append('<'+tag+'>'+''.join('<li>'+inline(x)+'</li>' for x in items)+'</'+tag+'>')
            continue
        elif not line.strip():
            flush()
        else:
            paragraph.append(line.strip())
        i+=1
    flush()
    return '\n'.join(out)


def main():
    notebook=json.loads((ROOT/'HuLLCirq.ipynb').read_text(encoding='utf-8'))
    body=[]
    for cell in notebook['cells']:
        source=''.join(cell['source'])
        if cell['cell_type']=='markdown':
            body.append('<section class="markdown">'+markdown(source)+'</section>')
        elif cell['cell_type']=='code':
            body.append('<details class="code"><summary>Executed Python cell '+str(cell.get('execution_count'))+'</summary><pre>'+html.escape(source)+'</pre></details>')
            for output in cell.get('outputs',[]):
                if output.get('output_type')=='error':
                    raise RuntimeError('Notebook contains an error output.')
                text=output.get('text',[])
                if text:
                    body.append('<pre class="output">'+html.escape(''.join(text))+'</pre>')
    page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>HuLLCirq — final review</title><style>
body{margin:0;color:#17263c;background:#f0f3f7;font:16px/1.65 system-ui,Segoe UI,Arial,sans-serif}main{max-width:1120px;margin:28px auto;background:white;padding:42px 50px;border-radius:12px;box-shadow:0 3px 20px #23334d14}a{color:#075ca8}h1,h2,h3{color:#102a4c;line-height:1.3}h1{font-size:32px}h2{margin-top:44px;border-top:1px solid #dce3ec;padding-top:26px}h3{margin-top:28px}.notice{background:#eaf4fb;border-left:4px solid #1481ad;padding:14px 20px;margin-bottom:28px}.table-scroll{overflow-x:auto;margin:18px 0}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;vertical-align:top;padding:9px 11px;border:1px solid #d8e1eb;min-width:75px;overflow-wrap:anywhere}th{background:#edf3f9}img{display:block;max-width:100%;height:auto;margin:22px auto;border:1px solid #e0e6ed}pre{white-space:pre;overflow:auto;background:#f5f7fa;border:1px solid #dce3ec;padding:16px;font:13px/1.55 Consolas,monospace}.output{background:#f1f8f5;border-left:4px solid #328362}code{font:0.88em Consolas,monospace;overflow-wrap:anywhere}details{margin:16px 0}summary{cursor:pointer;color:#36536f}.code summary{font-weight:600}@media(max-width:760px){main{padding:24px 16px;margin:0;border-radius:0}h1{font-size:27px}body{font-size:15px}}@media print{body{background:white}main{box-shadow:none;padding:10px}details{display:none}.notice{break-inside:avoid}img{break-inside:avoid}}
</style></head><body><main><div class="notice"><strong>Final reading copy.</strong> The editable source is <a href="HuLLCirq.ipynb">HuLLCirq.ipynb</a>. Python outputs below were recorded by actually executing its read-only cells. Images use the saved circuit evidence. No model, simulator or EDA starts by opening this page. See the <a href="docs/final_submission_checklist.md">final submission checklist</a> and <a href="submission/PR_DESCRIPTION.md">prepared PR description</a>.</div>'''+''.join(body)+'</main></body></html>\n'
    (ROOT/'HuLLCirq.html').write_text(page,encoding='utf-8')
    print('Created HuLLCirq.html from the executed notebook.')


if __name__=='__main__':
    main()
