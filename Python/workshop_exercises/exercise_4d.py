"""
Exercise 4d: Pooling MEPS Data Files - Joint Pain Analysis (2017-2019)

This program illustrates how to pool MEPS data files from different years.
It highlights one example of a discontinuity that may be encountered when
working with data from before and after the 2018 MEPS CAPI re-design.

The program pools 2017, 2018 and 2019 data and calculates:
    - Percentage of people with Joint Pain / Arthritis (JTPAIN**, ARTHDX)
    - Average expenditures per person, by Joint Pain status (TOTEXP, TOTSLF)
    - Standard errors by specifying common variance structure when pooling data

Input files:
    - 2017 Full-year consolidated file (h201)
    - 2018 Full-year consolidated file (h209)
    - 2019 Full-year consolidated file (h216)
    - 1996-2019 pooled linkage variance estimation file (h36u19)

Python equivalent of: SAS/workshop_exercises/exercise_4d/Exercise4.sas
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
    print("POOLED ESTIMATES FOR MEPS 2017-19: JOINT PAIN ANALYSIS")
    print("=" * 80)
    
    # Load 2017 Full-Year file
    fyc17_file = data_dir / "h201.sas7bdat"
    print(f"\nLoading 2017 data from: {fyc17_file}")
    
    meps_2017 = load_sas_data(
        fyc17_file,
        columns=['DUPERSID', 'PANEL', 'VARSTR', 'VARPSU', 'PERWT17F', 'AGELAST', 'ARTHDX', 'JTPAIN31', 'TOTEXP17', 'TOTSLF17']
    )
    
    # Rename and process 2017 data
    meps_2017 = meps_2017.rename(columns={
        'TOTEXP17': 'TOTEXP',
        'TOTSLF17': 'TOTSLF',
        'JTPAIN31': 'JTPAIN'
    })
    meps_2017['YEAR'] = 2017
    meps_2017['PERWTF'] = meps_2017['PERWT17F'] / 3
    
    # Convert 8-character DUPERSID to 10-character for 2017
    meps_2017['DUPERSID'] = meps_2017['PANEL'].astype(str).str.zfill(2) + meps_2017['DUPERSID'].astype(str)
    
    # Create subpopulation indicator and JOINT_PAIN variable
    meps_2017['SPOP'] = 0
    mask = (meps_2017['AGELAST'] >= 18) & ~((meps_2017['ARTHDX'] <= 0) & (meps_2017['JTPAIN'] < 0))
    meps_2017.loc[mask, 'SPOP'] = 1
    meps_2017.loc[mask & ((meps_2017['ARTHDX'] == 1) | (meps_2017['JTPAIN'] == 1)), 'JOINT_PAIN'] = 1
    meps_2017.loc[mask & ~((meps_2017['ARTHDX'] == 1) | (meps_2017['JTPAIN'] == 1)), 'JOINT_PAIN'] = 2
    
    # Load 2018 Full-Year file
    fyc18_file = data_dir / "h209.sas7bdat"
    print(f"Loading 2018 data from: {fyc18_file}")
    
    meps_2018 = load_sas_data(
        fyc18_file,
        columns=['DUPERSID', 'PANEL', 'VARSTR', 'VARPSU', 'PERWT18F', 'AGELAST', 'ARTHDX', 'JTPAIN31_M18', 'TOTEXP18', 'TOTSLF18']
    )
    
    # Rename and process 2018 data
    meps_2018 = meps_2018.rename(columns={
        'TOTEXP18': 'TOTEXP',
        'TOTSLF18': 'TOTSLF',
        'JTPAIN31_M18': 'JTPAIN'
    })
    meps_2018['YEAR'] = 2018
    meps_2018['PERWTF'] = meps_2018['PERWT18F'] / 3
    
    # Create subpopulation indicator and JOINT_PAIN variable
    meps_2018['SPOP'] = 0
    mask = (meps_2018['AGELAST'] >= 18) & ~((meps_2018['ARTHDX'] < 0) & (meps_2018['JTPAIN'] < 0))
    meps_2018.loc[mask, 'SPOP'] = 1
    meps_2018.loc[mask & ((meps_2018['ARTHDX'] == 1) | (meps_2018['JTPAIN'] == 1)), 'JOINT_PAIN'] = 1
    meps_2018.loc[mask & ~((meps_2018['ARTHDX'] == 1) | (meps_2018['JTPAIN'] == 1)), 'JOINT_PAIN'] = 2
    
    # Load 2019 Full-Year file
    fyc19_file = data_dir / "h216.sas7bdat"
    print(f"Loading 2019 data from: {fyc19_file}")
    
    meps_2019 = load_sas_data(
        fyc19_file,
        columns=['DUPERSID', 'PANEL', 'VARSTR', 'VARPSU', 'PERWT19F', 'AGELAST', 'ARTHDX', 'JTPAIN31_M18', 'TOTEXP19', 'TOTSLF19']
    )
    
    # Rename and process 2019 data
    meps_2019 = meps_2019.rename(columns={
        'TOTEXP19': 'TOTEXP',
        'TOTSLF19': 'TOTSLF',
        'JTPAIN31_M18': 'JTPAIN'
    })
    meps_2019['YEAR'] = 2019
    meps_2019['PERWTF'] = meps_2019['PERWT19F'] / 3
    
    # Create subpopulation indicator and JOINT_PAIN variable
    meps_2019['SPOP'] = 0
    mask = (meps_2019['AGELAST'] >= 18) & ~((meps_2019['ARTHDX'] < 0) & (meps_2019['JTPAIN'] < 0))
    meps_2019.loc[mask, 'SPOP'] = 1
    meps_2019.loc[mask & ((meps_2019['ARTHDX'] == 1) | (meps_2019['JTPAIN'] == 1)), 'JOINT_PAIN'] = 1
    meps_2019.loc[mask & ~((meps_2019['ARTHDX'] == 1) | (meps_2019['JTPAIN'] == 1)), 'JOINT_PAIN'] = 2
    
    # Concatenate all years
    meps_171819 = pd.concat([meps_2017, meps_2018, meps_2019], ignore_index=True)
    
    print(f"\nTotal records in pooled data: {len(meps_171819):,}")
    print(f"Records by year:")
    print(meps_171819['YEAR'].value_counts().sort_index())
    
    # Load pooled linkage variance estimation file
    vs_file = data_dir / "h36u19.sas7bdat"
    print(f"\nLoading variance structure file from: {vs_file}")
    
    try:
        vs_data = load_sas_data(vs_file, columns=['DUPERSID', 'PANEL', 'STRA9619', 'PSU9619'])
        
        # Convert 8-character DUPERSID to 10-character for older panels
        vs_data['DUPERSID_NEW'] = vs_data.apply(
            lambda row: str(row['PANEL']).zfill(2) + str(row['DUPERSID']) 
            if len(str(row['DUPERSID']).strip()) == 8 else str(row['DUPERSID']),
            axis=1
        )
        vs_data['DUPERSID'] = vs_data['DUPERSID_NEW']
        
        # Filter to panels 21-24 and remove duplicates
        vs_data = vs_data[vs_data['PANEL'].isin([21, 22, 23, 24])].drop_duplicates(subset='DUPERSID')
        
        # Merge with pooled data
        meps_171819_m = meps_171819.merge(
            vs_data[['DUPERSID', 'STRA9619', 'PSU9619']],
            on='DUPERSID',
            how='left'
        )
        
        use_pooled_variance = True
        print(f"Successfully merged variance structure file")
    except Exception as e:
        print(f"Warning: Could not load variance structure file: {e}")
        print("Using original VARSTR/VARPSU for variance estimation")
        meps_171819_m = meps_171819.copy()
        meps_171819_m['STRA9619'] = meps_171819_m['VARSTR']
        meps_171819_m['PSU9619'] = meps_171819_m['VARPSU']
        use_pooled_variance = False
    
    # Survey estimates for joint pain prevalence
    print("\n" + "=" * 60)
    print("JOINT PAIN PREVALENCE (Adults 18+)")
    print("=" * 60)
    
    pool_sub = meps_171819_m[(meps_171819_m['SPOP'] == 1) & (meps_171819_m['PERWTF'] > 0)].copy()
    pool_sub = pool_sub.dropna(subset=['STRA9619', 'PSU9619'])
    
    design = SurveyDesign(
        data=pool_sub,
        strata='STRA9619',
        cluster='PSU9619',
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
                strata='STRA9619',
                cluster='PSU9619',
                weight='PERWTF'
            )
            
            print(f"\n{jp_label}:")
            print(f"  N: {len(subset):,}")
            
            for var, label in [('TOTEXP', 'Total Health Care Expenses 2017-19'), ('TOTSLF', 'Amount Paid by Self/Family 2017-19')]:
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
