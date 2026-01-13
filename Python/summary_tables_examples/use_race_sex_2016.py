"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Use, expenditures, and population, 2016:
 - Number of people
 - Percent with expense
 - Total expenditures
 - Mean expenditure per person
 - Mean and median expenditure per person with expense
 - By race and sex

Input file: H192.ssp (2016 full-year consolidated)
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total, weighted_median, print_results


def main(meps_data_path: str = "C:/MEPS"):
    """
    Main function to run the analysis.
    
    Parameters
    ----------
    meps_data_path : str
        Path to directory containing MEPS data files
    """
    
    print("MEPS-HC Data Tools: Use, Expenditures, and Population, 2016")
    print("Expenditures by race and sex")
    print("="*80)
    
    # Format labels
    race_labels = {
        1: '1 Hispanic',
        2: '2 White',
        3: '3 Black',
        4: '4 Amer. Indian, AK Native, or mult. races',
        5: '5 Asian, Hawaiian, or Pacific Islander'
    }
    
    sex_labels = {
        1: 'Male',
        2: 'Female'
    }
    
    # Load FYC file
    print("\nLoading 2016 Full-Year Consolidated file...")
    h192 = load_sas_data(os.path.join(meps_data_path, "H192.sas7bdat"))
    
    # Define variables
    meps = h192.copy()
    
    # Race/ethnicity (for 2012 and later, use RACETHX and RACEV1X)
    meps['HISP'] = (meps['RACETHX'] == 1).astype(int)
    meps['WHITE'] = (meps['RACETHX'] == 2).astype(int)
    meps['BLACK'] = (meps['RACETHX'] == 3).astype(int)
    meps['NATIVE'] = ((meps['RACETHX'] > 3) & (meps['RACEV1X'].isin([3, 6]))).astype(int)
    meps['ASIAN'] = ((meps['RACETHX'] > 3) & (meps['RACEV1X'].isin([4, 5]))).astype(int)
    
    meps['RACE'] = (1 * meps['HISP'] + 2 * meps['WHITE'] + 3 * meps['BLACK'] + 
                   4 * meps['NATIVE'] + 5 * meps['ASIAN'])
    
    # Has expense indicator
    meps['HAS_EXP'] = (meps['TOTEXP16'] > 0).astype(int)
    meps['PERSON'] = 1
    
    # Calculate estimates
    print("\n" + "="*80)
    print("EXPENDITURES BY RACE AND SEX, 2016")
    print("="*80)
    
    # By race
    print("\n--- BY RACE ---")
    for race_val in sorted(meps['RACE'].dropna().unique()):
        if race_val == 0:
            continue
        
        meps_race = meps[meps['RACE'] == race_val].copy()
        
        if len(meps_race) == 0:
            continue
        
        design = SurveyDesign(
            data=meps_race,
            strata='VARSTR',
            cluster='VARPSU',
            weight='PERWT16F'
        )
        
        race_label = race_labels.get(int(race_val), str(race_val))
        print(f"\nRace: {race_label}")
        print("-" * 60)
        
        # Number of people
        person_total = survey_total(design, 'PERSON')
        print(f"  Number of people: {person_total['Sum'].values[0]:,.0f} (SE: {person_total['StdDev'].values[0]:,.0f})")
        
        # Percent with expense
        has_exp_mean = survey_mean(design, 'HAS_EXP')
        print(f"  Percent with expense: {has_exp_mean['Mean'].values[0]*100:.2f}% (SE: {has_exp_mean['StdErr'].values[0]*100:.2f}%)")
        
        # Total expenditures
        exp_total = survey_total(design, 'TOTEXP16')
        print(f"  Total expenditures: ${exp_total['Sum'].values[0]:,.0f} (SE: ${exp_total['StdDev'].values[0]:,.0f})")
        
        # Mean expenditure per person
        exp_mean = survey_mean(design, 'TOTEXP16')
        print(f"  Mean expenditure per person: ${exp_mean['Mean'].values[0]:,.2f} (SE: ${exp_mean['StdErr'].values[0]:,.2f})")
        
        # Mean and median expenditure per person with expense
        meps_with_exp = meps_race[meps_race['HAS_EXP'] == 1].copy()
        if len(meps_with_exp) > 0:
            design_exp = SurveyDesign(
                data=meps_with_exp,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT16F'
            )
            exp_mean_with = survey_mean(design_exp, 'TOTEXP16')
            exp_median_with = weighted_median(meps_with_exp['TOTEXP16'], meps_with_exp['PERWT16F'])
            print(f"  Mean expenditure per person with expense: ${exp_mean_with['Mean'].values[0]:,.2f} (SE: ${exp_mean_with['StdErr'].values[0]:,.2f})")
            print(f"  Median expenditure per person with expense: ${exp_median_with:,.2f}")
    
    # By sex
    print("\n--- BY SEX ---")
    for sex_val in sorted(meps['SEX'].dropna().unique()):
        meps_sex = meps[meps['SEX'] == sex_val].copy()
        
        if len(meps_sex) == 0:
            continue
        
        design = SurveyDesign(
            data=meps_sex,
            strata='VARSTR',
            cluster='VARPSU',
            weight='PERWT16F'
        )
        
        sex_label = sex_labels.get(int(sex_val), str(sex_val))
        print(f"\nSex: {sex_label}")
        print("-" * 60)
        
        # Number of people
        person_total = survey_total(design, 'PERSON')
        print(f"  Number of people: {person_total['Sum'].values[0]:,.0f} (SE: {person_total['StdDev'].values[0]:,.0f})")
        
        # Percent with expense
        has_exp_mean = survey_mean(design, 'HAS_EXP')
        print(f"  Percent with expense: {has_exp_mean['Mean'].values[0]*100:.2f}% (SE: {has_exp_mean['StdErr'].values[0]*100:.2f}%)")
        
        # Total expenditures
        exp_total = survey_total(design, 'TOTEXP16')
        print(f"  Total expenditures: ${exp_total['Sum'].values[0]:,.0f} (SE: ${exp_total['StdDev'].values[0]:,.0f})")
        
        # Mean expenditure per person
        exp_mean = survey_mean(design, 'TOTEXP16')
        print(f"  Mean expenditure per person: ${exp_mean['Mean'].values[0]:,.2f} (SE: ${exp_mean['StdErr'].values[0]:,.2f})")
        
        # Mean and median expenditure per person with expense
        meps_with_exp = meps_sex[meps_sex['HAS_EXP'] == 1].copy()
        if len(meps_with_exp) > 0:
            design_exp = SurveyDesign(
                data=meps_with_exp,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT16F'
            )
            exp_mean_with = survey_mean(design_exp, 'TOTEXP16')
            exp_median_with = weighted_median(meps_with_exp['TOTEXP16'], meps_with_exp['PERWT16F'])
            print(f"  Mean expenditure per person with expense: ${exp_mean_with['Mean'].values[0]:,.2f} (SE: ${exp_mean_with['StdErr'].values[0]:,.2f})")
            print(f"  Median expenditure per person with expense: ${exp_median_with:,.2f}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Summary Tables - Use Race Sex 2016')
    parser.add_argument('--data-path', type=str, default='C:/MEPS',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
