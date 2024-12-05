
#
# Author: Alec S. Adair
# C/Id Lookup Table Object
#
# Creation Date: March 24, 2023
#

import sys, os, getpass, shutil, operator, collections, copy, re
import numpy as np
import matplotlib
#matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
plt.rcParams['svg.fonttype'] = 'none'
import pandas as pd
import math

class CID:

    def __init__(self):
        self.techs = {}

    def add_tech_lut(self, tech_name, device_flavor="rvt", corner_name="tt", lut_csv="./LUTs/sky130_tt_25.csv", vdd=0.0):
        if(os.path.isfile(lut_csv)):
            print("Corner LUT file " + lut_csv + "does not exist.")
            return(False)
        cid_tech = None
        if tech_name not in self.techs:
            cid_tech = CIDTech(tech_name)
        else:
            cid_tech = self.techs[tech_name]
        cid_tech.add_device_lut(tech_name=tech_name, device_flavor=device_flavor, corner_name=corner_name, lut_csv=lut_sv, vdd=vdd)
        self.techs[tech_name] = cid_tech
        return(True)

    def get_bucket_for_ids_measurement(self, tech, flavor, corner, fet_type, l, ids_target):
        if tech not in self.techs:
            print("tech " + tech + "does not exist")
            return False
        tech = self.techs[tech]
        ids_bucket = tech.get_bucket_for_ids_measurement(flavor, corner, fet_type, l, ids_target)
        return ids_bucket



    @staticmethod
    def normalize_array(input_array):
        max_val = 0
        normalized_array = []
        for num in input_array:
            if num >= max_val:
                max_val = num
        min_val = max_val
        for num in input_array:
            if num <= min_val:
                min_val = num
        for num in input_array:
            normalized_array.append((num - min_val) / (max_val - min_val))
        return normalized_array


class CIDTech:

    def __init__(self, tech_name):
        self.tech_name = tech_name
        self.devices = {}

    def add_device_lut(self, tech_name, device_flavor, corner_name, lut_csv, vdd=0.0):
        device = None
        if device_flavor in self.devices:
            device = self.devices[device_flavor]
        else:
            device = CIDDevice(device=device_flavor, corner_name=corner_name, lut_csv=lut_csv, vdd=vdd)
        device.add_corner_lut(corner_name, lut_csv, vdd)
        return True

    def get_bucket_for_ids_measurement(self, device_flavor, corner, fet_type, l, ids_target):
        if device_flavor not in self.devices:
            print("Device " + device_flavor + "does not exist in tech " + self.tech_name)
            return 0.0
        device = self.devices[device_flavor]
        ids_bucket = device.get_bucket_for_ids_measurement(corner, fet_type, l, ids_target)
        return ids_bucket

