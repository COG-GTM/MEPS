"""
AHRQ MEPS Data Users Workshop - Misc Example M5

This example shows the difference between two uses of the term
"priority condition" in MEPS:

1. The MEPS Supplemental Priority Conditions (PC) section asks about
   the existence of certain priority conditions. These are on the
   Full-Year file (e.g., DIABDX53, ASTHDX53, HIBPDX53, EMPHDX53).

2. The Conditions file has conditions flagged as priority by the
   variable PRIOLIST. These come from reports of being bothered by
   the condition, associated events, or follow-up questions.

Input files:
    - h96.sas7bdat (2005 Medical Conditions File)
    - h97.sas7bdat (2005 Full-Year Data File)

Python equivalent of: SAS/older_exercises_1996_to_2006/Misc_examples/M5/M5.sas
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
    print("TWO DIFFERENT SETS OF PRIORITY CONDITIONS")
    print("=" * 80)
    
    # Labels
    icd9_labels = {
        '250': 'Diabetes Mellitus',
        '401': 'Essential Hypertension',
        '492': 'Emphysema',
        '493': 'Asthma'
    }
    
    # Load Conditions file
    print("\n" + "-" * 60)
    print("VARIABLES FROM 2005 CONDITIONS FILE")
    print("-" * 60)
    
    cond_file = data_dir / "h96.sas7bdat"
    print(f"Loading conditions data from: {cond_file}")
    
    cond2005 = load_sas_data(cond_file, columns=['DUPERSID', 'CONDIDX', 'ICD9CODX', 'PRIOLIST'])
    
    # Filter for selected conditions
    cond2005 = cond2005[cond2005['ICD9CODX'].isin(['250', '401', '492', '493'])].copy()
    print(f"Selected condition records: {len(cond2005):,}")
    
    print("\nCondition-level frequencies:")
    print(cond2005['ICD9CODX'].map(icd9_labels).value_counts())
    
    print("\nCondition by PRIOLIST flag:")
    print(pd.crosstab(cond2005['ICD9CODX'].map(icd9_labels), 
                      cond2005['PRIOLIST'].map({1: 'Yes', 2: 'No'}), margins=True))
    
    # Create person-level indicators from conditions file
    print("\n" + "-" * 60)
    print("PERSON-LEVEL INDICATORS FROM CONDITIONS FILE")
    print("-" * 60)
    
    # Create indicators for each condition
    condpers = cond2005.groupby('DUPERSID').apply(
        lambda x: pd.Series({
            'C_DIABETES': 1 if '250' in x['ICD9CODX'].values else 0,
            'C_HYPERTENSION': 1 if '401' in x['ICD9CODX'].values else 0,
            'C_EMPHYSEMA': 1 if '492' in x['ICD9CODX'].values else 0,
            'C_ASTHMA': 1 if '493' in x['ICD9CODX'].values else 0
        })
    ).reset_index()
    
    print(f"Persons with selected conditions: {len(condpers):,}")
    
    print("\nPerson-level frequencies (from Conditions file):")
    for col in ['C_DIABETES', 'C_ASTHMA', 'C_HYPERTENSION', 'C_EMPHYSEMA']:
        yes_count = (condpers[col] == 1).sum()
        print(f"  {col}: {yes_count:,} persons")
    
    # Load Full-Year file
    print("\n" + "-" * 60)
    print("VARIABLES FROM 2005 FULL-YEAR FILE")
    print("-" * 60)
    
    fyc_file = data_dir / "h97.sas7bdat"
    print(f"Loading FYC data from: {fyc_file}")
    
    fy2005 = load_sas_data(fyc_file, columns=[
        'DUPERSID', 'DIABDX53', 'ASTHDX53', 'HIBPDX53', 'EMPHDX53',
        'VARPSU', 'VARSTR', 'PERWT05F'
    ])
    
    # Rename and recode PC variables
    fy2005 = fy2005.rename(columns={
        'DIABDX53': 'PC_DIABETES',
        'ASTHDX53': 'PC_ASTHMA',
        'HIBPDX53': 'PC_HYPERTENSION',
        'EMPHDX53': 'PC_EMPHYSEMA'
    })
    
    # Recode: 1=Yes, 2=No/-9/-8/-7/-1 -> 0
    for col in ['PC_DIABETES', 'PC_ASTHMA', 'PC_HYPERTENSION', 'PC_EMPHYSEMA']:
        fy2005[col] = np.where(fy2005[col] == 1, 1, 0)
    
    print(f"Total persons: {len(fy2005):,}")
    
    print("\nPerson-level frequencies (from Full-Year file):")
    for col in ['PC_DIABETES', 'PC_ASTHMA', 'PC_HYPERTENSION', 'PC_EMPHYSEMA']:
        yes_count = (fy2005[col] == 1).sum()
        print(f"  {col}: {yes_count:,} persons")
    
    # Merge conditions and full-year files
    print("\n" + "=" * 80)
    print("COMPARISON: CONDITIONS FILE vs FULL-YEAR FILE")
    print("=" * 80)
    
    fycond05 = fy2005.merge(condpers, on='DUPERSID', how='left')
    
    # Fill missing condition indicators with 0
    for col in ['C_DIABETES', 'C_HYPERTENSION', 'C_EMPHYSEMA', 'C_ASTHMA']:
        fycond05[col] = fycond05[col].fillna(0).astype(int)
    
    # Count merge results
    both = len(fycond05[fycond05['C_DIABETES'].notna()])
    
    print(f"\nTotal persons in merged file: {len(fycond05):,}")
    
    # Cross-tabulations
    comparisons = [
        ('C_DIABETES', 'PC_DIABETES', 'Diabetes'),
        ('C_ASTHMA', 'PC_ASTHMA', 'Asthma'),
        ('C_HYPERTENSION', 'PC_HYPERTENSION', 'Hypertension'),
        ('C_EMPHYSEMA', 'PC_EMPHYSEMA', 'Emphysema')
    ]
    
    for c_col, pc_col, label in comparisons:
        print(f"\n{label}:")
        print(f"  C_{label.upper()} (Conditions file) vs PC_{label.upper()} (Full-Year file)")
        ct = pd.crosstab(
            fycond05[c_col].map({0: 'No', 1: 'Yes'}),
            fycond05[pc_col].map({0: 'No', 1: 'Yes'}),
            margins=True
        )
        print(ct)
    
    print("\n" + "=" * 80)
    print("KEY TAKEAWAY")
    print("=" * 80)
    print("""
The two sources of priority condition information may not match because:

1. Full-Year file PC questions ask "Has person EVER been told by a doctor
   that they have (condition)?" - This captures lifetime prevalence.

2. Conditions file captures conditions that were:
   - Reported as bothering the person during the year
   - Associated with an event or prescription during the year
   - Associated with a disability day during the year
   - Flagged as priority (PRIOLIST=1)

The Conditions file captures conditions relevant to the survey year,
while the Full-Year PC questions capture lifetime diagnoses.
""")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
