"""Eliminate storage-free internal resistor nodes without discarding devices or C."""
from pathlib import Path
import argparse,heapq,json,re
import numpy as np

def currents(edges,boundary,voltages):
    from scipy.sparse import csc_matrix,eye
    from scipy.sparse.linalg import splu
    nodes=sorted(set(boundary)|{n for a,b,g in edges for n in (a,b)})
    index={n:i for i,n in enumerate(nodes)};rows=[];cols=[];values=[]
    for a,b,g in edges:
        i,j=index[a],index[b];rows.extend([i,j,i,j]);cols.extend([i,j,j,i]);values.extend([g,g,-g,-g])
    matrix=csc_matrix((values,(rows,cols)),shape=(len(nodes),len(nodes)))
    visible=np.array([index[n] for n in boundary]);hidden=np.array([index[n] for n in nodes if n not in set(boundary)],dtype=int)
    out=matrix[visible,:][:,visible]@voltages
    if len(hidden):
        block=matrix[hidden,:][:,hidden]+eye(len(hidden),format='csc')*1e-18
        internal=splu(block).solve(-(matrix[hidden,:][:,visible]@voltages))
        out+=matrix[visible,:][:,hidden]@internal
    return np.asarray(out)

def reduce(source,target,max_degree=12):
    source=Path(source).resolve();target=Path(target).resolve();lines=source.read_text().splitlines();graph={};protected={'0'};original=[]
    def add(a,b,g):
        if a==b:return
        graph.setdefault(a,{})[b]=graph.get(a,{}).get(b,0.)+g
        graph.setdefault(b,{})[a]=graph.get(b,{}).get(a,0.)+g
    for line in lines:
        f=line.split()
        if not f or f[0].startswith(('*','.','+')):continue
        kind=f[0][0].upper()
        if kind=='R':
            assert len(f)==4,f
            a,b=f[1:3];g=1/float(f[3]);add(a,b,g);original.append((a,b,g))
        elif kind=='C':protected.update(f[1:3])
        elif kind=='X':
            model=next((i for i,v in enumerate(f) if v.startswith('sky130_fd_pr__')),len(f)-1)
            protected.update(f[1:model])
        elif kind in ('M','Q','D','V','I','E','G','L'):raise ValueError('Add an explicit terminal parser for '+f[0])
    initial_nodes=set(graph);queue=[(len(graph[n]),n) for n in graph if n not in protected];heapq.heapify(queue);removed=0
    while queue:
        degree,node=heapq.heappop(queue)
        if node not in graph or degree!=len(graph[node]) or degree>max_degree:continue
        neighbors=list(graph[node].items());total=sum(g for n,g in neighbors)
        for i,(a,ga) in enumerate(neighbors):
            for b,gb in neighbors[i+1:]:add(a,b,ga*gb/total)
        for a,g in neighbors:
            del graph[a][node]
            if a not in protected:heapq.heappush(queue,(len(graph[a]),a))
        del graph[node];removed+=1
    reduced=[(a,b,g) for a in sorted(graph) for b,g in sorted(graph[a].items()) if a<b]
    boundary=sorted(protected&initial_nodes)
    voltage=np.random.default_rng(20261029).uniform(-1.8,1.8,(len(boundary),8))
    before=currents(original,boundary,voltage);after=currents(reduced,boundary,voltage)
    error=float(np.max(np.abs(before-after)));relative=float(np.linalg.norm(before-after)/(np.linalg.norm(before)+1e-30))
    assert error<1e-9 and relative<1e-9,(error,relative)
    replacement=[f'RK{i} {a} {b} {1/g:.17g}' for i,(a,b,g) in enumerate(reduced)];output=[];written=False
    for line in lines:
        if re.match(r'^R\S*\s',line):
            if not written:output.extend(replacement);written=True
        else:output.append(line)
    assert written
    target.write_text('\n'.join(output)+'\n')
    report={'status':'PASS','method':'Exact star-mesh elimination of internal resistor-only nodes; every capacitor, transistor and subcircuit interface terminal is protected.',
        'source':str(source),'target':str(target),'original_resistors':len(original),'reduced_resistors':len(reduced),
        'original_resistor_nodes':len(initial_nodes),'remaining_resistor_nodes':len(graph),'eliminated_storage_free_nodes':removed,
        'protected_boundary_nodes':len(boundary),'independent_voltage_trials':8,'max_boundary_current_error_a':error,'relative_boundary_current_error':relative,
        'scope':'Algebraically equivalent passive resistor network with unchanged device/C terminals. Numerical simulator shunts are checked separately by convergence experiments.'}
    target.with_suffix('.reduction.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PEX_RESISTOR_REDUCTION_PASS','nodes',len(initial_nodes),'->',len(graph),'current_error_A',error,flush=True);return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--target',type=Path,required=True);args=parser.parse_args();reduce(args.source,args.target)
