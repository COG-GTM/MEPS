"""
Exercise 5b: Construct Insurance Status Variables

This program illustrates how to construct insurance status variables from
monthly insurance variables in the person-level data.

Monthly insurance variables include:
    - TRImm##X: Covered by TRICARE/CHAMPVA in month mm
    - MCRmm##X: Covered by Medicare in month mm
    - MCDmm##X: Covered by Medicaid or SCHIP in month mm
    - OPAmm##: Covered by Other Public A Ins in month mm
    - OPBmm##: Covered by Other Public B Ins in month mm
    - PUBmm##X: Covered by Any Public Ins in month mm
    - PEGmm##: Covered by Empl Union Ins in month mm
    - PDKmm##: Covered by Priv Ins (Source Unknown) in month mm
    - PNGmm##: Covered by Nongroup Ins in month mm
    - POGmm##: Covered by Other Group Ins in month mm
    - PRSmm##: Covered by Self-Emp Ins in month mm
    - POUmm##: Covered by Holder Outside of RU in month mm
    - PRImm##: Covered by Private Ins in month mm

where mm = JA-DE (January - December)

Input files:
    - 2015 Full-Year file (h181)

Python equivalent of: SAS/workshop_exercises/exercise_5b/Exercise5b.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_freq


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS")
    yr = '15'
    
    print("=" * 80)
    print("2018 AHRQ MEPS DATA USERS WORKSHOP")
    print(f"EXERCISE 5b: HOW TO CONSTRUCT INSURANCE STATUS VARIABLES, USING FY {yr} DATA")
    print("=" * 80)
    
    # Load 2015 Full-Year file
    fyc_file = data_dir / "h181.sas7bdat"
    print(f"\nLoading data from: {fyc_file}")
    
    fy1 = load_sas_data(fyc_file)
    
    # Define month abbreviations
    months = ['JA', 'FE', 'MA', 'AP', 'MY', 'JU', 'JL', 'AU', 'SE', 'OC', 'NO', 'DE']
    
    # 1) Count # of months with insurance
    print("\n" + "-" * 60)
    print("CREATE COUNT VARIABLES FOR # OF MONTHS WITH INSURANCE")
    print("-" * 60)
    
    # Initialize count variables
    fy1['PRI_N'] = 0    # Private insurance
    fy1['INS_N'] = 0    # Any insurance
    fy1['UNINS_N'] = 0  # Uninsured
    fy1['MCD_N'] = 0    # Medicaid
    fy1['MCR_N'] = 0    # Medicare
    fy1['TRI_N'] = 0    # TRICARE
    fy1['OPAB_N'] = 0   # Other Public A or B
    fy1['GRP_N'] = 0    # Private Group
    fy1['NG_N'] = 0     # Private Non-Group
    fy1['PUB_N'] = 0    # Public
    fy1['REF_N'] = 0    # Months in survey
    
    # Count months for each insurance type
    for month in months:
        # Private insurance
        pri_col = f'PRI{month}{yr}'
        if pri_col in fy1.columns:
            fy1['PRI_N'] += (fy1[pri_col] == 1).astype(int)
        
        # Any insurance (edited)
        ins_col = f'INS{month}{yr}X'
        if ins_col in fy1.columns:
            fy1['INS_N'] += (fy1[ins_col] == 1).astype(int)
            fy1['UNINS_N'] += (fy1[ins_col] == 2).astype(int)
            fy1['REF_N'] += (fy1[ins_col] > 0).astype(int)
        
        # Medicaid (edited)
        mcd_col = f'MCD{month}{yr}X'
        if mcd_col in fy1.columns:
            fy1['MCD_N'] += (fy1[mcd_col] == 1).astype(int)
        
        # Medicare (edited)
        mcr_col = f'MCR{month}{yr}X'
        if mcr_col in fy1.columns:
            fy1['MCR_N'] += (fy1[mcr_col] == 1).astype(int)
        
        # TRICARE (edited)
        tri_col = f'TRI{month}{yr}X'
        if tri_col in fy1.columns:
            fy1['TRI_N'] += (fy1[tri_col] == 1).astype(int)
        
        # Other Public A or B
        opa_col = f'OPA{month}{yr}'
        opb_col = f'OPB{month}{yr}'
        if opa_col in fy1.columns and opb_col in fy1.columns:
            fy1['OPAB_N'] += ((fy1[opa_col] == 1) | (fy1[opb_col] == 1)).astype(int)
        
        # Private Group (PEG, TRI, POU, PDK)
        peg_col = f'PEG{month}{yr}'
        pou_col = f'POU{month}{yr}'
        pdk_col = f'PDK{month}{yr}'
        if peg_col in fy1.columns:
            grp_mask = (fy1[peg_col] == 1)
            if tri_col in fy1.columns:
                grp_mask = grp_mask | (fy1[tri_col] == 1)
            if pou_col in fy1.columns:
                grp_mask = grp_mask | (fy1[pou_col] == 1)
            if pdk_col in fy1.columns:
                grp_mask = grp_mask | (fy1[pdk_col] == 1)
            fy1['GRP_N'] += grp_mask.astype(int)
        
        # Private Non-Group (PRX, PNG, POG, PRS)
        prx_col = f'PRX{month}{yr}'
        png_col = f'PNG{month}{yr}'
        pog_col = f'POG{month}{yr}'
        prs_col = f'PRS{month}{yr}'
        ng_mask = pd.Series(False, index=fy1.index)
        for col in [prx_col, png_col, pog_col, prs_col]:
            if col in fy1.columns:
                ng_mask = ng_mask | (fy1[col] == 1)
        fy1['NG_N'] += ng_mask.astype(int)
        
        # Public (MCR, MCD, OPA, OPB)
        pub_mask = pd.Series(False, index=fy1.index)
        for col in [mcr_col, mcd_col, opa_col, opb_col]:
            if col in fy1.columns:
                pub_mask = pub_mask | (fy1[col] == 1)
        fy1['PUB_N'] += pub_mask.astype(int)
    
    # Print frequency of count variables
    count_vars = ['PRI_N', 'INS_N', 'UNINS_N', 'MCD_N', 'MCR_N', 'TRI_N', 'OPAB_N', 'GRP_N', 'NG_N', 'PUB_N', 'REF_N']
    for var in count_vars:
        print(f"\n{var}:")
        print(fy1[var].value_counts().sort_index())
    
    # 2) Create flags for various types of insurance
    print("\n" + "-" * 60)
    print("CREATE FLAGS FOR VARIOUS TYPES OF INSURANCE")
    print("-" * 60)
    
    fy2 = fy1.copy()
    
    # Full year insured
    fy2['FULL_INSU'] = (fy2['UNINS_N'] == 0).astype(int)
    
    # Ever insured by private group
    fy2['GROUP_INS1'] = (fy2['GRP_N'] > 0).astype(int)
    
    # Insured by private group for full year
    fy2['GROUP_INS2'] = ((fy2['GRP_N'] > 0) & (fy2['GRP_N'] == fy2['REF_N'])).astype(int)
    
    # Ever insured by private non-group
    fy2['NG_INS'] = (fy2['NG_N'] > 0).astype(int)
    
    # Supporting crosstabs
    print("\nFULL_INSU (Insured for Full Year):")
    print(fy2['FULL_INSU'].value_counts().sort_index())
    
    print("\nGROUP_INS1 (Ever Insured by Private Group):")
    print(fy2['GROUP_INS1'].value_counts().sort_index())
    
    print("\nGROUP_INS2 (Insured by Private Group for Full Year):")
    print(fy2['GROUP_INS2'].value_counts().sort_index())
    
    print("\nNG_INS (Ever Insured by Private Non-Group):")
    print(fy2['NG_INS'].value_counts().sort_index())
    
    # 3) Calculate % of persons covered by insurance
    print("\n" + "=" * 60)
    print("% AND POPULATION WITH INSURANCE")
    print("=" * 60)
    
    design = SurveyDesign(
        data=fy2,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT15F'
    )
    
    ins_vars = ['FULL_INSU', 'GROUP_INS1', 'GROUP_INS2', 'NG_INS']
    labels = [
        'Insured for Full Year',
        'Ever Insured by Private Group',
        'Insured by Private Group for Full Year',
        'Ever Insured by Private Non-Group'
    ]
    
    print(f"\nN (unweighted): {len(fy2):,}")
    print(f"Sum of Weights: {fy2['PERWT15F'].sum():,.0f}")
    
    for var, label in zip(ins_vars, labels):
        mean_result = survey_mean(design, var)
        print(f"\n{label}:")
        print(f"  Proportion: {mean_result['mean'].values[0]:.4f}")
        print(f"  SE: {mean_result['se'].values[0]:.6f}")
    
    # By Race/Ethnicity
    print("\n" + "-" * 40)
    print("By Race/Ethnicity:")
    print("-" * 40)
    
    racethx_labels = {1: 'Hispanic', 2: 'White', 3: 'Black', 4: 'Asian', 5: 'Other Race'}
    
    for race_val, race_label in racethx_labels.items():
        subset = fy2[fy2['RACETHX'] == race_val].copy()
        if len(subset) > 0:
            design_race = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT15F'
            )
            
            print(f"\n{race_label}:")
            for var, label in zip(ins_vars, labels):
                mean_result = survey_mean(design_race, var)
                print(f"  {label}: {mean_result['mean'].values[0]:.4f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
