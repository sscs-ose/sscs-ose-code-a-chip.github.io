"""
Copyright 2022 John William Kustin

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import pickle
import numpy as np

mosDat = pickle.load(open('/tmp/kustinj/ee272b/pyMOSChar/mosSKY130__W1000000.0u.sky130_fd_pr__nfet_01v8.sky130_fd_pr__pfet_01v8.duplicate.lengths.dat','rb'))
dtypes = ['id','vt','gm','gds','cgg','cgs','cgd','cgb','cdd','css']
fettypes=['pfet','nfet']
for f in fettypes:
    for d in dtypes:
        mosDat[f][d] = np.delete(mosDat[f][d], 49, 0)
        mosDat[f][d] = np.delete(mosDat[f][d], 75-1, 0)
    mosDat[f]['length'] = np.delete(mosDat[f]['length'], 49)
    mosDat[f]['length'] = np.delete(mosDat[f]['length'], 75-1)
pickle.dump(mosDat, open('mosSKY130__W1000000.0u.sky130_fd_pr__nfet_01v8.sky130_fd_pr__pfet_01v8.dat', "wb"), pickle.HIGHEST_PROTOCOL)
