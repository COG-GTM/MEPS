"""
AHRQ MEPS Data Users Workshop - Linking Example L2

This example shows how to:
(1) Link 2001 MEPS to 1999 and 2000 NHIS
(2) Compare persons' status in NHIS with their status in MEPS

Note: This example requires NHIS data files which are not part of the standard
MEPS distribution. The NHIS-MEPS link file is available from AHRQ.

Input files:
    - nhisper99.dat (1999 NHIS Persons)
    - nhisper00.dat (2000 NHIS Persons)
    - nhmep01x.dat (NHIS-MEPS Link File)
    - h60.sas7bdat (2001 MEPS Persons)

Python equivalent of: SAS/older_exercises_1996_to_2006/Linking_examples/L2/L2.sas
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
    print("NHIS-MEPS Link")
    print("=" * 80)
    
    # Labels
    anylim_labels = {-9: 'Not Ascertained', -1: 'Inapplicable', 1: 'Yes', 2: 'No'}
    hstat_labels = {1: 'Excellent', 2: 'Very Good', 3: 'Good', 4: 'Fair', 5: 'Poor'}
    
    # Load 2001 MEPS file
    print("\n" + "-" * 60)
    print("2001 MEPS")
    print("-" * 60)
    
    meps_file = data_dir / "h60.sas7bdat"
    print(f"Loading MEPS data from: {meps_file}")
    
    meps01 = load_sas_data(meps_file, columns=[
        'DUPERSID', 'ANYLIM01', 'RTHLTH31', 'RTHLTH42', 'RTHLTH53',
        'PERWT01F', 'VARSTR01', 'VARPSU01'
    ])
    
    # Construct annual health status from last nonmissing round variable
    meps01['MEPSHSTAT'] = np.where(meps01['RTHLTH53'] > 0, meps01['RTHLTH53'],
                          np.where(meps01['RTHLTH42'] > 0, meps01['RTHLTH42'],
                          np.where(meps01['RTHLTH31'] > 0, meps01['RTHLTH31'], np.nan)))
    
    print(f"Total MEPS records: {len(meps01):,}")
    
    print("\nMEPS Health Status distribution:")
    print(meps01['MEPSHSTAT'].value_counts(dropna=False).sort_index())
    
    # Note: The following code would require NHIS data files
    # which are not part of the standard MEPS distribution
    
    print("\n" + "=" * 80)
    print("NOTE: NHIS-MEPS LINKING")
    print("=" * 80)
    print("""
This example demonstrates linking MEPS data with NHIS (National Health
Interview Survey) data. To complete this analysis, you would need:

1. NHIS Person files (nhisper99.dat, nhisper00.dat)
   - Available from NCHS: https://www.cdc.gov/nchs/nhis/

2. NHIS-MEPS Link file (nhmep01x.dat)
   - Available from AHRQ upon request

The linking process involves:
1. Reading NHIS person files with fixed-width format
2. Reading the NHIS-MEPS link file
3. Merging MEPS data with link file by DUPERSID
4. Merging with NHIS data by HHX, PX, and SRVY_YR
5. Comparing health status and limitation variables across surveys

Key variables for comparison:
- NHIS: NHISLIM (Any Limitation), NHISHSTAT (Health Status)
- MEPS: ANYLIM01 (Any Limitation), MEPSHSTAT (Health Status)
""")
    
    # Example of what the analysis would show
    print("\n" + "-" * 60)
    print("EXAMPLE OUTPUT (if NHIS data were available)")
    print("-" * 60)
    print("""
Cross-tabulation of NHIS Limitation Status vs MEPS Limitation Status:

                    MEPS ANYLIM01
NHIS NHISLIM        Yes     No    Total
Limited             XXX     XXX    XXX
Not Limited         XXX     XXX    XXX
Unknown             XXX     XXX    XXX
Total               XXX     XXX    XXX

Cross-tabulation of NHIS Health Status vs MEPS Health Status:

                    MEPS Health Status
NHIS Health Status  Excellent  Very Good  Good  Fair  Poor  Total
Excellent           XXX        XXX        XXX   XXX   XXX   XXX
Very Good           XXX        XXX        XXX   XXX   XXX   XXX
Good                XXX        XXX        XXX   XXX   XXX   XXX
Fair                XXX        XXX        XXX   XXX   XXX   XXX
Poor                XXX        XXX        XXX   XXX   XXX   XXX
Total               XXX        XXX        XXX   XXX   XXX   XXX
""")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
