"""
AHRQ MEPS Data Users Workshop - Linking Example L1

This example shows how to:
(1) Identify jobs in first part of 2001
(2) Count the numbers of each type of job for each person
(3) Merge JOBS and FY files
(4) Calculate standard errors for survey estimates

Input files:
    - h56.sas7bdat (2001 Jobs)
    - h60.sas7bdat (2001 Full-Year Persons)

Python equivalent of: SAS/older_exercises_1996_to_2006/Linking_examples/L1/L1.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_freq, survey_total


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS/DATA")
    
    print("=" * 80)
    print("AHRQ MEPS DATA USERS WORKSHOP (LINKING)")
    print("2001 JOBS")
    print("Types and Numbers of Jobs at Beginning of Year")
    print("=" * 80)
    
    # Load Jobs file
    jobs_file = data_dir / "h56.sas7bdat"
    print(f"\nLoading jobs data from: {jobs_file}")
    
    jobs = load_sas_data(jobs_file)
    print(f"Total job records: {len(jobs):,}")
    
    # Subset to first-round records
    # Panel 5, Round 3 or Panel 6, Round 1
    jobs_r1 = jobs[
        ((jobs['PANEL'] == 5) & (jobs['RN'] == 3)) |
        ((jobs['PANEL'] == 6) & (jobs['RN'] == 1))
    ].copy()
    
    print(f"First-round job records: {len(jobs_r1):,}")
    
    # Job subtype labels
    subtype_labels = {
        1: 'Current Main',
        2: 'Current Miscellaneous',
        3: 'Former Main',
        4: 'Former Miscellaneous',
        5: 'Last Job Outside Rn',
        6: 'Retirement'
    }
    
    # All jobs at beginning of year
    print("\n" + "-" * 60)
    print("ALL JOBS AT BEGINNING OF YEAR")
    print("-" * 60)
    
    for subtype, label in subtype_labels.items():
        count = len(jobs_r1[jobs_r1['SUBTYPE'] == subtype])
        print(f"{label}: {count:,}")
    
    # Get person-level counts of each type of job
    print("\n" + "-" * 60)
    print("CREATING PERSON-LEVEL JOB COUNTS")
    print("-" * 60)
    
    # Initialize counts
    jobs_r1['N1'] = (jobs_r1['SUBTYPE'] == 1).astype(int)  # Current Main
    jobs_r1['N2'] = (jobs_r1['SUBTYPE'] == 2).astype(int)  # Current Miscellaneous
    jobs_r1['N3'] = (jobs_r1['SUBTYPE'] == 3).astype(int)  # Former Main
    jobs_r1['N4'] = (jobs_r1['SUBTYPE'] == 4).astype(int)  # Former Miscellaneous
    jobs_r1['N5'] = (jobs_r1['SUBTYPE'] == 5).astype(int)  # Last Job Outside Rn
    jobs_r1['N6'] = (jobs_r1['SUBTYPE'] == 6).astype(int)  # Retirement
    jobs_r1['TOTJOBS'] = 1
    
    # Aggregate to person level
    jobsper = jobs_r1.groupby('DUPERSID').agg({
        'N1': 'sum',
        'N2': 'sum',
        'N3': 'sum',
        'N4': 'sum',
        'N5': 'sum',
        'N6': 'sum',
        'TOTJOBS': 'sum'
    }).reset_index()
    
    print(f"Persons with first-round job records: {len(jobsper):,}")
    
    # Distribution of total jobs
    print("\n" + "-" * 60)
    print("PERSONS WITH FIRST-ROUND JOBS RECORD")
    print("-" * 60)
    
    print("\nTotal Jobs:")
    print(jobsper['TOTJOBS'].value_counts().sort_index())
    
    print("\nCurrent Main Jobs (N1):")
    print(jobsper['N1'].value_counts().sort_index())
    
    print("\nCurrent Miscellaneous Jobs (N2):")
    print(jobsper['N2'].value_counts().sort_index())
    
    # Load Full-Year file
    fyc_file = data_dir / "h60.sas7bdat"
    print(f"\nLoading FYC data from: {fyc_file}")
    
    fyc = load_sas_data(fyc_file, columns=[
        'DUPERSID', 'PANEL01', 'AGE31X', 'PERWT01F', 'VARSTR01', 'VARPSU01'
    ])
    
    print(f"Total FYC records: {len(fyc):,}")
    
    # Merge jobs and FYC
    allper = fyc.merge(jobsper, on='DUPERSID', how='left')
    
    # Fill missing job counts with 0
    for col in ['N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'TOTJOBS']:
        allper[col] = allper[col].fillna(0)
    
    # Subset to persons age 18+
    print("\n" + "=" * 80)
    print("PERSONS AGE 18+: # OF CURRENT MAIN & MISCELLANEOUS JOBS")
    print("AT BEGINNING OF YEAR")
    print("=" * 80)
    
    curr = allper[allper['AGE31X'] >= 18].copy()
    
    # Count of current main or miscellaneous jobs
    curr['NUMCURR'] = curr['N1'] + curr['N2']
    
    # Collapse into categories (0, 1, 2, 3+)
    curr['NCURR'] = np.where(curr['NUMCURR'] >= 3, 3, curr['NUMCURR'])
    
    ncurr_labels = {0: 'None', 1: '1', 2: '2', 3: '3+'}
    
    # Calculate survey estimates
    design = SurveyDesign(
        data=curr,
        strata='VARSTR01',
        cluster='VARPSU01',
        weight='PERWT01F'
    )
    
    print("\n" + "-" * 80)
    print(f"{'# Curr Jobs':<12} {'Sample':>10} {'Population':>15} {'SE Pop':>12} {'RSE Pop':>10} {'Col %':>10} {'SE Col %':>10}")
    print("-" * 80)
    
    total_pop = curr['PERWT01F'].sum()
    
    for ncurr_val in [0, 1, 2, 3]:
        subset = curr[curr['NCURR'] == ncurr_val].copy()
        
        if len(subset) > 0:
            design_sub = SurveyDesign(
                data=subset,
                strata='VARSTR01',
                cluster='VARPSU01',
                weight='PERWT01F'
            )
            
            # Create a count variable
            subset['COUNT'] = 1
            design_sub = SurveyDesign(
                data=subset,
                strata='VARSTR01',
                cluster='VARPSU01',
                weight='PERWT01F'
            )
            
            total_result = survey_total(design_sub, 'COUNT')
            
            sample_n = len(subset)
            pop = total_result['total'].values[0]
            se_pop = total_result['se'].values[0]
            rse_pop = se_pop / pop if pop > 0 else 0
            col_pct = pop / total_pop * 100
            se_col = rse_pop * col_pct  # Approximate SE for percentage
            
            flag = '*' if rse_pop > 0.3 else ''
            
            print(f"{ncurr_labels[ncurr_val]:<12} {sample_n:>10,} {pop:>15,.0f} {se_pop:>12,.0f} {rse_pop:>10.3f} {col_pct:>10.2f} {se_col:>10.2f} {flag}")
    
    print("\n* RSE > 0.30, estimate may be unreliable")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
