"""Execute the draft in a fresh copy, then export that exact notebook to standalone HTML."""
from pathlib import Path
import base64, hashlib, html, importlib.metadata, json, os, re, shutil, subprocess, sys, time
from datetime import datetime, timezone
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
ROOT=Path(__file__).resolve().parents[1]
started=time.monotonic()
run=ROOT/"validation"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
run.mkdir(parents=True)
copy=run/"package"
copy.mkdir()
for name in ["review.py","test_review.py","sources.json","FoldAgent.ipynb","evidence","data","design","reproduction","physical","licenses","tools"]:
    src=ROOT/name
    if src.is_dir():shutil.copytree(src,copy/name)
    else:shutil.copy2(src,copy/name)
runtime=run/"runtime";runtime.mkdir()
kernel=runtime/"kernels/p0review";kernel.mkdir(parents=True)
(kernel/"kernel.json").write_text(json.dumps({"argv":[sys.executable,"-m","ipykernel_launcher","-f","{connection_file}"],
    "display_name":"FoldAgent validation","language":"python"}))
env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1","MPLCONFIGDIR":str(runtime/"mpl"),
    "IPYTHONDIR":str(runtime/"ipython"),"JUPYTER_RUNTIME_DIR":str(runtime/"jupyter")}
test=subprocess.run([sys.executable,"-m","unittest","-v","test_review.py"],cwd=copy,env=env,text=True,capture_output=True,timeout=60)
(run/"tests.log").write_text(test.stdout+test.stderr)
assert test.returncode==0,test.stdout+test.stderr
nb=nbformat.read(copy/"FoldAgent.ipynb",as_version=4)
original_sources=[c.source for c in nb.cells]
for c in nb.cells:
    if c.cell_type=="code":c.outputs=[];c.execution_count=None
km=KernelManager(kernel_name="p0review",kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(runtime/"kernels")]))
client=NotebookClient(nb,timeout=90,km=km,resources={"metadata":{"path":str(copy)}})
client.execute(env=env)
assert [c.source for c in nb.cells]==original_sources
code=[c for c in nb.cells if c.cell_type=="code"]
assert [c.execution_count for c in code]==list(range(1,len(code)+1))
assert not any(o.output_type=="error" for c in code for o in c.outputs)
nbformat.validate(nb)
nbformat.write(nb,copy/"FoldAgent.ipynb")
# The exported text uses the same authored HTML cells; no Markdown engine is needed.
body=[]
for c in nb.cells:
    if c.cell_type=="markdown":
        assert c.source.lstrip().startswith("<")
        def embed(m):
            rel=m[1];p=copy/rel
            assert p.is_file(),rel
            return 'src="data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode()+'"'
        body.append(re.sub(r'src="(figures/[^"]+\.png)"',embed,c.source))
    else:
        out="".join(o.get("text","") for o in c.outputs if o.output_type=="stream")
        assert all(o.output_type=="stream" for o in c.outputs),[o.output_type for o in c.outputs]
        body.append('<details class="code-output"><summary>Executed Python · cell '+str(c.execution_count)+'</summary><pre><code>'+
            html.escape(c.source)+'</code></pre><pre class="output">'+html.escape(out)+'</pre></details>')
