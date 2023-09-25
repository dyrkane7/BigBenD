# -*- coding: utf-8 -*-
"""
Created on Weds June 21 20:29:49 2023

@author: dkane
"""

"""
BigBend wafers are tested in 3 passes

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

# I3 and I4 dies
def update_xy_p1(x,y):
    ret_x = x*5 + 4
    ret_y = y*8 + 2
    return ret_x, ret_y

# I1 and J1 dies
def update_xy_p2(x,y):
    if x % 2: # if odd
        ret_x = x*5 + 4
    else:     # if even
        ret_x = x*5
    ret_y = y*8 + 6
    return ret_x, ret_y

# I2 and J2 dies
def update_xy_p3(x,y):
    if x % 2: # if odd
        ret_x = x*5
    else:     # if even
        ret_x = x*5 + 4
    ret_y = y*8 + 6
    return ret_x, ret_y

# pass num is integer - supported values are 1,2,3
# Cisco BigBenD wafers are tested in 3 passes (as of 6/23/2023)
def verify_pass_num(fp, pass_num):
    basename = os.path.basename(fp)
    fn_pass_num = basename.split('-')[1][:2]
    assert fn_pass_num == f"P{pass_num}", f"expected filename ({basename}) to contain 'P{pass_num}' (pass_num = {pass_num})"
    
    endian, version = utils.endian_and_version_from_file(fp)
    id_ts_dict = utils.id_to_ts()
    for rec in utils.check_records_from_file(fp):
        _, rec_type, rec_sub, raw_bytes = rec
        if (rec_type, rec_sub) == id_ts_dict["MIR"]:
            rec_obj = utils.create_record_object(version, endian, "MIR", raw_bytes)
            sblot_id = rec_obj.get_fields("SBLOT_ID")[3]
            assert sblot_id == f"PASS {pass_num}", f"expected sublot id of MIR to be 'PASS {pass_num}', found {sblot_id}"
            return 
    raise Exception(f"Could not find MIR in stdf: {basename}")

# def check_stdf_fp(fp, pass):
#     fp = os.path.abspath(fp)
#     assert os.path.isfile(stdf_fp_p1), f"the file does not exist:\n{stdf_fp_p1}"
#     assert utils.is_STDF(stdf_fp_p1), f"the file is not stdf file:\n{stdf_fp_p1}"
#     stdf_fn_p1 = os.path.basename(stdf_fp_p1)
#     assert '-P1' in stdf_fn_p1, "Expected pass 1 stdf filename to contain '-P1'"
#     print("pass1 stdf:", os.path.basename(stdf_fp_p1))
#     verify_pass_num(stdf_fp_p1)

# def compare_wafer_id(fp1, fp2):
#     fp1_basename = os.path.basename(fp1)
#     fp2_basename = os.path.basename(fp2)
#     splits = fp1_basename.split('-')
#     fp1_wafer_id = splits[0] + '-' + splits[1][2:]
#     splits = fp2_basename.split('-')
#     fp2_wafer_id = splits[0] + '-' + splits[1][2:]
#     assert fp1_wafer_id == fp2_wafer_id, f"file name wafer ID's do not match: {fp1_basename} != {fp2_basename}"
    
def compare_wafer_id(fp_list):
    ids = []
    for fp in fp_list:
        fn = os.path.basename(fp)
        splits = fn.split('-')
        id_ = splits[0] + '-' + splits[1][2:]
        ids.append(id_)
    assert all([id_ == ids[0] for id_ in ids])

def bigbend_stdf_post_process(
        update_xy_p1 = update_xy_p1,
        update_xy_p2 = update_xy_p2,
        update_xy_p3 = update_xy_p3,
        stdf_fp_p1 = "", 
        stdf_fp_p2 = "",
        stdf_fp_p3 = "",
):
    helper_list = [update_xy_p1, update_xy_p2, update_xy_p3]
    fp_list = [stdf_fp_p1, stdf_fp_p2, stdf_fp_p3]
    
    for pass_num, fp in enumerate(fp_list, 1):
        if fp == "":
            fp = filedialog.askopenfilename(title = f"Select pass {pass_num} stdf")
            
        fp = os.path.abspath(fp)
        assert os.path.isfile(fp), f"the file does not exist:\n{fp}"
        assert utils.is_STDF(fp), f"the file is not stdf file:\n{fp}"
        print(f"pass {pass_num} stdf:", os.path.basename(fp))
        verify_pass_num(fp, pass_num)
        fp_list[pass_num - 1] = fp
    
    compare_wafer_id(fp_list)

    rev1_fp_list = []
    for fp, helper in zip(fp_list, helper_list):
        rev1_fp = stdf_update_xy(helper, fp)
        assert rev1_fp != fp, f"rev1 file name matches original file name: {fp}"
        rev1_fp_list.append(rev1_fp)
        
    # stdf_fp_p1_rev1 = stdf_update_xy(update_xy_p1, stdf_fp_p1)
    # stdf_fp_p2_rev1 = stdf_update_xy(update_xy_p2, stdf_fp_p2)
    # assert stdf_fp_p1_rev1 != stdf_fp_p1, "p1 rev1 file name matches original file name"
    # assert stdf_fp_p2_rev1 != stdf_fp_p2, "p2 rev1 file name matches original file name"
    
    # fp_list = [stdf_fp_p1_rev1, stdf_fp_p2_rev1]
    
    stdf_fp = stdf_merge(rev1_fp_list, skip_fn_checks=True)
    
    # remove intermediate stdf files
    for fp in rev1_fp_list:
        os.remove(fp)

    # rename stdf file
    stdf_dirname = os.path.dirname(stdf_fp)
    stdf_basename = os.path.basename(stdf_fp)
    splits = stdf_basename.split('-', 1)
    temp = splits[0] + '-' + splits[1][2:]
    temp = temp.split('_', 1)[0]
    temp += "_MERGED_3X.stdf"
    new_stdf_fp = os.path.join(stdf_dirname, temp)
    os.rename(stdf_fp, new_stdf_fp)
    
    stdf_to_sinf(new_stdf_fp)


if __name__ == "__main__":
    fp_p1 = r"C:/Users/dkane/OneDrive - Presto Engineering/Documents/Integra-Job/Cisco/BigBend/Stdf/test 3-pass merge/5AIX5202_DUMMY-P106.std"
    fp_p2 = r"C:/Users/dkane/OneDrive - Presto Engineering/Documents/Integra-Job/Cisco/BigBend/Stdf/test 3-pass merge/5AIX5202_DUMMY-P206.std"
    fp_p3 = r"C:/Users/dkane/OneDrive - Presto Engineering/Documents/Integra-Job/Cisco/BigBend/Stdf/test 3-pass merge/5AIX5202_DUMMY-P306.std"
    
    # bigbend_stdf_post_process()
    bigbend_stdf_post_process(stdf_fp_p1=fp_p1, stdf_fp_p2=fp_p2, stdf_fp_p3=fp_p3)
    
    
