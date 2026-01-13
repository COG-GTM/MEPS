"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Use, expenditures, and population, 2016

Expenditures by race and sex:
    - Number of people
    - Percent of population with an expense
    - Total expenditures
    - Mean expenditure per person
    - Mean expenditure per person with expense
    - Median expenditure per person with expense

Input file: h192.ssp (2016 full-year consolidated)

Python equivalent of: SAS/summary_tables_examples/use_race_sex_2016.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total


def weighted_median(data, values, weights):
    """Calculate weighted median."""
    df = pd.DataFrame({'values': data[values], 'weights': data[weights]})
    df = df.dropna()
    df = df.sort_values('values')
    cumsum = df['weights'].cumsum()
    cutoff = df['weights'].sum() / 2.0
    return df[cumsum >= cutoff]['values'].iloc[0]


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS")
    
    print("=" * 80)
    print("USE, EXPENDITURES, AND POPULATION, 2016")
    print("Expenditures by Race and Sex")
    print("=" * 80)
    
    # Load FYC file
    fyc_file = data_dir / "h192.ssp"
    print(f"\nLoading data from: {fyc_file}")
    
    meps = load_sas_data(fyc_file)
    
    # Race/ethnicity (for 2012 and later, use RACETHX and RACEV1X)
    meps['HISP'] = (meps['RACETHX'] == 1).astype(int)
    meps['WHITE'] = (meps['RACETHX'] == 2).astype(int)
    meps['BLACK'] = (meps['RACETHX'] == 3).astype(int)
    meps['NATIVE'] = ((meps['RACETHX'] > 3) & (meps['RACEV1X'].isin([3, 6]))).astype(int)
    meps['ASIAN'] = ((meps['RACETHX'] > 3) & (meps['RACEV1X'].isin([4, 5]))).astype(int)
    
    meps['RACE'] = (1 * meps['HISP'] + 2 * meps['WHITE'] + 3 * meps['BLACK'] + 
                   4 * meps['NATIVE'] + 5 * meps['ASIAN'])
    
    # Create indicator variables
    meps['PERSON'] = 1
    meps['HAS_EXP'] = (meps['TOTEXP16'] > 0).astype(int)
    
    # Define labels
    race_labels = {
        1: 'Hispanic',
        2: 'White',
        3: 'Black',
        4: 'Amer. Indian, AK Native, or mult. races',
        5: 'Asian, Hawaiian, or Pacific Islander'
    }
    
    sex_labels = {
        1: 'Male',
        2: 'Female'
    }
    
    # Calculate estimates
    print("\n" + "=" * 80)
    print("EXPENDITURES BY RACE AND SEX")
    print("=" * 80)
    
    for sex_val, sex_label in sex_labels.items():
        print(f"\n{'='*60}")
        print(f"{sex_label}")
        print(f"{'='*60}")
        
        for race_val, race_label in race_labels.items():
            subset = meps[(meps['SEX'] == sex_val) & (meps['RACE'] == race_val)].copy()
            
            if len(subset) > 0:
                design = SurveyDesign(
                    data=subset,
                    strata='VARSTR',
                    cluster='VARPSU',
                    weight='PERWT16F'
                )
                
                # Number of people
                people_result = survey_total(design, 'PERSON')
                
                # Percent with expense
                pct_exp_result = survey_mean(design, 'HAS_EXP')
                
                # Total expenditures
                total_exp_result = survey_total(design, 'TOTEXP16')
                
                # Mean expenditure per person
                mean_exp_result = survey_mean(design, 'TOTEXP16')
                
                print(f"\n{race_label}:")
                print(f"  Number of people: {people_result['total'].values[0]:,.0f}")
                print(f"  Percent with expense: {pct_exp_result['mean'].values[0]*100:.2f}%")
                print(f"  Total expenditures: ${total_exp_result['total'].values[0]:,.0f}")
                print(f"  Mean exp per person: ${mean_exp_result['mean'].values[0]:,.2f}")
                
                # Mean and median for persons with expense
                subset_exp = subset[subset['HAS_EXP'] == 1].copy()
                if len(subset_exp) > 0:
                    design_exp = SurveyDesign(
                        data=subset_exp,
                        strata='VARSTR',
                        cluster='VARPSU',
                        weight='PERWT16F'
                    )
                    
                    mean_exp_with = survey_mean(design_exp, 'TOTEXP16')
                    median_exp = weighted_median(subset_exp, 'TOTEXP16', 'PERWT16F')
                    
                    print(f"  Mean exp per person with expense: ${mean_exp_with['mean'].values[0]:,.2f}")
                    print(f"  Median exp per person with expense: ${median_exp:,.2f}")
    
    # Summary table
    print("\n" + "=" * 80)
    print("SUMMARY TABLE")
    print("=" * 80)
    
    print(f"\n{'Sex':<10} {'Race':<45} {'# People':>12} {'% w/Exp':>10} {'Mean Exp':>12}")
    print("-" * 95)
    
    for sex_val, sex_label in sex_labels.items():
        for race_val, race_label in race_labels.items():
            subset = meps[(meps['SEX'] == sex_val) & (meps['RACE'] == race_val)].copy()
            
            if len(subset) > 0:
                design = SurveyDesign(
                    data=subset,
                    strata='VARSTR',
                    cluster='VARPSU',
                    weight='PERWT16F'
                )
                
                people_result = survey_total(design, 'PERSON')
                pct_exp_result = survey_mean(design, 'HAS_EXP')
                mean_exp_result = survey_mean(design, 'TOTEXP16')
                
                print(f"{sex_label:<10} {race_label:<45} {people_result['total'].values[0]:>12,.0f} {pct_exp_result['mean'].values[0]*100:>9.2f}% ${mean_exp_result['mean'].values[0]:>11,.2f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
