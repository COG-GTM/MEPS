"""
AHRQ MEPS Data Users Workshop - Misc Example M9

This example uses the 2005 Full-Year file to output descriptive statistics
showing health insurance status and healthcare utilization.

Types of events used:
- Prescribed Medicine Use (RXTOT05)
- Office-Based Visits (OBTOT05)
- Emergency Dept. Visits (ERTOT05)

Input file: h97.sas7bdat (2005 Full-Year Data File)

Python equivalent of: SAS/older_exercises_1996_to_2006/Misc_examples/M9/M9.sas
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
    print("AHRQ MEPS DATA USERS WORKSHOP")
    print("HEALTH INSURANCE STATUS AND HEALTHCARE UTILIZATION")
    print("=" * 80)
    
    # Labels
    unins_labels = {1: 'Uninsured', 2: 'Insured'}
    inscov_labels = {1: 'Any Private', 2: 'Public Only', 3: 'Uninsured'}
    
    # Load FYC file
    fyc_file = data_dir / "h97.sas7bdat"
    print(f"\nLoading data from: {fyc_file}")
    
    puf97 = load_sas_data(fyc_file, columns=[
        'UNINS05', 'INSCOV05', 'RXTOT05', 'OBTOTV05', 'ERTOT05',
        'VARPSU', 'VARSTR', 'PERWT05F'
    ])
    
    print(f"Total records: {len(puf97):,}")
    
    # Create survey design
    design = SurveyDesign(
        data=puf97,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT05F'
    )
    
    # Mean number of prescriptions and refills by insurance coverage status
    print("\n" + "=" * 80)
    print("MEAN NUMBER OF PRESCRIPTIONS AND REFILLS BY INSURANCE COVERAGE STATUS")
    print("=" * 80)
    
    # By UNINS05
    print("\nBy Uninsured Status (UNINS05):")
    print(f"{'Status':<20} {'N':>10} {'Sum Weight':>15} {'Mean':>10} {'SE':>10}")
    print("-" * 65)
    
    for unins in [1, 2]:
        subset = puf97[puf97['UNINS05'] == unins].copy()
        if len(subset) > 0:
            design_sub = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT05F'
            )
            result = survey_mean(design_sub, 'RXTOT05')
            n = len(subset)
            sumwgt = subset['PERWT05F'].sum()
            mean = result['mean'].values[0]
            se = result['se'].values[0]
            print(f"{unins_labels[unins]:<20} {n:>10,} {sumwgt:>15,.0f} {mean:>10.2f} {se:>10.4f}")
    
    # By INSCOV05
    print("\nBy Insurance Coverage (INSCOV05):")
    print(f"{'Status':<20} {'N':>10} {'Sum Weight':>15} {'Mean':>10} {'SE':>10}")
    print("-" * 65)
    
    for inscov in [1, 2, 3]:
        subset = puf97[puf97['INSCOV05'] == inscov].copy()
        if len(subset) > 0:
            design_sub = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT05F'
            )
            result = survey_mean(design_sub, 'RXTOT05')
            n = len(subset)
            sumwgt = subset['PERWT05F'].sum()
            mean = result['mean'].values[0]
            se = result['se'].values[0]
            print(f"{inscov_labels[inscov]:<20} {n:>10,} {sumwgt:>15,.0f} {mean:>10.2f} {se:>10.4f}")
    
    # Mean number of office visits by insurance coverage status
    print("\n" + "=" * 80)
    print("MEAN NUMBER OF OFFICE VISITS BY INSURANCE COVERAGE STATUS")
    print("=" * 80)
    
    # By UNINS05
    print("\nBy Uninsured Status (UNINS05):")
    print(f"{'Status':<20} {'N':>10} {'Sum Weight':>15} {'Mean':>10} {'SE':>10}")
    print("-" * 65)
    
    for unins in [1, 2]:
        subset = puf97[puf97['UNINS05'] == unins].copy()
        if len(subset) > 0:
            design_sub = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT05F'
            )
            result = survey_mean(design_sub, 'OBTOTV05')
            n = len(subset)
            sumwgt = subset['PERWT05F'].sum()
            mean = result['mean'].values[0]
            se = result['se'].values[0]
            print(f"{unins_labels[unins]:<20} {n:>10,} {sumwgt:>15,.0f} {mean:>10.2f} {se:>10.4f}")
    
    # By INSCOV05
    print("\nBy Insurance Coverage (INSCOV05):")
    print(f"{'Status':<20} {'N':>10} {'Sum Weight':>15} {'Mean':>10} {'SE':>10}")
    print("-" * 65)
    
    for inscov in [1, 2, 3]:
        subset = puf97[puf97['INSCOV05'] == inscov].copy()
        if len(subset) > 0:
            design_sub = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT05F'
            )
            result = survey_mean(design_sub, 'OBTOTV05')
            n = len(subset)
            sumwgt = subset['PERWT05F'].sum()
            mean = result['mean'].values[0]
            se = result['se'].values[0]
            print(f"{inscov_labels[inscov]:<20} {n:>10,} {sumwgt:>15,.0f} {mean:>10.2f} {se:>10.4f}")
    
    # Mean number of emergency dept visits by insurance coverage status
    print("\n" + "=" * 80)
    print("MEAN NUMBER OF EMERGENCY DEPT. VISITS BY INSURANCE COVERAGE STATUS")
    print("=" * 80)
    
    # By UNINS05
    print("\nBy Uninsured Status (UNINS05):")
    print(f"{'Status':<20} {'N':>10} {'Sum Weight':>15} {'Mean':>10} {'SE':>10}")
    print("-" * 65)
    
    for unins in [1, 2]:
        subset = puf97[puf97['UNINS05'] == unins].copy()
        if len(subset) > 0:
            design_sub = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT05F'
            )
            result = survey_mean(design_sub, 'ERTOT05')
            n = len(subset)
            sumwgt = subset['PERWT05F'].sum()
            mean = result['mean'].values[0]
            se = result['se'].values[0]
            print(f"{unins_labels[unins]:<20} {n:>10,} {sumwgt:>15,.0f} {mean:>10.2f} {se:>10.4f}")
    
    # By INSCOV05
    print("\nBy Insurance Coverage (INSCOV05):")
    print(f"{'Status':<20} {'N':>10} {'Sum Weight':>15} {'Mean':>10} {'SE':>10}")
    print("-" * 65)
    
    for inscov in [1, 2, 3]:
        subset = puf97[puf97['INSCOV05'] == inscov].copy()
        if len(subset) > 0:
            design_sub = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT05F'
            )
            result = survey_mean(design_sub, 'ERTOT05')
            n = len(subset)
            sumwgt = subset['PERWT05F'].sum()
            mean = result['mean'].values[0]
            se = result['se'].values[0]
            print(f"{inscov_labels[inscov]:<20} {n:>10,} {sumwgt:>15,.0f} {mean:>10.2f} {se:>10.4f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