class CIDCornerCollection:
    def __init__(self, collection_name="", file_list=None, corner_list=None):
        self.collection_name = collection_name
        self.corners = []
        if corner_list != None:
            for corner in corner_list:
                self.corners.append(corner)
        if file_list != None:
            for file in file_list:
                self.add_corner_from_lut(corner_name=file, lut_csv=file, vdd=0)

    def serialize(self):
        # Serialize the CIDCornerCollection object to a dictionary
        return {
            "collection_name": self.collection_name,
            "corners": [corner.serialize() for corner in self.corners]  # Serialize each corner
        }

    @classmethod
    def deserialize(cls, data):
        # Deserialize a CIDCornerCollection from the provided dictionary
        corner_list = [CIDCorner.deserialize(corner_data) for corner_data in data.get("corners", [])]
        return cls(
            collection_name=data.get("collection_name", ""),
            corner_list=corner_list
        )

    def add_corner_from_lut(self, corner_name, lut_csv, vdd):
        if os.path.exists(lut_csv):
            corner = CIDCorner(corner_name=corner_name, lut_csv=lut_csv, vdd=vdd)
            self.corners.append(corner)

    def magic_equation(self, gbw, cload, epsilon=5, show_plot=False, new_plot=True, ax1=None, fig1=None):
        kgm_min = 1e13
        ids_opt = 1e13
        first_corner = True
        color_list = ["blue", "orange", "green", "red", "purple", "brown", "pink", "gray", "olive", "cyan"]
        color_index = 0
        color_list_length = len(color_list)
        if ax1 == None or fig1 == None:
            ax1, fig1 = plt.subplots()
        for corner in self.corners:
            color = color_list[color_index]
            if first_corner == True:
                new_plot = True
            ids_opt, kgm_opt, ax1, fig1 = corner.magic_equation(gbw=gbw, cload=cload, show_plot=show_plot, new_plot=new_plot,
                                                     ax1=ax1, fig1=fig1, color=color)
            if abs(kgm_opt) < kgm_min:
                kgm_min = kgm_opt
            new_plot = False
            first_corner = False
            if(color_index == color_list_length - 1):
                color_index = 0
            else:
                color_index = color_index + 1
        max_id_corner = 0
        min_id_corner = 1e13
        kgm_step_size = kgm_min/100
        kgm_convergence = 0
        kgm_eval = kgm_min
        while kgm_eval > 0:
        #for i in reversed(range(0, kgm_min, kgm_step_size)):
            for corner in self.corners:
                #ids_opt, kgm_opt = corner.magic_equation(gbw=gbw, cload=cload, show_plot=show_plot, new_plot=new_plot,
                #                                         ax1=ax1, fig1=fig1)
                ids = abs(corner.evaluate_magic_function(gbw, cload, kgm_eval))
                if ids > max_id_corner:
                    max_id_corner = ids
                if ids < min_id_corner:
                    min_id_corner = ids
                percentage_diff = 100
                if min_id_corner != max_id_corner:
                    percentage_diff = (1 - (min_id_corner/max_id_corner))*100
                if percentage_diff < epsilon:
                    average_current = (max_id_corner + min_id_corner)/2
                    return average_current, kgm_eval
            kgm_eval = kgm_eval - kgm_step_size
        print("Device does not converge within " + str(epsilon) + "%")
        return -1, -1

    def plot_processes_params(self, param1, param2, norm_type="", show_plot=True, new_plot=True, fig1=None, ax1=None):
        corner_list = self.corners
        first_corner = True
        color_list = ['r-', 'b-', 'g-', 'c-', 'm-', 'y-', 'k-']
        color_list = ["blue", "orange", "green", "red", "purple", "brown", "pink", "gray", "olive", "cyan"]
        color_list_length = len(color_list)
        color_index = 0
        for corner in corner_list:
            color = color_list[color_index]
            corner_pdk = corner.pdk
            length_str = str(corner.length)
            corner_name = corner.corner_name
            legend_str = "PDK: " + corner_pdk + ", L: " + length_str + ", corner: " + corner_name
            if first_corner == True:
                fig1, ax1 = corner.plot_processes_params(param1=param1, param2=param2, norm_type=norm_type, show_plot=True,
                                                         new_plot=new_plot, fig1=fig1, ax1=ax1, color=color, legend_str=legend_str)
                first_corner = False
            else:
                fig1, ax1 = corner.plot_processes_params(param1=param1, param2=param2, norm_type=norm_type, show_plot=show_plot,
                                                         new_plot=False, fig1=fig1, ax1=ax1, color=color, legend_str=legend_str)
            if(color_index == color_list_length - 1):
                color_index = 0
            else:
                color_index = color_index + 1
        return 0

