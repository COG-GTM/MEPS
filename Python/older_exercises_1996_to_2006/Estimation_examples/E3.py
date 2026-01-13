"""
AHRQ MEPS Data Users Workshop - Estimation Example E3

This example shows how to create a longitudinal file for 1999-2000 (Panel 4)
and compute person-level estimates for insurance coverage and expenditures.

Variables:
    - UNINS99, UNINS00 (Insured all of 1999, 2000)
    - TOTEXP99, TOTEXP00 (Total healthcare expenditures)

Input files:
    - h50.sas7bdat (2000 Full-Year Data File)
    - h38.sas7bdat (1999 Full-Year Data File)
    - h58.sas7bdat (Panel 4 Longitudinal Weight File)

Python equivalent of: SAS/older_exercises_1996_to_2006/Estimation_examples/E3/E3.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_mean


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS/DATA")
    
    print("=" * 80)
    print("AHRQ MEPS DATA USERS WORKSHOP (ESTIMATION)")
    print("PANEL 4 LONGITUDINAL FILE (1999 - 2000)")
    print("=" * 80)
    
    # Load 1999 data (Panel 4 only)
    print("\nLoading 1999 data...")
    h38 = load_sas_data(data_dir / "h38.sas7bdat", columns=[
        'DUPERSID', 'UNINS99', 'TOTEXP99', 'PANEL99'
    ])
    h38 = h38[h38['PANEL99'] == 4].drop(columns=['PANEL99'])
    print(f"  1999 Panel 4 records: {len(h38):,}")
    
    # Load 2000 data (Panel 4 only)
    print("Loading 2000 data...")
    h50 = load_sas_data(data_dir / "h50.sas7bdat", columns=[
        'DUPERSID', 'UNINS00', 'TOTEXP00', 'PANEL00'
    ])
    h50 = h50[h50['PANEL00'] == 4].drop(columns=['PANEL00'])
    print(f"  2000 Panel 4 records: {len(h50):,}")
    
    # Load Panel 4 longitudinal weight file
    print("Loading longitudinal weight file...")
    h58 = load_sas_data(data_dir / "h58.sas7bdat", columns=[
        'DUPERSID', 'LONGWTP4', 'VARPSUP4', 'VARSTRP4', 'YRINDP4'
    ])
    # Select persons in both 1999 and 2000 files
    h58 = h58[h58['YRINDP4'] == 1].drop(columns=['YRINDP4'])
    print(f"  Longitudinal records: {len(h58):,}")
    
    # Merge files
    longp4 = h38.merge(h50, on='DUPERSID', how='inner')
    longp4 = longp4.merge(h58, on='DUPERSID', how='inner')
    
    print(f"\nMerged longitudinal file: {len(longp4):,} records")
    
    # Recode variables
    # UNINS99: 1=uninsured, 2=insured -> 1=uninsured, 0=insured
    longp4['UNINS99_RECODE'] = np.where(longp4['UNINS99'] == 1, 1, 0)
    # UNINS00: recode to 100 or 0 for percentage output
    longp4['UNINS00_RECODE'] = np.where(longp4['UNINS00'] == 1, 100, 0)
    
    # TOTEXP99: 1 if >0, 0 otherwise
    longp4['TOTEXP99_FLAG'] = np.where(longp4['TOTEXP99'] > 0, 1, 0)
    # TOTEXP00: 100 if >0, 0 otherwise
    longp4['TOTEXP00_FLAG'] = np.where(longp4['TOTEXP00'] > 0, 100, 0)
    
    # Frequency tables
    print("\n" + "=" * 80)
    print("OF THOSE WITH SOME EXPENSE IN 1999")
    print("=" * 80)
    
    with_exp_99 = longp4[longp4['TOTEXP99_FLAG'] == 1]
    total_wt = with_exp_99['LONGWTP4'].sum()
    
    for val, label in [(100, 'Some expense in 2000'), (0, 'No expense in 2000')]:
        subset = with_exp_99[with_exp_99['TOTEXP00_FLAG'] == val]
        wt = subset['LONGWTP4'].sum()
        pct = wt / total_wt * 100 if total_wt > 0 else 0
        print(f"{label}: {wt:,.0f} ({pct:.2f}%)")
    
    print("\n" + "=" * 80)
    print("OF THOSE WITH NO EXPENSE IN 1999")
    print("=" * 80)
    
    no_exp_99 = longp4[longp4['TOTEXP99_FLAG'] == 0]
    total_wt = no_exp_99['LONGWTP4'].sum()
    
    for val, label in [(100, 'Some expense in 2000'), (0, 'No expense in 2000')]:
        subset = no_exp_99[no_exp_99['TOTEXP00_FLAG'] == val]
        wt = subset['LONGWTP4'].sum()
        pct = wt / total_wt * 100 if total_wt > 0 else 0
        print(f"{label}: {wt:,.0f} ({pct:.2f}%)")
    
    # Insurance status analysis
    print("\n" + "=" * 80)
    print("INSURANCE STATUS")
    print("Percent uninsured in 2000, by 1999 insurance status")
    print("=" * 80)
    
    for unins99_val, label in [(1, 'Uninsured in 1999'), (0, 'Insured in 1999')]:
        subset = longp4[longp4['UNINS99_RECODE'] == unins99_val].copy()
        
        if len(subset) > 0:
            design = SurveyDesign(
                data=subset,
                strata='VARSTRP4',
                cluster='VARPSUP4',
                weight='LONGWTP4'
            )
            
            mean_result = survey_mean(design, 'UNINS00_RECODE')
            print(f"\n{label}:")
            print(f"  N: {len(subset):,}")
            print(f"  % Uninsured in 2000: {mean_result['mean'].values[0]:.2f}%")
            print(f"  SE: {mean_result['se'].values[0]:.2f}")
    
    # Healthcare expenditures analysis
    print("\n" + "=" * 80)
    print("HEALTHCARE EXPENDITURES")
    print("Percent with expense in 2000, by 1999 expense status")
    print("=" * 80)
    
    for exp99_val, label in [(1, 'Had expense in 1999'), (0, 'No expense in 1999')]:
        subset = longp4[longp4['TOTEXP99_FLAG'] == exp99_val].copy()
        
        if len(subset) > 0:
            design = SurveyDesign(
                data=subset,
                strata='VARSTRP4',
                cluster='VARPSUP4',
                weight='LONGWTP4'
            )
            
            mean_result = survey_mean(design, 'TOTEXP00_FLAG')
            print(f"\n{label}:")
            print(f"  N: {len(subset):,}")
            print(f"  % With expense in 2000: {mean_result['mean'].values[0]:.2f}%")
            print(f"  SE: {mean_result['se'].values[0]:.2f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
