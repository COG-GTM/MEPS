#!/usr/bin/env python3
"""
Python conversion of SAS Exercise1c.sas
Analyzes national healthcare expenses for civilian noninstitutionalized population in 2018
Uses weighted calculations to replicate SAS PROC SURVEYMEANS functionality
"""

import pandas as pd
import numpy as np
import pyreadstat
import warnings
warnings.filterwarnings('ignore')

def weighted_mean(values, weights):
    """Calculate weighted mean"""
    return np.average(values, weights=weights)

def weighted_median(values, weights):
    """
    Calculate weighted median using interpolation method
    More closely matches SAS PROC SURVEYMEANS median calculation
    """
    sorted_idx = np.argsort(values)
    sorted_values = values[sorted_idx]
    sorted_weights = weights[sorted_idx]
    
    cumsum_weights = np.cumsum(sorted_weights)
    total_weight = cumsum_weights[-1]
    median_weight = total_weight / 2
    
    median_idx = np.searchsorted(cumsum_weights, median_weight, side='right')
    
    if median_idx == 0:
        return sorted_values[0]
    elif median_idx >= len(sorted_values):
        return sorted_values[-1]
    else:
        lower_idx = median_idx - 1
        upper_idx = median_idx
        
        lower_cumweight = cumsum_weights[lower_idx] if lower_idx >= 0 else 0
        upper_cumweight = cumsum_weights[upper_idx]
        
        if abs(lower_cumweight - median_weight) < 1e-10:
            return sorted_values[lower_idx]
        elif abs(upper_cumweight - median_weight) < 1e-10:
            return sorted_values[upper_idx]
        
        weight_diff = upper_cumweight - lower_cumweight
        if weight_diff > 0:
            fraction = (median_weight - lower_cumweight) / weight_diff
            interpolated_value = sorted_values[lower_idx] + fraction * (sorted_values[upper_idx] - sorted_values[lower_idx])
            return interpolated_value
        else:
            return sorted_values[lower_idx]

