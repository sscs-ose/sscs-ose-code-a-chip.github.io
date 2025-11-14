import numpy as np
from scipy.spatial import distance
from scipy.linalg import eigh
import matplotlib.pyplot as plt
import skrf as rf
import torch
import tempfile
import subprocess
import os
import shutil

fmax = 200


def Ind_Processing_Batch(arr_ind, wida, widb):
    ind_a = []
    ind_b = [] 
    for (index, ind) in enumerate(arr_ind):
        result_a = []
        result_b = []
        dst_a = np.zeros(len(ind['a'])-1)
        aj_a = np.zeros((len(ind['a']),len(ind['a'])))
        dst_b = np.zeros(len(ind['b'])-1)
        aj_b = np.zeros((len(ind['b']),len(ind['b'])))
        
        for x in range(len(ind['a'])-1):
            dst = distance.euclidean(ind['a'][x],ind['a'][x+1])
            dst_a[x] = dst
            aj_a[x][x+1] = dst_a[x]
            aj_a[x+1][x] = dst_a[x]
        
        eigenvalues, eigenvectors = eigh(aj_a)
        
        for x in range(len(ind['a'])-1):
            #result_a.append([ind['a'][x][0]/100,ind['a'][x][1]/100,ind['a'][x+1][0]/100,ind['a'][x+1][1]/100,dst_a[x]/100,wida[index],np.sum(eigenvectors[x][1]+eigenvectors[x+1][1])])
            result_a.append([ind['a'][x][0]/100,ind['a'][x][1]/100,ind['a'][x+1][0]/100,ind['a'][x+1][1]/100,dst_a[x]/100,1,np.sum(eigenvectors[x][1]+eigenvectors[x+1][1])])
        ind_a.append(result_a[0:5])
        
        for x in range(len(ind['b'])-1):
            dst = distance.euclidean(ind['b'][x],ind['b'][x+1])
            dst_b[x] = dst
            aj_b[x][x+1] = dst_b[x]
            aj_b[x+1][x] = dst_b[x]
        
        eigenvalues, eigenvectors = eigh(aj_b)
        
        for x in range(len(ind['b'])-1):
            #result_b.append([ind['b'][x][0]/100,ind['b'][x][1]/100,ind['b'][x+1][0]/100,ind['b'][x+1][1]/100,dst_b[x]/100,widb[index],np.sum(eigenvectors[x][1]+eigenvectors[x+1][1])])
            result_b.append([ind['b'][x][0]/100,ind['b'][x][1]/100,ind['b'][x+1][0]/100,ind['b'][x+1][1]/100,dst_b[x]/100,1,np.sum(eigenvectors[x][1]+eigenvectors[x+1][1])])
        ind_b.append(result_b[0:5])
    return ind_a, ind_b

# Miscellaneous Functions & New Cap Models

import matplotlib.pyplot as plt
import CreateSeg_1x1_code_a_chip as csg
import skrf as rf
import torch

def CreateDiffShuntCapQ(spt_freq, capC, factorQ, centerF):
    line = rf.media.DefinedGammaZ0(frequency=spt_freq)
    C1 = line.capacitor_q(capC, centerF, factorQ, name='C1')
    port1 = rf.Circuit.Port(frequency=spt_freq, name='port1', z0=50)
    port2 = rf.Circuit.Port(frequency=spt_freq, name='port2', z0=50)
    port3 = rf.Circuit.Port(frequency=spt_freq, name='port3', z0=50)
    port4 = rf.Circuit.Port(frequency=spt_freq, name='port4', z0=50)
    connections = [
        [(port1, 0), (C1, 0), (port3, 0)],
        [(C1, 1), (port2, 0), (port4, 0)],
    ]
    circuit = rf.Circuit(connections)
    cap_cir = circuit.network
    cap_cir.renumber([0,1,2,3],[0,2,1,3])
    cap_cir.name = 'CapacitorQ circuit'
    return cap_cir

