"""
AHRQ MEPS Data Users Workshop - Misc Example M1

This example shows the need for using weight variables when analyzing
MEPS data for national estimates.

Input file: h97.sas7bdat (2005 Full-Year Data File)

Python equivalent of: SAS/older_exercises_1996_to_2006/Misc_examples/M1/M1.sas
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
    print("EFFECT OF WEIGHT VARIABLE ON RACE/ETHNICITY PERCENTAGE")
    print("=" * 80)
    
    # Labels
    racethnx_labels = {
        1: 'Hispanic',
        2: 'Black-No Other Race/Not Hispanic',
        3: 'Asian-No Other Race/Not Hispanic',
        4: 'Other/Not Hispanic'
    }
    
    # Load FYC file
    fyc_file = data_dir / "h97.sas7bdat"
    print(f"\nLoading data from: {fyc_file}")
    
    puf97 = load_sas_data(fyc_file, columns=['RACETHNX', 'PERWT05F'])
    print(f"Total records: {len(puf97):,}")
    
    # Create unweighted percentages
    print("\n" + "=" * 80)
    print("COMPARISON OF UNWEIGHTED VS WEIGHTED PERCENTAGES")
    print("=" * 80)
    
    # Unweighted
    unwt = puf97['RACETHNX'].value_counts(normalize=True) * 100
    unwt = unwt.sort_index()
    
    # Weighted
    wt_total = puf97['PERWT05F'].sum()
    wt = puf97.groupby('RACETHNX')['PERWT05F'].sum() / wt_total * 100
    wt = wt.sort_index()
    
    # Combine results
    print(f"\n{'Race/Ethnicity':<45} {'Unweighted %':>15} {'Weighted %':>15}")
    print("-" * 80)
    
    for racethnx in sorted(puf97['RACETHNX'].unique()):
        if racethnx in racethnx_labels:
            label = racethnx_labels[racethnx]
        else:
            label = f'Category {racethnx}'
        
        unwt_pct = unwt.get(racethnx, 0)
        wt_pct = wt.get(racethnx, 0)
        
        print(f"{label:<45} {unwt_pct:>14.2f}% {wt_pct:>14.2f}%")
    
    print("-" * 80)
    print(f"{'Total':<45} {100.00:>14.2f}% {100.00:>14.2f}%")
    
    print("\n" + "=" * 80)
    print("KEY TAKEAWAY")
    print("=" * 80)
    print("""
The unweighted percentages reflect the sample composition, while the
weighted percentages reflect the national population estimates.

MEPS oversamples certain populations (e.g., minorities, low-income)
to ensure adequate sample sizes for subgroup analyses. Using weights
adjusts for this oversampling and produces nationally representative
estimates.

ALWAYS use weights when producing national estimates from MEPS data.
""")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
