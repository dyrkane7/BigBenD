# -*- coding: utf-8 -*-
"""
Created on Thu Jul 20 11:21:26 2023

@author: dkane
"""
import os

import numpy as np
import plotly.graph_objects as go
from Semi_ATE.STDF import utils
from tkinter import filedialog

from stdf_file import STDFFile
from stdf_to_atdf import stdf_to_atdf

# optionally plot distribution of CAV1TOPS and CAV2TOPS data
# calculate upper fence (inner and outer) and set outliers as fail

# CAV1TOPS/CAV2TOPS fail is bin 4

def screen_outliers(stdf_fp = "", plot_distribution=False, gen_atdf=False, debug=True):
    if stdf_fp == "":
        stdf_fp = filedialog.askopenfilename()
    
    assert os.path.isfile(stdf_fp), "the file does not exist:\n{}".format(stdf_fp)
    assert utils.is_STDF(stdf_fp), "the file is not stdf file:\n{}".format(stdf_fp)
    
    filename = os.path.basename(stdf_fp)
    if debug:
        print("file name:", filename)
    stdf = STDFFile(stdf_fp, progress = True)
    version = stdf.index['version']
    endian = stdf.index['endian']
    
    cav1tops_dict = {"results" : {}}
    cav2tops_dict = {"results" : {}}
    if debug:
        print("getting CAV1TOPS and CAV2TOPS results...")
    for index_list in stdf.index['parts'].values():
        x, y = None, None
        cav1tops_result, cav2tops_result = -1, -1
        
        for index in index_list:
            rec, rec_id = stdf.index['indexes'][index]
            if rec_id == "PRR":
                rec_obj = utils.create_record_object(version, endian, rec_id, rec)
                x = rec_obj.get_fields('X_COORD')[3]
                y = rec_obj.get_fields('Y_COORD')[3]
            elif rec_id == "PTR":
                ptr_fields = stdf._get_ptr_fields_from_raw_bytes(rec)
                test_nam = ptr_fields['TEST_TXT']
                if test_nam == "TOPS_Res_TEST CAV1TOPS":
                    cav1tops_result = ptr_fields['RESULT']
                elif test_nam == "TOPS_Res_TEST CAV2TOPS":
                    cav2tops_result = ptr_fields['RESULT']
                    
        assert x != None and y != None, "Couldn't find x,y for part sequence"
        if cav1tops_result != -1:
            cav1tops_dict["results"][(x,y)] = cav1tops_result
        if cav2tops_result != -1:
            cav2tops_dict["results"][(x,y)] = cav2tops_result
    
    
    cav1tops_dict["param_name"] = "TOPS_Res_TEST CAV1TOPS"        
    cav2tops_dict["param_name"] = "TOPS_Res_TEST CAV2TOPS"        
    cav1tops_dict["sample_cnt"] = len(cav1tops_dict["results"])        
    cav2tops_dict["sample_cnt"] = len(cav2tops_dict["results"])     
    if debug:
        print("cav1tops sample count:", len(cav1tops_dict["results"]))
        print("cav2tops sample count:", len(cav2tops_dict["results"])) 
        print("calculating upper fence...")
    for param_dict in (cav1tops_dict, cav2tops_dict):
        results_list = list(param_dict["results"].values())
        Q1 = np.percentile(results_list, 25)
        Q3 = np.percentile(results_list, 75)
        IQR = Q3 - Q1
        upper_inner_fence = Q3 + (1.5 * IQR)
        upper_outer_fence = Q3 + (3 * IQR)
        param_dict["UIF"] = upper_inner_fence
        param_dict["UOF"] = upper_outer_fence
        print(f"{param_dict['param_name']} upper inner fence {upper_inner_fence:.2f}")
        print(f"{param_dict['param_name']} upper outer fence {upper_outer_fence:.2f}")
    
    if debug:
        print("plotting distribution...")
    if plot_distribution == True:
        for param_dict in (cav1tops_dict, cav2tops_dict):
            results_list = list(param_dict["results"].values())
            results_sorted = sorted(results_list)
            fig = go.Figure(data=go.Scatter(x=None, y=results_sorted, mode='markers'))
            fig.add_trace(go.Scatter(x=[1,param_dict["sample_cnt"]],y=[param_dict["UIF"],param_dict["UIF"]],mode='lines',name='Upper inner fence'))
            fig.add_trace(go.Scatter(x=[1,param_dict["sample_cnt"]],y=[param_dict["UOF"],param_dict["UOF"]],mode='lines',name='Upper outer fence'))
            fig.update_layout(title=filename + " - " + param_dict['param_name'], xaxis_title='sample#', yaxis_title='Resistance (ohms)')
            fig.show(renderer="browser")
            
    if debug:
        print("updating PTR's...")
        
    # update high limit and pass/fail for all CAV1TOPS/CAV2TOPS PTR       
    for index_list in stdf.index['parts'].values():
        is_pass = True
        lolim = None
        for index in index_list:
            rec, rec_id = stdf.index['indexes'][index]
            if rec_id == "PTR":
                rec_obj = utils.create_record_object(version, endian, rec_id, rec)
                test_nam = rec_obj.get_fields('TEST_TXT')[3]
                test_flag = rec_obj.get_fields('TEST_FLG')[3]
                # if not stdf.is_test_pass(test_flag):
                #     is_pass = False
                
                if test_nam == "TOPS_Res_TEST CAV1TOPS":
                    cav1tops_result = rec_obj.get_fields('RESULT')[3]
                    hilim = rec_obj.get_fields('HI_LIMIT')[3]
                    lolim = rec_obj.get_fields('LO_LIMIT')[3]
                    assert lolim == 340, f"lolim = {lolim}, Expected 340 ohms"
                    assert hilim == 390, f"hilim = {hilim}, Expected 390 ohms"
                    # if rec_obj.get_fields('LO_LIMIT')[3] != None: # some STDF files only include limits in first PTR for a given test
                    #     lolim = rec_obj.get_fields('LO_LIMIT')[3]
                    if float(cav1tops_dict['UIF']) < hilim:
                        hilim = float(cav1tops_dict['UIF'])
                    if cav1tops_result > lolim and cav1tops_result < hilim:
                        test_flag = stdf.set_test_flag_pf_bit(test_flag, is_pass=True)
                    else:
                        is_pass = False
                        test_flag = stdf.set_test_flag_pf_bit(test_flag, is_pass=False)
                    rec_obj.set_value("TEST_FLG", test_flag)
                    rec_obj.set_value("HI_LIMIT", hilim)
                    rec = rec_obj.__repr__()
                    stdf.index['indexes'][index] = (rec, rec_id)
                elif test_nam == "TOPS_Res_TEST CAV2TOPS":
                    cav2tops_result = rec_obj.get_fields('RESULT')[3]
                    hilim = rec_obj.get_fields('HI_LIMIT')[3]
                    lolim = rec_obj.get_fields('LO_LIMIT')[3]
                    assert lolim == 340, f"lolim = {lolim}, Expected 340 ohms"
                    assert hilim == 390, f"hilim = {hilim}, Expected 390 ohms"
                    # if rec_obj.get_fields('LO_LIMIT')[3] != None: # some STDF files only include limits in first PTR for a given test
                    #     lolim = rec_obj.get_fields('LO_LIMIT')[3]
                    if float(cav2tops_dict['UIF']) < hilim:
                        hilim = float(cav2tops_dict['UIF'])
                    if cav2tops_result > lolim and cav2tops_result < hilim:
                        test_flag = stdf.set_test_flag_pf_bit(test_flag, is_pass=True)
                    else:
                        is_pass = False
                        test_flag = stdf.set_test_flag_pf_bit(test_flag, is_pass=False)
                    rec_obj.set_value("TEST_FLG", test_flag)
                    rec_obj.set_value("HI_LIMIT", hilim)
                    rec = rec_obj.__repr__()
                    stdf.index['indexes'][index] = (rec, rec_id)
                elif not stdf.is_test_pass(test_flag):
                    is_pass = False
                    
        # update PRR part flag pass/fail bit
        prr_index = index_list[-1] # PRR should be last record in part sequencee
        rec, rec_id = stdf.index['indexes'][prr_index]
        assert rec_id == 'PRR', f"Last record in part sequence should be PRR, found {rec_id}"
        rec_obj = utils.create_record_object(version, endian, rec_id, rec)
        part_flag = rec_obj.get_fields("PART_FLG")[3]
        x = rec_obj.get_fields("X_COORD")[3]
        y = rec_obj.get_fields("Y_COORD")[3]
        prescreen_sbin = rec_obj.get_fields("SOFT_BIN")[3]
        # print(f"(DEBUG) prescreen_sbin: {prescreen_sbin}, is_pass: {is_pass}")
        if prescreen_sbin != 1 and is_pass == True: # fail -> pass
            print(f"(DEBUG) [{x},{y}] {prescreen_sbin}->1 (fail->pass)")
            stdf.set_part_flag_pf_bit(part_flag, is_pass=True)
            rec_obj.set_value("SOFT_BIN", 1)
            rec_obj.set_value("HARD_BIN", 1)
        elif prescreen_sbin == 1 and is_pass == False: # pass -> fail
            print(f"(DEBUG) [{x},{y}] {prescreen_sbin}->4 (pass->fail)")
            stdf.set_part_flag_pf_bit(part_flag, is_pass=False)
            rec_obj.set_value("SOFT_BIN", 4)
            rec_obj.set_value("HARD_BIN", 4)
        rec_obj.set_value("PART_FLG", part_flag)
        rec = rec_obj.__repr__()
        stdf.index['indexes'][index] = (rec, rec_id)
         
    '''
    update TSR for CAV1TOPS and CAV2TOPS
    TSR fields to update:
        # of test failures (FAIL_CNT)
        TEST_MIN
        TEST_MAX
        TST_SUMS
        TST_SQRS
    '''
    tnum_tnam = [(3004, 'TOPS_Res_TEST CAV1TOPS'), (3005, 'TOPS_Res_TEST CAV2TOPS')]
    
    if debug:
        print("updating TSR's...")
    stdf.update_tsr(tnum_tnam = tnum_tnam)
    
    sbin_cnts = stdf.get_sbin_cnts()
    stdf.update_sbin_cnts()
    print("sbin_cnts:", sbin_cnts)
    
    hbin_cnts = stdf.get_hbin_cnts()
    stdf.update_hbin_cnts()
    print("hbin_cnts:", hbin_cnts)
    
    total_cnt = stdf.get_total_part_cnt()
    print("total_cnt:", total_cnt)
    stdf.update_total_part_count()
    
    pass_cnt = stdf.get_pass_part_cnt()
    print("pass_cnt:", pass_cnt)
    stdf.update_pass_part_count()

    retest_cnt = stdf.get_retest_part_cnt()
    print("retest_cnt:", retest_cnt)
    stdf.update_retest_part_count()
        
    screened_stdf_fp = stdf_fp[:-5] + "_SCREENED.stdf"
    stdf.write_stdf(screened_stdf_fp)
    
    # debug
    if gen_atdf:
        stdf_to_atdf([screened_stdf_fp])
        
    return screened_stdf_fp
            
if __name__ == "__main__":
    # fp = r"C:/Users/dkane/OneDrive - Presto Engineering/Documents/Integra-Job/Cisco/BigBend/Stdf/test 3-pass merge/5AIX5202_MERGED_3X.stdf"
    # fp = r"C:/Users/dkane/OneDrive - Presto Engineering/Documents/Integra-Job/Cisco/BigBend/Stdf/Lot_5AIX5202_3wafers_06_23_2023_stdf/5AIX5202-07_MERGED.stdf"
    for wafer_num in [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]:
        fp = rf"C:/Users/dkane/OneDrive - Presto Engineering/Documents/Integra-Job/Cisco/BigBend/Lot 5AIY2001/5AIY2001_W13-W25_082223/5AIY2001-{str(wafer_num).zfill(2)}_MERGED_3X_SCREENED.stdf"
        
        screen_outliers(stdf_fp=fp, plot_distribution=True, gen_atdf=True, debug=True)
        # screen_outliers()

