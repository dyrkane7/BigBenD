# -*- coding: utf-8 -*-
"""
Created on Weds June 21 20:29:49 2023

@author: dkane
"""

"""
BigBend wafers are tested in 3 passes

Post-processing steps:
1) Update x,y coordinates of 3 STDF files 
2) Merge 3 STDF files into single STDF file
3) Screen CAV1TOPS and CAV2TOPS results in merged STDF file
4) Generate SINF format wafer map based on screened and merged STDF

"""


import os
import glob
import re
from datetime import datetime
from datetime import timedelta

from tkinter import filedialog
from Semi_ATE.STDF import utils

from stdf_file import STDFFile
from stdf_update_xy import stdf_update_xy 
from stdf_merge_v4 import stdf_merge
from bigbend_stdf_to_sinf import stdf_to_sinf
from bigbend_screen_outliers import screen_outliers

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
            sblot_opt = [f"PASS {pass_num}", f"PASS{pass_num}", f"Pass{pass_num}"]
            assert sblot_id in sblot_opt, \
                f"expected sublot id of MIR to be 'PASS {pass_num}', found {sblot_id}"
            return 
    raise Exception(f"Could not find MIR in stdf: {basename}")

def compare_wafer_id(fp_list):
    ids = []
    for fp in fp_list:
        fn = os.path.basename(fp)
        splits = fn.split('-')
        id_ = splits[0] + '-' + splits[1][2:4]
        ids.append(id_)
    assert all([id_ == ids[0] for id_ in ids])
    
def log_yield_to_summary_file(stdf_fp, summary_fp, debug=True):
    if debug:
        print("stdf_fp: ", stdf_fp)
        print("summary_fp: ", summary_fp)
    stdf = STDFFile(stdf_fp)
    total_part_cnt = stdf.get_total_part_cnt()
    pass_part_cnt = stdf.get_pass_part_cnt()
    percent_yield = 100 * (pass_part_cnt / total_part_cnt)
    
    # get lot# and wafer#
    offset = stdf.index['records']['WIR'][0]
    rec = stdf.index['indexes'][offset][0]
    rec_obj = utils.create_record_object(stdf.index['version'], stdf.index['endian'], 'WIR', rec)
    wafer_id = rec_obj.get_fields('WAFER_ID')[3]
    if debug:
        print("wafer_id from stdf: ", wafer_id)
    if '-' in wafer_id:
        wafer_number = wafer_id.split('-')[1][2:4]
        lot_id = wafer_id.split('-')[0]
    elif '.' in wafer_id:
        wafer_number = wafer_id.split('.')[1][2:4]
        lot_id = wafer_id.split('.')[0]
    else:
        raise Exception(f"Did not find expected delimiter in wafer ID. Expected '-' or '.'. Wafer ID: {wafer_id}")
        
    
    if not os.path.exists(summary_fp):
        with open(summary_fp, 'a') as f:
            f.write('Lot ID,Wafer ID,Yield\n')
    with open(summary_fp, 'a') as f:
        f.write(f'{lot_id},{wafer_number.zfill(2)},{percent_yield:.2f}%\n')
    

