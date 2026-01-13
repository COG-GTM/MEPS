"""
AHRQ MEPS Data Users Workshop - Misc Example M3

This example shows the use of ID variables on different MEPS public-use
files (PUFs) and how to use these ID variables to merge MEPS files.

DUPERSID (HC-097) is a person-level identifier.
CONDIDX (HC-096) is a person-condition-level identifier.

Note: When processing data across several MEPS years, DUPERSID (and
other IDs) may not be unique. Starting with MEPS 2004, Panel 9, IDs
duplicate earlier years. Always include PANEL in merges.

Input files:
    - h97.sas7bdat (2005 Full-Year Data File)
    - h96.sas7bdat (2005 Conditions File)

Python equivalent of: SAS/older_exercises_1996_to_2006/Misc_examples/M3/M3.sas
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
    print("AHRQ MEPS DATA USERS WORKSHOP")
    print("ILLUSTRATING THE USE OF ID VARIABLES (DUPERSID, CONDIDX)")
    print("=" * 80)
    
    # Labels
    sex_labels = {1: 'Male', 2: 'Female'}
    yesno_labels = {-9: 'Not Ascertained', -1: 'Inapplicable', 1: 'Yes', 2: 'No'}
    
    # Load Full-Year file
    print("\n" + "-" * 60)
    print("GET DUPERSID AND OTHER VARIABLES FROM HC-097")
    print("-" * 60)
    
    fyc_file = data_dir / "h97.sas7bdat"
    print(f"Loading FYC data from: {fyc_file}")
    
    fy2005 = load_sas_data(fyc_file, columns=[
        'DUID', 'PID', 'DUPERSID', 'PANEL', 'AGE05X', 'SEX', 'PERWT05F', 'VARSTR', 'VARPSU'
    ])
    fy2005 = fy2005.sort_values(['DUPERSID', 'PANEL'])
    
    print(f"Total person records: {len(fy2005):,}")
    
    print("\nSample of HC-097 records to show DUPERSID:")
    print(fy2005[['DUID', 'PID', 'DUPERSID', 'PANEL', 'AGE05X', 'SEX']].iloc[39:90].to_string(index=False))
    
    # Load Conditions file
    print("\n" + "-" * 60)
    print("GET DUPERSID, CONDIDX AND OTHER VARIABLES FROM HC-096")
    print("-" * 60)
    
    cond_file = data_dir / "h96.sas7bdat"
    print(f"Loading conditions data from: {cond_file}")
    
    cond2005 = load_sas_data(cond_file, columns=[
        'DUPERSID', 'PANEL', 'CONDN', 'CONDIDX', 'INJURY', 'ICD9CODX'
    ])
    cond2005 = cond2005.sort_values(['DUPERSID', 'PANEL', 'CONDIDX'])
    
    print(f"Total condition records: {len(cond2005):,}")
    
    print("\nSample of HC-096 records to show DUPERSID and CONDIDX:")
    print(cond2005[['DUPERSID', 'PANEL', 'CONDN', 'CONDIDX', 'INJURY', 'ICD9CODX']].iloc[139:190].to_string(index=False))
    
    # Merge files
    print("\n" + "-" * 60)
    print("MERGE FILES TO CONNECT PERSON INFO WITH CONDITION INFO")
    print("(Using DUPERSID and PANEL)")
    print("-" * 60)
    
    # Full merge (all records)
    condinfo = fy2005.merge(cond2005, on=['DUPERSID', 'PANEL'], how='outer')
    print(f"\nFull merge (outer join): {len(condinfo):,} records")
    
    print("\nSample of merged records:")
    cols = ['DUPERSID', 'PANEL', 'CONDIDX', 'AGE05X', 'SEX', 'INJURY', 'ICD9CODX']
    print(condinfo[cols].iloc[139:190].to_string(index=False))
    
    # Inner merge (only matching records)
    print("\n" + "-" * 60)
    print("MERGE FILES - ONLY KEEP MATCHING RECORDS")
    print("-" * 60)
    
    condinfo_b = fy2005.merge(cond2005, on=['DUPERSID', 'PANEL'], how='inner')
    print(f"\nInner merge: {len(condinfo_b):,} records")
    
    print("\nSample of merged records (matched only):")
    print(condinfo_b[cols].iloc[139:190].to_string(index=False))
    
    print("\n" + "=" * 80)
    print("KEY TAKEAWAYS")
    print("=" * 80)
    print("""
1. DUPERSID is the person-level identifier used across MEPS files.
   - Format: 8 characters (DUID + PID)
   - Unique within a single year of data

2. CONDIDX is the condition-level identifier.
   - Format: DUPERSID + condition number
   - Unique identifier for each condition record

3. When merging files:
   - Always include PANEL in the merge key
   - Starting with MEPS 2004 (Panel 9), IDs may duplicate earlier years
   - Use inner join (how='inner') to keep only matching records
   - Use outer join (how='outer') to keep all records

4. Merge patterns:
   - Person-to-condition: One person can have multiple conditions
   - The merged file will be at the condition level (one row per condition)
""")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