class CIDDevice:

    def __init__(self, device_name, vdd=0.0, lut_directory=None, corner_list=None):
        self.device_name = device_name
        self.vdd = vdd
        self.corners = []
        self.length = 0
        self.pdk = 0
        if corner_list != None:
            for corner in corner_list:
                self.corners.append(corner)
        if lut_directory != None and os.path.exists(lut_directory):
            i = 0
            base_corner_name = ""
            for filename in os.listdir(lut_directory):
                filename_parse = filename.split(".")
                lut_file = os.path.join(lut_directory, filename)
                corner_name = base_corner_name + filename_parse[0]
                corner = CIDCorner(corner_name=corner_name,
                                   lut_csv=lut_file,
                                   vdd=vdd)
                self.corners.append(corner)
                i = i + 1
        if len(self.corners) != 0:
            pdk_col = self.corners[0].df["pdk"]
            l_col = self.corners[0].df["L"]
            self.pdk = pdk_col[0]
            self.length = l_col[0]


    def add_corner_from_lut(self, corner_name, lut_csv, vdd=0.0):
        if os.path.exists(lut_csv):
            corner = CIDCorner(corner_name=corner_name, lut_csv=lut_csv, vdd=vdd)
            self.corner_list.append(corner)

    def magic_equation(self, gbw, cload, beta_factor=1, c_coeff=[1, 1, 1], epsilon=10, show_plot=False, new_plot=False, ax1=None, fig1=None):
        kgm_min = 1e13
        ids_opt = 1e13
        first_corner = True
        color_list = ["blue", "orange", "green", "red", "purple", "brown", "pink", "gray", "olive", "cyan"]
        color_index = 0
        color_list_length = len(color_list)
        if ax1 == None or fig1 == None and show_plot == True and new_plot == False:
            ax1, fig1 = plt.subplots()
        for corner in self.corners:
            color = color_list[color_index]
            if first_corner == True:
                new_plot = True
            ids_opt, kgm_opt, ax1, fig1 = corner.current_as_function_of_kgm(gbw=gbw, cload=cload, beta_factor=beta_factor, c_coeff=c_coeff, show_plot=show_plot, new_plot=new_plot,ax1=ax1, fig1=fig1, color=color)
            if abs(kgm_opt) < kgm_min:
                kgm_min = kgm_opt
            new_plot = False
            first_corner = False
            if(color_index == color_list_length - 1):
                color_index = 0
            else:
                color_index = color_index + 1
        max_id_corner = 0
        min_id_corner = 1e13
        kgm_step_size = kgm_min/100
        kgm_convergence = 0
        kgm_eval = kgm_min
        while kgm_eval > 0:
        #for i in reversed(range(0, kgm_min, kgm_step_size)):
            for corner in self.corners:
                #ids_opt, kgm_opt = corner.magic_equation(gbw=gbw, cload=cload, show_plot=show_plot, new_plot=new_plot,
                #                                         ax1=ax1, fig1=fig1)
                ids = abs(corner.evaluate_magic_function(gbw, cload, kgm_eval))
                if ids > max_id_corner:
                    max_id_corner = ids
                if ids < min_id_corner:
                    min_id_corner = ids
                percentage_diff = 100
                if min_id_corner != max_id_corner:
                    percentage_diff = (1 - (min_id_corner/max_id_corner))*100
                if percentage_diff < epsilon:
                    average_current = (max_id_corner + min_id_corner)/2
                    return average_current, kgm_eval
            kgm_eval = kgm_eval - kgm_step_size
        print("Device does not converge within " + str(epsilon) + "% Across PVT")
        return -1, -1

    def plot_processes_params(self, param1, param2, norm_type="", show_plot=True, new_plot=True, fig1=None, ax1=None):
        corner_list = self.corners
        first_corner = True
        color_list = ['r-', 'b-', 'g-', 'c-', 'm-', 'y-', 'k-']
        color_list = ["blue", "orange", "green", "red", "purple", "brown", "pink", "gray", "olive", "cyan"]
        color_list_length = len(color_list)
        color_index = 0
        for corner in corner_list:
            color = color_list[color_index]
            corner_pdk = corner.pdk
            length_str = str(corner.length)
            corner_name = corner.corner_name
            legend_str = "PDK: " + corner_pdk + ", L: " + length_str + ", corner: " + corner_name
            if first_corner == True:
                fig1, ax1 = corner.plot_processes_params(param1=param1, param2=param2, norm_type=norm_type, show_plot=True,
                                                         new_plot=new_plot, fig1=fig1, ax1=ax1, color=color, legend_str=legend_str)
                first_corner = False
            else:
                fig1, ax1 = corner.plot_processes_params(param1=param1, param2=param2, norm_type=norm_type, show_plot=show_plot,
                                                         new_plot=False, fig1=fig1, ax1=ax1, color=color, legend_str=legend_str)
            if(color_index == color_list_length - 1):
                color_index = 0
            else:
                color_index = color_index + 1
        return 0





