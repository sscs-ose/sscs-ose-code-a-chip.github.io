from pygmid import Lookup as lk
import numpy as np
import scipy.constants as sc
import pandas as pd
from tabulate import tabulate

# Load lookup tables from local folder (same directory)
n = lk('nfet_03v3.mat')

#spes
gm = 3.392e-05 
l=3 
gm_id= np.array([18,19,20]) # tergantung sistem mau di region brp

id = gm/gm_id
jd = n.lookup('ID_W', GM_ID=gm_id, L=l)
print(id)
w = id/jd

cgg_w=n.lookup('CGG_W', GM_ID=gm_id, L=l)
cgg = w*cgg_w
ft = gm/cgg/2/np.pi

df = pd.DataFrame([gm_id, id, jd, w, cgg, ft], ['gm_id', 'id', 'jd', 'w', 'cgg', 'ft'], columns = ['option1', 'option2', 'option3']); df
print(tabulate(df, headers='keys', tablefmt='pretty'))