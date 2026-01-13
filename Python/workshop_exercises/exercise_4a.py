"""
Exercise 4a: Pooling MEPS Data Files from Different Years (2015-2016)

This program illustrates how to pool MEPS data files from different years.
The example used is population age 26-30 who are uninsured but have high income.

Data from 2015 and 2016 are pooled.

Variables with year-specific names must be renamed before combining files.
In this program the insurance coverage variables 'INSCOV15' and 'INSCOV16'
are renamed to 'INSCOV'.

Input files:
    - 2016 Full-Year file (h192)
    - 2015 Full-Year file (h181)

Python equivalent of: SAS/workshop_exercises/exercise_4a/Exercise4a.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS")
    
    print("=" * 80)
    print("2018 AHRQ MEPS DATA USERS WORKSHOP")
    print("EXERCISE 4a: POOL MEPS DATA FILES FROM DIFFERENT YEARS (2015 and 2016)")
    print("=" * 80)
    
    # Load 2015 Full-Year file
    fyc15_file = data_dir / "h181.sas7bdat"
    print(f"\nLoading 2015 data from: {fyc15_file}")
    
    yr1 = load_sas_data(
        fyc15_file,
        columns=['DUPERSID', 'INSCOV15', 'PERWT15F', 'VARSTR', 'VARPSU', 'POVCAT15', 'AGELAST', 'TOTSLF15']
    )
    yr1 = yr1[yr1['PERWT15F'] > 0].copy()
    
    # Frequency for 2015 persons age 26-30
    print("\n" + "-" * 60)
    print("UNWEIGHTED FREQUENCY FOR 2015 FY PERSONS WITH AGE 26-30")
    print("-" * 60)
    
    yr1_2630 = yr1[(yr1['AGELAST'] >= 26) & (yr1['AGELAST'] <= 30)]
    print(f"\nTotal persons age 26-30 in 2015: {len(yr1_2630):,}")
    
    povcat_labels = {1: 'Poor/Negative', 2: 'Near Poor', 3: 'Low Income', 4: 'Middle Income', 5: 'High Income'}
    inscov_labels = {1: 'Any Private', 2: 'Public Only', 3: 'Uninsured'}
    
    crosstab = pd.crosstab(
        yr1_2630['POVCAT15'].map(povcat_labels),
        yr1_2630['INSCOV15'].map(inscov_labels),
        margins=True
    )
    print(crosstab)
    
    # Load 2016 Full-Year file
    fyc16_file = data_dir / "h192.sas7bdat"
    print(f"\nLoading 2016 data from: {fyc16_file}")
    
    yr2 = load_sas_data(
        fyc16_file,
        columns=['DUPERSID', 'INSCOV16', 'PERWT16F', 'VARSTR', 'VARPSU', 'POVCAT16', 'AGELAST', 'TOTSLF16']
    )
    yr2 = yr2[yr2['PERWT16F'] > 0].copy()
    
    # Frequency for 2016 persons age 26-30
    print("\n" + "-" * 60)
    print("UNWEIGHTED FREQUENCY FOR 2016 FY PERSONS WITH AGE 26-30")
    print("-" * 60)
    
    yr2_2630 = yr2[(yr2['AGELAST'] >= 26) & (yr2['AGELAST'] <= 30)]
    print(f"\nTotal persons age 26-30 in 2016: {len(yr2_2630):,}")
    
    crosstab = pd.crosstab(
        yr2_2630['POVCAT16'].map(povcat_labels),
        yr2_2630['INSCOV16'].map(inscov_labels),
        margins=True
    )
    print(crosstab)
    
    # Rename year-specific variables prior to combining files
    yr1x = yr1.rename(columns={
        'INSCOV15': 'INSCOV',
        'PERWT15F': 'PERWT',
        'POVCAT15': 'POVCAT',
        'TOTSLF15': 'TOTSLF'
    })
    
    yr2x = yr2.rename(columns={
        'INSCOV16': 'INSCOV',
        'PERWT16F': 'PERWT',
        'POVCAT16': 'POVCAT',
        'TOTSLF16': 'TOTSLF'
    })
    
    # Pool the data
    pool = pd.concat([yr1x, yr2x], ignore_index=True)
    
    # Create pooled weight (divide by number of years)
    pool['POOLWT'] = pool['PERWT'] / 2
    
    # Create subpopulation flag
    # Age 26-30, High Income (POVCAT=5), Uninsured (INSCOV=3)
    pool['SUBPOP'] = np.where(
        (pool['AGELAST'] >= 26) & (pool['AGELAST'] <= 30) & 
        (pool['POVCAT'] == 5) & (pool['INSCOV'] == 3),
        1, 2
    )
    
    # Check missing values
    print("\n" + "-" * 60)
    print("CHECK MISSING VALUES ON THE COMBINED DATA")
    print("-" * 60)
    print(f"\nTotal records in pooled data: {len(pool):,}")
    print(f"Missing values:")
    print(pool[['INSCOV', 'AGELAST', 'POVCAT', 'VARSTR', 'VARPSU', 'POOLWT', 'TOTSLF']].isna().sum())
    
    # Supporting crosstab for subpop flag
    print("\n" + "-" * 60)
    print("SUPPORTING CROSSTAB FOR THE CREATION OF THE SUBPOP FLAG")
    print("-" * 60)
    
    print("\nSUBPOP distribution:")
    print(pool['SUBPOP'].value_counts().sort_index())
    
    subpop1 = pool[pool['SUBPOP'] == 1]
    print(f"\nPersons in subpopulation (Age 26-30, Uninsured, High Income): {len(subpop1):,}")
    
    # Calculate weighted estimate
    print("\n" + "=" * 60)
    print("WEIGHTED ESTIMATE ON TOTSLF FOR COMBINED DATA")
    print("(Age=26-30, Uninsured Whole Year, High Income)")
    print("=" * 60)
    
    # Subset to subpopulation
    pool_sub = pool[pool['SUBPOP'] == 1].copy()
    
    design = SurveyDesign(
        data=pool_sub,
        strata='VARSTR',
        cluster='VARPSU',
        weight='POOLWT'
    )
    
    mean_result = survey_mean(design, 'TOTSLF')
    
    print(f"\nN (unweighted): {len(pool_sub):,}")
    print(f"Mean (Total Amount Paid by Self/Family): ${mean_result['mean'].values[0]:,.1f}")
    print(f"SE of Mean: ${mean_result['se'].values[0]:.4f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