def main():
    print("MEPS FULL-YEAR CONSOLIDATED FILE, 2018")
    print("=" * 60)
    print("Python Survey Analysis - Exercise 1c")
    print("National healthcare expenses analysis")
    print("Data: 2018 Full-year consolidated data file (HC-209)")
    print()
    
    data_file = "/home/ubuntu/attachments/f7c05e0e-0670-4077-8658-ea9e22b91083/h209.sas7bdat"
    
    print("Loading MEPS data...")
    df, meta = pyreadstat.read_sas7bdat(
        data_file,
        usecols=['TOTEXP18', 'AGELAST', 'VARSTR', 'VARPSU', 'PERWT18F', 'PANEL']
    )
    
    print(f"Initial observations: {len(df)}")
    
    df = df[df['PERWT18F'] > 0].copy()
    print(f"Observations with positive weights: {len(df)}")
    print(f"Observations with non-positive weights: {30461 - len(df)}")
    
    df['AGECAT'] = pd.cut(df['AGELAST'], 
                         bins=[0, 64, 999], 
                         labels=['0-64', '65+'], 
                         right=True)
    
    df['has_expense'] = (df['TOTEXP18'] > 0).astype(int)
    df['expense_category'] = df['TOTEXP18'].apply(
        lambda x: 'No Expense' if x == 0 else 'Any Expense'
    )
    
    n_strata = df['VARSTR'].nunique()
    n_clusters = df['VARPSU'].nunique()
    n_obs = len(df)
    sum_weights = df['PERWT18F'].sum()
    
    print(f"\nData Summary:")
    print(f"Number of strata: {n_strata}")
    print(f"Number of clusters: {n_clusters}")
    print(f"Number of observations: {n_obs}")
    print(f"Sum of weights: {sum_weights:,.0f}")
    
    print(f"\nAge categories: {df['AGECAT'].value_counts().to_dict()}")
    print(f"Expense categories: {df['expense_category'].value_counts().to_dict()}")
    
    print("\n" + "="*80)
    print("PERCENTAGE OF PERSONS WITH AN EXPENSE, 2018")
    print("="*80)
    
    pct_with_expense = weighted_mean(df['has_expense'], df['PERWT18F']) * 100
    pct_without_expense = 100 - pct_with_expense
    
    freq_with_expense = df[df['has_expense'] == 1]['PERWT18F'].sum()
    freq_without_expense = df[df['has_expense'] == 0]['PERWT18F'].sum()
    
    print(f"Any Expense:")
    print(f"  Frequency: {(df['has_expense'] == 1).sum()}")
    print(f"  Weighted Frequency: {freq_with_expense:,.0f}")
    print(f"  Percent: {pct_with_expense:.4f}%")
    
    print(f"No Expense:")
    print(f"  Frequency: {(df['has_expense'] == 0).sum()}")
    print(f"  Weighted Frequency: {freq_without_expense:,.0f}")
    print(f"  Percent: {pct_without_expense:.4f}%")
    
    print(f"Total:")
    print(f"  Frequency: {len(df)}")
    print(f"  Weighted Frequency: {sum_weights:,.0f}")
    print(f"  Percent: 100.0000%")
    
    results = {
        'pct_with_expense': pct_with_expense,
        'pct_without_expense': pct_without_expense,
        'freq_with_expense': int((df['has_expense'] == 1).sum()),
        'freq_without_expense': int((df['has_expense'] == 0).sum()),
        'weighted_freq_with_expense': freq_with_expense,
        'weighted_freq_without_expense': freq_without_expense
    }
    
    print("\n" + "="*80)
    print("MEAN AND MEDIAN EXPENSE PER PERSON WITH AN EXPENSE, OVERALL and FOR AGES 0-64, AND 65+, 2018")
    print("="*80)
    
    overall_mean = weighted_mean(df['TOTEXP18'], df['PERWT18F'])
    overall_median = weighted_median(df['TOTEXP18'].values, df['PERWT18F'].values)
    
    print(f"\nOverall Statistics (All People):")
    print(f"  N: {len(df)}")
    print(f"  Mean: ${overall_mean:.6f}")
    print(f"  Median: ${overall_median:.6f}")
    
    results['overall_mean'] = overall_mean
    results['overall_median'] = overall_median
    
    expense_data = df[df['TOTEXP18'] > 0].copy()
    
    print(f"\nStatistics for People with Any Expense:")
    print(f"  N: {len(expense_data)}")
    
    if len(expense_data) > 0:
        mean_expense = weighted_mean(expense_data['TOTEXP18'], expense_data['PERWT18F'])
        median_expense = weighted_median(expense_data['TOTEXP18'].values, expense_data['PERWT18F'].values)
        
        print(f"  Mean: ${mean_expense:.6f}")
        print(f"  Median: ${median_expense:.6f}")
        
        results['mean_expense_with_expense'] = mean_expense
        results['median_expense_with_expense'] = median_expense
    
    print(f"\nAge-Stratified Statistics for People with Any Expense:")
    
    for age_group in ['0-64', '65+']:
        age_expense_data = df[(df['TOTEXP18'] > 0) & (df['AGECAT'] == age_group)].copy()
        
        if len(age_expense_data) > 0:
            age_mean = weighted_mean(age_expense_data['TOTEXP18'], age_expense_data['PERWT18F'])
            age_median = weighted_median(age_expense_data['TOTEXP18'].values, age_expense_data['PERWT18F'].values)
            
            print(f"  Age {age_group}:")
            print(f"    N: {len(age_expense_data)}")
            print(f"    Mean: ${age_mean:.6f}")
            print(f"    Median: ${age_median:.6f}")
            
            age_key = age_group.replace('-', '_').replace('+', 'plus')
            results[f'mean_expense_{age_key}'] = age_mean
            results[f'median_expense_{age_key}'] = age_median
    
    print("\n" + "="*80)
    print("SUMMARY OF KEY RESULTS")
    print("="*80)
    print(f"1. Percentage with any expense: {results['pct_with_expense']:.4f}%")
    print(f"2. Mean expense (those with expenses): ${results['mean_expense_with_expense']:.2f}")
    if 'median_expense_0_64' in results:
        print(f"3. Median expense (0-64 years): ${results['median_expense_0_64']:.6f}")
    if 'median_expense_65plus' in results:
        print(f"4. Median expense (65+ years): ${results['median_expense_65plus']:.6f}")
    
    import json
    with open('/home/ubuntu/repos/MEPS/Python/workshop_exercises/exercise_1c/python_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to python_results.json")
    return results

if __name__ == "__main__":
    results = main()
