"""
Exercise 4b: Pooling MEPS Longitudinal Data Files from Different Panels

This program illustrates how to pool MEPS longitudinal data files from different panels.
The example used is Panels 17-19 population age 26-30 who are uninsured but have
high income in the first year.

Data from Panels 17, 18, and 19 are pooled.

Input files:
    - Panel 19 Longitudinal file (h183)
    - Panel 18 Longitudinal file (h172)
    - Panel 17 Longitudinal file (h164)

Python equivalent of: SAS/workshop_exercises/exercise_4b/Exercise4b.sas
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
    
    print("=" * 80)
    print("2018 AHRQ MEPS DATA USERS WORKSHOP")
    print("EXERCISE 4b: POOL MEPS DATA FILES FROM DIFFERENT PANELS (17, 18, 19)")
    print("=" * 80)
    
    # Define columns to keep
    keep_cols = ['DUPERSID', 'INSCOVY1', 'INSCOVY2', 'LONGWT', 'VARSTR', 'VARPSU', 'POVCATY1', 'AGEY1X', 'PANEL']
    
    # Load Panel 17 Longitudinal file
    p17_file = data_dir / "h164.sas7bdat"
    print(f"\nLoading Panel 17 data from: {p17_file}")
    p17 = load_sas_data(p17_file, columns=keep_cols)
    
    # Load Panel 18 Longitudinal file
    p18_file = data_dir / "h172.sas7bdat"
    print(f"Loading Panel 18 data from: {p18_file}")
    p18 = load_sas_data(p18_file, columns=keep_cols)
    
    # Load Panel 19 Longitudinal file
    p19_file = data_dir / "h183.sas7bdat"
    print(f"Loading Panel 19 data from: {p19_file}")
    p19 = load_sas_data(p19_file, columns=keep_cols)
    
    # Pool the data
    pool = pd.concat([p17, p18, p19], ignore_index=True)
    
    # Create pooled weight (divide by number of panels)
    pool['POOLWT'] = pool['LONGWT'] / 3
    
    # Create subpopulation flag
    # Uninsured in Year 1 (INSCOVY1=3), Age 26-30, High Income (POVCATY1=5)
    pool['SUBPOP'] = np.where(
        (pool['INSCOVY1'] == 3) & 
        (pool['AGEY1X'] >= 26) & (pool['AGEY1X'] <= 30) & 
        (pool['POVCATY1'] == 5),
        1, 2
    )
    
    # Check missing values
    print("\n" + "-" * 60)
    print("CHECK MISSING VALUES ON THE COMBINED DATA")
    print("-" * 60)
    print(f"\nTotal records in pooled data: {len(pool):,}")
    print(f"Missing values:")
    print(pool.isna().sum())
    
    # Supporting crosstab for subpop flag
    print("\n" + "-" * 60)
    print("SUPPORTING CROSSTAB FOR THE CREATION OF THE SUBPOP FLAG")
    print("-" * 60)
    
    print("\nSUBPOP distribution:")
    print(pool['SUBPOP'].value_counts().sort_index())
    
    print("\nSUBPOP by Panel:")
    print(pd.crosstab(pool['SUBPOP'], pool['PANEL'], margins=True))
    
    # Labels for display
    inscov_labels = {-1: 'Inapplicable', 1: 'Any Private', 2: 'Public Only', 3: 'Uninsured'}
    povcat_labels = {1: 'Poor/Negative', 2: 'Near Poor', 3: 'Low Income', 4: 'Middle Income', 5: 'High Income'}
    
    subpop1 = pool[pool['SUBPOP'] == 1]
    print(f"\nPersons in subpopulation (Age 26-30, Uninsured Y1, High Income): {len(subpop1):,}")
    
    # Calculate insurance status in Year 2 for subpopulation
    print("\n" + "=" * 60)
    print("INSURANCE STATUS IN YEAR 2 FOR THOSE WITH")
    print("Age=26-30, Uninsured Whole Year, High Income in Year 1")
    print("=" * 60)
    
    # Subset to subpopulation
    pool_sub = pool[pool['SUBPOP'] == 1].copy()
    
    design = SurveyDesign(
        data=pool_sub,
        strata='VARSTR',
        cluster='VARPSU',
        weight='POOLWT'
    )
    
    # Calculate proportions for INSCOVY2
    freq_result = survey_freq(design, 'INSCOVY2')
    
    print(f"\nN (unweighted): {len(pool_sub):,}")
    print("\nInsurance Status in Year 2:")
    print("-" * 40)
    
    for idx, row in freq_result.iterrows():
        level = row['level']
        label = inscov_labels.get(int(level), str(level))
        print(f"  {label}:")
        print(f"    Proportion: {row['proportion']:.3f}")
        print(f"    SE: {row['se']:.6f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
