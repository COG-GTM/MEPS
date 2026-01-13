"""
AHRQ MEPS Data Users Workshop - Estimation Example E7

This example shows how to compute selected estimates from MEPS Statistical
Brief #188, "Screening Colonoscopy Among U.S. Noninstitutionalized Adult
Population Age 50 and Older, 2005".

Note: The Statistical Brief used the MEPS 2005 Population Characteristics
File (HC-90) so estimates generated using the 2005 Consolidated Data File
(HC-97) may differ slightly.

Input file: h97.sas7bdat (2005 Full-Year Data File)

Python equivalent of: SAS/older_exercises_1996_to_2006/Estimation_examples/E7/E7.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_freq


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS/DATA")
    
    print("=" * 80)
    print("AHRQ MEPS DATA USERS WORKSHOP")
    print("COLONOSCOPY SCREENING AMONG ADULTS 50 AND OLDER, 2005")
    print("=" * 80)
    
    # Load FYC file
    fyc_file = data_dir / "h97.sas7bdat"
    print(f"\nLoading data from: {fyc_file}")
    
    puf97 = load_sas_data(fyc_file, columns=[
        'DUPERSID', 'VARSTR', 'VARPSU', 'AGE05X', 'AGE53X', 'AGE42X', 'AGE31X',
        'RACEX', 'HISPANX', 'EDUCYR', 'BOWEL53', 'WHNBWL53', 'PERWT05F'
    ])
    
    print(f"Total records: {len(puf97):,}")
    
    # Create BOWELYES variable
    puf97['BOWELYES'] = (puf97['BOWEL53'] == 1).astype(int)
    
    # Create AGE variable
    puf97['AGE'] = np.where(puf97['AGE05X'] >= 0, puf97['AGE05X'],
                   np.where(puf97['AGE53X'] >= 0, puf97['AGE53X'],
                   np.where(puf97['AGE42X'] >= 0, puf97['AGE42X'],
                   np.where(puf97['AGE31X'] >= 0, puf97['AGE31X'], -1))))
    
    # Create age categories - 3 levels
    puf97['AGECAT'] = np.where((puf97['AGE'] >= 0) & (puf97['AGE'] <= 49), 1,
                     np.where((puf97['AGE'] >= 50) & (puf97['AGE'] <= 64), 2,
                     np.where(puf97['AGE'] >= 65, 3, -1)))
    
    # Create age categories - 2 levels
    puf97['AGE50PLUS'] = np.where((puf97['AGE'] >= 0) & (puf97['AGE'] <= 49), 1,
                        np.where(puf97['AGE'] >= 50, 2, -1))
    
    # Create RACETH variable
    puf97['RACETH'] = np.where(puf97['HISPANX'] == 1, 1,  # Hispanic
                     np.where((puf97['HISPANX'] == 2) & (puf97['RACEX'] == 1), 2,  # White, Non-Hispanic
                     np.where((puf97['HISPANX'] == 2) & (puf97['RACEX'] == 2), 3,  # Black, Non-Hispanic
                     np.where((puf97['HISPANX'] == 2) & (puf97['RACEX'] == 3), 4,  # Amer. Ind/AK Native
                     np.where((puf97['HISPANX'] == 2) & (puf97['RACEX'] == 4), 5,  # Asian
                     np.where((puf97['HISPANX'] == 2) & (puf97['RACEX'] == 5), 6,  # Hawaiian/Pacific Isl.
                     np.where((puf97['HISPANX'] == 2) & (puf97['RACEX'] == 6), 7,  # Multiple races
                     np.nan)))))))
    
    # Create NEWRACE variable (collapsed)
    puf97['NEWRACE'] = np.where(puf97['RACETH'] == 1, 1,  # Hispanic
                      np.where(puf97['RACETH'] == 2, 2,  # White, Non-Hispanic
                      np.where(puf97['RACETH'] == 3, 3,  # Black, Non-Hispanic
                      np.where(puf97['RACETH'] == 5, 4,  # Asian, Non-Hispanic
                      np.where(puf97['RACETH'].isin([4, 6, 7]), 5,  # Other Non-Hispanic
                      np.nan)))))
    
    # Create HIGHEDUC variable
    puf97['HIGHEDUC'] = np.where(puf97['AGE'] < 16, 5,  # Younger than 16
                        np.where(puf97['EDUCYR'] < 0, 4,  # Unknown or refused
                        np.where(puf97['EDUCYR'] < 12, 1,  # Less than 12 years
                        np.where(puf97['EDUCYR'] == 12, 2,  # High school grad
                        np.where(puf97['EDUCYR'] > 12, 3,  # At least some college
                        -1)))))
    
    # Labels
    agecat_labels = {1: '0-49', 2: '50-64', 3: '65+'}
    age50plus_labels = {1: '0-49', 2: '50+'}
    bowel_labels = {1: 'Yes', 2: 'No'}
    race_labels = {1: 'Hispanic', 2: 'White Non-Hispanic', 3: 'Black Non-Hispanic', 
                   4: 'Asian Non-Hispanic', 5: 'Other Non-Hispanic'}
    educ_labels = {1: 'Less than High School', 2: 'High School Grad', 
                   3: 'At Least Some College', 4: 'Unknown', 5: 'Younger than 16'}
    
    # Figure 1: Total (by age category)
    print("\n" + "=" * 80)
    print("MEPS STAT BRIEF #188, FIGURE 1 (TOTAL)")
    print("Colonoscopy Screening by Age Category")
    print("=" * 80)
    
    # By 3 age categories
    print("\n" + "-" * 60)
    print("BY AGE CATEGORY (3 LEVELS)")
    print("-" * 60)
    
    for agecat in [1, 2, 3]:
        subset = puf97[(puf97['AGECAT'] == agecat) & (puf97['BOWEL53'].isin([1, 2]))].copy()
        if len(subset) > 0:
            design = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT05F'
            )
            
            freq_result = survey_freq(design, 'BOWEL53')
            yes_pct = freq_result[freq_result['BOWEL53'] == 1]['proportion'].values[0] * 100 if len(freq_result[freq_result['BOWEL53'] == 1]) > 0 else 0
            
            print(f"\n{agecat_labels[agecat]}:")
            print(f"  N: {len(subset):,}")
            print(f"  % with colonoscopy: {yes_pct:.1f}%")
    
    # By 2 age categories (50+ vs under 50)
    print("\n" + "-" * 60)
    print("BY AGE CATEGORY (2 LEVELS)")
    print("-" * 60)
    
    for age50 in [1, 2]:
        subset = puf97[(puf97['AGE50PLUS'] == age50) & (puf97['BOWEL53'].isin([1, 2]))].copy()
        if len(subset) > 0:
            design = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT05F'
            )
            
            freq_result = survey_freq(design, 'BOWEL53')
            yes_pct = freq_result[freq_result['BOWEL53'] == 1]['proportion'].values[0] * 100 if len(freq_result[freq_result['BOWEL53'] == 1]) > 0 else 0
            
            print(f"\n{age50plus_labels[age50]}:")
            print(f"  N: {len(subset):,}")
            print(f"  % with colonoscopy: {yes_pct:.1f}%")
    
    # Figure 2: By Race/Ethnicity (among 50+)
    print("\n" + "=" * 80)
    print("MEPS STAT BRIEF #188, FIGURE 2 (RACE/ETHNICITY)")
    print("Colonoscopy Screening Among Adults 50+ by Race/Ethnicity")
    print("=" * 80)
    
    subset_50plus = puf97[(puf97['AGE50PLUS'] == 2) & (puf97['BOWEL53'].isin([1, 2]))].copy()
    
    for race in [1, 2, 3, 4, 5]:
        subset = subset_50plus[subset_50plus['NEWRACE'] == race].copy()
        if len(subset) > 0:
            design = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT05F'
            )
            
            freq_result = survey_freq(design, 'BOWEL53')
            yes_pct = freq_result[freq_result['BOWEL53'] == 1]['proportion'].values[0] * 100 if len(freq_result[freq_result['BOWEL53'] == 1]) > 0 else 0
            
            print(f"\n{race_labels[race]}:")
            print(f"  N: {len(subset):,}")
            print(f"  % with colonoscopy: {yes_pct:.1f}%")
    
    # Figure 3: By Education (among 50+)
    print("\n" + "=" * 80)
    print("MEPS STAT BRIEF #188, FIGURE 3 (EDUCATION)")
    print("Colonoscopy Screening Among Adults 50+ by Education")
    print("=" * 80)
    
    for educ in [1, 2, 3]:
        subset = subset_50plus[subset_50plus['HIGHEDUC'] == educ].copy()
        if len(subset) > 0:
            design = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT05F'
            )
            
            freq_result = survey_freq(design, 'BOWEL53')
            yes_pct = freq_result[freq_result['BOWEL53'] == 1]['proportion'].values[0] * 100 if len(freq_result[freq_result['BOWEL53'] == 1]) > 0 else 0
            
            print(f"\n{educ_labels[educ]}:")
            print(f"  N: {len(subset):,}")
            print(f"  % with colonoscopy: {yes_pct:.1f}%")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
