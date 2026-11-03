"""Execute the account-free notebook cells and export the same body to embedded HTML."""
import argparse
from pathlib import Path
import sys

import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter
from jupyter_client import KernelManager

CASE=Path(__file__).resolve().parents[1]


def render(notebook_path,html_path):
    notebook_path,html_path=Path(notebook_path).resolve(),Path(html_path).resolve()
    notebook=nbformat.read(notebook_path,as_version=4)
    manager=KernelManager(kernel_name='python3')
    manager.kernel_spec.argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}']
    client=NotebookClient(notebook,km=manager,timeout=300,resources={'metadata':{'path':str(notebook_path.parent)}})
    try:
        client.execute()
    finally:
        if manager.has_kernel:manager.shutdown_kernel(now=True)
    assert all(not any(o.output_type=='error' for o in cell.get('outputs',[])) for cell in notebook.cells)
    nbformat.write(notebook,notebook_path)
    exporter=HTMLExporter(template_name='lab',embed_images=True)
    body,_=exporter.from_notebook_node(notebook,resources={'metadata':{'path':str(notebook_path.parent)}})
    # Local preview uses the exact executed body. Figures remain available at full vector size.
    style='<style>.jp-Notebook{max-width:1240px;margin:auto} .jp-RenderedMarkdown img{max-width:100%;height:auto} .jp-RenderedMarkdown table{font-size:0.95rem}</style>'
    html_path.write_text(body.replace('</head>',style+'</head>'),encoding='utf-8')
    print('NOTEBOOK_EXECUTED_AND_HTML_EXPORTED',notebook_path,html_path)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--notebook',type=Path,default=CASE/'ChipWave.ipynb')
    parser.add_argument('--html',type=Path,default=CASE/'ChipWave.html')
    args=parser.parse_args();render(args.notebook,args.html)
