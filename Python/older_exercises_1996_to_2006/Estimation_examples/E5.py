"""
AHRQ MEPS Data Users Workshop - Estimation Example E5

This example shows how to compute event-level estimates.

(1) The 2001 MEPS Inpatient Hospital Stays file is used to compute
    mean facility expense per stay.
(2) The 2001 MEPS Office-Based Medical Provider Visits file is used
    to compute mean expense per office visit to a medical provider.

Input files:
    - h59d.sas7bdat (2001 Hospital Stays File)
    - h59g.sas7bdat (2001 Office-Based Visits File)

Python equivalent of: SAS/older_exercises_1996_to_2006/Estimation_examples/E5/E5.sas
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
    print("COMPUTING EVENT-LEVEL ESTIMATES")
    print("=" * 80)
    
    # Inpatient Hospital Stays
    print("\n" + "=" * 80)
    print("MEAN FACILITY EXPENSE PER INPATIENT STAY")
    print("=" * 80)
    
    ip_file = data_dir / "h59d.sas7bdat"
    print(f"\nLoading data from: {ip_file}")
    
    ip2001 = load_sas_data(ip_file, columns=[
        'DUPERSID', 'IPFXP01X', 'PERWT01F', 'VARSTR01', 'VARPSU01'
    ])
    
    print(f"Total inpatient stay records: {len(ip2001):,}")
    
    design_ip = SurveyDesign(
        data=ip2001,
        strata='VARSTR01',
        cluster='VARPSU01',
        weight='PERWT01F'
    )
    
    mean_ip = survey_mean(design_ip, 'IPFXP01X')
    print(f"\nMean facility expense per inpatient stay: ${mean_ip['mean'].values[0]:,.2f}")
    print(f"  SE: ${mean_ip['se'].values[0]:.2f}")
    print(f"  N (unweighted): {len(ip2001):,}")
    print(f"  Sum of weights: {ip2001['PERWT01F'].sum():,.0f}")
    
    # Office-Based Medical Provider Visits
    print("\n" + "=" * 80)
    print("MEAN EXPENSE PER OFFICE VISIT TO A MEDICAL PROVIDER")
    print("=" * 80)
    
    ob_file = data_dir / "h59g.sas7bdat"
    print(f"\nLoading data from: {ob_file}")
    
    ob2001 = load_sas_data(ob_file, columns=[
        'DUPERSID', 'OBXP01X', 'PERWT01F', 'VARSTR01', 'VARPSU01'
    ])
    
    print(f"Total office visit records: {len(ob2001):,}")
    
    design_ob = SurveyDesign(
        data=ob2001,
        strata='VARSTR01',
        cluster='VARPSU01',
        weight='PERWT01F'
    )
    
    mean_ob = survey_mean(design_ob, 'OBXP01X')
    print(f"\nMean expense per office visit: ${mean_ob['mean'].values[0]:,.2f}")
    print(f"  SE: ${mean_ob['se'].values[0]:.2f}")
    print(f"  N (unweighted): {len(ob2001):,}")
    print(f"  Sum of weights: {ob2001['PERWT01F'].sum():,.0f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