def CreateDiffShuntCap(spt_freq, capC):
    line = rf.media.DefinedGammaZ0(frequency=spt_freq)
    C1 = line.capacitor(capC, name='C1')
    port1 = rf.Circuit.Port(frequency=spt_freq, name='port1', z0=50)
    port2 = rf.Circuit.Port(frequency=spt_freq, name='port2', z0=50)
    port3 = rf.Circuit.Port(frequency=spt_freq, name='port3', z0=50)
    port4 = rf.Circuit.Port(frequency=spt_freq, name='port4', z0=50)
    connections = [
        [(port1, 0), (C1, 0), (port3, 0)],
        [(C1, 1), (port2, 0), (port4, 0)],
    ]
    circuit = rf.Circuit(connections)
    cap_cir = circuit.network
    cap_cir.renumber([0,1,2,3],[0,2,1,3])
    cap_cir.name = 'Capacitor circuit'
    return cap_cir

def CreateDiffSeriesCap(spt_freq, capC):
    line = rf.media.DefinedGammaZ0(frequency=spt_freq)
    C1 = line.capacitor(capC, name='C1')
    C2 = line.capacitor(capC, name='C2')
    port1 = rf.Circuit.Port(frequency=spt_freq, name='port1', z0=50)
    port2 = rf.Circuit.Port(frequency=spt_freq, name='port2', z0=50)
    port3 = rf.Circuit.Port(frequency=spt_freq, name='port3', z0=50)
    port4 = rf.Circuit.Port(frequency=spt_freq, name='port4', z0=50)
    connections = [
        [(port1, 0), (C1, 0)],
        [(C1, 1), (port3, 0)],
        [(port2, 0), (C2, 0)],
        [(C2, 1), (port4, 0)]
    ]
    circuit = rf.Circuit(connections)
    cap_cir = circuit.network
    cap_cir.renumber([0,1,2,3],[0,2,1,3])
    cap_cir.name = 'Series Capacitor circuit'
    return cap_cir



def CreateDiffCrossCap(spt_freq, capC):
    line = rf.media.DefinedGammaZ0(frequency=spt_freq)
    C1 = line.capacitor(capC, name='C1')
    C2 = line.capacitor(capC, name='C2')
    port1 = rf.Circuit.Port(frequency=spt_freq, name='port1', z0=50)
    port2 = rf.Circuit.Port(frequency=spt_freq, name='port2', z0=50)
    port3 = rf.Circuit.Port(frequency=spt_freq, name='port3', z0=50)
    port4 = rf.Circuit.Port(frequency=spt_freq, name='port4', z0=50)
    connections = [
        [(port1, 0), (C1, 0)],
        [(C2, 0), (port3, 0)],
        [(port2, 0), (C2, 1)],
        [(C1, 1), (port4, 0)]
    ]
    circuit = rf.Circuit(connections)
    cap_cir = circuit.network
    cap_cir.renumber([0,1,2,3],[0,2,1,3])
    cap_cir.name = 'Cross Capacitor circuit'
    return cap_cir

def CreateCrossSeris(spt_freq, capC, capS):
    network1 = CreateDiffCrossCap(spt_freq, capC)
    network2 = CreateDiffSeriesCap(spt_freq, capS)
    return rf.Network(spt_freq, s=network1.s + network2.s, z0=network1.z0)

def Segment_Regen(params):
    (ra, rb, wida, widb, gapa, gapb, opena, openb, dist, ratio) = params
    na = 1
    nb = 1
    outbound = 50
    exta = outbound + 20 + gapa
    extb = outbound + 20 + gapb
    outa = 30
    outb = 30
    return csg.CreateInductorDownSegC00(ra,ra,wida,opena,outa,exta,gapa,na,ratio),csg.CreateInductorUpSeg(rb,rb,widb,openb,outb,extb,gapb,nb,ratio,dist)

def GammaCalc(zl,zg=50+1j*0):
    return (zl-np.conj(zg))/(zl+zg)*(zg/np.conj(zg))

