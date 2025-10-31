import os
import math
import numpy as np
import pandas as pd


def CreateRightHalfSegC00(rx, ry, wid, wdown, wup, ratio, rev = 0):
	Dcps = wid * (math.sqrt(2) - 1) / 2
	rm = min(rx, ry)
	li = []
	li += [(wdown/2+wid/2,-ry-wid/2),(rm*ratio+wid*Dcps,-ry-wid/2),(rx+wid/2,-rm*ratio-wid*Dcps),(rx+wid/2,rm*ratio+wid*Dcps),(rm*ratio+wid*Dcps,ry+wid/2),(wup/2+wid/2,ry+wid/2)]
	if (rev): li.reverse()
	return li

def CreateLeftHalfSegC00(rx, ry, wid, wdown, wup, ratio, rev = 0):
	return list(map(lambda item: (-item[0],item[1]),CreateRightHalfSegC00(rx,ry,wid,wdown,wup,ratio,rev)))

def CreateInductorDownSegC00(rx, ry, wid, wopen, wout, lext, gap, n:int, ratio):
	ri = []
	for i in range(n):
		ri.append(((1 if (n-i)&1 else -1)*(wid+gap)/2,(1 if (n-i)&1 else -1)*(ry+i*(wid+gap)+wid/2)))
		ri += (CreateRightHalfSegC00 if (n-i)&1 else CreateLeftHalfSegC00)(rx+i*(wid+gap),ry+i*(wid+gap),wid,wout if i==n-1 else wopen,wopen,ratio,(n-i)&1)
		if (i<n-1): ri.append(((1 if (n-i)&1 else -1)*(wid+gap)/2,(-1 if (n-i)&1 else 1)*(ry+i*(wid+gap)+wid/2)))
	ri.append((wout/2+wid/2,-ry-n*(wid+gap)+gap-lext))
	le = []
	for i in range(n):
		le.append(((-1 if (n-i)&1 else 1)*(wid+gap)/2,(1 if (n-i)&1 else -1)*(ry+i*(wid+gap)+wid/2)))
		le += (CreateLeftHalfSegC00 if (n-i)&1 else CreateRightHalfSegC00)(rx+i*(wid+gap),ry+i*(wid+gap),wid,wout if i==n-1 else wopen,wopen,ratio,(n-i)&1)
		if (i<n-1): le.append(((-1 if (n-i)&1 else 1)*(wid+gap)/2,(-1 if (n-i)&1 else 1)*(ry+i*(wid+gap)+wid/2)))
	le.append((-wout/2-wid/2,-ry-n*(wid+gap)+gap-lext))
	le.reverse()
	return le + ri

def CreateInductorUpSeg(rx, ry, wid, wopen, wout, lext, gap, n:int, ratio, dist):
	return list(map(lambda item: (item[0],dist-item[1]),CreateInductorDownSegC00(rx,ry,wid,wopen,wout,lext,gap,n,ratio)))