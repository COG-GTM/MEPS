"""
AHRQ MEPS Data Users Workshop - Misc Example M10

This example compares hospital inpatient expenditures (facility, physician,
total) for stays that do and do not include facility expenditures for the
preceding emergency room visit.

Records with preceding ER facility expenditures are identified by the
variable ERHEVIDX.

Input file: h77d.sas7bdat (2003 Hospital Inpatient File)

Python equivalent of: SAS/older_exercises_1996_to_2006/Misc_examples/M10/M10.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_glm


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS/DATA")
    
    print("=" * 80)
    print("AHRQ MEPS DATA USERS WORKSHOP")
    print("HOSPITAL INPATIENT STAY EXPENDITURES:")
    print("COMPARING STAYS WITH AND WITHOUT PRECEDING ER FACILITY EXPENDITURES")
    print("=" * 80)
    
    # Labels
    er_labels = {0: 'ER_YES (Includes ER Facility Exp)', 1: 'ER_NO (No ER Facility Exp)'}
    
    # Load 2003 Hospital Inpatient file
    ip_file = data_dir / "h77d.sas7bdat"
    print(f"\nLoading IP data from: {ip_file}")
    
    staz2003 = load_sas_data(ip_file, columns=[
        'DUPERSID', 'ERHEVIDX', 'IPXP03X', 'IPFXP03X', 'IPDXP03X',
        'PERWT03F', 'VARSTR', 'VARPSU'
    ])
    
    # Create ER facility expense indicator
    # ER_FACEX = 0 if includes ER facility exp (ERHEVIDX != -1)
    # ER_FACEX = 1 if no ER facility exp (ERHEVIDX == -1)
    staz2003['ER_FACEX'] = np.where(staz2003['ERHEVIDX'] != -1, 0, 1)
    
    print(f"Total IP stay records: {len(staz2003):,}")
    print(f"Stays with ER facility exp: {(staz2003['ER_FACEX'] == 0).sum():,}")
    print(f"Stays without ER facility exp: {(staz2003['ER_FACEX'] == 1).sum():,}")
    
    # Create survey design
    design = SurveyDesign(
        data=staz2003,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT03F'
    )
    
    # Total 2003 IP Expenditures
    print("\n" + "=" * 80)
    print("TOTAL 2003 IP EXPENDITURES (IPXP03X)")
    print("=" * 80)
    
    result = survey_mean(design, 'IPXP03X')
    print(f"\nOverall:")
    print(f"  N: {len(staz2003):,}")
    print(f"  Sum Weight: {staz2003['PERWT03F'].sum():,.0f}")
    print(f"  Mean: ${result['mean'].values[0]:,.2f}")
    print(f"  SE: ${result['se'].values[0]:.2f}")
    
    # By ER facility expense status
    print("\nBy ER Facility Expense Status:")
    print(f"{'Status':<45} {'N':>8} {'Mean':>12} {'SE':>10}")
    print("-" * 75)
    
    for er_val in [0, 1]:
        subset = staz2003[staz2003['ER_FACEX'] == er_val].copy()
        if len(subset) > 0:
            design_sub = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT03F'
            )
            result = survey_mean(design_sub, 'IPXP03X')
            print(f"{er_labels[er_val]:<45} {len(subset):>8,} ${result['mean'].values[0]:>10,.2f} ${result['se'].values[0]:>8.2f}")
    
    # Regression: IPXP03X = ER_FACEX
    print("\nRegression: IPXP03X ~ ER_FACEX")
    reg_result = survey_glm(design, 'IPXP03X', ['ER_FACEX'])
    print(reg_result)
    
    # Facility IP Expenditures
    print("\n" + "=" * 80)
    print("FACILITY IP EXPENDITURES (IPFXP03X)")
    print("=" * 80)
    
    print("\nBy ER Facility Expense Status:")
    print(f"{'Status':<45} {'N':>8} {'Mean':>12} {'SE':>10}")
    print("-" * 75)
    
    for er_val in [0, 1]:
        subset = staz2003[staz2003['ER_FACEX'] == er_val].copy()
        if len(subset) > 0:
            design_sub = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT03F'
            )
            result = survey_mean(design_sub, 'IPFXP03X')
            print(f"{er_labels[er_val]:<45} {len(subset):>8,} ${result['mean'].values[0]:>10,.2f} ${result['se'].values[0]:>8.2f}")
    
    # Regression: IPFXP03X = ER_FACEX
    print("\nRegression: IPFXP03X ~ ER_FACEX")
    reg_result = survey_glm(design, 'IPFXP03X', ['ER_FACEX'])
    print(reg_result)
    
    # Physician IP Expenditures
    print("\n" + "=" * 80)
    print("PHYSICIAN IP EXPENDITURES (IPDXP03X)")
    print("=" * 80)
    
    print("\nBy ER Facility Expense Status:")
    print(f"{'Status':<45} {'N':>8} {'Mean':>12} {'SE':>10}")
    print("-" * 75)
    
    for er_val in [0, 1]:
        subset = staz2003[staz2003['ER_FACEX'] == er_val].copy()
        if len(subset) > 0:
            design_sub = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT03F'
            )
            result = survey_mean(design_sub, 'IPDXP03X')
            print(f"{er_labels[er_val]:<45} {len(subset):>8,} ${result['mean'].values[0]:>10,.2f} ${result['se'].values[0]:>8.2f}")
    
    # Regression: IPDXP03X = ER_FACEX
    print("\nRegression: IPDXP03X ~ ER_FACEX")
    reg_result = survey_glm(design, 'IPDXP03X', ['ER_FACEX'])
    print(reg_result)
    
    print("\n" + "=" * 80)
    print("KEY TAKEAWAY")
    print("=" * 80)
    print("""
Hospital inpatient stays that include facility expenditures for the
preceding emergency room visit (ERHEVIDX != -1) may have higher total
expenditures because they include both the ER and IP components.

When analyzing IP expenditures, researchers should be aware of this
and consider whether to include or exclude stays with preceding ER
facility expenditures depending on the research question.
""")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
