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

import os
import os.path
import sys
import pickle
import spice3read
import numpy as np
import pdb
import signal
import subprocess
import sys

class charMOS:
    def __init__(self, settings: dict):

        self.mosDat = {}
        self.settings = {} 
        self.settings = settings
        
        for modelFile in settings['modelFiles']: 
            if (not os.path.isfile(modelFile)):
                print("Model file {0} not found!".format(modelFile))
                print("Please call init() again with a valid model file")
                return None
        
        vgsMax = settings['vgsMax']
        vdsMax = settings['vdsMax']
        vsbMax = settings['vsbMax']
        vgsStep = settings['vgsStep']
        vdsStep = settings['vdsStep']
        vsbStep = settings['vsbStep']

        self.vgs = np.linspace(0, vgsMax, int(vgsMax/vgsStep + 1))
        self.vds = np.linspace(0, vdsMax, int(vdsMax/vdsStep + 1))
        self.vsb = np.linspace(0, vsbMax, int(vsbMax/vsbStep + 1))

        self.mosDat['pfet'] = {}
        self.mosDat['nfet'] = {}
        self.mosDat['modelFiles'] = settings['modelFiles']
        self.mosDat['simulator'] = settings['simulator']

        self.mosDat['nfet']['corners'] = settings['corners']
        self.mosDat['nfet']['temp'] = settings['temp']
        self.mosDat['nfet']['length'] = settings['mosLengthsNfet']
        self.mosDat['nfet']['width'] = settings['mosWidthsNfet']
        self.mosDat['nfet']['numfing'] = settings['numfing']
        self.mosDat['nfet']['vgs'] = self.vgs
        self.mosDat['nfet']['vds'] = self.vds
        self.mosDat['nfet']['vsb'] = -self.vsb
        
        self.mosDat['pfet']['corners'] = settings['corners']
        self.mosDat['pfet']['temp'] = settings['temp']
        self.mosDat['pfet']['length'] = settings['mosLengthsPfet']
        self.mosDat['pfet']['width'] = settings['mosWidthsPfet']
        self.mosDat['pfet']['numfing'] = settings['numfing']
        self.mosDat['pfet']['vgs'] = self.vgs
        self.mosDat['pfet']['vds'] = self.vds
        self.mosDat['pfet']['vsb'] = -self.vsb

        assert(len(self.mosDat['nfet']['length']) == len(self.mosDat['pfet']['length']))

        # 4D arrays to store MOS data-->f(L,               VSB,      VDS,      VGS      )
        ssParams = ['id', 'vt', 'gm', 'gmb', 'gds', 'cgg', 'cgs', 'cgd', 'cgb', 'cdd', 'css'];
        for x in ssParams:
            self.mosDat['nfet'][x]  = np.zeros((len(self.mosDat['nfet']['length']), len(self.vsb), len(self.vds), len(self.vgs)))
            self.mosDat['pfet'][x]  = np.zeros((len(self.mosDat['pfet']['length']), len(self.vsb), len(self.vds), len(self.vgs)))

    def writeSources(self, netlistHandler, type: str):
        # type: str - "nfet" or "pfet"
        tab = {
            "nfet": "modelN",
            "pfet": "modelP"
        }
        tab1 = {
            "nfet": "n",
            "pfet": "p"
        }
        data = self.mosDat[type]
        sizes = [data["length"], data["width"]]
        assert len(sizes[0]) == len(sizes[1])
        # the driving voltage sources of the 1 analysis
        
        devNames = []
        idxs = []
        netlistHandler.write(f'vds vds 0 dc 0\n')
        netlistHandler.write(f'vgs vgs  0 dc 0\n')
        for i in range(len(sizes[0])):
                    for ivsb, vsb in enumerate(data["vsb"]):
                        idx = f'{i}d{ivsb}d{tab1[type]}'
                        idxs.append(idx)
                        devName = f'@m.x{tab1[type]}d{idx}.m'+self.settings[tab[type]]
                        devNames.append(devName)
                        netlistHandler.write(f'vvds{idx} vds vdsd{idx} dc 0\n')
                        netlistHandler.write(f'vvgs{idx} vgs vgsd{idx} dc 0\n')
                        netlistHandler.write(f'vvdsd{idx} vdsd{idx}  {tab1[type]}Draind{idx} dc 0\n')
                        netlistHandler.write(f'vvgsd{idx} vgsd{idx}  {tab1[type]}Gated{idx}  dc 0\n')
                        netlistHandler.write(f'vvbsd{idx} vbsd{idx}  {tab1[type]}Bulkd{idx}  dc {-vsb}\n')
                        netlistHandler.write("\n")
                        model = self.settings[tab[type]]
                        length = sizes[0][i]
                        width = sizes[1][i]
                        netlistHandler.write(f"x{tab1[type]}d{idx} {tab1[type]}Draind{idx} {tab1[type]}Gated{idx} 0 {tab1[type]}Bulkd{idx} {model} L={round(length,3)} W={round(width,3)}\n")
                        netlistHandler.write("\n")

        vgsMax = self.settings['vgsMax']
        vgsStep = self.settings['vgsStep']
        vdsMax = self.settings['vdsMax']
        vdsStep = self.settings['vdsStep']
        netlistHandler.write(f'.dc vgs 0 {vgsMax} {vgsStep} vds 0 {vdsMax} {vdsStep}\n'.format())
        
        return idxs, devNames
                    
    def genNetlistNngspice(self, fName='charNMOS.net'):
        netlistN = open(fName, 'w')
        netlistN.write("**Characterize N Channel MOSFET\n")
        netlistN.write("\n")
        for modelFile, corner in zip(self.settings['modelFiles'], self.mosDat['nfet']['corners']):
            netlistN.write(".lib \"{0}\" {1}\n".format(modelFile, corner[0]))
        netlistN.write("\n")
        idxs, devNames = self.writeSources(netlistN, "nfet")
        netlistN.write(".options dccap post brief accurate\n")
        netlistN.write(".control\n")
        strList = ["save all"]
        ssParams = ["[id]", "[vth]", "[gm]", "[gmbs]", "[gds]", "[cgg]", "[cgs]", "[cgd]", "[cdd]", "[cbs]"]
        for devName in devNames:
            for ssp in ssParams:
                strList.append(devName + ssp)
        
        netlistN.write(' '.join(strList))
        netlistN.write("\n")

        strList2 = []
        for idx, devName in zip(idxs, devNames):
            strList2.append(f'let id{idx}   =  {devName}[id]')
            strList2.append(f'let vt{idx}   =  {devName}[vth]')
            strList2.append(f'let gm{idx}   =  {devName}[gm]')
            strList2.append(f'let gmb{idx}  =  {devName}[gmbs]')
            strList2.append(f'let gds{idx}  =  {devName}[gds]')
            strList2.append(f'let cgg{idx}  =  {devName}[cgg]')
            strList2.append(f'let cgs{idx}  = - {devName}[cgs]')
            strList2.append(f'let cgd{idx}  = - {devName}[cgd]')
            strList2.append(f'let cgb{idx}  = {devName}[cgg] - (-{devName}[cgs])-(-{devName}[cgd])\n')
            strList2.append(f'let cdd{idx}  = {devName}[cdd]')
            strList2.append(f'let css{idx}  = -{devName}[cgs]-{devName}[cbs]')
        netlistN.write('\n'.join(strList2))
        netlistN.write('\n')
        netlistN.write('run\n')
        netlistN.write("write outN.raw all\n")
        netlistN.write("exit\n")
        netlistN.write(".endc\n")
        netlistN.write(".end\n")
        netlistN.close();
        
    def genNetlistPngspice(self, fName='charPMOS.net'):
        netlistP = open(fName, 'w')
        netlistP.write("Characterize P Channel MOSFET\n")
        netlistP.write("\n")
        devName = '@m.xp.m'+self.settings['modelP']
        for modelFile, corner in zip(self.settings['modelFiles'], self.mosDat['pfet']['corners']):
            netlistP.write(".lib \"{0}\" {1}\n".format(modelFile, corner[0]))
        netlistP.write("\n")
        idxs, devNames = self.writeSources(netlistP, "pfet")
        netlistP.write(".options dccap post brief accurate\n")
        netlistP.write(".control\n")
        strList = ["save all"]
        ssParams = ["[id]", "[vth]", "[gm]", "[gmbs]", "[gds]", "[cgg]", "[cgs]", "[cgd]", "[cdd]", "[cbs]"]
        for devName in devNames:
            for ssp in ssParams:
                strList.append(devName + ssp)
        
        netlistP.write(' '.join(strList))
        netlistP.write("\n")

        strList2 = []
        for idx, devName in zip(idxs, devNames):
            strList2.append(f'let id{idx}   =  {devName}[id]')
            strList2.append(f'let vt{idx}   =  {devName}[vth]')
            strList2.append(f'let gm{idx}   =  {devName}[gm]')
            strList2.append(f'let gmb{idx}  =  {devName}[gmbs]')
            strList2.append(f'let gds{idx}  =  {devName}[gds]')
            strList2.append(f'let cgg{idx}  =  {devName}[cgg]')
            strList2.append(f'let cgs{idx}  = - {devName}[cgs]')
            strList2.append(f'let cgd{idx}  = - {devName}[cgd]')
            strList2.append(f'let cgb{idx}  = {devName}[cgg] - (-{devName}[cgs])-(-{devName}[cgd])\n')
            strList2.append(f'let cdd{idx}  = {devName}[cdd]')
            strList2.append(f'let css{idx}  = -{devName}[cgs]-{devName}[cbs]')
        netlistP.write('\n'.join(strList2))
        netlistP.write('\n')
        netlistP.write('run\n')
        netlistP.write("write outP.raw all\n")
        netlistP.write("exit\n")
        netlistP.write(".endc\n")
        netlistP.write(".end\n")
        netlistP.close();

    def genNetlistNEldo(self, fName='charNMOS.net'):
        netlistN = open(fName, 'w')

    # TODO: TEMPORARY BYPASS

    # def genNetlistSpectre(self, fName='charMOS.scs'):

    #     if (subcktPath == ""):
    #         nmos = "xn"
    #         pmos = "xp"
    #     else:
    #         nmos = "xn." + subcktPath
    #         pmos = "xp." + subcktPath

    #     netlist = open(fName, 'w')
    #     netlist.write('//charMOS.scs \n')
    #     for modelFile, corner in zip(modelFiles, corners):
    #         netlist.write('include  "{0}" {1}\n'.format(modelFile, corner))
    #     netlist.write('include "simParams.scs" \n')
    #     netlist.write('save {0}:ids {0}:vth {0}:igd {0}:igs {0}:gm {0}:gmbs {0}:gds {0}:cgg {0}:cgs {0}:cgd {0}:cgb {0}:cdd {0}:cdg {0}:css {0}:csg {0}:cjd {0}:cjs {1}:ids {1}:vth {1}:igd {1}:igs {1}:gm {1}:gmbs {1}:gds {1}:cgg {1}:cgs {1}:cgd {1}:cgb {1}:cdd {1}:cdg {1}:css {1}:csg {1}:cjd {1}:cjs\n'.format(nmos, pmos))
    #     netlist.write('parameters mosChar_gs=0 mosChar_ds=0 \n')
    #     netlist.write('vdsn     (vdn 0)         vsource dc=mosChar_ds  \n')
    #     netlist.write('vgsn     (vgn 0)         vsource dc=mosChar_gs  \n')
    #     netlist.write('vbsn     (vbn 0)         vsource dc=-mosChar_sb \n')
    #     netlist.write('vdsp     (vdp 0)         vsource dc=-mosChar_ds \n')
    #     netlist.write('vgsp     (vgp 0)         vsource dc=-mosChar_gs \n')
    #     netlist.write('vbsp     (vbp 0)         vsource dc=mosChar_sb  \n')
    #     netlist.write('\n')
    #     netlist.write(f"xn (vdn vgn 0 vbn) {self.mosDat["modelN"]} l={self.mosDat["length"]*1e-6} w={self.mosDat["width"]}u multi=1 nf={numfing} _ccoflag=1\n"
    #     netlist.write(f"xp (vdp vgp 0 vbp) {self.mosDat["modelN"]} l={self.mosDat["length"]*1e-6} w={self.mosDat["width"]}u multi=1 nf={numfing} _ccoflag=1\n"
    #     netlist.write('\n')
    #     netlist.write('options1 options gmin=1e-13 dc_pivot_check=yes reltol=1e-4 vabstol=1e-6 iabstol=1e-10 temp=27 tnom=27 rawfmt=nutbin rawfile="./charMOS.raw" save=none\n')
    #     netlist.write('sweepvds sweep param=mosChar_ds start=0 stop={0} step={1} {{ \n'.format(vdsMax, vdsStep))
    #     netlist.write('sweepvgs dc param=mosChar_gs start=0 stop={0} step={1} \n'.format(vgsMax, vgsStep))
    #     netlist.write('}\n')

    def genSimParamsSpectre(self, L, VSB):
        paramFile = open("simParams.scs", 'w')
        paramFile.write("parameters length={0}\n".format(L))
        paramFile.write("parameters mosChar_sb={0}\n".format(VSB))
        paramFile.close()
        
    #  TODO: check that ngspice is installed on the machine
    def runSim(self, fileName='charMOS.net', simulator='ngspice'): 
        fileHandler = open('charMOSPy.log', 'w')
        proc = subprocess.run([simulator, fileName], stdout=fileHandler, check=True)
        fileHandler.close()
        # os.system("{0} {1} &>> charMOSPy.log".format(simulator, fileName))


    def genDB(self):
        if (self.settings['simulator'] == "ngspice"):
            self.genNetlistNngspice()
            self.genNetlistPngspice()
        elif (self['simulator'] == "spectre"):
            self.genNetlistSpectre()
        else:
            print("ERROR: Invalid/Unsupported simulator specified")
            sys.exit(0)
        #  TODO: make sure the prog total is right. e.g. if num of nmos widths != num of pmos widths 
        progTotal = len(self.mosDat['nfet']['length'])*len(self.mosDat['nfet']['vsb'])*len(self.mosDat['nfet']['width'])
        progCurr  = 0
        print("Data generation in progress. Go have a coffee...")
        vsb = self.mosDat['nfet']['vsb']

        tab = {
            "nfet": "modelN",
            "pfet": "modelP"
        }
        tab1 = {
            "nfet": "n",
            "pfet": "p"
        }

        for idxL in range(len(self.mosDat['nfet']['length'])):
            for idxVSB in range(len(vsb)):
                
                if (self.settings['simulator'] == "ngspice"):
                    myfile = open("charMOSpy.log", "a")
                    myfile.write(f"charMOS: Simulating for NMOS L={self.mosDat['nfet']['length'][idxL]} PMOS L={self.mosDat['pfet']['length'][idxL]}, VSB={vsb[idxVSB]}\n")
                    myfile.close()

                    self.runSim("charNMOS.net", "ngspice")
                    # pdb.set_trace()
                    simDat = spice3read.read('outN.raw')
                    
                    
                    devTypes = ['nfet', 'pfet']
                    idx = f'{idxL}d{idxVSB}d{tab1[devTypes[0]]}'
                    devName = f'@m.x{tab1[devTypes[0]]}d{idx}.m'+self.settings[tab[devTypes[0]]]
                    self.mosDat[devTypes[0]]['id'][idxL][idxVSB]  = simDat[f'i({devName}[id])']
                    self.mosDat[devTypes[0]]['vt'][idxL][idxVSB]  = simDat[f'v({devName}[vth])']
                    self.mosDat[devTypes[0]]['gm'][idxL][idxVSB]  = simDat[f'{devName}[gm]']
                    self.mosDat[devTypes[0]]['gmb'][idxL][idxVSB] = simDat[f'{devName}[gmbs]']
                    self.mosDat[devTypes[0]]['gds'][idxL][idxVSB] = simDat[f'{devName}[gds]']
                    self.mosDat[devTypes[0]]['cgg'][idxL][idxVSB] = simDat[f'{devName}[cgg]']
                    self.mosDat[devTypes[0]]['cgs'][idxL][idxVSB] = simDat[f'{devName}[cgs]']
                    self.mosDat[devTypes[0]]['cgd'][idxL][idxVSB] = simDat[f'{devName}[cgd]']
                    self.mosDat[devTypes[0]]['cgb'][idxL][idxVSB] = self.mosDat[devTypes[0]]['cgg'][idxL][idxVSB] - self.mosDat[devTypes[0]]['cgs'][idxL][idxVSB] - self.mosDat[devTypes[0]]['cgd'][idxL][idxVSB]
                    self.mosDat[devTypes[0]]['cdd'][idxL][idxVSB] = simDat[f'{devName}[cdd]']
                    self.mosDat[devTypes[0]]['css'][idxL][idxVSB] = simDat[f'{devName}[cgs]'] - simDat[f'{devName}[cbs]']

                    self.runSim("charPMOS.net", "ngspice")
                    simDat = spice3read.read('outP.raw')
                    
                    idx = f'{idxL}d{idxVSB}d{tab1[devTypes[1]]}'
                    devName = f'@m.x{tab1[devTypes[1]]}d{idx}.m'+self.settings[tab[devTypes[1]]]
                    self.mosDat[devTypes[1]]['id'][idxL][idxVSB]  = simDat[f'i({devName}[id])']
                    self.mosDat[devTypes[1]]['vt'][idxL][idxVSB]  = simDat[f'v({devName}[vth])']
                    self.mosDat[devTypes[1]]['gm'][idxL][idxVSB]  = simDat[f'{devName}[gm]']
                    self.mosDat[devTypes[1]]['gmb'][idxL][idxVSB] = simDat[f'{devName}[gmbs]']
                    self.mosDat[devTypes[1]]['gds'][idxL][idxVSB] = simDat[f'{devName}[gds]']
                    self.mosDat[devTypes[1]]['cgg'][idxL][idxVSB] = simDat[f'{devName}[cgg]']
                    self.mosDat[devTypes[1]]['cgs'][idxL][idxVSB] = simDat[f'{devName}[cgs]']
                    self.mosDat[devTypes[1]]['cgd'][idxL][idxVSB] = simDat[f'{devName}[cgd]']
                    self.mosDat[devTypes[1]]['cgb'][idxL][idxVSB] = self.mosDat[devTypes[1]]['cgg'][idxL][idxVSB] - self.mosDat[devTypes[1]]['cgs'][idxL][idxVSB] - self.mosDat[devTypes[1]]['cgd'][idxL][idxVSB]
                    self.mosDat[devTypes[1]]['cdd'][idxL][idxVSB] = simDat[f'{devName}[cdd]']
                    self.mosDat[devTypes[1]]['css'][idxL][idxVSB] = simDat[f'{devName}[cgs]'] - simDat[f'{devName}[cbs]']

                elif (self.settings['simulator'] == "spectre"): #  TODO: Fix this part
                    genSimParamsSpectre(mosLengths[idxL], vsb[idxVSB])
                    
                    self.runSim("charMOS.scs", "spectre")
                    simDat = spice3read.read('charMOS.raw', 'spectre')
                    
                    if (subcktPath == ""):
                        nmos = "xn"
                        pmos = "xp"
                    else:
                        nmos = "xn." + subcktPath
                        pmos = "xp." + subcktPath

                    self.mosDat['nfet']['id'][idxL][idxVSB]  = simDat['{0}:ids'.format(nmos)]
                    self.mosDat['nfet']['vt'][idxL][idxVSB]  = simDat['{0}:vth'.format(nmos)]
                    self.mosDat['nfet']['gm'][idxL][idxVSB]  = simDat['{0}:gm'.format(nmos)]
                    self.mosDat['nfet']['gmb'][idxL][idxVSB] = simDat['{0}:gmbs'.format(nmos)]
                    self.mosDat['nfet']['gds'][idxL][idxVSB] = simDat['{0}:gds'.format(nmos)]
                    self.mosDat['nfet']['cgg'][idxL][idxVSB] = simDat['{0}:cgg'.format(nmos)]
                    self.mosDat['nfet']['cgs'][idxL][idxVSB] = simDat['{0}:cgs'.format(nmos)]
                    self.mosDat['nfet']['cgd'][idxL][idxVSB] = simDat['{0}:cgd'.format(nmos)]
                    self.mosDat['nfet']['cgb'][idxL][idxVSB] = simDat['{0}:cgb'.format(nmos)]
                    self.mosDat['nfet']['cdd'][idxL][idxVSB] = simDat['{0}:cdd'.format(nmos)]
                    self.mosDat['nfet']['css'][idxL][idxVSB] = simDat['{0}:css'.format(nmos)]

                    self.mosDat['pfet']['id'][idxL][idxVSB]  = simDat['{0}:ids'.format(pmos)]
                    self.mosDat['pfet']['vt'][idxL][idxVSB]  = simDat['{0}:vth'.format(pmos)]
                    self.mosDat['pfet']['gm'][idxL][idxVSB]  = simDat['{0}:gm'.format(pmos)]
                    self.mosDat['pfet']['gmb'][idxL][idxVSB] = simDat['{0}:gmbs'.format(pmos)]
                    self.mosDat['pfet']['gds'][idxL][idxVSB] = simDat['{0}:gds'.format(pmos)]
                    self.mosDat['pfet']['cgg'][idxL][idxVSB] = simDat['{0}:cgg'.format(pmos)]
                    self.mosDat['pfet']['cgs'][idxL][idxVSB] = simDat['{0}:cgs'.format(pmos)]
                    self.mosDat['pfet']['cgd'][idxL][idxVSB] = simDat['{0}:cgd'.format(pmos)]
                    self.mosDat['pfet']['cgb'][idxL][idxVSB] = simDat['{0}:cgb'.format(pmos)]
                    self.mosDat['pfet']['cdd'][idxL][idxVSB] = simDat['{0}:cdd'.format(pmos)]
                    self.mosDat['pfet']['css'][idxL][idxVSB] = simDat['{0}:css'.format(pmos)]
                
                
                rows, columns = os.popen('stty size', 'r').read().split()
                columns = int(columns) - 10
                progCurr += 1
                progPercent = 100 * progCurr / progTotal
                progLen = int(progPercent*columns/100)
                sys.stdout.write("\r[{0}{1}] {2}%".format("#"*progLen, " "*(columns-progLen), progPercent))
                sys.stdout.flush()

        os.system('rm -fr charNMOS.net charPMOS.net outN.raw outP.raw b3v33check.log charMOS.scs simParams.scs charMOS.raw charMOS.raw.psf charMOS.ahdlSimDB charMOS.log')
        print
        print("Data generated. Saving...")
        pickle.dump(self.mosDat, open(self.settings["datFileName"], "wb"), pickle.HIGHEST_PROTOCOL)
        print("Done! Data saved in " + self.settings["datFileName"])
