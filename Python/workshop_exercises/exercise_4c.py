"""
Exercise 4c: Pooling MEPS Data Files - Joint Pain Analysis (2017-2018)

This program illustrates how to pool MEPS data files from different years.
It highlights one example of a discontinuity that may be encountered when
working with data from before and after the 2018 CAPI re-design.

The program pools 2017 and 2018 data and calculates for the civilian
noninstitutionalized population:
    - Percentage of people with Joint Pain / Arthritis (JTPAIN**, ARTHDX)
    - Average expenditures per person, by Joint Pain status (TOTEXP, TOTSLF)

Input files:
    - 2017 Full-year consolidated file (h201)
    - 2018 Full-year consolidated file (h209)

Python equivalent of: SAS/workshop_exercises/exercise_4c/Exercise4c.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total, survey_freq


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS")
    
    print("=" * 80)
    print("MEPS 2017-18 COMBINED: JOINT PAIN ANALYSIS")
    print("=" * 80)
    
    # Load 2017 Full-Year file
    fyc17_file = data_dir / "h201.sas7bdat"
    print(f"\nLoading 2017 data from: {fyc17_file}")
    
    meps_2017 = load_sas_data(
        fyc17_file,
        columns=['VARSTR', 'VARPSU', 'PERWT17F', 'AGELAST', 'ARTHDX', 'JTPAIN31', 'TOTEXP17', 'TOTSLF17']
    )
    
    # Rename year-specific variables and create pooled weight
    meps_2017 = meps_2017.rename(columns={
        'TOTEXP17': 'TOTEXP',
        'TOTSLF17': 'TOTSLF',
        'JTPAIN31': 'JTPAIN'
    })
    meps_2017['PERWTF'] = meps_2017['PERWT17F'] / 2
    
    # Create subpopulation indicator and JOINT_PAIN variable
    meps_2017['SPOP'] = 2
    mask = (meps_2017['AGELAST'] >= 18) & ~((meps_2017['ARTHDX'] <= 0) & (meps_2017['JTPAIN'] < 0))
    meps_2017.loc[mask, 'SPOP'] = 1
    meps_2017.loc[mask & ((meps_2017['ARTHDX'] == 1) | (meps_2017['JTPAIN'] == 1)), 'JOINT_PAIN'] = 1
    meps_2017.loc[mask & ~((meps_2017['ARTHDX'] == 1) | (meps_2017['JTPAIN'] == 1)), 'JOINT_PAIN'] = 2
    
    # Load 2018 Full-Year file
    fyc18_file = data_dir / "h209.sas7bdat"
    print(f"Loading 2018 data from: {fyc18_file}")
    
    meps_2018 = load_sas_data(
        fyc18_file,
        columns=['VARSTR', 'VARPSU', 'PERWT18F', 'AGELAST', 'ARTHDX', 'JTPAIN31_M18', 'TOTEXP18', 'TOTSLF18']
    )
    
    # Rename year-specific variables and create pooled weight
    meps_2018 = meps_2018.rename(columns={
        'TOTEXP18': 'TOTEXP',
        'TOTSLF18': 'TOTSLF',
        'JTPAIN31_M18': 'JTPAIN'
    })
    meps_2018['PERWTF'] = meps_2018['PERWT18F'] / 2
    
    # Create subpopulation indicator and JOINT_PAIN variable
    meps_2018['SPOP'] = 2
    mask = (meps_2018['AGELAST'] >= 18) & ~((meps_2018['ARTHDX'] <= 0) & (meps_2018['JTPAIN'] < 0))
    meps_2018.loc[mask, 'SPOP'] = 1
    meps_2018.loc[mask & ((meps_2018['ARTHDX'] == 1) | (meps_2018['JTPAIN'] == 1)), 'JOINT_PAIN'] = 1
    meps_2018.loc[mask & ~((meps_2018['ARTHDX'] == 1) | (meps_2018['JTPAIN'] == 1)), 'JOINT_PAIN'] = 2
    
    # Concatenate 2017 and 2018 data
    meps_1718 = pd.concat([meps_2017, meps_2018], ignore_index=True)
    
    print(f"\nTotal records in pooled data: {len(meps_1718):,}")
    
    # Frequency tables
    print("\n" + "-" * 60)
    print("FREQUENCY TABLES FOR POOLED DATA")
    print("-" * 60)
    
    print("\nSPOP distribution:")
    print(meps_1718['SPOP'].value_counts().sort_index())
    
    print("\nJOINT_PAIN distribution (among SPOP=1):")
    spop1 = meps_1718[meps_1718['SPOP'] == 1]
    print(spop1['JOINT_PAIN'].value_counts().sort_index().rename({1: 'Yes', 2: 'No'}))
    
    # Survey estimates for joint pain prevalence
    print("\n" + "=" * 60)
    print("JOINT PAIN PREVALENCE (Adults 18+)")
    print("=" * 60)
    
    pool_sub = meps_1718[meps_1718['SPOP'] == 1].copy()
    
    design = SurveyDesign(
        data=pool_sub,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWTF'
    )
    
    freq_result = survey_freq(design, 'JOINT_PAIN')
    
    print(f"\nN (unweighted): {len(pool_sub):,}")
    print("\nJoint Pain Status:")
    joint_pain_labels = {1: 'Yes', 2: 'No'}
    for idx, row in freq_result.iterrows():
        level = row['level']
        label = joint_pain_labels.get(int(level), str(level))
        print(f"  {label}:")
        print(f"    Proportion: {row['proportion']:.3f}")
        print(f"    SE: {row['se']:.6f}")
        print(f"    Sum: {row['count']:,.0f}")
    
    # Survey estimates for expenditures by joint pain status
    print("\n" + "=" * 60)
    print("EXPENDITURES BY JOINT PAIN STATUS (Adults 18+)")
    print("=" * 60)
    
    for jp_val, jp_label in [(1, 'Yes - Joint Pain'), (2, 'No - No Joint Pain')]:
        subset = pool_sub[pool_sub['JOINT_PAIN'] == jp_val].copy()
        if len(subset) > 0:
            design_jp = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWTF'
            )
            
            print(f"\n{jp_label}:")
            print(f"  N: {len(subset):,}")
            
            for var, label in [('TOTEXP', 'Total Health Care Expenses'), ('TOTSLF', 'Amount Paid by Self/Family')]:
                mean_result = survey_mean(design_jp, var)
                total_result = survey_total(design_jp, var)
                print(f"  {label}:")
                print(f"    Mean: ${mean_result['mean'].values[0]:,.2f}")
                print(f"    SE: ${mean_result['se'].values[0]:.2f}")
                print(f"    Sum: ${total_result['total'].values[0]:,.0f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
