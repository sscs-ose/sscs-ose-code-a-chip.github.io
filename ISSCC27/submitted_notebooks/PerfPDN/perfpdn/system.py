"""Assemble shared resistor, device and external-source matrices."""
import json
import numpy as np
from scipy.sparse import coo_matrix,diags
from scipy.sparse.linalg import splu


def assemble(network,state,project):
    fixed={"0":0.,**{s["node"]:s["dc"] for s in state["design"]["sources"]}}
    ac_fixed={"0":0j,**{s["node"]:complex(*s["ac"]) for s in state["design"]["sources"]}}
    edges=network["edges"];names=sorted({n for a,b,*_ in edges for n in (a,b)}-fixed.keys())
    index={n:i for i,n in enumerate(names)};rows=[];cols=[];values=[]
    for k,(a,b,*_) in enumerate(edges):
        for node,sign in ((a,1),(b,-1)):
            if node in index:rows.append(index[node]);cols.append(k);values.append(sign)
    B=coo_matrix((values,(rows,cols)),shape=(len(names),len(edges))).tocsc()
    R=np.array([e[2] for e in edges]);G=(B@diags(1/R)@B.T).tocsc()
    terminal=np.array([index[t] for p,t in state["ports"]])
    rhs=-B@(np.array([ac_fixed.get(a,0)-ac_fixed.get(b,0) for a,b,*_ in edges])/R)
    cp=[];ci=[];cj=[]
    for load in state["design"]["capacitors"]:
        for a,sa in ((load["a"],1),(load["b"],-1)):
            if a not in index:continue
            for b,sb in ((load["a"],1),(load["b"],-1)):
                if b in index:ci.append(index[a]);cj.append(index[b]);cp.append(sa*sb*load["F"])
    C=coo_matrix((cp,(ci,cj)),shape=G.shape).tocsc()

    if any(n in ac_fixed and ac_fixed[n]!=0 for l in state["design"]["capacitors"] for n in (l["a"],l["b"])):
        raise ValueError("Load capacitance on an AC-driven boundary is not supported by this profile.")
    input_voltage=ac_fixed[project["transfer"]["input"][0]]-ac_fixed[project["transfer"]["input"][1]]
    if abs(input_voltage)==0:raise ValueError("The transfer input must have a nonzero external AC voltage.")
    c=np.zeros(len(names),complex)
    for node,sign in zip(project["transfer"]["output"],(1,-1)):
        if node!="0":c[index[node]]+=sign/input_voltage
    return {"names":names,"index":index,"B":B,"R":R,"G":G,"C":C,"terminal":terminal,
            "fixed":fixed,"ac_fixed":ac_fixed,"rhs":rhs,"c":c,"edges":edges,"network":network,"state":state}


def device_matrix(system,y):
    t=system["terminal"]
    return coo_matrix((y.ravel(),(np.repeat(t,len(t)),np.tile(t,len(t)))),shape=system["G"].shape).tocsc()


def reduce_network(network,state,project):
    system=assemble(network,state,project)
    retained=list(dict.fromkeys([t for p,t in state["ports"]]+
                  [n for l in state["design"]["capacitors"] for n in (l["a"],l["b"])]+
                  project["transfer"]["output"]))
    retained=[n for n in retained if n not in system["fixed"]]
    keep=np.array([system["index"][n] for n in retained]);keep_set=set(keep)
    internal=np.array([i for i in range(len(system["names"])) if i not in keep_set],dtype=int)
    G=system["G"];B=system["B"];R=system["R"]
    fixed_drop=np.array([system["fixed"].get(a,0)-system["fixed"].get(b,0) for a,b,*_ in system["edges"]])
    dc_rhs=-B@(fixed_drop/R);ac_rhs=system["rhs"]
    S=G[keep][:,keep].toarray();dc=dc_rhs[keep];ac=ac_rhs[keep]
    if len(internal):
        factor=splu(G[internal][:,internal]);coupling=G[keep][:,internal]
        S-=coupling@factor.solve(G[internal][:,keep].toarray())
        dc-=coupling@factor.solve(dc_rhs[internal])
        ac-=coupling@factor.solve(ac_rhs[internal].real)+1j*(coupling@factor.solve(ac_rhs[internal].imag))
    return {"S":S,"dc_rhs":dc,"ac_rhs":ac,"C":system["C"][keep][:,keep].toarray(),
            "c":system["c"][keep],"names":retained}
