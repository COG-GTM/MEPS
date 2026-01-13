"""
AHRQ MEPS Data Users Workshop - Misc Example M2

This example shows the need for using the stratum and PSU variables
when analyzing MEPS data for national estimates. That is, taking the
MEPS complex design properties into account.

Input file: h97.sas7bdat (2005 Full-Year Data File)

Python equivalent of: SAS/older_exercises_1996_to_2006/Misc_examples/M2/M2.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_total


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS/DATA")
    
    print("=" * 80)
    print("AHRQ MEPS DATA USERS WORKSHOP")
    print("EFFECT OF STRATA AND PSU VARIABLES ON COMPUTING")
    print("STANDARD ERRORS FOR TOTAL HEALTH-CARE EXPENDITURES")
    print("=" * 80)
    
    # Load FYC file
    fyc_file = data_dir / "h97.sas7bdat"
    print(f"\nLoading data from: {fyc_file}")
    
    puf97 = load_sas_data(fyc_file, columns=['TOTEXP05', 'VARPSU', 'VARSTR', 'PERWT05F'])
    print(f"Total records: {len(puf97):,}")
    
    # Simple Random Sample assumption (ignoring complex design)
    print("\n" + "=" * 80)
    print("ASSUME SIMPLE RANDOM SAMPLE")
    print("(Ignoring complex survey design)")
    print("=" * 80)
    
    # Calculate weighted total
    srs_total = (puf97['TOTEXP05'] * puf97['PERWT05F']).sum()
    
    # Calculate SE assuming SRS
    # For SRS, SE of total = sqrt(sum(w^2 * (x - xbar)^2))
    weighted_mean = srs_total / puf97['PERWT05F'].sum()
    srs_var = ((puf97['PERWT05F'] ** 2) * ((puf97['TOTEXP05'] - weighted_mean) ** 2)).sum()
    srs_se = np.sqrt(srs_var)
    
    print(f"\nSRS Total: ${srs_total:,.2f}")
    print(f"SRS SE Total: ${srs_se:,.2f}")
    
    # Account for MEPS complex sample design
    print("\n" + "=" * 80)
    print("ACCOUNT FOR MEPS COMPLEX SAMPLE DESIGN")
    print("(Using strata and PSU variables)")
    print("=" * 80)
    
    design = SurveyDesign(
        data=puf97,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT05F'
    )
    
    result = survey_total(design, 'TOTEXP05')
    complex_total = result['total'].values[0]
    complex_se = result['se'].values[0]
    
    print(f"\nComplex Design Total: ${complex_total:,.2f}")
    print(f"Complex Design SE Total: ${complex_se:,.2f}")
    
    # Comparison
    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)
    
    se_ratio = srs_se / complex_se if complex_se > 0 else 0
    
    print(f"\n{'Method':<30} {'Total':>25} {'SE':>25}")
    print("-" * 80)
    print(f"{'Simple Random Sample':<30} ${srs_total:>24,.0f} ${srs_se:>24,.0f}")
    print(f"{'Complex Design':<30} ${complex_total:>24,.0f} ${complex_se:>24,.0f}")
    print("-" * 80)
    print(f"\nRatio of SRS SE to Complex SE: {se_ratio:.2f}")
    
    print("\n" + "=" * 80)
    print("KEY TAKEAWAY")
    print("=" * 80)
    print("""
The standard errors differ substantially between the two approaches.

MEPS uses a complex survey design with:
- Stratification (VARSTR): Groups similar sampling units together
- Clustering (VARPSU): Primary sampling units within strata

Ignoring the complex design typically leads to:
- Underestimated standard errors
- Overstated statistical significance
- Invalid confidence intervals

ALWAYS use the VARSTR and VARPSU variables when computing standard
errors from MEPS data to account for the complex survey design.
""")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
