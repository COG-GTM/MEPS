"""
DESCRIPTION: THIS PROGRAM ILLUSTRATES HOW TO CONSTRUCT INSURANCE STATUS VARIABLES FROM
             MONTHLY INSURANCE VARIABLES IN THE PERSON-LEVEL DATA

TRImm15X   Covered by TRICARE/CHAMPVA in mm (Ed)
MCRmm15    Covered by Medicare in mm
MCRmm15X   Covered by Medicare in mm (Ed)
MCDmm15    Covered by Medicaid or SCHIP in mm
MCDmm15X   Covered by Medicaid or SCHIP in mm  (Ed)
OPAmm15    Covered by Other Public A Ins in mm
OPBmm15    Covered by Other Public B Ins in mm
PUBmm15X   Covered by Any Public Ins in mm (Ed)
PEGmm15    Covered by Empl Union Ins in mm
PDKmm15    Coverer by Priv Ins (Source Unknown) in mm
PNGmm15    Covered by Nongroup Ins in mm
POGmm15    Covered by Other Group Ins in mm
PRSmm15    Covered by Self-Emp Ins in mm
POUmm15    Covered by Holder Outside of RU in mm
PRImm15    Covered by Private Ins in mm

where mm = JA-DE  (January - December)

INPUT FILE:   H181.SAS7BDAT (2015 FY PUF DATA)
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total, print_results


def main(meps_data_path: str = "C:/MEPS/SAS/DATA"):
    """
    Main function to run the analysis.
    
    Parameters
    ----------
    meps_data_path : str
        Path to directory containing MEPS data files
    """
    
    YR = '15'
    
    print("2018 AHRQ MEPS DATA USERS WORKSHOP")
    print(f"EXERCISE7.SAS: HOW TO CONSTRUCT INSURANCE STATUS VARIABLES, USING FY {YR} DATA")
    print("="*80)
    
    # Format labels
    racethx_labels = {
        1: '1 HISPANIC',
        2: '2 WHITE',
        3: '3 BLACK',
        4: '4 ASIAN',
        5: '5 OTHER RACE'
    }
    
    # Load 2015 Full-Year Consolidated file
    print("\nLoading 2015 Full-Year Consolidated file...")
    h181 = load_sas_data(os.path.join(meps_data_path, "H181.sas7bdat"))
    
    # Month abbreviations
    months = ['JA', 'FE', 'MA', 'AP', 'MY', 'JU', 'JL', 'AU', 'SE', 'OC', 'NO', 'DE']
    
    # 1) COUNT # OF MONTHS WITH INSURANCE
    fy1 = h181.copy()
    
    # Initialize count variables
    fy1['PRI_N'] = 0
    fy1['INS_N'] = 0
    fy1['UNINS_N'] = 0
    fy1['MCD_N'] = 0
    fy1['MCR_N'] = 0
    fy1['TRI_N'] = 0
    fy1['OPAB_N'] = 0
    fy1['GRP_N'] = 0
    fy1['NG_N'] = 0
    fy1['PUB_N'] = 0
    fy1['REF_N'] = 0
    
    # Count months for each insurance type
    for mm in months:
        # Private insurance
        pri_col = f'PRI{mm}{YR}'
        if pri_col in fy1.columns:
            fy1['PRI_N'] += (fy1[pri_col] == 1).astype(int)
        
        # Any insurance
        ins_col = f'INS{mm}{YR}X'
        if ins_col in fy1.columns:
            fy1['INS_N'] += (fy1[ins_col] == 1).astype(int)
            fy1['UNINS_N'] += (fy1[ins_col] == 2).astype(int)
            fy1['REF_N'] += (fy1[ins_col] > 0).astype(int)
        
        # Medicaid
        mcd_col = f'MCD{mm}{YR}X'
        if mcd_col in fy1.columns:
            fy1['MCD_N'] += (fy1[mcd_col] == 1).astype(int)
        
        # Medicare
        mcr_col = f'MCR{mm}{YR}X'
        if mcr_col in fy1.columns:
            fy1['MCR_N'] += (fy1[mcr_col] == 1).astype(int)
        
        # TRICARE
        tri_col = f'TRI{mm}{YR}X'
        if tri_col in fy1.columns:
            fy1['TRI_N'] += (fy1[tri_col] == 1).astype(int)
        
        # Other Public A or B
        opa_col = f'OPA{mm}{YR}'
        opb_col = f'OPB{mm}{YR}'
        if opa_col in fy1.columns and opb_col in fy1.columns:
            fy1['OPAB_N'] += ((fy1[opa_col] == 1) | (fy1[opb_col] == 1)).astype(int)
        
        # Group insurance
        peg_col = f'PEG{mm}{YR}'
        pou_col = f'POU{mm}{YR}'
        pdk_col = f'PDK{mm}{YR}'
        if peg_col in fy1.columns:
            grp_mask = (fy1.get(peg_col, 0) == 1) | (fy1.get(tri_col, 0) == 1) | \
                       (fy1.get(pou_col, 0) == 1) | (fy1.get(pdk_col, 0) == 1)
            fy1['GRP_N'] += grp_mask.astype(int)
        
        # Non-group insurance
        prx_col = f'PRX{mm}{YR}'
        png_col = f'PNG{mm}{YR}'
        pog_col = f'POG{mm}{YR}'
        prs_col = f'PRS{mm}{YR}'
        if png_col in fy1.columns:
            ng_mask = (fy1.get(prx_col, 0) == 1) | (fy1.get(png_col, 0) == 1) | \
                      (fy1.get(pog_col, 0) == 1) | (fy1.get(prs_col, 0) == 1)
            fy1['NG_N'] += ng_mask.astype(int)
        
        # Public insurance
        if mcr_col in fy1.columns and mcd_col in fy1.columns:
            pub_mask = (fy1.get(mcr_col, 0) == 1) | (fy1.get(mcd_col, 0) == 1) | \
                       (fy1.get(opa_col, 0) == 1) | (fy1.get(opb_col, 0) == 1)
            fy1['PUB_N'] += pub_mask.astype(int)
    
    # Labels
    count_labels = {
        'PRI_N': '# OF MONTHS COV BY PRIVATE INSU',
        'INS_N': '# OF MONTHS COV BY ANY INSU',
        'UNINS_N': '# OF MONTHS WITHOUT INSU',
        'MCD_N': '# OF MONTHS COV BY MEDICAID',
        'MCR_N': '# OF MONTHS COV BY MEDICARE',
        'TRI_N': '# OF MONTHS COV BY TRICARE',
        'OPAB_N': '# OF MONTHS COV BY OTHER PUBLIC A OR B INSU',
        'GRP_N': '# OF MONTHS COV BY PRIVATE GROUP INSU',
        'NG_N': '# OF MONTHS COV BY PRIVATE NON-GROUP INSU',
        'PUB_N': '# OF MONTHS COV BY PUBLIC INSU',
        'REF_N': '# OF MONTHS IN MEPS SURVEY'
    }
    
    print("\nCREATE COUNT VARIABLES FOR # OF MONTHS WITH INSURANCE:")
    for var, label in count_labels.items():
        print(f"\n{var} ({label}):")
        print(fy1[var].value_counts().sort_index())
    
    # 2) CREATE FLAGS FOR VARIOUS TYPES OF INSURANCE
    fy2 = fy1.copy()
    
    fy2['FULL_INSU'] = (fy2['UNINS_N'] == 0).astype(int)
    fy2['GROUP_INS1'] = (fy2['GRP_N'] > 0).astype(int)
    fy2['GROUP_INS2'] = ((fy2['GRP_N'] > 0) & (fy2['GRP_N'] == fy2['REF_N'])).astype(int)
    fy2['NG_INS'] = (fy2['NG_N'] > 0).astype(int)
    
    flag_labels = {
        'FULL_INSU': 'INSURED FOR FULL YEAR',
        'GROUP_INS1': 'EVER INSURED BY PRIVATE GROUP',
        'GROUP_INS2': 'INSURED BY PRIVATE GROUP FOR FULL YEAR',
        'NG_INS': 'EVER INSURED BY PRIVATE NON-GROUP'
    }
    
    print("\n" + "="*80)
    print("SUPPORTING CROSSTABS TO VERIFY THE CREATION OF THE FLAGS:")
    print("="*80)
    
    for var, label in flag_labels.items():
        print(f"\n{var} ({label}):")
        print(fy2[var].value_counts())
    
    # 3) CALCULATE % OF PERSONS COVERED BY INSURANCE
    print("\n" + "="*80)
    print("% AND POPULATION WITH INSURANCE")
    print("="*80)
    
    # Overall estimates
    design = SurveyDesign(
        data=fy2,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT15F'
    )
    
    vars_to_analyze = ['FULL_INSU', 'GROUP_INS1', 'GROUP_INS2', 'NG_INS']
    
    means = survey_mean(design, vars_to_analyze)
    totals = survey_total(design, vars_to_analyze)
    
    results = pd.merge(
        means[['Variable', 'N', 'SumWgt', 'Mean', 'StdErr']],
        totals[['Variable', 'Sum', 'StdDev']],
        on='Variable'
    )
    
    print("\nOverall estimates:")
    print(f"\n{'Variable':<15} {'N':>10} {'Sum of Wgt':>15} {'Sum':>15} {'SE Sum':>12} {'Mean':>10} {'SE Mean':>10}")
    print("-" * 90)
    
    for _, row in results.iterrows():
        var = row['Variable']
        print(f"{var:<15} {row['N']:>10,.0f} {row['SumWgt']:>15,.0f} {row['Sum']:>15,.0f} {row['StdDev']:>12,.0f} {row['Mean']:>10,.4f} {row['StdErr']:>10,.5f}")
    
    # By race/ethnicity
    print("\n\nEstimates by RACETHX:")
    
    for race_val, race_label in racethx_labels.items():
        fy2_race = fy2[fy2['RACETHX'] == race_val].copy()
        
        if len(fy2_race) == 0:
            continue
        
        design_race = SurveyDesign(
            data=fy2_race,
            strata='VARSTR',
            cluster='VARPSU',
            weight='PERWT15F'
        )
        
        means_race = survey_mean(design_race, vars_to_analyze)
        
        print(f"\n{race_label}:")
        for _, row in means_race.iterrows():
            var = row['Variable']
            label = flag_labels.get(var, var)
            print(f"  {var}: {row['Mean']*100:.2f}% (SE: {row['StdErr']*100:.3f}%)")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Exercise 5b - Insurance Status Variables 2015')
    parser.add_argument('--data-path', type=str, default='C:/MEPS/SAS/DATA',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