def Direct_SP_Predict_batch(params, band_models, S_max, S_min, device):
    # Prepare segmented inputs
    temp_ind = []
    for _ in range(params.shape[0]):
        temp_a, temp_b = Segment_Regen(params[_])
        temp_ind.append({'a':temp_a,'b':temp_b})
    test_prediction = np.zeros((params.shape[0],fmax,12))
    inp1, inp2 = Ind_Processing_Batch(temp_ind,params[:,4],params[:,5])
    inp1 = torch.from_numpy(np.array(inp1))
    inp1 = inp1.type(torch.float32)
    inp1 = inp1.to(device)
    inp2 = torch.from_numpy(np.array(inp2))
    inp2 = inp2.type(torch.float32)
    inp2 = inp2.to(device)


    with torch.no_grad():
        test_prediction = band_models(inp1, inp2).cpu().detach().numpy()

    # Post-process to physical S-params range
    pred = list(test_prediction)
    for i in range(len(pred)):
        pred[i] = np.reshape((np.array(pred[i]) + 1) * (S_max - S_min) / 2 + S_min, [fmax, 6, 2])
    pred = np.array(pred)
    SPData_all = []
    
    for j in range(len(params)):
        SPData = np.zeros((fmax,4,4)) + 1j*np.zeros((fmax,4,4))
        for i in range(fmax):
            SPData[i,0,0]=pred[j,i,0,0]+1j*pred[j,i,0,1]
            SPData[i,0,1]=pred[j,i,1,0]+1j*pred[j,i,1,1]
            SPData[i,0,2]=pred[j,i,2,0]+1j*pred[j,i,2,1]
            SPData[i,0,3]=pred[j,i,3,0]+1j*pred[j,i,3,1]
            SPData[i,2,2]=pred[j,i,4,0]+1j*pred[j,i,4,1]
            SPData[i,2,3]=pred[j,i,5,0]+1j*pred[j,i,5,1]
            SPData[i,1,1]=SPData[i,0,0]
            SPData[i,3,3]=SPData[i,2,2]
            SPData[i,1,2]=SPData[i,0,3]
            SPData[i,1,3]=SPData[i,0,2]
            for _p in range(4):
                for _q in range(_p):
                    SPData[i,_p,_q]=SPData[i,_q,_p]
        SPData_all.append(SPData)
      
    return np.array(SPData_all)






infx = 500

def fun_batch(params,freqs,weights,z1,z2,cap1,cap2,model,S_max,S_min,device,area_penalty,wcross=1,wil=1):
    freq = rf.Frequency(1, fmax, fmax, 'ghz')
    #freq = rf.Frequency(1, 201, 201, 'ghz')
    res = [0]*params.shape[0]
    params_new = []
    corresp = []
    area = []
    for dex in range(params.shape[0]):
        (ra, rb, wida, widb, gapa, gapb, opena, openb, dist, ratio) = params[dex]
        na = 1
        nb = 1
        # outbound = 50
        # exta = outbound + 20 + gapa
        # extb = outbound + 20 + gapb
        outa = 30
        outb = 30
        if (na>1 and wida>=6 and gapa<=2):
            res[dex]=infx
            continue
        if (nb>1 and widb>=6 and gapb<=2):
            res[dex]=infx
            continue
        if (ra<openb*0.5+gapb+widb):
            res[dex]=infx
            continue
        if (rb<opena*0.5+gapa+wida):
            res[dex]=infx
            continue
        if (ra+rb<dist+(gapa+gapb)/2):
            res[dex]=infx
            continue
        if (dist+rb<ra+(wida+gapa)*na):
            res[dex]=infx
            continue
        if (dist+ra<rb+(widb+gapb)*nb):
            res[dex]=infx
            continue
        if (0.5*opena+wida>ratio*ra):
            res[dex]=infx
            continue
        if (0.5*openb+wida>ratio*rb):
            res[dex]=infx
            continue
        if (0.5*outa+wida>ratio*(ra+(na-1)*(wida+gapa))):
            res[dex]=infx
            continue
        if (0.5*outb+wida>ratio*(rb+(nb-1)*(widb+gapb))):
            res[dex]=infx
            continue
        params_new.append(params[dex])
        corresp.append(dex)
        area.append((dist + ra + rb + (gapa + wida) * na + (gapb + widb) * nb) * max(ra, rb) * 2)
    if (len(corresp)>0): sp_cur = Direct_SP_Predict_batch(np.array(params_new),model,S_max,S_min,device)

    for dex in range(len(corresp)):
        ntwk = rf.Network(frequency=freq, s=sp_cur[dex], name='a 4-port')
        ntwk.renumber([0,1,2,3],[0,1,3,2])
        ntwk.write_touchstone('FUN_BATCH.s4p', return_string=False)
        ntwk = rf.cascade_list([CreateDiffShuntCap(freq,cap1[corresp[dex]]*1e-15),ntwk,CreateDiffShuntCap(freq,cap2[corresp[dex]]*1e-15)])

        ntwk.se2gmm(p=2)
        res_err = 0
        for i in range(len(freqs)):
            s_org = ntwk.s[freqs[i]-1]
            sc = np.array([[s_org[0,0],s_org[0,1]],[s_org[1,0],s_org[1,1]]])
            g0 = GammaCalc(z1)
            g1 = GammaCalc(z2)
            gamma = np.array([[g0,0],[0,g1]])
            dii = np.array([[(1-g0)*np.sqrt(1-np.abs(g0)**2)/(1-np.conj(g0)),0],[0,(1-g1)*np.sqrt(1-np.abs(g1)**2)/(1-np.conj(g1))]])
            sg = np.linalg.inv(np.conj(dii)) @ (sc - np.conj(gamma)) @ np.linalg.inv(np.array([[1,0],[0,1]]) - gamma @ sc) @ dii
            res_err += (np.abs(sg[0,0])*wcross + np.abs(sg[1,1])*(2-wcross) + (1-np.abs(sg[1,0]*sg[0,1]))*wil)*weights[i]
        res[corresp[dex]] = res_err + area_penalty * area[dex]
    return np.array(res)




    


    
