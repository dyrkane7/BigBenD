# -*- coding: utf-8 -*-
"""
Created on Wed Sep 13 08:45:02 2023

@author: dkane
"""

import os

from Semi_ATE.STDF import utils

from wafer_map import wafer_map
from stdf_file import STDFFile

def bigbend_single_pass_xlsx_wafermap(fp = ""):
    stdf = STDFFile(fp)
    
    die_info = {}
    
    for offset in stdf.index['records']['PRR']:
        prr = stdf.index['indexes'][offset][0]
        prr_obj = utils.create_record_object(stdf.index['version'], stdf.index['endian'], 'PRR', prr)
        x = prr_obj.get_value('X_COORD')
        y = prr_obj.get_value('Y_COORD')
        sbin_num = prr_obj.get_value('SOFT_BIN')
        die_info[(x,y)] = {'sbin_num' : sbin_num, 'sbin_name' : '_'}
    
    xlsx_fp = os.path.splitext(fp)[0] + '_wafermap.xlsx'

    wafer_map(die_info, xlsx_fp, bin_opt='SW', open_xlsx=True)
    
    
    
if __name__ == "__main__":
    # fp = r"C:/Users/dkane/OneDrive - Presto Engineering/Documents/Integra-Job/Cisco/BigBend/Cisco BigBenD SiNx PC Correlation/PC-V1 vs PC-V2 SAIW3301_W01_P1_09122023/SAIW3301-P101091223_1.std"
    fp = r"C:/Users/dkane/OneDrive - Presto Engineering/Documents/Integra-Job/Cisco/BigBend/Cisco BigBenD SiNx PC Correlation/PC-V1 vs PC-V2 SAIW3301_W01_P1_09122023/SAIW3301-P101230512.std"
    
    bigbend_single_pass_xlsx_wafermap(fp)