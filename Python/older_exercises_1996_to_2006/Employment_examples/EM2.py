"""
AHRQ MEPS Data Users Workshop - Employment Example EM2

This example shows how to use the 2002 MEPS Jobs file (HC-063) to determine
how many persons working at the start of the year changed jobs.

Input files:
    - h63.sas7bdat (2002 MEPS Jobs File)
    - h62.sas7bdat (2002 MEPS Full-Year File)

Python equivalent of: SAS/older_exercises_1996_to_2006/Employment_examples/EM2/EM2.sas
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
    print("AHRQ MEPS DATA USERS WORKSHOP (EMPLOYMENT)")
    print("Job Changes Among Workers, 2002")
    print("=" * 80)
    
    # Load Jobs file
    jobs_file = data_dir / "h63.sas7bdat"
    print(f"\nLoading jobs data from: {jobs_file}")
    
    h63 = load_sas_data(jobs_file)
    print(f"Total job records: {len(h63):,}")
    
    # Identify persons who had a job on or before January 1, 2002
    # Panel 6, Round 3 or Panel 7, Round 1
    # Subtype 1-4 (current or former jobs)
    # Job started before 2002 or on Jan 1, 2002
    
    empstart_cond = (
        (((h63['PANEL'] == 6) & (h63['RN'] == 3)) | 
         ((h63['PANEL'] == 7) & (h63['RN'] == 1))) &
        (h63['SUBTYPE'].isin([1, 2, 3, 4])) &
        ((h63['JSTRTY'] < 2002) | 
         ((h63['JSTRTM'] == 1) & (h63['JSTRTD'] == 1) & (h63['JSTRTY'] == 2002)))
    )
    
    empstart_pop = h63[empstart_cond][['DUPERSID']].drop_duplicates()
    print(f"\nPersons with job at start of 2002: {len(empstart_pop):,}")
    
    # Identify those who either added a job or changed jobs
    # Subtype 3,4 (former jobs) OR
    # Subtype 1,2 (current jobs) that started after Jan 1, 2002
    
    h63_subset = h63[['DUPERSID', 'SUBTYPE', 'JSTRTM', 'JSTRTD', 'JSTRTY', 'JOBSIDX']].copy()
    
    # Merge with empstart_pop to get only those who had a job at start
    h63_merged = h63_subset.merge(empstart_pop, on='DUPERSID', how='inner')
    
    # Identify job changers
    chngjob_cond = (
        (h63_merged['SUBTYPE'].isin([3, 4])) |  # Former jobs
        ((h63_merged['SUBTYPE'].isin([1, 2])) &  # Current jobs started after Jan 1
         (h63_merged['JSTRTY'] == 2002) & 
         ~((h63_merged['JSTRTD'] == 1) & (h63_merged['JSTRTM'] == 1)))
    )
    
    chngjob_pop = h63_merged[chngjob_cond][['DUPERSID']].drop_duplicates()
    print(f"Persons who changed/added jobs: {len(chngjob_pop):,}")
    
    # Load FYC file
    fyc_file = data_dir / "h62.sas7bdat"
    print(f"\nLoading FYC data from: {fyc_file}")
    
    h62 = load_sas_data(fyc_file, columns=[
        'DUPERSID', 'AGE02X', 'AGE42X', 'AGE31X', 'PERWT02P'
    ])
    
    # Create AGE variable
    h62['AGE'] = np.where(h62['AGE02X'] >= 0, h62['AGE02X'],
                 np.where(h62['AGE42X'] >= 0, h62['AGE42X'],
                 np.where(h62['AGE31X'] >= 0, h62['AGE31X'], -1)))
    
    # Subset to adults 18+
    hc62 = h62[h62['AGE'] >= 18][['DUPERSID', 'AGE', 'PERWT02P']].copy()
    print(f"Adults 18+: {len(hc62):,}")
    
    # Age distribution
    print("\n" + "-" * 60)
    print("AGE DISTRIBUTION (UNWEIGHTED)")
    print("-" * 60)
    
    hc62['AGEGRP'] = pd.cut(hc62['AGE'], bins=[17, 44, 64, 85], labels=['18-44', '45-64', '65-85'])
    print(hc62['AGEGRP'].value_counts().sort_index())
    
    # Create combined dataset
    chnginfo = hc62.copy()
    chnginfo['EMPSTART'] = chnginfo['DUPERSID'].isin(empstart_pop['DUPERSID']).map({True: 'YES', False: 'NO'})
    chnginfo['CHNGJOB'] = chnginfo['DUPERSID'].isin(chngjob_pop['DUPERSID']).map({True: 'YES', False: 'NO'})
    
    # Unweighted frequencies
    print("\n" + "=" * 80)
    print("UNWEIGHTED FREQUENCIES")
    print("=" * 80)
    
    print("\nEMPSTART (Had job at start of 2002):")
    print(chnginfo['EMPSTART'].value_counts())
    
    print("\nCHNGJOB (Changed/added job):")
    print(chnginfo['CHNGJOB'].value_counts())
    
    print("\nCross-tabulation:")
    print(pd.crosstab(chnginfo['EMPSTART'], chnginfo['CHNGJOB']))
    
    # Among those with job at start of year
    print("\n" + "=" * 80)
    print("AMONG PERSONS 18+ WITH A CURRENT JOB STARTING ON OR BEFORE JAN 1, 2002")
    print("PERCENT WHO EITHER ADDED OR STOPPED A JOB IN 2002")
    print("=" * 80)
    
    empstart_subset = chnginfo[chnginfo['EMPSTART'] == 'YES']
    
    print("\nUnweighted frequency:")
    print(empstart_subset['CHNGJOB'].value_counts())
    
    print("\nWeighted frequency:")
    for val in ['YES', 'NO']:
        subset = empstart_subset[empstart_subset['CHNGJOB'] == val]
        wt_sum = subset['PERWT02P'].sum()
        print(f"  {val}: {wt_sum:,.0f}")
    
    total_wt = empstart_subset['PERWT02P'].sum()
    yes_wt = empstart_subset[empstart_subset['CHNGJOB'] == 'YES']['PERWT02P'].sum()
    pct_changed = yes_wt / total_wt * 100 if total_wt > 0 else 0
    
    print(f"\nPercent who changed/added jobs: {pct_changed:.1f}%")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
