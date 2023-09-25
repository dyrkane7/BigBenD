# -*- coding: utf-8 -*-
"""
Created on Thu Jun  1 14:07:26 2023

@author: dkane
"""
import os

from Semi_ATE.STDF import utils
from tkinter import filedialog

# TODO: !!! This module needs to be updated to work generally, currently only works for Cisco BigBend spec change (6/2/2023)

def is_pass(part_flag):
    assert part_flag[-5] == '0', "part flag pass/fail bit is invalid"
    if part_flag[-4] == '0': 
        return True
    else:
        return False

'''
    Change spec limits and re-bin dies.
    Dies that switched fail->pass for one test and failed no other tests switch to bin 1
    Dies that switched fail->pass for any test(s) but failed other tests don't change bin #
    update PTR P/F status and limits
    update PRR P/F status and sbin/hbin numbers
    
    TODO: update good_bin count
    TODO: update hw/sw bin counts
    
    new_specs: new spec limits to bin against
        ex. {<param_name> : {"hilim" : <hilim>, "lolim" : <lolim>, "hispec" : <hispec>, "lospec" : <lospec>}, ...}
    tnum2bin: mapping of test name to bin name/num
        ex. {<test_name> : {"bin_num" : <bin_num>, "bin_name" : <bin_name>}, ...}
'''

def stdf_spec_screen(new_specs, fp = ""):
    if fp == "":
        fp = filedialog.askopenfilenames()
    assert os.path.isfile(fp), "the file does not exist:\n{}".format(fp)
    assert utils.is_STDF(fp), "the file is not stdf file:\n{}".format(fp)
    
    endian, version = utils.endian_and_version_from_file(fp)
    id_ts_dict = utils.id_to_ts()
    part_i = 0
    # PIP = False # part in progress
    is_fail = False
    # flip_part_dict = {} # {<rec_index> : {}}
    change_rec_index = {} # keys: indeces of records to update
                          # values: dict of {<param> : new_value>} pairs
    for i, rec in enumerate(utils.check_records_from_file(fp)):
        rec_len, rec_type, rec_sub, raw_bytes = rec
        if (rec_type,rec_sub) == id_ts_dict["PIR"]:
            part_i += 1
            # PIP = True
            is_fail = False
            # FTP_tests = []
            # FTF_tests = []
        elif (rec_type,rec_sub) == id_ts_dict["FTR"]:
            rec_obj = utils.create_record_object(version, endian, "FTR", raw_bytes)
            if int(rec_obj.get_fields("TEST_FLG")[3][0]):
                is_fail = True
        elif (rec_type,rec_sub) == id_ts_dict["PTR"]:
            rec_obj = utils.create_record_object(version, endian, "PTR", raw_bytes)
            test_text = rec_obj.get_fields("TEST_TXT")[3]
            if test_text in new_specs:
                change_rec_index[i] = {"REC_ID" : "PTR", "params" : {}}
                # TODO: check if missing data for HI_LIMIT/LO_LIMIT/HI_SPEC/LO_SPEC,
                #       update HI_LIMIT/LO_LIMIT/HI_SPEC/LO_SPEC only if data is not missing
                if "lospec" in new_specs[test_text]:
                    change_rec_index[i]["params"]["LO_SPEC"] = new_specs[test_text]["lospec"]
                if "hispec" in new_specs[test_text]:
                    change_rec_index[i]["params"]["HI_SPEC"] = new_specs[test_text]["hispec"]
                if "lolim" in new_specs[test_text]:
                    lolim = new_specs[test_text]["lolim"]
                    change_rec_index[i]["params"]["LO_LIMIT"] = lolim
                else:
                    lolim = rec_obj.get_fields("LO_LIMIT")[3]
                if "hilim" in new_specs[test_text]:
                    hilim = new_specs[test_text]["hilim"]
                    change_rec_index[i]["params"]["HI_LIMIT"] = hilim
                else:
                    hilim = rec_obj.get_fields("HI_LIMIT")[3]
                # assume fail criteria is result > hilim or result < lolim
                # TODO update PARM_FLG bits 3 and 4 to indicate if fail result is high (bit3 = 1) or low (bit4 = 1)
                result = rec_obj.get_fields("RESULT")[3]
                if result > hilim or result < lolim:
                    # change_rec_index[i]["params"]["is_fail"] = True
                    is_fail = True
                # else:
                #     change_rec_index[i]["params"]["is_fail"] = False
            else:
                if int(rec_obj.get_fields("TEST_FLG")[3][0]):
                    is_fail = True
                
        elif (rec_type,rec_sub) == id_ts_dict["PRR"]:
            rec_obj = utils.create_record_object(version, endian, "PRR", raw_bytes)
            part_flag = rec_obj.get_fields("PART_FLG")[3]
            prr_is_fail = not is_pass(part_flag)
            if is_fail != prr_is_fail: # need to update pass/fail status and bin#
                print("found PRR to udpate")
                change_rec_index[i] = {"REC_ID" : "PRR", "params" : {}}
                # change_rec_index[i]["params"]["is_fail"] = prr_is_fail
                if not prr_is_fail:
                    print("prr_is_fail")
                    # TODO: make bin# update work generally; below code is specifici to CISCO BigBend spec change
                    change_rec_index[i]["params"]["HARD_BIN"] = 4
                    change_rec_index[i]["params"]["SOFT_BIN"] = 4
    # print(change_rec_index)
    fp_no_ext = os.path.splitext(fp)[0]
    temp_stdf_fp = fp_no_ext + "_TEMP.stdf"
    print(temp_stdf_fp)
    with open(temp_stdf_fp, 'wb') as temp_stdf:
        for i, rec in enumerate(utils.check_records_from_file(fp)):
            rec_len, rec_type, rec_sub, raw_bytes = rec
            if i in change_rec_index:
                REC_ID = change_rec_index[i]["REC_ID"]
                rec_obj = utils.create_record_object(version, endian, REC_ID, raw_bytes)
                for param, val in change_rec_index[i]["params"].items():
                    rec_obj.set_value(param, val)
                raw_bytes = rec_obj.__repr__()
            temp_stdf.write(raw_bytes)
                    

            

if __name__ == "__main__":
    fp_list = [r"C:/Users/dkane/OneDrive - Presto Engineering/Documents/Integra-Job/Cisco/BigBend/Stdf/5AIX5202-06_MERGED.stdf"]
    
    new_specs = {
        "TOPS_Res_TEST CAV2TOPS" : {"hilim" : 390, "hispec" : 390, "hbin" : 4, "sbin" : 4},
        "TOPS_Res_TEST CAV1TOPS" : {"hilim" : 390, "hispec" : 390, "hbin" : 4, "sbin" : 4}
    }
    
    for fp in fp_list:
        stdf_spec_screen(new_specs, fp)
        # stdf_spec_screen(new_specs, tnum2bin)
    