def fun_PRINT(params,freqs,weights,z1,z2,cap1,cap2,model,S_max,S_min,device,area_penalty,wcross=1,wil=1):
    print('params_fun_print=',params)
    (ra, rb, wida, widb, gapa, gapb, opena, openb, dist, ratio) = params
    na = 1
    nb = 1
    # outbound = 50
    # exta = outbound + 20 + gapa
    # extb = outbound + 20 + gapb
    outa = 30
    outb = 30
    if (na>1 and wida>=6 and gapa<=2): return infx
    if (nb>1 and widb>=6 and gapb<=2): return infx
    if (ra<openb*0.5+gapb+widb): return infx
    if (rb<opena*0.5+gapa+wida): return infx
    if (ra+rb<dist+(gapa+gapb)/2): return infx
    if (dist+rb<ra+(wida+gapa)*na): return infx
    if (dist+ra<rb+(widb+gapb)*nb): return infx
    if (0.5*opena+wida>ratio*ra): return infx
    if (0.5*openb+wida>ratio*rb): return infx
    if (0.5*outa+wida>ratio*(ra+(na-1)*(wida+gapa))): return infx
    if (0.5*outb+wida>ratio*(rb+(nb-1)*(widb+gapb))): return infx
    sp_cur = Direct_SP_Predict_batch(np.array([params]),model,S_max,S_min,device)[0]
    freq = rf.Frequency(1, fmax, fmax, 'ghz')
    ntwk = rf.Network(frequency=freq, s=sp_cur, name='a 4-port',)
    ntwk.renumber([0,1,2,3],[0,1,3,2])
    ntwk.write_touchstone('fun_PRINT_opt_withoutcap.s4p', return_string=False)
    ntwk = rf.cascade_list([CreateDiffShuntCap(freq,cap1*1e-15),ntwk,CreateDiffShuntCap(freq,cap2*1e-15)])
    ntwk.write_touchstone('fun_PRINT_opt.s4p', return_string=False)
    # print(ntwk)
     #print(ntwk.write_touchstone('t.s2p', return_string=True))
    ntwk.se2gmm(p=2)
    s_general = []
    for i in range(1,fmax+1):
        s_org = ntwk.s[i-1]
        sc = np.array([[s_org[0,0],s_org[0,1]],[s_org[1,0],s_org[1,1]]])
        g0 = GammaCalc(z1)
        g1 = GammaCalc(z2)
        gamma = np.array([[g0,0],[0,g1]])
        dii = np.array([[(1-g0)*np.sqrt(1-np.abs(g0)**2)/(1-np.conj(g0)),0],[0,(1-g1)*np.sqrt(1-np.abs(g1)**2)/(1-np.conj(g1))]])
        sg = np.linalg.inv(np.conj(dii)) @ (sc - np.conj(gamma)) @ np.linalg.inv(np.array([[1,0],[0,1]]) - gamma @ sc) @ dii
        s_general.append(sg)
    s_general = np.array(s_general)

    res_err = 0
    area = (dist + ra + rb + (gapa + wida) * na + (gapb + widb) * nb) * max(ra, rb) * 2
    print('area=',area)
    for i in range(len(freqs)):
        s_org = ntwk.s[freqs[i]-1]
        sc = np.array([[s_org[0,0],s_org[0,1]],[s_org[1,0],s_org[1,1]]])
        g0 = GammaCalc(z1)
        g1 = GammaCalc(z2)
        gamma = np.array([[g0,0],[0,g1]])
        dii = np.array([[(1-g0)*np.sqrt(1-np.abs(g0)**2)/(1-np.conj(g0)),0],[0,(1-g1)*np.sqrt(1-np.abs(g1)**2)/(1-np.conj(g1))]])
        sg = np.linalg.inv(np.conj(dii)) @ (sc - np.conj(gamma)) @ np.linalg.inv(np.array([[1,0],[0,1]]) - gamma @ sc) @ dii
        #print(i,sg)
        res_err += (np.abs(sg[0,0])*wcross + np.abs(sg[1,1])*(2-wcross) + (1-np.abs(sg[1,0]*sg[0,1]))*wil)*weights[i]
    return res_err + area_penalty * area,s_general,area

