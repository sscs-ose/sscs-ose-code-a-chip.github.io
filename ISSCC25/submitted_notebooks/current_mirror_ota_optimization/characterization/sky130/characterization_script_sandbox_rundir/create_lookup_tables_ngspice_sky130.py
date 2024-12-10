
#
# Author: Alec S. Adair
# ROAR Flow Turku, Finland August 19, 2024
# This script generates all lookuptables for a given PDK
#

import os
import shutil
import re

def create_netlist_from_template(netlist_template, length, corner, temperature):
    if os.path.exists(netlist_template):
        with open(netlist_template, 'r') as net_temp:
            netlist_data = net_temp.read()
        length_str = str(length)
        netlist_data = netlist_data.replace("_LENGTH", length_str)
        netlist_data = netlist_data.replace("_CORNER", corner)
        netlist_data = netlist_data.replace("_TEMPERATURE", temperature)
        return netlist_data

def fix_data_line(text):
    # Remove leading spaces from each line
    text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)

    # Replace one or more spaces with a single comma, but keep newline characters
    text = re.sub(r'[ \t]+', ',', text)

    return text

def create_lookup_tables(tech_name=""):
    pdk = "sky130"
    luts_dir = "LUTs_" + tech_name
    netlists_dir = "netlists_" + tech_name
    if os.path.exists(luts_dir):
        shutil.rmtree(luts_dir)
    os.system("mkdir " + luts_dir)
    models = ["01v8"]

    nfet = "nfet"
    pfet = "pfet"

    #models = [nfet, pfet]

    ss = "ss"
    tt = "tt"
    ff = "ff"

    corners = [ss, tt, ff]
    corners = [tt]

    cold = "-25"
    room = "25"
    hot = "75"

    temperatures = [cold, room, hot]

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

    lengths = [".150", ".200", ".250", ".300", ".500", "1.000"]
    #lengths = [".150"]
    width = "1.0"
    ncorners = [nsscold, nttcold, nffcold,
                nssroom, nttroom, nffroom,
                nsshot, ntthot, nffhot]

    pcorners = [psscold, pttcold, pffcold,
                pssroom, pttroom, pffroom,
                psshot, ptthot, pffhot]

    #ncorners = [nttroom]

    run_n = True
    run_p = True

    model = "nfet"

    netlists_dir = "netlists"
    netlist_mkdir = "mkdir " + netlists_dir
    if not os.path.exists(netlists_dir):
        os.system(netlist_mkdir)

    netlist_template_file = "char_template.cir"
    for model in models:
        n_model = "n_" + model
        p_model = "p_" + model
        n_model_dir = luts_dir + "/" + n_model
        p_model_dir = luts_dir + "/" + p_model
        if run_n == True:
            if os.path.exists(n_model_dir):
                shutil.rmtree(n_model_dir)
            os.system("mkdir " + n_model_dir)
        if run_p == True:
            if os.path.exists(p_model_dir):
                shutil.rmtree(p_model_dir)
            os.system("mkdir " + p_model_dir)
        for length in lengths:
            length_str = str(length.replace(".", ""))
            n_length_dir = n_model_dir + "/LUT_N_" + str(length_str)
            p_length_dir = p_model_dir + "/LUT_P_" + str(length_str)
            if run_n == True:
                if os.path.exists(n_length_dir):
                    shutil.rmtree(n_length_dir)
                os.system("mkdir " + n_length_dir)
            if run_p == True:
                if os.path.exists(p_length_dir):
                    shutil.rmtree(p_length_dir)
                os.system("mkdir " + p_length_dir)
            for corner in corners:
                for temp in temperatures:
                    print("Creating netlist...")
                    edited_netlist = create_netlist_from_template(netlist_template=netlist_template_file, length=length, corner=corner, temperature=temp)
                    netlist_name = model + "_" + length + "_" + corner + "_" + temp + ".cir"
                    corner_name = corner+temp
                    with open(netlist_name, 'w') as file:
                        file.write(edited_netlist)
                    print("Running characterization...")
                    os.system("ngspice -b " + netlist_name)
                    if os.path.exists(n_length_dir) and os.path.exists("nfet_cid_characterization.csv"):
                        with open("nfet_cid_characterization.csv", 'r') as file:
                            lines = file.readlines()
                        with open("nfet_cid_characterization.csv", 'w') as file:
                            for i, line in enumerate(lines):
                                line = fix_data_line(line)
                                if i == 0:
                                    #file.write(line.rstrip('\n') + ",W,L,pdk\n")
                                    file.write(line)
                                else:
                                    file.write(line.rstrip('\n') + "1.0," + str(length) + "," + pdk + "\n")
                        with open("pfet_cid_characterization.csv", 'r') as file:
                            lines = file.readlines()
                        with open("pfet_cid_characterization.csv", 'w') as file:
                            for i, line in enumerate(lines):
                                line = fix_data_line(line)
                                if i == 0:
                                    file.write(line)
                                    #file.write(line.rstrip('\n') + ",W,L,pdk,\n")
                                else:
                                    file.write(line.rstrip('\n') + "1.0," + str(length) + "," + pdk + "\n")
                        os.system("mv nfet_cid_characterization.csv " + n_length_dir + "/nfet" + corner_name + ".csv")
                    if os.path.exists(n_length_dir) and os.path.exists("pfet_cid_characterization.csv"):
                        os.system("mv pfet_cid_characterization.csv " + p_length_dir + "/pfet" + corner_name + ".csv")
                    os.system("mv " + netlist_name + " netlists")


if __name__ == "__main__":
    create_lookup_tables("SKY130")
print("characterization done")
