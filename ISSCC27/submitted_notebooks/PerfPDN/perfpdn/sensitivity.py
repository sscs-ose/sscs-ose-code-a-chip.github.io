"""Reuse one DC system and one AC adjoint per configured scalar metric."""
import json
import numpy as np
from scipy.sparse.linalg import splu
from .native import read_scalar_raw
from .terminals import terminal_jacobian
from .devices import device_matrices
from .measure import measure, response
from .system import assemble,device_matrix,reduce_network
from .project import SIMULATOR


def calibrate(project,base,folder):
    folder.mkdir(parents=True,exist_ok=True)
    state=json.loads((base/"summary.json").read_text())
    network=json.loads((base/"network.json").read_text())
    ports=[p for p,t in state["ports"]]
    Ydc,checks=terminal_jacobian(base,folder/"DC_devices",ports,SIMULATOR)
    measured,points=measure(project,base,folder/"measurement")
    frequencies=list(measured["frequencies"].values())
    Y,dY,device_checks=device_matrices(base,folder/"AC_devices",frequencies,project["voltage_step_V"])
    system=assemble(network,state,project);system["Ydc"]=Ydc
    G,B,R=system["G"],system["B"],system["R"]
    K=G+device_matrix(system,Ydc);factor=splu(K.T.tocsc())
    terminal=system["terminal"];names=system["names"]
    q=np.zeros((len(names),len(project["metrics"])))
    direct=np.zeros((len(R),len(project["metrics"])));conversion=[]
    comparisons=[]
    reduced=reduce_network(network,state,project)
    baseline_v=np.array([state["node_voltages_V"][n] for n in reduced["names"]])
    raw=read_scalar_raw(base/"op.raw")
    baseline_i=np.zeros(len(baseline_v));baseline_i[:len(ports)]=[raw[f"i(v_{p})"] for p in ports]
    reduction_residual=float(max(abs(reduced["S"]@baseline_v+baseline_i-reduced["dc_rhs"])))
    if reduction_residual>1e-9:raise ValueError("Reduced network does not reproduce baseline current balance.")
    for k,(name,spec) in enumerate(project["metrics"].items()):
        f=frequencies[k];point=points[name];H=response(project,point)
        acv=lambda n:0j if n=="0" else point[f"v({n})"]
        x=np.array([acv(n) for n in names])
        A=G+device_matrix(system,Y[k])+2j*np.pi*f*system["C"]

        adjoint=splu(A.T.tocsc()).solve(system["c"])
        reconstructed=adjoint@system["rhs"]
        mismatch=abs(reconstructed-H)/max(abs(H),1e-30)
        if mismatch>1e-6:raise ValueError(f"AC network reconstruction failed: {mismatch}")
        q_port=-np.real(np.einsum("i,kij,j->k",adjoint[terminal],dY[:,k],x[terminal])/H)
        np.add.at(q[:,k],terminal,q_port)
        values=dict(zip(names,adjoint))
        direct[:,k]=[np.real((values.get(a,0)-values.get(b,0))*(acv(a)-acv(b))/(r*r*H))
                     for a,b,r,*_ in system["edges"]]
        conversion.append(20/np.log(10) if spec["measurement"]=="gain_dB"
                          else -measured["metrics"][name]/measured["crossing_log_slope"])
        reduced_A=reduced["S"].astype(complex)+2j*np.pi*f*reduced["C"]
        reduced_A[:len(ports),:len(ports)]+=Y[k]
        reduced_H=reduced["c"]@np.linalg.solve(reduced_A,reduced["ac_rhs"])
        reduced_error=float(abs(reduced_H-H)/max(abs(H),1e-30))
        if reduced_error>1e-6:raise ValueError("Reduced network does not reproduce the native AC transfer.")
        comparisons.append({"metric":name,"transfer_relative_error":float(mismatch),
                            "reduced_transfer_relative_error":reduced_error})
    dc_adjoint=factor.solve(q);values=dict(zip(names,dc_adjoint))
    bias=np.array([(values.get(a,np.zeros(q.shape[1]))-values.get(b,np.zeros(q.shape[1])))*
                   drop/r**2 for (a,b,r,*_),drop in zip(system["edges"],state["edge_drops_V"])])
    gradient=(direct+bias)*conversion
    np.savez_compressed(folder/"gradients.npz",dmetric_dR=gradient,direct=direct*conversion,bias=bias*conversion,Ydc=Ydc)
    (folder/"checks.json").write_text(json.dumps({"DC":checks,"devices":device_checks,"AC":comparisons,"reduced_DC_residual_A":reduction_residual},indent=2)+"\n")
    system["baseline"]=measured
    return measured,gradient,system