def CreateFqWt(fc, halfbw, rho):
    fq = []
    wt = []
    for f in range(fc-halfbw+1,fc+halfbw):
        fq.append(f)
        wt.append((1-pow(abs(f-fc)/halfbw,rho))/halfbw)
    return [fq,wt]

    
def fun_munal(params,freqs,weights,area_penalty,z1,z2,cap1,cap2,fmax,wcross=1,wil=1, layout_file=None):
    (ra, rb, wida, widb, gapa, gapb, opena, openb, dist, ratio) = map(float, params)
    na = 1
    nb = 1
   # ntwk = rf.Network('/rdf/shared/design_automation/GUI_DATA_Test/Inverse_1to1_Same/SPData/0.s4p')
    file_path = layout_file if layout_file else '/rdf/shared/design_automation/GUI_DATA_Test/test/SPData/0.s4p'
    ntwk = rf.Network(file_path)
    freq = rf.Frequency(1, fmax, fmax, 'ghz')
    ntwk.renumber([0,1,2,3],[0,1,3,2])
    ntwk = rf.cascade_list([CreateDiffShuntCap(freq,cap1*1e-15),ntwk,CreateDiffShuntCap(freq,cap2*1e-15)])
    ntwk.write_touchstone('fun_PRINT_sim.s4p', return_string=False)
    ntwk.se2gmm(p=2)
    res_err = 0
    s_general = []
    for i in range(1,fmax+1):
        s_org = ntwk.s[i-1]
        sc = np.array([[s_org[0,0],s_org[0,1]],[s_org[1,0],s_org[1,1]]])
        g0 = GammaCalc(z1)
        g1 = GammaCalc(z2)
        gamma = np.array([[g0,0],[0,g1]])
        dii = np.array([[(1-g0)*np.sqrt(1-np.abs(g0)**2)/(1-np.conj(g0)),0],[0,(1-g1)*np.sqrt(1-np.abs(g1)**2)/(1-np.conj(g1))]])
        sg = np.linalg.inv(np.conj(dii)) @ (sc - np.conj(gamma)) @ np.linalg.inv(np.array([[1,0],[0,1]]) - gamma @ sc) @ dii
        s_general.append(sg)
    s_general = np.array(s_general)

    for i in range(len(freqs)):
        s_org = ntwk.s[freqs[i]-1]
        sc = np.array([[s_org[0,0],s_org[0,1]],[s_org[1,0],s_org[1,1]]])
        g0 = GammaCalc(z1)
        g1 = GammaCalc(z2)
        gamma = np.array([[g0,0],[0,g1]])
        dii = np.array([[(1-g0)*np.sqrt(1-np.abs(g0)**2)/(1-np.conj(g0)),0],[0,(1-g1)*np.sqrt(1-np.abs(g1)**2)/(1-np.conj(g1))]])
        sg = np.linalg.inv(np.conj(dii)) @ (sc - np.conj(gamma)) @ np.linalg.inv(np.array([[1,0],[0,1]]) - gamma @ sc) @ dii
        #print(i,sg)
        res_err += (np.abs(sg[0,0])*wcross + np.abs(sg[1,1])*(2-wcross) + (1-np.abs(sg[1,0]*sg[0,1]))*wil)*weights[i]
        
    area = (dist + ra + rb + (gapa + wida) * na + (gapb + widb) * nb) * max(ra, rb) * 2
    return res_err + area_penalty * area, s_general