def bigbend_stdf_post_process(
        update_xy_p1 = update_xy_p1,
        update_xy_p2 = update_xy_p2,
        update_xy_p3 = update_xy_p3,
        stdf_fp_p1 = "", 
        stdf_fp_p2 = "",
        stdf_fp_p3 = "",
        is_verify_pass_num = True
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
        if is_verify_pass_num:
            verify_pass_num(fp, pass_num)
        fp_list[pass_num - 1] = fp
    
    compare_wafer_id(fp_list)

    rev1_fp_list = []
    for fp, helper in zip(fp_list, helper_list):
        rev1_fp = stdf_update_xy(helper, fp)
        rev1_fp_list.append(rev1_fp)
        
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
    
    # screened_stdf_fp = screen_outliers(new_stdf_fp, plot_distribution=True, gen_atdf=True)
    screened_stdf_fp = screen_outliers(new_stdf_fp, plot_distribution=True, gen_atdf=True)
    
    os.remove(new_stdf_fp)
    
    # create filepath for yield summary file
    lot_id = os.path.basename(screened_stdf_fp).split('-')[0]
    dirname = os.path.dirname(screened_stdf_fp)
    print("lot_id of summary file:", lot_id)
    summary_fp = os.path.join(dirname, lot_id + '_merged_screened_yield_summary.csv')
    
    log_yield_to_summary_file(screened_stdf_fp, summary_fp)
    
    stdf_to_sinf(screened_stdf_fp)


if __name__ == "__main__":
    dt0 = datetime.now()
    
    # fp_p1 = r"C:/Users/dkane/OneDrive - Presto Engineering/Documents/Integra-Job/Cisco/BigBend/Stdf/test 3-pass merge/5AIX5202_DUMMY-P106.std"
    # fp_p2 = r"C:/Users/dkane/OneDrive - Presto Engineering/Documents/Integra-Job/Cisco/BigBend/Stdf/test 3-pass merge/5AIX5202_DUMMY-P206.std"
    # fp_p3 = r"C:/Users/dkane/OneDrive - Presto Engineering/Documents/Integra-Job/Cisco/BigBend/Stdf/test 3-pass merge/5AIX5202_DUMMY-P306.std"
    
    # for wafer_num in [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]:
    # base_path = r"C:/Users/dkane/OneDrive - Presto Engineering/Documents/Integra-Job/Cisco/BigBend/Cisco BigBenD SiNx PC Correlation/PCV1 vs PCV2 SAIW3301 W02 W03 3-pass 9-13-2023/PCV1"
    # for wafer_num in [2,3]:
    #     fp_p1 = rf"{base_path}/5AIW3301-P1{str(wafer_num).zfill(2)}_072823.std"
    #     fp_p2 = rf"{base_path}/5AIW3301-P2{str(wafer_num).zfill(2)}_072823.std"
    #     fp_p3 = rf"{base_path}/5AIW3301-P3{str(wafer_num).zfill(2)}_072823.std"
        
    #     bigbend_stdf_post_process(stdf_fp_p1=fp_p1, stdf_fp_p2=fp_p2, stdf_fp_p3=fp_p3)

    # ~~~~~~~~~~~~~ User Config ~~~~~~~~~~~~~~~~~~~~
    base_path = r"C:/Users/dkane/OneDrive - Presto Engineering/Documents/Integra-Job/Cisco/BigBend/Lot 5AIY2001/216891-1-1_5A1Y2001.1_stdf_files"
    lot_num = "5A1Y2001"
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    p1_fp_list = glob.glob(os.path.join(base_path, f"{lot_num}-P1*.std"))
    
    print(f"(DEBUG) found {len(p1_fp_list)} pass 1 stdf files")
    
    for p1_fp in p1_fp_list:
        p1_fn = os.path.basename(p1_fp)
        wafer_num = p1_fn.split(f'{lot_num}-P1')[1][:2]
        
        p2_match_fp_list = glob.glob(os.path.join(base_path, f"{lot_num}-P2{wafer_num}*.std"))
        p3_match_fp_list = glob.glob(os.path.join(base_path, f"{lot_num}-P3{wafer_num}*.std"))

        assert len(p2_match_fp_list) == 1, f"Expected exactly one match file for P2 Wafer# {wafer_num}. Found {len(p2_match_fp_list)}"
        assert len(p3_match_fp_list) == 1, f"Expected exactly one match file for P3 Wafer# {wafer_num}. Found {len(p3_match_fp_list)}"
        
        p2_fp = p2_match_fp_list[0]
        p3_fp = p3_match_fp_list[0]
        
        bigbend_stdf_post_process(stdf_fp_p1=p1_fp, stdf_fp_p2=p2_fp, stdf_fp_p3=p3_fp, is_verify_pass_num = True)

    dt1 = datetime.now()
    delta = timedelta()
    delta = dt1 - dt0
    
    print("End time: ", dt1)
    print("Elapsed time: ", delta)
    
    
