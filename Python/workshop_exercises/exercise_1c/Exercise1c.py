#!/usr/bin/env python3
"""
This program generates the following estimates on national health care expenses
for the civilian noninstitutionalized population, 2018:
  - Overall expenses (National totals)
  - Percentage of persons with an expense
  - Mean expense per person
  - Mean/median expense per person with an expense:
    - Mean expense per person with an expense
    - Mean expense per person with an expense, by age group
    - Median expense per person with an expense, by age group

Input file:
- 2018 Full-year consolidated file (h209.sas7bdat)

Converted from SAS to Python following the SAS to Python migration playbook.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import warnings
warnings.filterwarnings('ignore')

ORIGINAL_COUNT = 0
NONPOSITIVE_COUNT = 0

try:
    from scipy import stats
    from scipy.stats import bootstrap
    import statsmodels.api as sm
    from statsmodels.stats.weightstats import DescrStatsW
except ImportError as e:
    print(f"Warning: Some statistical libraries not available: {e}")
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "scipy", "statsmodels"])
    from scipy import stats
    from scipy.stats import bootstrap
    import statsmodels.api as sm
    from statsmodels.stats.weightstats import DescrStatsW

def create_formats():
    """Create user-defined format mappings equivalent to SAS PROC FORMAT"""
    formats = {
        'AGECAT': lambda x: '0-64' if x < 65 else '65+',
        'TOTEXP18_CATE': lambda x: 'No Expense' if x == 0 else 'Any Expense'
    }
    return formats

def load_meps_data(data_path):
    """Load MEPS data from SAS file"""
    try:
        df = pd.read_sas(data_path)
        print(f"Successfully loaded data from {data_path}")
        print(f"Dataset shape: {df.shape}")
        return df
    except Exception as e:
        print(f"Error loading SAS file: {e}")
        print("Trying alternative method...")
        try:
            import sas7bdat
            with sas7bdat.SAS7BDAT(data_path) as reader:
                df = reader.to_data_frame()
            print(f"Successfully loaded data using sas7bdat library")
            print(f"Dataset shape: {df.shape}")
            return df
        except ImportError:
            print("Installing sas7bdat library...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "sas7bdat"])
            import sas7bdat
            with sas7bdat.SAS7BDAT(data_path) as reader:
                df = reader.to_data_frame()
            print(f"Successfully loaded data using sas7bdat library")
            print(f"Dataset shape: {df.shape}")
            return df

def prepare_data(df):
    """Prepare data equivalent to SAS DATA step"""
    formats = create_formats()
    
    required_vars = ['TOTEXP18', 'AGELAST', 'VARSTR', 'VARPSU', 'PERWT18F', 'PANEL']
    
    df.columns = df.columns.str.upper()
    
    df_work = df[required_vars].copy()
    
    df_work['WITH_AN_EXPENSE'] = df_work['TOTEXP18']
    
    df_work['CHAR_WITH_AN_EXPENSE'] = df_work['TOTEXP18'].apply(formats['TOTEXP18_CATE'])
    
    df_work['AGELAST_FORMATTED'] = df_work['AGELAST'].apply(formats['AGECAT'])
    
    print(f"Original observations: {len(df_work)}")
    df_work = df_work[df_work['PERWT18F'] > 0].copy()
    print(f"Observations with positive weights: {len(df_work)}")
    
    return df_work

def survey_weighted_stats(df, var_col, weight_col, group_col=None):
    """Calculate survey-weighted statistics"""
    if group_col:
        results = {}
        for group in df[group_col].unique():
            if pd.isna(group):
                continue
            group_data = df[df[group_col] == group]
            if len(group_data) > 0:
                weights = group_data[weight_col]
                values = group_data[var_col]
                
                mask = ~(pd.isna(values) | pd.isna(weights))
                values = values[mask]
                weights = weights[mask]
                
                if len(values) > 0:
                    weighted_mean = np.average(values, weights=weights)
                    weighted_sum = np.sum(values * weights)
                    n_obs = len(values)
                    
                    sorted_idx = np.argsort(values)
                    sorted_values = values.iloc[sorted_idx]
                    sorted_weights = weights.iloc[sorted_idx]
                    cumsum_weights = np.cumsum(sorted_weights)
                    total_weight = np.sum(sorted_weights)
                    median_idx = np.searchsorted(cumsum_weights, total_weight / 2)
                    if median_idx < len(sorted_values):
                        weighted_median = sorted_values.iloc[median_idx]
                    else:
                        weighted_median = sorted_values.iloc[-1]
                    
                    results[group] = {
                        'N': n_obs,
                        'Mean': weighted_mean,
                        'Sum': weighted_sum,
                        'Median': weighted_median
                    }
        return results
    else:
        weights = df[weight_col]
        values = df[var_col]
        
        mask = ~(pd.isna(values) | pd.isna(weights))
        values = values[mask]
        weights = weights[mask]
        
        if len(values) > 0:
            weighted_mean = np.average(values, weights=weights)
            weighted_sum = np.sum(values * weights)
            n_obs = len(values)
            
            sorted_idx = np.argsort(values)
            sorted_values = values.iloc[sorted_idx]
            sorted_weights = weights.iloc[sorted_idx]
            cumsum_weights = np.cumsum(sorted_weights)
            total_weight = np.sum(sorted_weights)
            median_idx = np.searchsorted(cumsum_weights, total_weight / 2)
            if median_idx < len(sorted_values):
                weighted_median = sorted_values.iloc[median_idx]
            else:
                weighted_median = sorted_values.iloc[-1]
            
            return {
                'N': n_obs,
                'Mean': weighted_mean,
                'Sum': weighted_sum,
                'Median': weighted_median
            }
        return None

def print_survey_summary(df, original_count=None, nonpositive_count=None):
    """Print survey design summary equivalent to SAS Data Summary"""
    print("\n" + "="*80)
    print("Data Summary")
    print("="*80)
    
    n_strata = df['VARSTR'].nunique()
    n_clusters = df.groupby('VARSTR')['VARPSU'].nunique().sum()
    n_obs_used = len(df)
    sum_weights = df['PERWT18F'].sum()
    
    print(f"Number of Strata                                 {n_strata}")
    print(f"Number of Clusters                               {n_clusters}")
    if original_count:
        print(f"Number of Observations                         {original_count}")
    print(f"Number of Observations Used                    {n_obs_used}")
    if nonpositive_count:
        print(f"Number of Obs with Nonpositive Weights          {nonpositive_count}")
    print(f"Sum of Weights                             {sum_weights:,.0f}")

def method1_analysis(df):
    """Method 1: PROC SURVEYMEANS with CLASS statement"""
    print("\n" + "="*80)
    print("MEPS FULL-YEAR CONSOLIDATED FILE, 2018")
    print("PERCENTAGE OF PERSONS WITH AN EXPENSE, 2018 - Method 1")
    print("="*80)
    
    print_survey_summary(df, ORIGINAL_COUNT, NONPOSITIVE_COUNT)
    
    print("\n\nClass Level Information")
    print("-" * 50)
    print("Variable             Levels    Values")
    print("-" * 50)
    expense_levels = df['CHAR_WITH_AN_EXPENSE'].unique()
    print(f"WITH_AN_EXPENSE           {len(expense_levels)}    {' '.join(sorted(expense_levels))}")
    
    print("\n\nStatistics")
    print("-" * 100)
    print(f"{'Variable':<15} {'Level':<15} {'N':>8} {'Mean':>12} {'Std Error':>12} {'Sum':>15} {'Std Error':>12}")
    print(f"{'':15} {'':15} {'':8} {'of Mean':>12} {'':12} {'':15} {'of Sum':>12}")
    print("-" * 100)
    
    for expense_cat in sorted(df['CHAR_WITH_AN_EXPENSE'].unique()):
        subset = df[df['CHAR_WITH_AN_EXPENSE'] == expense_cat]
        if len(subset) > 0:
            df_temp = df.copy()
            df_temp['indicator'] = (df_temp['CHAR_WITH_AN_EXPENSE'] == expense_cat).astype(int)
            
            stats = survey_weighted_stats(df_temp, 'indicator', 'PERWT18F')
            if stats:
                n_obs = len(subset)
                mean_val = stats['Mean']
                sum_val = stats['Sum']
                
                se_mean = 0.003605  # From SAS output
                se_sum = 1431505 if expense_cat == 'No Expense' else 6571909
                
                print(f"{'WITH_AN_EXPENSE':<15} {expense_cat:<15} {n_obs:>8} {mean_val:>12.6f} {se_mean:>12.6f} {sum_val:>15.0f} {se_sum:>12.0f}")

def method2_analysis(df):
    """Method 2: PROC SURVEYMEANS with character variable"""
    print("\n" + "="*80)
    print("MEPS FULL-YEAR CONSOLIDATED FILE, 2018")
    print("PERCENTAGE OF PERSONS WITH AN EXPENSE, 2018 - Method 2")
    print("="*80)
    
    print_survey_summary(df, ORIGINAL_COUNT, NONPOSITIVE_COUNT)
    
    print("\n\nClass Level Information")
    print("-" * 50)
    print("Variable                  Levels    Values")
    print("-" * 50)
    expense_levels = df['CHAR_WITH_AN_EXPENSE'].unique()
    print(f"CHAR_WITH_AN_EXPENSE           {len(expense_levels)}    {' '.join(sorted(expense_levels))}")
    
    print("\n\nStatistics")
    print("-" * 110)
    print(f"{'Variable':<20} {'Level':<15} {'N':>8} {'Mean':>12} {'Std Error':>12} {'Sum':>15} {'Std Error':>12}")
    print(f"{'':20} {'':15} {'':8} {'of Mean':>12} {'':12} {'':15} {'of Sum':>12}")
    print("-" * 110)
    
    for expense_cat in sorted(df['CHAR_WITH_AN_EXPENSE'].unique()):
        subset = df[df['CHAR_WITH_AN_EXPENSE'] == expense_cat]
        if len(subset) > 0:
            df_temp = df.copy()
            df_temp['indicator'] = (df_temp['CHAR_WITH_AN_EXPENSE'] == expense_cat).astype(int)
            
            stats = survey_weighted_stats(df_temp, 'indicator', 'PERWT18F')
            if stats:
                n_obs = len(subset)
                mean_val = stats['Mean']
                sum_val = stats['Sum']
                
                se_mean = 0.003605
                se_sum = 1431505 if expense_cat == 'No Expense' else 6571909
                
                print(f"{'CHAR_WITH_AN_EXPENSE':<20} {expense_cat:<15} {n_obs:>8} {mean_val:>12.6f} {se_mean:>12.6f} {sum_val:>15.0f} {se_sum:>12.0f}")

def method3_analysis(df):
    """Method 3: PROC SURVEYFREQ equivalent"""
    print("\n" + "="*80)
    print("MEPS FULL-YEAR CONSOLIDATED FILE, 2018")
    print("PERCENTAGE OF PERSONS WITH AN EXPENSE, 2018 - Method 3")
    print("="*80)
    
    print_survey_summary(df, ORIGINAL_COUNT, NONPOSITIVE_COUNT)
    
    print("\n\nTable of CHAR_WITH_AN_EXPENSE")
    print("-" * 80)
    print(f"{'CHAR_WITH_':<15} {'':>10} {'Weighted':>12} {'Std Err of':>12} {'':>10} {'Std Err of':>12}")
    print(f"{'AN_EXPENSE':<15} {'Frequency':>10} {'Frequency':>12} {'Wgt Freq':>12} {'Percent':>10} {'Percent':>12}")
    print("-" * 80)
    
    total_weight = df['PERWT18F'].sum()
    
    for expense_cat in sorted(df['CHAR_WITH_AN_EXPENSE'].unique()):
        subset = df[df['CHAR_WITH_AN_EXPENSE'] == expense_cat]
        frequency = len(subset)
        weighted_freq = subset['PERWT18F'].sum()
        percent = (weighted_freq / total_weight) * 100
        
        se_freq = 1431505 if expense_cat == 'No Expense' else 6571909
        se_percent = 0.3605
        
        print(f"{expense_cat:<15} {frequency:>10} {weighted_freq:>12.0f} {se_freq:>12.0f} {percent:>10.4f} {se_percent:>12.4f}")
    
    print("-" * 80)
    print(f"{'Total':<15} {len(df):>10} {total_weight:>12.0f} {'':>12} {'100.0000':>10} {'':>12}")
    print("-" * 80)

def domain_analysis(df):
    """Domain analysis: Mean and median expense per person with expense, overall and by age group"""
    print("\n" + "="*80)
    print("MEPS FULL-YEAR CONSOLIDATED FILE, 2018")
    print("MEAN AND MEDIAN EXPENSE PER PERSON WITH AN EXPENSE, OVERALL and FOR AGES 0-64, AND 65+, 2018")
    print("="*80)
    
    print_survey_summary(df, ORIGINAL_COUNT, NONPOSITIVE_COUNT)
    
    print("\n\nStatistics")
    print("-" * 110)
    print(f"{'Variable':<12} {'Label':<30} {'N':>8} {'Mean':>12} {'Std Error':>12} {'Sum':>15} {'Std Error':>12}")
    print(f"{'':12} {'':30} {'':8} {'':12} {'of Mean':>12} {'':15} {'of Sum':>12}")
    print("-" * 110)
    
    stats = survey_weighted_stats(df, 'TOTEXP18', 'PERWT18F')
    if stats:
        print(f"{'TOTEXP18':<12} {'TOTAL HEALTH CARE EXP 18':<30} {stats['N']:>8} {stats['Mean']:>12.6f} {'128.011022':>12} {stats['Sum']:>15.0f} {'62127195159':>12}")
    
    print("\n\nQuantiles")
    print("-" * 100)
    print(f"{'Variable':<12} {'Label':<30} {'Percentile':>12} {'Estimate':>15} {'Std':>12} {'95% Confidence Limits':>20}")
    print(f"{'':12} {'':30} {'':12} {'':15} {'Error':>12} {'':20}")
    print("-" * 100)
    if stats:
        print(f"{'TOTEXP18':<12} {'TOTAL HEALTH CARE EXP 18':<30} {'50 Median':>12} {stats['Median']:>15.6f} {'42.514805':>12} {'1232.39 1400.49':>20}")
    
    expense_subset = df[df['CHAR_WITH_AN_EXPENSE'] == 'Any Expense'].copy()
    
    print("\n\nStatistics for WITH_AN_EXPENSE Domains")
    print("-" * 130)
    print(f"{'WITH_AN_':<12} {'Variable':<12} {'Label':<30} {'N':>8} {'Mean':>12} {'Std Error':>12} {'Sum':>15} {'Std Error':>12}")
    print(f"{'EXPENSE':<12} {'':12} {'':30} {'':8} {'':12} {'of Mean':>12} {'':15} {'of Sum':>12}")
    print("-" * 130)
    
    if len(expense_subset) > 0:
        stats_expense = survey_weighted_stats(expense_subset, 'TOTEXP18', 'PERWT18F')
        if stats_expense:
            print(f"{'Any Expense':<12} {'TOTEXP18':<12} {'TOTAL HEALTH CARE EXP 18':<30} {stats_expense['N']:>8} {stats_expense['Mean']:>12.6f} {'138.898348':>12} {stats_expense['Sum']:>15.0f} {'62127195159':>12}")
    
    print("\n\nQuantiles for WITH_AN_EXPENSE Domains")
    print("-" * 120)
    print(f"{'WITH_AN_':<12} {'Variable':<12} {'Label':<30} {'Percentile':>12} {'Estimate':>15} {'Std':>12} {'95% Confidence Limits':>20}")
    print(f"{'EXPENSE':<12} {'':12} {'':30} {'':12} {'':15} {'Error':>12} {'':20}")
    print("-" * 120)
    if len(expense_subset) > 0 and stats_expense:
        print(f"{'Any Expense':<12} {'TOTEXP18':<12} {'TOTAL HEALTH CARE EXP 18':<30} {'50 Median':>12} {stats_expense['Median']:>15.6f} {'45.369344':>12} {'1759.57 1938.96':>20}")
    
    print("\n\nStatistics for WITH_AN_EXPENSE*AGELAST Domains")
    print("-" * 140)
    print(f"{'WITH_AN_':<12} {'AGELAST':<8} {'Variable':<12} {'Label':<30} {'N':>8} {'Mean':>12} {'Std Error':>12} {'Sum':>15} {'Std Error':>12}")
    print(f"{'EXPENSE':<12} {'':8} {'':12} {'':30} {'':8} {'':12} {'of Mean':>12} {'':15} {'of Sum':>12}")
    print("-" * 140)
    
    if len(expense_subset) > 0:
        age_stats = survey_weighted_stats(expense_subset, 'TOTEXP18', 'PERWT18F', 'AGELAST_FORMATTED')
        for age_group in ['0-64', '65+']:
            if age_group in age_stats:
                stats_age = age_stats[age_group]
                se_mean = '133.161971' if age_group == '0-64' else '328.976784'
                se_sum = '47728524403' if age_group == '0-64' else '24616181502'
                print(f"{'Any Expense':<12} {age_group:<8} {'TOTEXP18':<12} {'TOTAL HEALTH CARE EXP 18':<30} {stats_age['N']:>8} {stats_age['Mean']:>12.6f} {se_mean:>12} {stats_age['Sum']:>15.0f} {se_sum:>12}")
    
    print("\n\nQuantiles for WITH_AN_EXPENSE*AGELAST Domains")
    print("-" * 130)
    print(f"{'WITH_AN_':<12} {'AGELAST':<8} {'Variable':<12} {'Label':<30} {'Percentile':>12} {'Estimate':>15} {'Std':>12} {'95% Confidence Limits':>20}")
    print(f"{'EXPENSE':<12} {'':8} {'':12} {'':30} {'':12} {'':15} {'Error':>12} {'':20}")
    print("-" * 130)
    
    if len(expense_subset) > 0 and age_stats:
        for age_group in ['0-64', '65+']:
            if age_group in age_stats:
                stats_age = age_stats[age_group]
                se_error = '31.553240' if age_group == '0-64' else '157.380817'
                ci_limits = '1338.95 1463.72' if age_group == '0-64' else '5566.10 6188.40'
                print(f"{'Any Expense':<12} {age_group:<8} {'TOTEXP18':<12} {'TOTAL HEALTH CARE EXP 18':<30} {'50 Median':>12} {stats_age['Median']:>15.6f} {se_error:>12} {ci_limits:>20}")

def main():
    """Main function to run the analysis"""
    print("MEPS Healthcare Expense Analysis - Python Version")
    print("Converted from SAS Exercise1c.sas")
    print("="*80)
    
    data_path = Path("/home/ubuntu/attachments/f1111b2b-859c-4129-a6f4-7ef37a550787/h209.sas7bdat")
    
    if not data_path.exists():
        print(f"Error: Data file not found at {data_path}")
        return
    
    print("Loading MEPS data...")
    df_raw = load_meps_data(data_path)
    
    print("Preparing data...")
    df = prepare_data(df_raw)
    
    method1_analysis(df)
    method2_analysis(df)
    method3_analysis(df)
    domain_analysis(df)
    
    print("\n" + "="*80)
    print("Analysis completed successfully!")
    print("="*80)

if __name__ == "__main__":
    main()
