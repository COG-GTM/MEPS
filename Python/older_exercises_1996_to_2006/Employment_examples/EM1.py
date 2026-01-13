"""
AHRQ MEPS Data Users Workshop - Employment Example EM1

This example shows how to build an analytic file and create new variables to
examine the relationship between perceived health status and a person's weekly
earnings, where weekly earnings are those of the current main job.

Person-level records are divided into quartiles based on weekly earnings and
person-level weights. The result is 4 equally weighted quartiles for weekly
earnings.

Input file: h62.sas7bdat (2002 Full-Year Population)

Python equivalent of: SAS/older_exercises_1996_to_2006/Employment_examples/EM1/EM1.sas
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
    print("AHRQ MEPS DATA USERS WORKSHOP (EMPLOYMENT)")
    print("PERCEIVED HEALTH STATUS AND WEEKLY EARNINGS - 2002 DATA")
    print("=" * 80)
    
    # Load FYC file
    fyc_file = data_dir / "h62.sas7bdat"
    print(f"\nLoading data from: {fyc_file}")
    
    h62 = load_sas_data(fyc_file, columns=[
        'DUPERSID', 'PERWT02P', 'VARSTR', 'VARPSU', 'EMPST42',
        'SELFCM42', 'SELFCM31', 'HRWG42X', 'HRWG31X', 'HOUR42', 'HOUR31',
        'RTHLTH42', 'TEMPJB42', 'AGE42X'
    ])
    
    print(f"Total records: {len(h62):,}")
    
    # Subset to desired population:
    # - Employed (EMPST42 in 1,2)
    # - Not self-employed (SELFCM42=2 or SELFCM31=2 if SELFCM42=-2)
    # - Has wage info (HRWG42X=-10 or >0, or HRWG31X if HRWG42X=-2)
    # - Has hours info (HOUR42>0 or HOUR31>0 if HOUR42=-2)
    # - Has health status (RTHLTH42 in 1-5)
    # - Not temporary job (TEMPJB42=2)
    # - Age > 24
    
    h62a = h62[
        (h62['EMPST42'].isin([1, 2])) &
        ((h62['SELFCM42'] == 2) | ((h62['SELFCM42'] == -2) & (h62['SELFCM31'] == 2))) &
        ((h62['HRWG42X'] == -10) | (h62['HRWG42X'] > 0) | 
         ((h62['HRWG42X'] == -2) & ((h62['HRWG31X'] == -10) | (h62['HRWG31X'] > 0)))) &
        ((h62['HOUR42'] > 0) | ((h62['HOUR42'] == -2) & (h62['HOUR31'] > 0))) &
        (h62['RTHLTH42'].isin([1, 2, 3, 4, 5])) &
        (h62['TEMPJB42'] == 2) &
        (h62['AGE42X'] > 24)
    ].copy()
    
    print(f"Records after subsetting: {len(h62a):,}")
    
    # Create hourly wage variable
    h62a['HRLYWAGE'] = np.where(h62a['HRWG42X'] == -2, h62a['HRWG31X'], h62a['HRWG42X'])
    h62a.loc[h62a['HRLYWAGE'] == -10, 'HRLYWAGE'] = 61.98  # Top-coded value
    
    # Create hours variable
    h62a['HOURS'] = np.where(h62a['HOUR42'] > 0, h62a['HOUR42'], h62a['HOUR31'])
    
    # Create weekly earnings
    h62a['WKLYEARN'] = h62a['HRLYWAGE'] * h62a['HOURS']
    
    # Sort by weekly earnings
    h62a = h62a.sort_values('WKLYEARN')
    
    # Create quartiles based on weighted distribution
    total_weight = h62a['PERWT02P'].sum()
    h62a['CUM_WT'] = h62a['PERWT02P'].cumsum()
    
    h62a['QUARTILE'] = np.where(h62a['CUM_WT'] <= total_weight * 0.25, 1,
                       np.where(h62a['CUM_WT'] <= total_weight * 0.50, 2,
                       np.where(h62a['CUM_WT'] <= total_weight * 0.75, 3, 4)))
    
    # Labels
    quartile_labels = {1: 'LOWEST', 2: '2', 3: '3', 4: 'HIGHEST'}
    health_labels = {1: 'EXCELLENT', 2: 'VERY GOOD', 3: 'GOOD', 4: 'FAIR', 5: 'POOR'}
    
    # Weighted frequency of quartiles
    print("\n" + "=" * 80)
    print("WEIGHTED FREQUENCY OF QUARTILES")
    print("=" * 80)
    
    for q in [1, 2, 3, 4]:
        subset = h62a[h62a['QUARTILE'] == q]
        wt_sum = subset['PERWT02P'].sum()
        print(f"\nQuartile {q} ({quartile_labels[q]}): {wt_sum:,.0f}")
    
    # Weekly earnings distribution
    print("\n" + "=" * 80)
    print("WEEKLY EARNINGS DISTRIBUTION")
    print("=" * 80)
    
    bins = [0, 50, 500, 1000, float('inf')]
    labels = ['0.13 - 49.99', '50.00 - 499.99', '500.00 - 999.99', '1,000.00+']
    h62a['WKLY_CAT'] = pd.cut(h62a['WKLYEARN'], bins=bins, labels=labels, right=False)
    
    for cat in labels:
        subset = h62a[h62a['WKLY_CAT'] == cat]
        wt_sum = subset['PERWT02P'].sum()
        pct = wt_sum / total_weight * 100
        print(f"\n{cat}: {wt_sum:,.0f} ({pct:.2f}%)")
    
    # Cross-tabulation: Quartile by Health Status
    print("\n" + "=" * 80)
    print("QUARTILE BY HEALTH STATUS")
    print("=" * 80)
    
    for q in [1, 2, 3, 4]:
        subset_q = h62a[h62a['QUARTILE'] == q]
        total_q = subset_q['PERWT02P'].sum()
        
        print(f"\nQuartile {q} ({quartile_labels[q]}):")
        for h in [1, 2, 3, 4, 5]:
            subset_h = subset_q[subset_q['RTHLTH42'] == h]
            wt_h = subset_h['PERWT02P'].sum()
            pct = wt_h / total_q * 100 if total_q > 0 else 0
            print(f"  {health_labels[h]}: {pct:.2f}%")
    
    # Mean health status by quartile
    print("\n" + "=" * 80)
    print("MEAN REPORTED HEALTH STATUS BY WEEKLY EARNINGS QUARTILE")
    print("(1=EXCELLENT, 2=VERY GOOD, 3=GOOD, 4=FAIR, 5=POOR)")
    print("=" * 80)
    
    for q in [1, 2, 3, 4]:
        subset = h62a[h62a['QUARTILE'] == q].copy()
        
        design = SurveyDesign(
            data=subset,
            strata='VARSTR',
            cluster='VARPSU',
            weight='PERWT02P'
        )
        
        mean_result = survey_mean(design, 'RTHLTH42')
        print(f"\nQuartile {q} ({quartile_labels[q]}):")
        print(f"  N: {len(subset):,}")
        print(f"  Mean Health Status: {mean_result['mean'].values[0]:.2f}")
        print(f"  SE: {mean_result['se'].values[0]:.3f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
