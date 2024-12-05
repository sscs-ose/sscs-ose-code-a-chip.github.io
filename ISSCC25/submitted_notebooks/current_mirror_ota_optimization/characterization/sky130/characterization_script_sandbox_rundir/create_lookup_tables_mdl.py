
#
# Author: Alec S. Adair
# This script generates all lookuptables for a given PDK
#

import os
import shutil

def create_lookup_tables():

    nfet = "nfet"
    pfet = "pfet"

    ss = "ss"
    tt = "tt"
    ff = "ff"

    cold = "cold"
    room = "room"
    hot = "hot"

    nsscold = nfet + ss + cold
    nttcold = nfet + tt + cold
    nffcold = nfet + ff + cold
    nssroom = nfet + ss + room
    nttroom = nfet + tt + room
    nffroom = nfet + ff + room
    nsshot = nfet + ss + hot
    ntthot = nfet + tt + hot
    nffhot = nfet + ff + hot

    psscold = pfet + ss + cold
    pttcold = pfet + tt + cold
    pffcold = pfet + ff + cold
    pssroom = pfet + ss + room
    pttroom = pfet + tt + room
    pffroom = pfet + ff + room
    psshot = pfet + ss + hot
    ptthot = pfet + tt + hot
    pffhot = pfet + ff + hot

    lengths = ["20n", "50n", "82n", "100n", "220n", "500n"]

    ncorners = [nsscold, nttcold, nffcold,
                nssroom, nttroom, nffroom,
                nsshot, ntthot, nffhot]

    pcorners = [psscold, pttcold, pffcold,
                pssroom, pttroom, pffroom,
                psshot, ptthot, pffhot]

    #ncorners = [nttroom]

    run_n = True
    run_p = False

    model = "nfet"

    netlists_dir = "netlists"
    netlist_mkdir = "mkdir netlists"
    if not os.path.exists(netlists_dir):
        os.system(netlist_mkdir)

    for length in lengths:
        sim_string = "simulator lang=spectre"
        param_string = "parameters L=" + length

        if run_n == True:
            n_sim_echo = "echo " + sim_string + " > n_netlist_" + length
            os.system(n_sim_echo)
            n_echo = "echo " + param_string + "  >> n_netlist_" + length
            os.system(n_echo)
            n_cat = "cat template_n_netlist >> n_netlist_" + length
            os.system(n_cat)
            n_copy = "cp n_netlist_" + length + " n_netlist"
            os.system(n_copy)
            lookuptable_dir_n = "LUT_N_" + length
            n_mkdir = "mkdir " + lookuptable_dir_n
            if os.path.exists(lookuptable_dir_n):
                shutil.rmtree(lookuptable_dir_n)
            os.system(n_mkdir)
            for ncorner in ncorners:
                spectre_command = "spectremdl -format psfascii -batch nfet_characterization.mdl -design " + ncorner + ".scs"
                os.system(spectre_command)
                mv_command = "mv techLUT.csv " + lookuptable_dir_n + "/" + ncorner + ".csv"
                os.system(mv_command)
                os.system("./clean")

        if run_p == True:
            p_sim_echo = "echo " + sim_string + " > p_netlist_" + length
            os.system(p_sim_echo)
            p_echo = "echo " + param_string + "  >> p_netlist_" + length
            os.system(p_echo)
            p_cat = "cat template_p_netlist >> p_netlist_" + length
            os.system(p_cat)
            p_copy = "cp p_netlist_" + length + " p_netlist"
            os.system(p_copy)
            lookuptable_dir_p = "LUT_P_" + length
            p_mkdir = "mkdir " + lookuptable_dir_p
            if os.path.exists(lookuptable_dir_p):
                shutil.rmtree(lookuptable_dir_p)
            os.system(p_mkdir)
            for pcorner in pcorners:
                spectre_command = "spectremdl -format psfascii -batch nfet_characterization.mdl -design " + pcorner + ".scs"
                os.system(spectre_command)
                mv_command = "mv techLUT.csv " + lookuptable_dir_p + "/" + pcorner + ".csv"
                os.system(mv_command)
                os.system("./clean")

    os.system("mv n_netlist_* netlists")
    os.system("mv p_netlist_* netlists")
        #if run_n == True:

       # if run_p == True:


create_lookup_tables()
print("characterization done")