style="""body{font:17px/1.7 system-ui,-apple-system,sans-serif;color:#1f2933;background:#f2f5f7;margin:0}
main{max-width:1060px;margin:auto;background:white;padding:48px 64px}h1{font-size:34px;line-height:1.25;color:#143e50}
h2{font-size:25px;margin-top:48px;color:#143e50;border-bottom:1px solid #dbe5e9;padding-bottom:8px}
h3{font-size:20px}p{margin:18px 0}a{color:#086e8a}table{border-collapse:collapse;width:100%;font-size:15px}
td,th{border-bottom:1px solid #d6e0e5;text-align:left;padding:10px}th{background:#e9f2f5}
figure{margin:30px 0}img{width:100%;height:auto}figcaption{font-size:14px;color:#4f6069}
details{background:#f4f7f9;border:1px solid #dbe5e9;padding:12px;margin:18px 0}summary{cursor:pointer;font-size:14px;color:#345}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.5 monospace}.output{background:#e9f2ed;padding:12px}
.teaching-explanation{background:#edf5f7;border-left:4px solid #086e8a;padding:12px 18px;margin:18px 0}
code{font-size:.9em}nav{font-size:14px}footer{margin-top:48px;font-size:13px;color:#667}
@media(max-width:720px){main{padding:24px 18px}h1{font-size:27px}table{font-size:13px}}
@media print{body{background:white}main{padding:0}details.code-output{display:none}.teaching-explanation{display:block}figure{break-inside:avoid}h2{break-after:avoid}}"""
page='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FoldAgent: Agent-Assisted Logic Folding with Automated Verification — Zhanchen Zhao, Wenyu Sun, Yaqing Lai and Yubo Deng</title><style>'+style+'</style></head><body><main><nav>Apache-2.0 · Figures embedded · <a href="FoldAgent-zh.html">中文完整参考稿</a> · <a href="REVIEW_zh.md">中文读图说明</a> · <a href="FoldAgent.ipynb">Notebook</a></nav>'+"\n".join(body)+'<footer>Generated from the executed FoldAgent.ipynb. Project materials: <a href="LICENSE">Apache-2.0</a>; <a href="LICENSE-SCOPE.md">license scope and exceptions</a>.</footer></main></body></html>'
(ROOT/"FoldAgent.html").write_text(page)
# Check all relative links in both the notebook and Markdown navigation.
links=[]
for c in nb.cells:
    if c.cell_type=="markdown":links+=re.findall(r'(?:href|src)="([^"]+)"',c.source)
for path in ROOT.glob("*.md"):
    links+=re.findall(r'\]\(([^)]+)\)',path.read_text())
for link in links:
    if link.startswith(("https://","http://","#")):continue
    base=copy if link.startswith("figures/") else ROOT
    path=(base/link.split("#")[0]).resolve()
    assert path.is_relative_to(base) and path.is_file(),link
# Check original frozen inputs and old notebook again when the original workspace is present.
protected=json.loads((ROOT/"evidence/protected-inputs.json").read_text())
workspace=ROOT.parents[1]
frozen_checked=0
if (workspace/"work/chipnebula-p0-electrical-closure/frozen/L0/manifest.json").exists():
    for rel,expected in protected["frozen"].items():
        assert hashlib.sha256((workspace/rel).read_bytes()).hexdigest()==expected,rel
        frozen_checked+=1
    old=protected["old_notebook"]
    assert hashlib.sha256((workspace/old["path"]).read_bytes()).hexdigest()==old["sha256"]
shutil.copy2(copy/"FoldAgent.ipynb",ROOT/"FoldAgent.ipynb")
for p in (copy/"figures").iterdir():shutil.copy2(p,ROOT/"figures"/p.name)
(ROOT/"FoldAgent.html").write_text(page)
report=dict(status="passed",report_scope='Notebook redraw/export and saved-input checks only; the full 324 RTL simulations and three STA runs are recorded in portability/result.json.',executed_code_cells=len(code),markdown_cells=len(nb.cells)-len(code),
    execution="fresh independent package copy, exact authored sources",design_experiments_rerun=0,
    model_calls=0,tests="8 unit tests including performance-input binding and subprocess failure handling",relative_links_checked=len([l for l in links if not l.startswith(("http","#"))]),
    frozen_original_files_verified=frozen_checked,old_StackLink_preserved=frozen_checked>0,
    seconds=time.monotonic()-started,finished_at=datetime.now(timezone.utc).isoformat(),
    notebook_sha256=hashlib.sha256((ROOT/"FoldAgent.ipynb").read_bytes()).hexdigest(),
    html_sha256=hashlib.sha256((ROOT/"FoldAgent.html").read_bytes()).hexdigest(),
    environment={"python":sys.version,"packages":{n:importlib.metadata.version(n) for n in ["matplotlib","nbformat","nbclient","ipykernel","jupyter_client"]}},
    execution_directory=str(run.relative_to(ROOT)))
(ROOT/"validation.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