class CIDCorner():

    def __init__(self, corner_name="", lut_csv="", vdd=0.0, pdk=""):
        self.vdd = vdd
        self.max_min_vals = {}
        self.ic_consts = {}
        self.lut = None
        self.corner_name = corner_name
        self.lut_csv = lut_csv
        self.df = None
        self.length = 0
        #self.nfet_df = None
        #self.pfet_df = None
        self.pdk = pdk

        if lut_csv != "" and os.path.isfile(lut_csv):
            self.import_lut(lut_csv, vdd, corner_name=corner_name)
        else:
            print("LUT CSV File " + lut_csv + " does not exist")
            return None


    def serialize(self):
        # Convert the CIDCorner object into a dictionary
        return {
            "vdd": self.vdd,
            "max_min_vals": self.max_min_vals,
            "ic_consts": self.ic_consts,
            "lut": self.lut,  # Could add more specific serialization logic if necessary
            "corner_name": self.corner_name,
            "lut_csv": self.lut_csv,
            "length": self.length,
            "pdk": self.pdk
            # Skipping df for now unless you want to serialize that as well
        }

    @classmethod
    def deserialize(cls, data):
        # Create a CIDCorner object from the provided dictionary
        corner = cls(
            corner_name=data.get("corner_name", ""),
            lut_csv=data.get("lut_csv", ""),
            vdd=data.get("vdd", 0.0),
            pdk=data.get("pdk", "")
        )
        corner.max_min_vals = data.get("max_min_vals", {})
        corner.ic_consts = data.get("ic_consts", {})
        corner.lut = data.get("lut", None)
        corner.length = data.get("length", 0)
        corner.import_lut(corner.lut_csv, vdd=corner.vdd, corner_name=corner.corner_name)
        return corner

    def reset_df(self):
        self.df.reset_index()

    def import_lut(self, lut_csv, vdd=0.0, corner_name=""):
        if not os.path.isfile(lut_csv):
            print("File " + lut_csv + "does not exist.")
            return(False)
        self.vdd = vdd
        self.df = pd.read_csv(lut_csv, skipinitialspace=True)
        pdk_col = self.df["pdk"]
        self.pdk = pdk_col[0]
        self.lut_csv = lut_csv
        length_col = self.df["L"]
        if "ids" not in self.df.columns:
            self.df["ids"] = self.df["id"]
        self.length = length_col[0]
        if corner_name == "":
            self.corner_name = corner_name
        self.df.reset_index()
        if not self.check_if_param_exists("ft"):
            ft_array = []
            cgg_col = self.df["cgg"]
            gm_col = self.df["gm"]
            for i in range(len(cgg_col)):
                cgg = abs(cgg_col[i])
                gm = gm_col[i]
                ft = gm/(2*math.pi*cgg)
                ft_array.append(ft)
            self.df["ft"] = ft_array
        if not self.check_if_param_exists("kcdd"):
            kcdd_array = []
            cdd_col = self.df["cdd"]
            i_col = self.df["ids"]
            for i in range(len(cdd_col)):
                cdd = cdd_col[i]
                id = i_col[i]
                kcdd = cdd/id
                kcdd_array.append(kcdd)
            self.df["kcdd"] = kcdd_array
        if not self.check_if_param_exists("kcgg"):
            kcgg_array = []
            cgg_col = self.df["cgg"]
            i_col = self.df["ids"]
            for i in range(len(cgg_col)):
                cgg = cgg_col[i]
                id = i_col[i]
                kcgg = cgg/id
                kcgg_array.append(kcgg)
            self.df["kcgg"] = kcgg_array
        if not self.check_if_param_exists("kcgd"):
            kcgd_array = []
            cgd_col = abs(self.df["cgd"])
            i_col = self.df["ids"]
            for i in range(len(cgd_col)):
                cgd = cgd_col[i]
                id = i_col[i]
                kcgd = cgd/id
                kcgd_array.append(kcgd)
            self.df["kcgd"] = kcgg_array
        if not self.check_if_param_exists("kcgs"):
            kcgs_array = []
            cgs_col = abs(self.df["cgs"])
            i_col = self.df["ids"]
            for i in range(len(cgs_col)):
                cgs = cgs_col[i]
                id = i_col[i]
                kcgs = cgs/id
                kcgs_array.append(kcgs)
            self.df["kcgs"] = kcgs_array
        if not self.check_if_param_exists("kcds"):
            kcds_array = []
            cds_col = abs(self.df["cds"])
            i_col = self.df["ids"]
            for i in range(len(cds_col)):
                cds = cds_col[i]
                id = i_col[i]
                kcds = cds/id
                kcds_array.append(kcds)
            self.df["kcds"] = kcds_array
        if not self.check_if_param_exists("gmro"):
            gmro_array = []
            gds_gm_array = []
            kgds_array = []
            gm_col = self.df["gm"]
            gds_col = self.df["gds"]
            i_col = self.df["ids"]

            for i in range(len(gm_col)):
                gm = gm_col[i]
                gds = gds_col[i]
                gmro = gm/gds
                gds_gm = 1/gmro
                kgds = gds_col[i]/i_col[i]
                kgds_array.append(kgds)
                gmro_array.append(gmro)
                gds_gm_array.append(gds_gm)
            self.df["gmro"] = gmro_array
            self.df["gm/gds"] = gmro_array
            self.df["gds/gm"] = gds_gm_array
            self.df["kgds"] = kgds_array
        if not self.check_if_param_exists("kgds"):
            kgds_array = []
            gds_col = self.df["gds"]
            i_col = self.df["ids"]
            for i in range(len(i_col)):
                gds = gds_col[i]
                ids = i_col[i]
                kgds = gds/ids
                kgds_array.append(kgds)
            self.df["kgds"] = kgds_array
        if not self.check_if_param_exists("iden"):
            iden_array = []
            ids_col = self.df["ids"]
            width = self.df["W"][0]
            if self.pdk == "sky130":
                width = width*1e-6
            for i in range(len(ids_col)):
                ids = ids_col[i]
                iden = ids/width
                iden_array.append(iden)
            self.df["iden"] = iden_array
        if not self.check_if_param_exists("kgmft"):
            kgmft_array = []
            kgm_col = self.df["kgm"]
            ft_col = self.df["ft"]
            for i in range(len(kgm_col)):
                kgm = kgm_col[i]
                ft = ft_col[i]
                kgmft = kgm*ft
                kgmft_array.append(kgmft)
            self.df["kgmft"] = kgmft_array
            self.df["gmidft"] = kgmft_array
        if not self.check_if_param_exists("vds"):
            vds_array = []
            vds_col = self.df["VDS"]
            for i in range(len(vds_col)):
                vds = vds_col[i]
                vds_array.append(vds)
            self.df["vds"] = vds_array
        if not self.check_if_param_exists("vgs"):
            vgs_array = []
            vgs_col = self.df["VGS"]
            for i in range(len(vgs_col)):
                vgs = vgs_col[i]
                vgs_array.append(vgs)
            self.df["vgs"] = vgs_array
        if not self.check_if_param_exists("kgds"):
            kgds_array = []
            gds_col = self.df["gds"]
            ids_col = self.df["ids"]
            #gds_col = 1/gds_col
            for i in range(len(gds_col)):
                kgds = gds_col[i]/ids_col[i]
                kgds_array.append(kgds)
            self.df["kgds"] = kgds_array
        """
        if not self.check_if_param_exists("dkcgs"):
            kcgs_col = self.df["kcgs"]
            kgm_col = self.df["kgm"]
            num = np.diff(kcgs_col)
            denom = np.diff(kgm_col)
            dkcgs_array = np.diff(kcgs_col)/np.diff(kgm_col)
            dkcgs_array = np.append(dkcgs_array, 0.0)
            self.df["dkcgs"] = dkcgs_array
        """
        return 0

    #method not needed
    @staticmethod
    def get_bucket_for_ids_measurement(self, fet_type, l, ids_target):
        ids_diff = 10e6
        l_str = str(l)
        ids_range = self.lookup_tables[tech][fet_type][l_str]
        ids_output = 0
        for ids in ids_range:
            ids_float = float(ids)
            ids_target_float = float(ids_target)
            ids_current_diff = abs(ids_target_float - ids_float)
            if(ids_current_diff <= ids_diff):
                ids_diff = ids_current_diff
                ids_output = ids
        return(ids_output)


    def get_closest_param_val(self, param, param_val):
        self.get_closest_param_value(param, param_val)

    def get_closest_param_in_df(self, param, param_val):
        smallest_param_diff = 1e33
        closest_param = None
        index = 0
        param_col = self.df[param]
        for i in range(0, len(param_col)):
        #for i, row in self.df.iterrows():
            param_i = param_col[i]
            param_diff = abs(param_i - param_val)
            if param_diff <= smallest_param_diff:
                smallest_param_diff = param_diff
                closest_param = param_i
                index = i
        return closest_param, index


    def get_closest_param_value(self, fet_type, length, param, param_val):
        largest_param_diff = 1e33
        length_str = str(length)
        closest_param = None
        fet_type_str = str(fet_type)
        if fet_type == "nfet":
            fet_type = 0.0
        elif fet_type == "pfet":
            fet_type = 1.0
        elif fet_type == 0:
            fet_type = 0.0
        elif fet_type == 1:
            fet_type = 1.0
        else:
            print("fet type " + fet_type_str + " is not valid")
            return -1
        fet_type_int = fet_type
        param_diff = 0
        for i, row in self.df.iterrows():
            param_i = row[param]
            l_i = row["L"]
            type_i = row["type"]
            if l_i == length_str and fet_type == type_i:
                param_diff = abs(param_i - param_val)
                if param_diff > largest_param_diff:
                    largest_param_diff = param_diff
                    closest_param = param_i
        return closest_param



    def get_bucket_for_length(self, fet_type, target_l):
        float_type = 0.0
        if fet_type == "pfet":
            float_type = 1.0
        type_df = self.df.loc[self.df['type'] == float_type]
        print(type_df)
        return(0)

    def get_bucket_for_param(self, fet_type, l, ids_target):
        closest_l = self.get_bucket_for_length(fet_type=fet_type, target_l=l)
        print("TODO")


    def lookup2(self):
        print("TODO")


    def lookup3(self, param1, param2, fet_type, l, norm_type="",):
        print("TODO")


    def bucket_lookup_val(self, param, val):
        print("TODO")


    def lookup(self, param1, param2, param1_val):
        if not self.check_if_param_exists(param1) and self.check_if_param_exists(param2):
            return None
        closest_value = self.df[param1].values[np.abs(self.df[param1].values - param1_val).argmin()]
        result = self.df.loc[self.df[param1] == closest_value, param2].values[0]
        return result

    def check_if_param_exists(self, param):
        if param in self.df.columns:
            return True
        else:
            return False

    def get_max_val_for_param(self, param):
        if not self.check_if_param_exists(param):
            return None
        max_value = self.df[param].max()
        # get the row number of the maximum value
        row_number = self.df.loc[self.df[param] == max_value].index[0]
        return max_value, row_number

    def get_min_val_for_param(self, param):
        if not self.check_if_param_exists(param):
            return None
        min_value = self.df[param].min()
        # get the row number of the minimum value
        row_number = self.df.loc[self.df[param] == min_value].index[0]
        return min_value, row_number

    def take_deriv_for_param(self, param):
        if not self.check_if_param_exists(param):
            return None
        deriv = self.df[param].diff()
        return deriv

    def get_param_values(self, param):
        if not self.check_if_param_exists(param):
            return None
        vals = self.df[param].values
        return vals

    def current_as_function_of_kgm(self, gbw, cload, beta_factor=1, c_coeff=[1, 1, 1], show_plot=False, new_plot=True, ax1=None, fig1=None, color="blue", kcgd_col=None, legend_str=""):
        legend_str = "PDK: " + self.pdk + ", L: " + str(self.length) + ", corner: " + self.corner_name
        graph_data_x = []
        graph_data_y = []
        #graph = show_plot
        min_ids = 1000000000
        kgm_col  = self.df["kgm"]
        cgg_col = self.df["cgg"]
        #if kcgd_col == None:
        #    kcgd_col = self.df["kcgd"]
        kcgd_col = self.df["kcgd"]
        kcgs_col = self.df["kcgs"]
        kcds_col = self.df["kcds"]
        ids_col = self.df["ids"]
        kgm_opt = 0
        for i in range(len(kgm_col)):
            kcgd = kcgd_col[i]*c_coeff[0]
            kcgs = kcgs_col[i]*c_coeff[1]
            kcds = kcds_col[i]*c_coeff[2]
            kgm = kgm_col[i]
            strong_inv = 2*math.pi*gbw*cload/(kgm*beta_factor)
            weak_inv = 1/(1 - (2*math.pi*gbw*(kcgd + kcgs + kcds))/kgm)
            ids = strong_inv*weak_inv
            if ids >= 0:
                graph_data_y.append(ids)
                graph_data_x.append(kgm)
            if ids <= min_ids and ids > 0:
                min_ids = ids
                kgm_opt = kgm
        if show_plot:
            if new_plot:
                fig1, ax1 = plt.subplots()
                plt.plot(graph_data_x, graph_data_y, color=color, label=legend_str)
                if show_plot == True:
                    plt.show()
            else:
                ax1.plot(graph_data_x, graph_data_y, color=color, label=legend_str)
            ax1.set_xlabel("kgm")
            ax1.set_ylabel("id")
            ax1.set_title(self.pdk + " GBW = " + str(gbw) + " CLoad = " + str(cload))
            legend = ax1.legend()
            #legend = ax1.legend(bbox_to_anchor=(1.0, 0.5), loc="center left", fontsize='small')
        return min_ids, kgm_opt, ax1, fig1


    def magic_equation(self, gbw, cload, beta_scale=1, show_plot=False, new_plot=True, ax1=None, fig1=None, color="blue", kcgd_col=None, legend_str=""):
        legend_str = "PDK: " + self.pdk + ", L: " + str(self.length) + ", corner: " + self.corner_name
        graph_data_x = []
        graph_data_y = []
        #graph = show_plot
        min_ids = 1000000000
        kgm_col  = self.df["kgm"]
        cgg_col = self.df["cgg"]
        if kcgd_col == None:
            kcgd_col = self.df["kcgd"]
        ids_col = self.df["ids"]
        kgm_opt = 0
        for i in range(len(kgm_col)):
            kcgd = kcgd_col[i]
            kgm = kgm_col[i]
            strong_inv = 2*math.pi*gbw*cload/kgm
            weak_inv = 1/(1 - (2*math.pi*gbw*kcgd)/kgm)
            ids = strong_inv*weak_inv
            if ids >= 0:
                graph_data_y.append(ids)
                graph_data_x.append(kgm)
            if ids <= min_ids and ids > 0:
                min_ids = ids
                kgm_opt = kgm
        if show_plot:
            if new_plot:
                fig1, ax1 = plt.subplots()
                plt.plot(graph_data_x, graph_data_y, color=color, label=legend_str)
                if show_plot == True:
                    plt.show()
            else:
                ax1.plot(graph_data_x, graph_data_y, color=color, label=legend_str)
            ax1.set_xlabel("kgm")
            ax1.set_ylabel("id")
            ax1.set_title(self.pdk + " GBW = " + str(gbw) + " CLoad = " + str(cload))
            legend = ax1.legend()
            #legend = ax1.legend(bbox_to_anchor=(1.0, 0.5), loc="center left", fontsize='small')
        return min_ids, kgm_opt, ax1, fig1

    def evaluate_magic_function(self, gbw, cload, kgm, kcgd_col=None):
        min_ids = 1000000000
        kgm_col  = self.df["kgm"]
        cgg_col = self.df["cgg"]
        if kcgd_col == None:
            kcgd_col = self.df["kcgd"]
        closest_kgm, index = self.get_closest_param_in_df("kgm", kgm)
        kcgd = kcgd_col[index]
        kgm = kgm_col[index]
        strong_inv = 2*math.pi*gbw*cload/kgm
        weak_inv = 1/(1 - (2*math.pi*gbw*kcgd)/kgm)
        ids = strong_inv*weak_inv
        return ids


    def plot_processes_params(self, param1, param2, param3=None, norm_type="", show_plot=True, new_plot=True, fig1=None, ax1=None, color=None,
                              legend_str=None, show_legend=True, enable_3d=False):
        color_list = ['r-', 'b-', 'g-', 'c-', 'm-', 'y-', 'k-']
        color_list_length = len(color_list)
        color_index = 0
        if new_plot == True:
            fig1, ax1 = plt.subplots()
        lines = []
        params3_all = []
        if enable_3d and param3 != None:
            params3_all = self.df[param3]
        else:
            params3_all = self.df[param1]
        params1_all = self.df[param1]
        params2_all = self.df[param2]

        kgm_col = self.df["kgm"]
        params1 = []
        params2 = []
        params3 = []
        for i in range(len(params1_all)):
            kgm_col_i = kgm_col[i]
            if kgm_col_i > 0.5 and kgm_col_i < 40:
                params1.append(params1_all[i])
                params2.append(params2_all[i])
                params3.append(params3_all[i])
        params1_normalized = []
        params2_normalized = []
        params3_normalized = []
        params1_max = 0
        for num in params1:
            if num >= params1_max:
                params1_max = num
        params1_min = params1_max
        for num in params1:
            if num <= params1_min:
                params1_min = num
        params2_max = 0
        for num in params2:
            if num >= params2_max:
                params2_max = num
        params2_min = params2_max
        for num in params2:
            if num <= params2_min:
                params2_min = num
        params3_max = 0
        for num in params3:
            if num >= params3_max:
                params3_max = num
        params3_min = params3_max
        for num in params3:
            if num <= params3_min:
                params3_min = num


        for num in params1:
            params1_normalized.append((num - params1_min) / (params1_max - params1_min))
        for num in params2:
            params2_normalized.append((num - params2_min) / (params2_max - params2_min))
        for num in params3:
            params3_normalized.append((num - params3_min) / (params3_max - params3_min))
        color_string = ""
        if color == None:
            color = color_list[color_index]
        if (norm_type == "xnorm"):
            ax1.plot(params1_normalized, params2, color, label=legend_str)
            lines.append(params1_normalized)
            lines.append(params2)
        elif (norm_type == "ynorm"):
            ax1.plot(params1, params2_normalized, color, label=legend_str)
            lines.append(params1)
            lines.append(params2_normalized)
        elif (norm_type == "norm"):
            ax1.plot(params1_normalized, params2_normalized, color, label=legend_str)
            lines.append(params1_normalized)
            lines.append(params2_normalized)
        else:
            if enable_3d == False:
                ax1.plot(params1, params2, color, label=legend_str)
                lines.append(params1)
                lines.append(params2)
            else:
                print("TODO")
        if(color_index == color_list_length - 1):
            color_index = 0
        else:
            color_index = color_index + 1

        ax1.set_xlabel(param1)
        ax1.set_ylabel(param2)
        graph_title_string = self.pdk + " " + param2 + " vs " + param1
        ax1.set_title(graph_title_string)
        if show_plot == True:
            plt.grid(True)
        #legend = ax1.legend(bbox_to_anchor=(1.0, 0.5), loc="center left", fontsize='small')
        if show_legend:
            legend = ax1.legend()
            lined = {}
            for legline, origline in zip(legend.get_lines(), lines):
                legline.set_picker(True)
                lined[legline] = origline
        #fig1.canvas.mpl_connect('pick_event', self.on_pick)
        if show_plot == True:
            plt.subplots_adjust(right=0.7)
        if(show_plot == True):
            plt.show()
        return((fig1, ax1))
