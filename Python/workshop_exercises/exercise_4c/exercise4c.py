"""
This program illustrates how to pool MEPS data files from different years. It
highlights one example of a discontinuity that may be encountered when
working with data from before and after the 2018 CAPI re-design.

The program pools 2017 and 2018 data and calculates for the civilian noninstitutionized population:
 - Percentage of people with Joint Pain / Arthritis (JTPAIN**, ARTHDX)
 - Average expenditures per person, by Joint Pain status (TOTEXP, TOTSLF)

Notes:
 - Variables with year-specific names must be renamed before combining files
   (e.g. 'TOTEXP17' and 'TOTEXP18' renamed to 'totexp')

Input files:
 - 2017 Full-year consolidated file
 - 2018 Full-year consolidated file
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total, survey_freq, print_results


def main(meps_data_path: str = "C:/MEPS_Data"):
    """
    Main function to run the analysis.
    
    Parameters
    ----------
    meps_data_path : str
        Path to directory containing MEPS data files
    """
    
    print("MEPS 2017-18 COMBINED: JOINT PAIN / ARTHRITIS ANALYSIS")
    print("="*80)
    
    # Format labels
    yes_no_labels = {1: 'Yes', 2: 'No'}
    
    # Load 2017 data
    print("\nLoading 2017 Full-Year Consolidated file...")
    h201 = load_sas_data(os.path.join(meps_data_path, "H201.sas7bdat"))
    
    keep_vars_2017 = ['VARSTR', 'VARPSU', 'PERWT17F', 'AGELAST', 'ARTHDX', 'JTPAIN31', 'TOTEXP17', 'TOTSLF17']
    meps_2017 = h201[[c for c in keep_vars_2017 if c in h201.columns]].copy()
    
    # Rename year-specific variables
    meps_2017 = meps_2017.rename(columns={
        'TOTEXP17': 'TOTEXP',
        'TOTSLF17': 'TOTSLF'
    })
    
    # Create pooled weight
    meps_2017['PERWTF'] = meps_2017['PERWT17F'] / 2
    
    # Create subpopulation indicator and joint_pain variable
    meps_2017['SPOP'] = 2
    mask = (meps_2017['AGELAST'] >= 18) & ~((meps_2017['ARTHDX'] <= 0) & (meps_2017['JTPAIN31'] < 0))
    meps_2017.loc[mask, 'SPOP'] = 1
    meps_2017['JOINT_PAIN'] = np.nan
    meps_2017.loc[mask & ((meps_2017['ARTHDX'] == 1) | (meps_2017['JTPAIN31'] == 1)), 'JOINT_PAIN'] = 1
    meps_2017.loc[mask & ~((meps_2017['ARTHDX'] == 1) | (meps_2017['JTPAIN31'] == 1)), 'JOINT_PAIN'] = 2
    
    # Rename JTPAIN31 for consistency
    meps_2017 = meps_2017.rename(columns={'JTPAIN31': 'JTPAIN'})
    
    # Load 2018 data
    print("\nLoading 2018 Full-Year Consolidated file...")
    h209 = load_sas_data(os.path.join(meps_data_path, "H209.sas7bdat"))
    
    keep_vars_2018 = ['VARSTR', 'VARPSU', 'PERWT18F', 'AGELAST', 'ARTHDX', 'JTPAIN31_M18', 'TOTEXP18', 'TOTSLF18']
    meps_2018 = h209[[c for c in keep_vars_2018 if c in h209.columns]].copy()
    
    # Rename year-specific variables
    meps_2018 = meps_2018.rename(columns={
        'TOTEXP18': 'TOTEXP',
        'TOTSLF18': 'TOTSLF',
        'JTPAIN31_M18': 'JTPAIN'
    })
    
    # Create pooled weight
    meps_2018['PERWTF'] = meps_2018['PERWT18F'] / 2
    
    # Create subpopulation indicator and joint_pain variable
    meps_2018['SPOP'] = 2
    mask = (meps_2018['AGELAST'] >= 18) & ~((meps_2018['ARTHDX'] <= 0) & (meps_2018['JTPAIN'] < 0))
    meps_2018.loc[mask, 'SPOP'] = 1
    meps_2018['JOINT_PAIN'] = np.nan
    meps_2018.loc[mask & ((meps_2018['ARTHDX'] == 1) | (meps_2018['JTPAIN'] == 1)), 'JOINT_PAIN'] = 1
    meps_2018.loc[mask & ~((meps_2018['ARTHDX'] == 1) | (meps_2018['JTPAIN'] == 1)), 'JOINT_PAIN'] = 2
    
    # Concatenate 2017 and 2018 analytic data files
    common_cols = ['VARSTR', 'VARPSU', 'AGELAST', 'ARTHDX', 'JTPAIN', 'TOTEXP', 'TOTSLF', 'PERWTF', 'SPOP', 'JOINT_PAIN']
    meps_1718 = pd.concat([meps_2017[common_cols], meps_2018[common_cols]], ignore_index=True)
    meps_1718['TOTEXP_X'] = meps_1718['TOTEXP']
    
    # Frequency tables
    print("\nMEPS 2017-18 combined:")
    print("\nARTHDX * JTPAIN * JOINT_PAIN crosstab:")
    print(pd.crosstab([meps_1718['ARTHDX'], meps_1718['JTPAIN']], meps_1718['JOINT_PAIN'].map(yes_no_labels), margins=True))
    
    print("\nSPOP distribution:")
    print(meps_1718['SPOP'].value_counts())
    
    print("\nJOINT_PAIN distribution:")
    print(meps_1718['JOINT_PAIN'].map(yes_no_labels).value_counts())
    
    # Calculate estimates for joint pain prevalence
    print("\n" + "="*80)
    print("MEPS 2017-18 COMBINED: JOINT PAIN PREVALENCE")
    print("="*80)
    
    # Filter to subpopulation (adults with valid responses)
    meps_sub = meps_1718[meps_1718['SPOP'] == 1].copy()
    
    design = SurveyDesign(
        data=meps_sub,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWTF'
    )
    
    # Joint pain prevalence
    freq_results = survey_freq(design, 'JOINT_PAIN')
    print("\nJoint Pain Prevalence (SPOP=1):")
    for _, row in freq_results.iterrows():
        label = yes_no_labels.get(int(row['Level']), str(row['Level']))
        print(f"  {label}: {row['Proportion']*100:.2f}% (N={row['N']:,.0f})")
    
    # Calculate estimates for expenditures by joint pain status
    print("\n" + "="*80)
    print("MEPS 2017-18 COMBINED: EXPENDITURES BY JOINT PAIN STATUS")
    print("="*80)
    
    for jp_val, jp_label in yes_no_labels.items():
        meps_jp = meps_sub[meps_sub['JOINT_PAIN'] == jp_val].copy()
        
        if len(meps_jp) == 0:
            continue
        
        design_jp = SurveyDesign(
            data=meps_jp,
            strata='VARSTR',
            cluster='VARPSU',
            weight='PERWTF'
        )
        
        means = survey_mean(design_jp, ['TOTEXP', 'TOTSLF'])
        totals = survey_total(design_jp, ['TOTEXP', 'TOTSLF'])
        
        print(f"\nJoint Pain = {jp_label}:")
        print(f"  N: {means['N'].values[0]:,.0f}")
        print(f"  TOTEXP Mean: ${means[means['Variable'] == 'TOTEXP']['Mean'].values[0]:,.2f} (SE: ${means[means['Variable'] == 'TOTEXP']['StdErr'].values[0]:,.2f})")
        print(f"  TOTEXP Sum: ${totals[totals['Variable'] == 'TOTEXP']['Sum'].values[0]:,.0f}")
        print(f"  TOTSLF Mean: ${means[means['Variable'] == 'TOTSLF']['Mean'].values[0]:,.2f} (SE: ${means[means['Variable'] == 'TOTSLF']['StdErr'].values[0]:,.2f})")
        print(f"  TOTSLF Sum: ${totals[totals['Variable'] == 'TOTSLF']['Sum'].values[0]:,.0f}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Exercise 4c - Pool MEPS Data 2017-2018 Joint Pain Analysis')
    parser.add_argument('--data-path', type=str, default='C:/MEPS_Data',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
