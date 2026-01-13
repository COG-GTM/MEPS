"""
AHRQ MEPS Data Users Workshop - Linking Example L1A

This example shows how to:
(1) Identify 2001 jobs that began in 2000
(2) Identify first-reported 2000 jobs
(3) Update missing 2001 values with 2000 values

Input files:
    - h40.sas7bdat (2000 Jobs)
    - h56.sas7bdat (2001 Jobs)

Python equivalent of: SAS/older_exercises_1996_to_2006/Linking_examples/L1A/L1A.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from meps_utils import load_sas_data


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS/DATA")
    
    print("=" * 80)
    print("AHRQ MEPS DATA USERS WORKSHOP (LINKING)")
    print("Link 2000 and 2001 JOBS Files")
    print("=" * 80)
    
    # Load 2000 Jobs file
    jobs00_file = data_dir / "h40.sas7bdat"
    print(f"\nLoading 2000 jobs data from: {jobs00_file}")
    
    h40 = load_sas_data(jobs00_file)
    print(f"Total 2000 job records: {len(h40):,}")
    
    # Load 2001 Jobs file
    jobs01_file = data_dir / "h56.sas7bdat"
    print(f"Loading 2001 jobs data from: {jobs01_file}")
    
    h56 = load_sas_data(jobs01_file)
    print(f"Total 2001 job records: {len(h56):,}")
    
    # Sample listing for specific persons
    sample_ids = ['80001021', '80005018', '80005025', '80006012', '80006029']
    
    print("\n" + "=" * 80)
    print("SAMPLE LISTING: ALL JOB RECORDS FOR PERSONS WITH SAME JOB IN 2000 AND 2001")
    print("Variables of Interest: SICKPAY, PAYDRVST, PAYVACTN")
    print("=" * 80)
    
    # 2000 records (rounds 1,2)
    s00 = h40[(h40['DUPERSID'].isin(sample_ids)) & (h40['RN'].isin([1, 2]))].copy()
    s00['YEAR'] = 2000
    
    # 2001 records
    s01 = h56[h56['DUPERSID'].isin(sample_ids)].copy()
    s01['YEAR'] = 2001
    
    # Combine and sort
    combined = pd.concat([s00, s01], ignore_index=True)
    combined = combined.sort_values(['DUPERSID', 'JOBSN', 'RN'])
    
    print("\nSample records:")
    cols = ['DUPERSID', 'YEAR', 'RN', 'JOBSN', 'SUBTYPE', 'STILLAT']
    if 'SICKPAY' in combined.columns:
        cols.extend(['SICKPAY', 'PAYDRVST', 'PAYVACTN'])
    print(combined[cols].head(30).to_string(index=False))
    
    # Identify 2001 Current Main Jobs that began in 2000
    print("\n" + "=" * 80)
    print("2001 CURRENT MAIN JOBS THAT BEGAN IN 2000")
    print("=" * 80)
    
    # 2001 CMJs (Panel 5, Round 3) that began in 2000
    cmj01 = h56[
        (h56['PANEL'] == 5) & 
        (h56['RN'] == 3) & 
        (h56['SUBTYPE'] == 1) & 
        (h56['STILLAT'] == 1)
    ].copy()
    
    print(f"\n2001 (Panel 5 Round 3) CMJ records: {len(cmj01):,}")
    
    if 'SICKPAY' in cmj01.columns:
        print("\nSICKPAY distribution:")
        print(cmj01['SICKPAY'].value_counts(dropna=False).sort_index())
    
    # Identify newly-reported 2000 CMJs (Panel 5, Rounds 1,2)
    cmj00 = h40[
        (h40['PANEL'] == 5) & 
        (h40['RN'].isin([1, 2])) & 
        (h40['SUBTYPE'] == 1) & 
        (h40['STILLAT'] == -1)
    ].copy()
    
    print(f"\n2000 (Panel 5 Round 1,2) CMJ records: {len(cmj00):,}")
    
    if 'SICKPAY' in cmj00.columns:
        print("\nSICKPAY distribution:")
        print(cmj00['SICKPAY'].value_counts(dropna=False).sort_index())
    
    # Merge records from both years
    print("\n" + "=" * 80)
    print("MERGING 2000 AND 2001 RECORDS")
    print("=" * 80)
    
    # Sort both files
    cmj01 = cmj01.sort_values(['DUPERSID', 'JOBSN', 'RN'])
    cmj00 = cmj00.sort_values(['DUPERSID', 'JOBSN', 'RN'])
    
    # Rename 2000 variables
    rename_cols = {}
    if 'SICKPAY' in cmj00.columns:
        rename_cols['SICKPAY'] = 'SICKPAYX'
    if 'PAYDRVST' in cmj00.columns:
        rename_cols['PAYDRVST'] = 'PAYDRVSTX'
    if 'PAYVACTN' in cmj00.columns:
        rename_cols['PAYVACTN'] = 'PAYVACTNX'
    
    cmj00_renamed = cmj00.rename(columns=rename_cols)
    
    # Merge on DUPERSID and JOBSN
    merge_cols = ['DUPERSID', 'JOBSN']
    keep_cols_01 = merge_cols + ['PANEL', 'SUBTYPE', 'STILLAT']
    keep_cols_00 = merge_cols + list(rename_cols.values())
    
    if 'SICKPAY' in cmj01.columns:
        keep_cols_01.extend(['SICKPAY', 'PAYDRVST', 'PAYVACTN'])
    
    new = cmj01[keep_cols_01].merge(
        cmj00_renamed[[c for c in keep_cols_00 if c in cmj00_renamed.columns]],
        on=merge_cols,
        how='inner'
    )
    
    print(f"\nMerged records: {len(new):,}")
    
    # Show cross-tabulation of original vs first-reported values
    if 'SICKPAYX' in new.columns and 'SICKPAY' in new.columns:
        print("\n" + "-" * 60)
        print("CROSS-TABULATION: SICKPAYX (2000) vs SICKPAY (2001)")
        print("-" * 60)
        print(pd.crosstab(new['SICKPAYX'], new['SICKPAY'], margins=True))
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
