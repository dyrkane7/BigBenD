# -*- coding: utf-8 -*-
"""
Created on Mon May 15 20:29:49 2023

@author: dkane
"""

"""
BigBend wafers are tested in 2 passes

"""


import os

from tkinter import filedialog
from Semi_ATE.STDF import utils

from stdf_update_xy import stdf_update_xy 
from stdf_merge_v4 import stdf_merge
from bigbend_stdf_to_sinf import stdf_to_sinf

# def update_xy_p1(x,y):
#     return x, 2*y

# def update_xy_p2(x,y):
#     return x, 2*y + 1

def update_xy_p1(x,y):
    ret_x = x*5 + 4
    ret_y = y*8 + 2
    return ret_x, ret_y

def update_xy_p2(x,y):
    if x % 2: # if odd
        ret_x = x*5 + 4
    else:     # if even
        ret_x = x*5
    ret_y = y*8 + 6
    return ret_x, ret_y

def verify_pass_num(fp):
    basename = os.path.basename(fp)
    endian, version = utils.endian_and_version_from_file(fp)
    id_ts_dict = utils.id_to_ts()
    for rec in utils.check_records_from_file(fp):
        _, rec_type, rec_sub, raw_bytes = rec
        if (rec_type, rec_sub) == id_ts_dict["MIR"]:
            rec_obj = utils.create_record_object(version, endian, "MIR", raw_bytes)
            sblot_id = rec_obj.get_fields("SBLOT_ID")[3]
            fn_pass_num = basename.split('-')[1][:2]
            if sblot_id == "PASS 1":
                assert fn_pass_num == "P1", f"pass# in filename ({fn_pass_num}) conflicts with pass # in sublot_id ({sblot_id})"
            elif sblot_id == "PASS 2":
                assert fn_pass_num == "P2", f"pass# in filename ({fn_pass_num}) conflicts with pass # in sublot_id ({sblot_id})"
            else:
                raise Exception("sublot_id does not match expected values of 'PASS 1' or 'PASS 2'")
            return 
    raise Exception(f"Could not find MIR in stdf: {basename}")

def compare_wafer_id(fp1, fp2):
    fp1_basename = os.path.basename(fp1)
    fp2_basename = os.path.basename(fp2)
    splits = fp1_basename.split('-')
    fp1_wafer_id = splits[0] + '-' + splits[1][2:]
    splits = fp2_basename.split('-')
    fp2_wafer_id = splits[0] + '-' + splits[1][2:]
    assert fp1_wafer_id == fp2_wafer_id, f"file name wafer ID's do not match: {fp1_basename} != {fp2_basename}"

def bigbend_stdf_post_process(
        update_xy_p1 = update_xy_p1,
        update_xy_p2 = update_xy_p2,
        stdf_fp_p1 = "", 
        stdf_fp_p2 = ""
):

    if stdf_fp_p1 == "":  
        stdf_fp_p1 = filedialog.askopenfilename(title = "Select pass 1 stdf")
        
    stdf_fp_p1 = os.path.abspath(stdf_fp_p1)
    assert os.path.isfile(stdf_fp_p1), f"the file does not exist:\n{stdf_fp_p1}"
    assert utils.is_STDF(stdf_fp_p1), f"the file is not stdf file:\n{stdf_fp_p1}"
    stdf_fn_p1 = os.path.basename(stdf_fp_p1)
    assert '-P1' in stdf_fn_p1, "Expected pass 1 stdf filename to contain '-P1'"
    print("pass1 stdf:", os.path.basename(stdf_fp_p1))
    verify_pass_num(stdf_fp_p1)
        
    if stdf_fp_p2 == "":  
        stdf_fp_p2 = filedialog.askopenfilename(title = "Select pass 2 stdf")
        
    stdf_fp_p2 = os.path.abspath(stdf_fp_p2)
    assert os.path.isfile(stdf_fp_p2), f"the file does not exist:\n{stdf_fp_p2}"
    assert utils.is_STDF(stdf_fp_p2), f"the file is not stdf file:\n{stdf_fp_p2}"
    stdf_fn_p2 = os.path.basename(stdf_fp_p2)
    assert '-P2' in stdf_fn_p2, "Expected pass 2 stdf filename to contain '-P2'"
    print("pass2 stdf:", os.path.basename(stdf_fp_p2))
    verify_pass_num(stdf_fp_p2)
    
    compare_wafer_id(stdf_fp_p1, stdf_fp_p2)

    stdf_fp_p1_rev1 = stdf_update_xy(update_xy_p1, stdf_fp_p1)
    stdf_fp_p2_rev1 = stdf_update_xy(update_xy_p2, stdf_fp_p2)
    assert stdf_fp_p1_rev1 != stdf_fp_p1, "p1 rev1 file name matches original file name"
    assert stdf_fp_p2_rev1 != stdf_fp_p2, "p2 rev1 file name matches original file name"
    
    fp_list = [stdf_fp_p1_rev1, stdf_fp_p2_rev1]
    stdf_fp = stdf_merge(fp_list, skip_fn_checks=True)
    
    # remove intermediate stdf files
    for fp in fp_list:
        os.remove(fp)

    # rename stdf file
    stdf_dirname = os.path.dirname(stdf_fp)
    stdf_basename = os.path.basename(stdf_fp)
    splits = stdf_basename.split('-', 1)
    temp = splits[0] + '-' + splits[1][2:]
    temp = temp.split('_', 1)[0]
    temp += "_MERGED.stdf"
    new_stdf_fp = os.path.join(stdf_dirname, temp)
    os.rename(stdf_fp, new_stdf_fp)
    
    stdf_to_sinf(new_stdf_fp)


if __name__ == "__main__":
    fp_p1 = r"C:/Users/dkane/OneDrive - Presto Engineering/Documents/Integra-Job/Cisco/BigBend/Stdf/5AIX5202-P106.std"
    fp_p2 = r"C:/Users/dkane/OneDrive - Presto Engineering/Documents/Integra-Job/Cisco/BigBend/Stdf/5AIX5202-P206.std"
    
    # bigbend_stdf_post_process()
    bigbend_stdf_post_process(stdf_fp_p1=fp_p1, stdf_fp_p2=fp_p2)
    
    
