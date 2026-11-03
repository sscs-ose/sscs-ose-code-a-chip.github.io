"""Epoch-wise unnormalized complex-S R² for canonical reciprocal S-parameter responses."""
import numpy as np
import torch


SCHEMA='physical-complex-full-matrix-variance-weighted-r2-v1'


class EpochR2:
    """Observe evaluated predictions without changing training or RNG state."""
    def __init__(self,data,kind):
        self.scale=torch.from_numpy((data['ymax']-data['ymin'])/2).double()
        self.offset=torch.from_numpy((data['ymax']+data['ymin'])/2).double()
        pairs={(min(i,j),max(i,j)) for i,j in kind.sel}
        expected={(i,j) for i in range(kind.nport) for j in range(i,kind.nport)}
        if pairs!=expected or len(kind.sel)!=len(expected):
            raise ValueError('The output representation must contain each independent S entry once')
        multiplicity=np.array([1 if i==j else 2 for i,j in kind.sel],dtype=float)
        frequencies=data['s'].shape[1]
        self.weights=torch.from_numpy(np.tile(np.r_[multiplicity,multiplicity],frequencies))
        self.targets=[];self.denominators=[];self.rows=[]
        for key in ('tr','va'):
            response=data['s'][data[key]]
            if not np.array_equal(response,response.swapaxes(-1,-2)):
                raise ValueError('Complete-matrix triangle weighting requires reciprocal targets')
            target=torch.from_numpy(kind.s_to_vec(response)).double()
            denominator=torch.sum((target-target.mean(0))**2*self.weights)
            if not torch.isfinite(denominator) or float(denominator)<=0:
                raise ValueError('R² requires finite, nonzero target variance in each partition')
            self.targets.append(target);self.denominators.append(denominator)

    def __call__(self,epoch,training,validation,history_row=None):
        device=training.device
        if self.scale.device!=device:
            self.scale=self.scale.to(device);self.offset=self.offset.to(device)
            self.weights=self.weights.to(device)
            self.targets=[value.to(device) for value in self.targets]
            self.denominators=[value.to(device) for value in self.denominators]
        scores=[]
        for predicted,target,denominator in zip((training,validation),self.targets,self.denominators):
            response=predicted.double()*self.scale+self.offset
            residual=torch.sum((response-target)**2*self.weights)
            scores.append(float(1-residual/denominator))
        self.rows.append([int(epoch),*scores])
