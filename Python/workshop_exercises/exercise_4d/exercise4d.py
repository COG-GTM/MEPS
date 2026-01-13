"""
This program illustrates how to pool MEPS data files from different years. It
highlights one example of a discontinuity that may be encountered when
working with data from before and after the 2018 MEPS CAPI re-design.

The program pools 2017, 2018 and 2019 data and calculates
 - percentage of people with Joint Pain / Arthritis (JTPAIN**, ARTHDX)
 - average expenditures per person, by Joint Pain status (TOTEXP, TOTSLF)
 - standard errors by specifying common variance structure when pooling data.
for the U.S. civilian noninstitutionized population.

Input files:
 - 2017 Full-year consolidated file
 - 2018 Full-year consolidated file
 - 2019 Full-year consolidated file
 - 1996-2019 pooled linkage variance estimation file
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
    
    print("POOLED ESTIMATES FOR MEPS 2017-19: JOINT PAIN / ARTHRITIS ANALYSIS")
    print("="*80)
    
    # Format labels
    yes_no_labels = {1: 'Yes', 2: 'No'}
    spop_labels = {1: 'Age 18+', 0: 'Age 0-17'}
    
    # Load 2017 data
    print("\nLoading 2017 Full-Year Consolidated file...")
    h201 = load_sas_data(os.path.join(meps_data_path, "H201.sas7bdat"))
    
    keep_vars_2017 = ['DUPERSID', 'PANEL', 'VARSTR', 'VARPSU', 'PERWT17F', 'AGELAST', 'ARTHDX', 'JTPAIN31', 'TOTEXP17', 'TOTSLF17']
    meps_2017 = h201[[c for c in keep_vars_2017 if c in h201.columns]].copy()
    meps_2017['YEAR'] = 2017
    meps_2017 = meps_2017.rename(columns={'TOTEXP17': 'TOTEXP', 'TOTSLF17': 'TOTSLF'})
    meps_2017['PERWTF'] = meps_2017['PERWT17F'] / 3
    
    # Create 10-character DUPERSID for 2017
    meps_2017['DUPERSID'] = meps_2017['PANEL'].astype(str).str.zfill(2) + meps_2017['DUPERSID'].astype(str)
    
    # Create subpopulation indicator and joint_pain variable
    meps_2017['SPOP'] = 0
    mask = (meps_2017['AGELAST'] >= 18) & ~((meps_2017['ARTHDX'] <= 0) & (meps_2017['JTPAIN31'] < 0))
    meps_2017.loc[mask, 'SPOP'] = 1
    meps_2017['JOINT_PAIN'] = np.nan
    meps_2017.loc[mask & ((meps_2017['ARTHDX'] == 1) | (meps_2017['JTPAIN31'] == 1)), 'JOINT_PAIN'] = 1
    meps_2017.loc[mask & ~((meps_2017['ARTHDX'] == 1) | (meps_2017['JTPAIN31'] == 1)), 'JOINT_PAIN'] = 2
    
    # Load 2018 data
    print("\nLoading 2018 Full-Year Consolidated file...")
    h209 = load_sas_data(os.path.join(meps_data_path, "H209.sas7bdat"))
    
    keep_vars_2018 = ['DUPERSID', 'PANEL', 'VARSTR', 'VARPSU', 'PERWT18F', 'AGELAST', 'ARTHDX', 'JTPAIN31_M18', 'TOTEXP18', 'TOTSLF18']
    meps_2018 = h209[[c for c in keep_vars_2018 if c in h209.columns]].copy()
    meps_2018['YEAR'] = 2018
    meps_2018 = meps_2018.rename(columns={'TOTEXP18': 'TOTEXP', 'TOTSLF18': 'TOTSLF', 'JTPAIN31_M18': 'JTPAIN31'})
    meps_2018['PERWTF'] = meps_2018['PERWT18F'] / 3
    
    # Create subpopulation indicator and joint_pain variable
    meps_2018['SPOP'] = 0
    mask = (meps_2018['AGELAST'] >= 18) & ~((meps_2018['ARTHDX'] < 0) & (meps_2018['JTPAIN31'] < 0))
    meps_2018.loc[mask, 'SPOP'] = 1
    meps_2018['JOINT_PAIN'] = np.nan
    meps_2018.loc[mask & ((meps_2018['ARTHDX'] == 1) | (meps_2018['JTPAIN31'] == 1)), 'JOINT_PAIN'] = 1
    meps_2018.loc[mask & ~((meps_2018['ARTHDX'] == 1) | (meps_2018['JTPAIN31'] == 1)), 'JOINT_PAIN'] = 2
    
    # Load 2019 data
    print("\nLoading 2019 Full-Year Consolidated file...")
    h216 = load_sas_data(os.path.join(meps_data_path, "H216.sas7bdat"))
    
    keep_vars_2019 = ['DUPERSID', 'PANEL', 'VARSTR', 'VARPSU', 'PERWT19F', 'AGELAST', 'ARTHDX', 'JTPAIN31_M18', 'TOTEXP19', 'TOTSLF19']
    meps_2019 = h216[[c for c in keep_vars_2019 if c in h216.columns]].copy()
    meps_2019['YEAR'] = 2019
    meps_2019 = meps_2019.rename(columns={'TOTEXP19': 'TOTEXP', 'TOTSLF19': 'TOTSLF', 'JTPAIN31_M18': 'JTPAIN31'})
    meps_2019['PERWTF'] = meps_2019['PERWT19F'] / 3
    
    # Create subpopulation indicator and joint_pain variable
    meps_2019['SPOP'] = 0
    mask = (meps_2019['AGELAST'] >= 18) & ~((meps_2019['ARTHDX'] < 0) & (meps_2019['JTPAIN31'] < 0))
    meps_2019.loc[mask, 'SPOP'] = 1
    meps_2019['JOINT_PAIN'] = np.nan
    meps_2019.loc[mask & ((meps_2019['ARTHDX'] == 1) | (meps_2019['JTPAIN31'] == 1)), 'JOINT_PAIN'] = 1
    meps_2019.loc[mask & ~((meps_2019['ARTHDX'] == 1) | (meps_2019['JTPAIN31'] == 1)), 'JOINT_PAIN'] = 2
    
    # Concatenate 2017, 2018, and 2019 data
    common_cols = ['DUPERSID', 'PANEL', 'VARSTR', 'VARPSU', 'AGELAST', 'ARTHDX', 'JTPAIN31', 
                   'TOTEXP', 'TOTSLF', 'YEAR', 'PERWTF', 'SPOP', 'JOINT_PAIN']
    meps_171819 = pd.concat([
        meps_2017[[c for c in common_cols if c in meps_2017.columns]],
        meps_2018[[c for c in common_cols if c in meps_2018.columns]],
        meps_2019[[c for c in common_cols if c in meps_2019.columns]]
    ], ignore_index=True)
    
    # Load pooled linkage variance estimation file
    print("\nLoading pooled linkage variance estimation file...")
    try:
        h36u19 = load_sas_data(os.path.join(meps_data_path, "H36U19.sas7bdat"))
        
        # Filter to panels 21-24 and create 10-character DUPERSID
        h36u19 = h36u19[h36u19['PANEL'].isin([21, 22, 23, 24])].copy()
        h36u19['DUPERSID_NEW'] = h36u19.apply(
            lambda x: str(int(x['PANEL'])).zfill(2) + str(x['DUPERSID']) 
            if len(str(x['DUPERSID'])) == 8 else str(x['DUPERSID']),
            axis=1
        )
        h36u19 = h36u19.drop_duplicates(subset=['DUPERSID_NEW'])
        h36u19 = h36u19.rename(columns={'DUPERSID_NEW': 'DUPERSID_LINK'})
        
        # Merge with pooled data
        meps_171819 = pd.merge(
            meps_171819,
            h36u19[['DUPERSID_LINK', 'STRA9619', 'PSU9619']].rename(columns={'DUPERSID_LINK': 'DUPERSID'}),
            on='DUPERSID',
            how='left'
        )
        use_pooled_variance = True
    except Exception as e:
        print(f"Warning: Could not load pooled variance file: {e}")
        print("Using year-specific variance structure instead.")
        use_pooled_variance = False
    
    # Create zero weight indicator
    meps_171819['ZERO_WEIGHT'] = (meps_171819['PERWTF'] == 0).astype(int)
    
    # QC checks
    print("\nQC: SPOP * JOINT_PAIN crosstab:")
    print(pd.crosstab(meps_171819['SPOP'].map(spop_labels), 
                      meps_171819['JOINT_PAIN'].map(yes_no_labels), 
                      margins=True))
    
    # Calculate estimates
    print("\n" + "="*80)
    print("POOLED ESTIMATES FOR MEPS 2017-19")
    print("="*80)
    
    # Filter to subpopulation (adults with valid responses and positive weight)
    meps_sub = meps_171819[(meps_171819['SPOP'] == 1) & (meps_171819['PERWTF'] > 0)].copy()
    
    # Use pooled variance structure if available
    if use_pooled_variance and 'STRA9619' in meps_sub.columns:
        meps_sub = meps_sub[meps_sub['STRA9619'].notna() & meps_sub['PSU9619'].notna()]
        design = SurveyDesign(
            data=meps_sub,
            strata='STRA9619',
            cluster='PSU9619',
            weight='PERWTF'
        )
    else:
        design = SurveyDesign(
            data=meps_sub,
            strata='VARSTR',
            cluster='VARPSU',
            weight='PERWTF'
        )
    
    # Joint pain prevalence
    print("\nJoint Pain Prevalence (SPOP=1, Age 18+):")
    freq_results = survey_freq(design, 'JOINT_PAIN')
    for _, row in freq_results.iterrows():
        if pd.notna(row['Level']):
            label = yes_no_labels.get(int(row['Level']), str(row['Level']))
            print(f"  {label}: {row['Proportion']*100:.2f}% (N={row['N']:,.0f})")
    
    # Expenditures by joint pain status
    print("\n" + "="*80)
    print("EXPENDITURES BY JOINT PAIN STATUS")
    print("="*80)
    
    for jp_val, jp_label in yes_no_labels.items():
        meps_jp = meps_sub[meps_sub['JOINT_PAIN'] == jp_val].copy()
        
        if len(meps_jp) == 0:
            continue
        
        if use_pooled_variance and 'STRA9619' in meps_jp.columns:
            design_jp = SurveyDesign(
                data=meps_jp,
                strata='STRA9619',
                cluster='PSU9619',
                weight='PERWTF'
            )
        else:
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
    parser = argparse.ArgumentParser(description='MEPS Exercise 4d - Pool MEPS Data 2017-2019 Joint Pain Analysis')
    parser.add_argument('--data-path', type=str, default='C:/MEPS_Data',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
