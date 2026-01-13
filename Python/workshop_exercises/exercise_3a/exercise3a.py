"""
DESCRIPTION: THIS PROGRAM ILLUSTRATES HOW TO IDENTIFY PERSONS WITH A CONDITION AND
             CALCULATE ESTIMATES ON USE AND EXPENDITURES FOR PERSONS WITH THE CONDITION

             THE CONDITION USED IN THIS EXERCISE IS DIABETES (CCS CODE=049 OR 050)

INPUT FILES:  1) H180.SAS7BDAT (2015 CONDITION PUF DATA)
              2) H181.SAS7BDAT (2015 FY PUF DATA)
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total, print_results


def main(meps_data_path: str = "C:/MEPS/SAS/DATA"):
    """
    Main function to run the analysis.
    
    Parameters
    ----------
    meps_data_path : str
        Path to directory containing MEPS data files
    """
    
    print("2018 AHRQ MEPS DATA USERS WORKSHOP")
    print("EXERCISE4.SAS: CALCULATE ESTIMATES ON USE AND EXPENDITURES FOR PERSONS WITH A CONDITION (DIABETES)")
    print("="*80)
    
    # Format labels
    sex_labels = {1: 'MALE', 2: 'FEMALE'}
    yesno_labels = {1: 'YES', 2: 'NO'}
    
    # 1) PULL OUT CONDITIONS WITH DIABETES (CCS CODE='049', '050') FROM 2015 CONDITION PUF - HC180
    print("\nLoading 2015 Condition file...")
    h180 = load_sas_data(os.path.join(meps_data_path, "H180.sas7bdat"))
    
    # Filter for diabetes conditions
    diab = h180[h180['CCCODEX'].isin(['049', '050'])].copy()
    
    print("\nCHECK CCS CODES FOR DIABETIC CONDITIONS:")
    print(diab['CCCODEX'].value_counts())
    
    # 2) IDENTIFY PERSONS WHO REPORTED DIABETES
    diabpers = diab[['DUPERSID']].drop_duplicates()
    
    print(f"\nNumber of unique persons with diabetes: {len(diabpers)}")
    
    # 3) CREATE A FLAG FOR PERSONS WITH DIABETES IN THE 2015 FY DATA
    print("\nLoading 2015 Full-Year Consolidated file...")
    h181 = load_sas_data(os.path.join(meps_data_path, "H181.sas7bdat"))
    
    # Merge
    fy1 = pd.merge(h181, diabpers, on='DUPERSID', how='left', indicator=True)
    fy1['DIABPERS'] = np.where(fy1['_merge'] == 'both', 1, 2)
    fy1 = fy1.drop('_merge', axis=1)
    
    # Supporting crosstabs
    print("\nUNWEIGHTED # OF PERSONS WHO REPORTED DIABETES, 2015:")
    print(fy1['DIABPERS'].map(yesno_labels).value_counts())
    
    print("\nDIABPERS * SEX crosstab (unweighted):")
    print(pd.crosstab(fy1['DIABPERS'].map(yesno_labels), fy1['SEX'].map(sex_labels)))
    
    # Weighted frequency
    print("\nWEIGHTED # OF PERSONS WHO REPORTED DIABETES, 2015:")
    for diabpers_val in [1, 2]:
        subset = fy1[fy1['DIABPERS'] == diabpers_val]
        weighted_count = subset['PERWT15F'].sum()
        print(f"  {yesno_labels[diabpers_val]}: {weighted_count:,.0f}")
    
    # 4) CALCULATE ESTIMATES ON USE AND EXPENDITURES FOR PERSONS WHO REPORTED DIABETES
    print("\n" + "="*80)
    print("ESTIMATES ON USE AND EXPENDITURES FOR PERSONS WHO REPORTED DIABETES, 2015")
    print("="*80)
    
    # Filter to persons with diabetes (DIABPERS = 1)
    fy1_diab = fy1[fy1['DIABPERS'] == 1].copy()
    
    design = SurveyDesign(
        data=fy1_diab,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT15F'
    )
    
    # Variables to analyze
    vars_to_analyze = ['TOTEXP15', 'TOTSLF15', 'OBTOTV15']
    var_labels = {
        'TOTEXP15': 'TOTAL EXPENDITURES',
        'TOTSLF15': 'TOTAL SELF/FAMILY PAYMENTS',
        'OBTOTV15': 'TOTAL OFFICE-BASED VISITS'
    }
    
    # Overall estimates
    print("\nOverall estimates (DIABPERS = YES):")
    print("-" * 80)
    
    means = survey_mean(design, vars_to_analyze)
    totals = survey_total(design, vars_to_analyze)
    
    results = pd.merge(
        means[['Variable', 'N', 'SumWgt', 'Mean', 'StdErr']],
        totals[['Variable', 'Sum', 'StdDev']],
        on='Variable'
    )
    
    print(f"\n{'Variable':<25} {'N':>8} {'Pop Size':>15} {'Sum':>18} {'SE Sum':>15} {'Mean':>12} {'SE Mean':>10}")
    print("-" * 105)
    
    for _, row in results.iterrows():
        var = row['Variable']
        label = var_labels.get(var, var)
        print(f"{label:<25} {row['N']:>8,.0f} {row['SumWgt']:>15,.0f} {row['Sum']:>18,.0f} {row['StdDev']:>15,.0f} {row['Mean']:>12,.2f} {row['StdErr']:>10,.2f}")
    
    # By sex
    print("\n\nEstimates by SEX (DIABPERS = YES):")
    print("-" * 80)
    
    for sex_val, sex_label in sex_labels.items():
        fy1_sex = fy1_diab[fy1_diab['SEX'] == sex_val].copy()
        
        if len(fy1_sex) == 0:
            continue
        
        design_sex = SurveyDesign(
            data=fy1_sex,
            strata='VARSTR',
            cluster='VARPSU',
            weight='PERWT15F'
        )
        
        means_sex = survey_mean(design_sex, vars_to_analyze)
        totals_sex = survey_total(design_sex, vars_to_analyze)
        
        results_sex = pd.merge(
            means_sex[['Variable', 'N', 'SumWgt', 'Mean', 'StdErr']],
            totals_sex[['Variable', 'Sum', 'StdDev']],
            on='Variable'
        )
        
        print(f"\nSEX = {sex_label}:")
        for _, row in results_sex.iterrows():
            var = row['Variable']
            label = var_labels.get(var, var)
            print(f"  {label}: N={row['N']:,.0f}, Pop={row['SumWgt']:,.0f}, Sum={row['Sum']:,.0f}, Mean={row['Mean']:,.2f} (SE: {row['StdErr']:.2f})")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Exercise 3a - Diabetes Condition Analysis 2015')
    parser.add_argument('--data-path', type=str, default='C:/MEPS/SAS/DATA',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
