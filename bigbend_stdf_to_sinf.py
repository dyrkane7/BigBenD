# -*- coding: utf-8 -*-
"""
Created on Thu May 18 14:50:21 2023

@author: dkane
"""

'''
Change Log:
    [6/15/2023] Hardcode wmap_dict["FNLOC"] = "0" instead of reading flat location from WCR
    [6/21/2023] Swap ROWCT and COLCT calculations.
'''

import os

from Semi_ATE.STDF import utils
from tkinter import filedialog

def stdf_to_sinf(stdf_fp = "", debug=False):
    if stdf_fp == "":
        stdf_fp = filedialog.askopenfilename()
        
    stdf_fp = os.path.abspath(stdf_fp)
    stdf_fn = os.path.basename(stdf_fp)
    stdf_dir = os.path.dirname(stdf_fp)
    if debug:
        print("stdf file name:", stdf_fn)
        print("stdf directory:", stdf_dir)
    
    assert os.path.isfile(stdf_fp), "the file does not exist:\n{}".format(stdf_fp)
    assert utils.is_STDF(stdf_fp), "the file is not stdf file:\n{}".format(stdf_fp)
    endian, version = utils.endian_and_version_from_file(stdf_fp)
    
    wmap_dict = {
        "header": {
            "DEVICE" : "", "LOT" : "", "Wafer" : "",
            "FNLOC" : "0", "ROWCT" : "", "COLCT" : "",
            "BCEQU" : "", 
            "REFPX" : "0", "REFPY" : "0",
            "DUTMS" : "mm", "XDIES" : "2", "YDIES" : "1.8"
        },
        "bins" : {}, # (x,y) keys, bin# values
        "bin_cnts" : {}, # bin# keys, bin count values
    }
    good_sbin_nums = []
    id_ts_dict = utils.id_to_ts()
    for rec in utils.check_records_from_file(stdf_fp):
        _, rec_type, rec_sub, raw_bytes = rec
        # if (rec_type, rec_sub) == id_ts_dict["WCR"]:
        #     wf_flat_opt = {"U":"0","D":"180","L":"270","R":"90"}
        #     rec_obj = utils.create_record_object(version, endian, "WCR", raw_bytes)
        #     wmap_dict["header"]["FNLOC"] = wf_flat_opt[rec_obj.get_fields("WF_FLAT")[3]]
        #     print(rec_obj)
        if (rec_type, rec_sub) == id_ts_dict["WIR"]:
            rec_obj = utils.create_record_object(version, endian, "WIR", raw_bytes)
            temp = rec_obj.get_fields("WAFER_ID")[3]
            if '-' in temp:
                splits = temp.split('-')
            elif '.' in temp:
                splits = temp.split('.')
            wmap_dict["header"]["Wafer"] = splits[0] + '-' + splits[1][2:].zfill(2)
            # print(rec_obj)
        elif (rec_type, rec_sub) == id_ts_dict["MIR"]:
            rec_obj = utils.create_record_object(version, endian, "MIR", raw_bytes)
            wmap_dict["header"]["DEVICE"] = rec_obj.get_fields("PART_TYP")[3]
            temp = rec_obj.get_fields("LOT_ID")[3]
            wmap_dict["header"]["LOT"] = temp.split('-')[0]
            # print(rec_obj)
        elif (rec_type,rec_sub) == id_ts_dict["PRR"]:
            rec_obj = utils.create_record_object(version, endian, "PRR", raw_bytes)
            x = rec_obj.get_fields('X_COORD')[3]
            y = rec_obj.get_fields('Y_COORD')[3]
            soft_bin = rec_obj.get_fields('SOFT_BIN')[3]
            wmap_dict["bins"][(x,y)] = soft_bin
            if soft_bin not in wmap_dict["bin_cnts"]:
                wmap_dict["bin_cnts"][soft_bin] = 0
            wmap_dict["bin_cnts"][soft_bin] += 1
        elif (rec_type,rec_sub) == id_ts_dict["SBR"]:
            rec_obj = utils.create_record_object(version, endian, "SBR", raw_bytes)
            sbin_pf = rec_obj.get_fields('SBIN_PF')[3]
            sbin_num = rec_obj.get_fields('SBIN_NUM')[3]
            if sbin_pf == "P" and sbin_num not in good_sbin_nums:
                good_sbin_nums.append(sbin_num)
                    
    # x_min = min([x for (x,y) in wmap_dict["bins"]])
    x_max = max([x for (x,y) in wmap_dict["bins"]])
    # y_min = min([y for (x,y) in wmap_dict["bins"]])
    y_max = max([y for (x,y) in wmap_dict["bins"]])
    wmap_dict["header"]["ROWCT"] = str(y_max + 1)
    wmap_dict["header"]["COLCT"] = str(x_max + 1)
    wmap_dict["header"]["BCEQU"] = ",".join([str(num).zfill(2) for num in good_sbin_nums])
    
    fp_wo_ext = os.path.splitext(stdf_fp)[0]
    txt_fp = fp_wo_ext + '_MAP.txt'
    
    with open(txt_fp, 'w') as txt_file:
        for key, val in wmap_dict["header"].items():
            txt_file.write(key + ": " + val + "\n")
        for y in range(y_max+1):
            row = "RowData:"
            for x in range(x_max+1):
                if (x,y) in wmap_dict["bins"]:
                    bin_num = wmap_dict["bins"][(x,y)]
                    row += (" " + str(bin_num).zfill(2)) # changed from "zfill(3)" to "zfill(2)" on 7/20/2023
                else:
                    row += " __" # changed from " ___" to " __" on 7/20/2023
            txt_file.write(row + "\n")
        for key, val in wmap_dict["bin_cnts"].items():
            txt_file.write("Bin_" + str(key) + ": " + str(val) + "\n")
        if debug:
            print(wmap_dict["header"])
    
if __name__ == "__main__":
    fp = r"C:/Users/dkane/OneDrive - Presto Engineering/Documents/Integra-Job/Cisco/BigBend/Stdf/5AIX5202-03_MERGED_TEMP.stdf"
    stdf_to_sinf(fp, debug=True)


