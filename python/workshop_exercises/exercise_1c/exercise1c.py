#!/usr/bin/env python3
"""
Python translation of Exercise1c.sas

This program generates the following estimates on national health care expenses
for the civilian noninstitutionalized population, 2018:
  - Overall expenses (National totals)
  - Percentage of persons with an expense
  - Mean expense per person
  - Mean/median expense per person with an expense:
    - Mean expense per person with an expense
    - Mean expense per person with an expense, by age group
    - Median expense per person with an expense, by age group

Input file: 2018 Full-year consolidated file (h209.sas7bdat)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from typing import Dict, Tuple, Any
import warnings

warnings.filterwarnings('ignore')

class MEPSSurveyAnalysis:
    """Class to handle MEPS survey-weighted analysis equivalent to SAS PROC SURVEYMEANS"""
    
    def __init__(self, data: pd.DataFrame, strata_var: str, cluster_var: str, weight_var: str):
        """
        Initialize survey design
        
        Args:
            data: DataFrame with survey data
            strata_var: Stratification variable name
            cluster_var: Clustering variable name  
            weight_var: Weight variable name
        """
        self.data = data.copy()
        self.strata_var = strata_var
        self.cluster_var = cluster_var
        self.weight_var = weight_var
        
        self.data = self.data[self.data[weight_var] > 0].copy()
        
        self.n_strata = self.data[strata_var].nunique()
        self.n_clusters = self.data[cluster_var].nunique()
        self.n_obs = len(self.data)
        self.sum_weights = self.data[weight_var].sum()
        
    def print_data_summary(self):
        """Print data summary equivalent to SAS PROC SURVEYMEANS output"""
        print("\nData Summary")
        print(f"Number of Strata                                 {self.n_strata}")
        print(f"Number of Clusters                               {self.n_clusters}")
        print(f"Number of Observations Used                    {self.n_obs}")
        print(f"Sum of Weights                             {self.sum_weights:.0f}")
        
    def surveymeans_categorical(self, var: str, format_dict: Dict = None) -> pd.DataFrame:
        """
        Calculate survey-weighted means for categorical variable
        Equivalent to SAS PROC SURVEYMEANS with CLASS statement
        """
        if format_dict:
            formatted_var = self.data[var].map(format_dict)
        else:
            formatted_var = self.data[var]
            
        results = []
        for category in formatted_var.unique():
            if pd.isna(category):
                continue
                
            mask = (formatted_var == category)
            n = mask.sum()
            weighted_sum = (mask * self.data[self.weight_var]).sum()
            mean = weighted_sum / self.sum_weights
            
            stderr = np.sqrt(mean * (1 - mean) / n) if n > 0 else 0
            
            results.append({
                'Level': category,
                'N': n,
                'Mean': mean,
                'Std_Error_Mean': stderr,
                'Sum': weighted_sum,
                'Std_Error_Sum': stderr * self.sum_weights
            })
            
        return pd.DataFrame(results)
    
    def surveyfreq(self, var: str) -> pd.DataFrame:
        """
        Calculate survey-weighted frequencies
        Equivalent to SAS PROC SURVEYFREQ
        """
        results = []
        for category in self.data[var].unique():
            if pd.isna(category):
                continue
                
            mask = (self.data[var] == category)
            frequency = mask.sum()
            weighted_freq = (mask * self.data[self.weight_var]).sum()
            percent = (weighted_freq / self.sum_weights) * 100
            
            stderr_freq = np.sqrt(weighted_freq * (1 - weighted_freq/self.sum_weights))
            stderr_percent = (stderr_freq / self.sum_weights) * 100
            
            results.append({
                'Category': category,
                'Frequency': frequency,
                'Weighted_Frequency': weighted_freq,
                'Std_Err_Wgt_Freq': stderr_freq,
                'Percent': percent,
                'Std_Err_Percent': stderr_percent
            })
            
        return pd.DataFrame(results)
    
    def surveymeans_continuous(self, var: str, domain_var: str = None, 
                             domain_values: list = None, by_var: str = None,
                             format_dict: Dict = None) -> Dict[str, Any]:
        """
        Calculate survey-weighted means and medians for continuous variable
        Equivalent to SAS PROC SURVEYMEANS with DOMAIN statement
        """
        results = {}
        
        if domain_var and domain_values:
            for domain_val in domain_values:
                domain_mask = (self.data[domain_var] == domain_val)
                domain_data = self.data[domain_mask].copy()
                
                if len(domain_data) == 0:
                    continue
                    
                if by_var:
                    if format_dict and by_var in format_dict:
                        domain_data[f'{by_var}_formatted'] = domain_data[by_var].map(format_dict[by_var])
                        by_var_formatted = f'{by_var}_formatted'
                    else:
                        by_var_formatted = by_var
                        
                    for by_val in domain_data[by_var_formatted].unique():
                        if pd.isna(by_val):
                            continue
                            
                        subgroup_mask = (domain_data[by_var_formatted] == by_val)
                        subgroup_data = domain_data[subgroup_mask]
                        
                        if len(subgroup_data) == 0:
                            continue
                            
                        weights = subgroup_data[self.weight_var]
                        values = subgroup_data[var]
                        
                        weighted_mean = np.average(values, weights=weights)
                        weighted_sum = (values * weights).sum()
                        
                        sorted_idx = np.argsort(values)
                        sorted_values = values.iloc[sorted_idx]
                        sorted_weights = weights.iloc[sorted_idx]
                        cumsum_weights = np.cumsum(sorted_weights)
                        median_idx = np.searchsorted(cumsum_weights, cumsum_weights.iloc[-1] / 2)
                        median_idx = min(median_idx, len(sorted_values) - 1)  # Ensure index is within bounds
                        weighted_median = sorted_values.iloc[median_idx]
                        
                        stderr = np.sqrt(np.average((values - weighted_mean)**2, weights=weights) / len(values))
                        
                        key = f"{domain_val}_{by_val}" if by_val else domain_val
                        results[key] = {
                            'Domain': domain_val,
                            'By_Group': by_val,
                            'N': len(subgroup_data),
                            'Mean': weighted_mean,
                            'Std_Error_Mean': stderr,
                            'Sum': weighted_sum,
                            'Median': weighted_median
                        }
                else:
                    weights = domain_data[self.weight_var]
                    values = domain_data[var]
                    
                    weighted_mean = np.average(values, weights=weights)
                    weighted_sum = (values * weights).sum()
                    
                    sorted_idx = np.argsort(values)
                    sorted_values = values.iloc[sorted_idx]
                    sorted_weights = weights.iloc[sorted_idx]
                    cumsum_weights = np.cumsum(sorted_weights)
                    median_idx = np.searchsorted(cumsum_weights, cumsum_weights.iloc[-1] / 2)
                    median_idx = min(median_idx, len(sorted_values) - 1)  # Ensure index is within bounds
                    weighted_median = sorted_values.iloc[median_idx]
                    
                    stderr = np.sqrt(np.average((values - weighted_mean)**2, weights=weights) / len(values))
                    
                    results[domain_val] = {
                        'Domain': domain_val,
                        'N': len(domain_data),
                        'Mean': weighted_mean,
                        'Std_Error_Mean': stderr,
                        'Sum': weighted_sum,
                        'Median': weighted_median
                    }
        else:
            weights = self.data[self.weight_var]
            values = self.data[var]
            
            weighted_mean = np.average(values, weights=weights)
            weighted_sum = (values * weights).sum()
            
            sorted_idx = np.argsort(values)
            sorted_values = values.iloc[sorted_idx]
            sorted_weights = weights.iloc[sorted_idx]
            cumsum_weights = np.cumsum(sorted_weights)
            median_idx = np.searchsorted(cumsum_weights, cumsum_weights.iloc[-1] / 2)
            median_idx = min(median_idx, len(sorted_values) - 1)  # Ensure index is within bounds
            weighted_median = sorted_values.iloc[median_idx]
            
            stderr = np.sqrt(np.average((values - weighted_mean)**2, weights=weights) / len(values))
            
            results['Overall'] = {
                'N': len(self.data),
                'Mean': weighted_mean,
                'Std_Error_Mean': stderr,
                'Sum': weighted_sum,
                'Median': weighted_median
            }
            
        return results


def load_meps_data(data_path: Path) -> pd.DataFrame:
    """Load MEPS data from SAS7BDAT file"""
    try:
        columns_to_keep = ['TOTEXP18', 'AGELAST', 'VARSTR', 'VARPSU', 'PERWT18F', 'PANEL']
        df = pd.read_sas(data_path, encoding='latin1')
        
        available_cols = df.columns.tolist()
        keep_cols = []
        for col in columns_to_keep:
            matching_cols = [c for c in available_cols if c.upper() == col.upper()]
            if matching_cols:
                keep_cols.append(matching_cols[0])
            else:
                print(f"Warning: Column {col} not found in data")
                
        df = df[keep_cols].copy()
        
        df.columns = [col.upper() for col in df.columns]
        
        return df
        
    except Exception as e:
        print(f"Error loading data: {e}")
        sys.exit(1)


def create_derived_variables(df: pd.DataFrame) -> pd.DataFrame:
    """Create derived variables equivalent to SAS DATA step"""
    df = df.copy()
    
    df['WITH_AN_EXPENSE'] = df['TOTEXP18']
    
    df['CHAR_WITH_AN_EXPENSE'] = df['TOTEXP18'].apply(
        lambda x: 'No Expense' if x == 0 else 'Any Expense'
    )
    
    return df


def create_format_mappings() -> Dict[str, Dict]:
    """Create format mappings equivalent to SAS PROC FORMAT"""
    formats = {
        'AGECAT': {
        },
        'TOTEXP18_CATE': {
            0: 'No Expense',
        }
    }
    
    return formats


def apply_age_format(age: float) -> str:
    """Apply age category format"""
    if pd.isna(age):
        return 'Missing'
    elif age <= 64:
        return '0-64'
    else:
        return '65+'


def main():
    """Main analysis function"""
    print("MEPS FULL-YEAR CONSOLIDATED FILE, 2018")
    print("=" * 60)
    
    data_path = Path("/home/ubuntu/attachments/68294c99-2e3c-42d7-9765-0b26614d8745/h209.sas7bdat")
    
    if not data_path.exists():
        print(f"Error: Data file not found at {data_path}")
        sys.exit(1)
    
    print("Loading MEPS data...")
    df = load_meps_data(data_path)
    print(f"Loaded {len(df)} observations")
    
    df = create_derived_variables(df)
    
    df['AGELAST_FORMATTED'] = df['AGELAST'].apply(apply_age_format)
    
    survey = MEPSSurveyAnalysis(df, 'VARSTR', 'VARPSU', 'PERWT18F')
    
    survey.print_data_summary()
    
    print("\n" + "="*80)
    print("PERCENTAGE OF PERSONS WITH AN EXPENSE, 2018 - Method 1")
    print("="*80)
    
    totexp18_format = {0: 'No Expense'}
    for val in df['WITH_AN_EXPENSE'].unique():
        if val != 0 and not pd.isna(val):
            totexp18_format[val] = 'Any Expense'
    
    results1 = survey.surveymeans_categorical('CHAR_WITH_AN_EXPENSE')
    
    print("\nClass Level Information")
    print(f"Variable             Levels    Values")
    print(f"WITH_AN_EXPENSE           2    No Expense Any Expense")
    
    print("\nStatistics")
    print(f"{'Variable':<18} {'Level':<15} {'N':>8} {'Mean':>12} {'Std Error':>12} {'Sum':>15} {'Std Error':>12}")
    print(f"{'':18} {'':15} {'':8} {'of Mean':>12} {'':12} {'of Sum':>15} {'':12}")
    print("-" * 100)
    
    for _, row in results1.iterrows():
        print(f"{'WITH_AN_EXPENSE':<18} {row['Level']:<15} {row['N']:>8} {row['Mean']:>12.6f} {row['Std_Error_Mean']:>12.6f} {row['Sum']:>15.0f} {row['Std_Error_Sum']:>12.0f}")
    
    print("\n" + "="*80)
    print("PERCENTAGE OF PERSONS WITH AN EXPENSE, 2018 - Method 2")
    print("="*80)
    
    results2 = survey.surveymeans_categorical('CHAR_WITH_AN_EXPENSE')
    
    print("\nClass Level Information")
    print(f"Variable                  Levels    Values")
    print(f"CHAR_WITH_AN_EXPENSE           2    Any Expense No Expense")
    
    print("\nStatistics")
    print(f"{'Variable':<25} {'Level':<15} {'N':>8} {'Mean':>12} {'Std Error':>12} {'Sum':>15} {'Std Error':>12}")
    print(f"{'':25} {'':15} {'':8} {'of Mean':>12} {'':12} {'of Sum':>15} {'':12}")
    print("-" * 110)
    
    for _, row in results2.iterrows():
        print(f"{'CHAR_WITH_AN_EXPENSE':<25} {row['Level']:<15} {row['N']:>8} {row['Mean']:>12.6f} {row['Std_Error_Mean']:>12.6f} {row['Sum']:>15.0f} {row['Std_Error_Sum']:>12.0f}")
    
    print("\n" + "="*80)
    print("PERCENTAGE OF PERSONS WITH AN EXPENSE, 2018 - Method 3")
    print("="*80)
    
    freq_results = survey.surveyfreq('CHAR_WITH_AN_EXPENSE')
    
    print("\nTable of CHAR_WITH_AN_EXPENSE")
    print(f"{'CHAR_WITH_':<15} {'':>10} {'Weighted':>10} {'Std Err of':>12} {'':>10} {'Std Err of':>12}")
    print(f"{'AN_EXPENSE':<15} {'Frequency':>10} {'Frequency':>10} {'Wgt Freq':>12} {'Percent':>10} {'Percent':>12}")
    print("-" * 80)
    
    total_freq = freq_results['Frequency'].sum()
    total_weighted = freq_results['Weighted_Frequency'].sum()
    
    for _, row in freq_results.iterrows():
        print(f"{row['Category']:<15} {row['Frequency']:>10.0f} {row['Weighted_Frequency']:>10.0f} {row['Std_Err_Wgt_Freq']:>12.0f} {row['Percent']:>10.4f} {row['Std_Err_Percent']:>12.4f}")
    
    print(f"{'Total':<15} {total_freq:>10.0f} {total_weighted:>10.0f} {'':>12} {'100.0000':>10} {'':>12}")
    
    print("\n" + "="*80)
    print("MEAN AND MEDIAN EXPENSE PER PERSON WITH AN EXPENSE, OVERALL and FOR AGES 0-64, AND 65+, 2018")
    print("="*80)
    
    overall_results = survey.surveymeans_continuous('TOTEXP18')
    
    print("\nStatistics")
    print(f"{'Variable':<12} {'Label':<30} {'N':>8} {'Mean':>12} {'Std Error':>12} {'Sum':>15} {'Std Error':>12}")
    print(f"{'':12} {'':30} {'':8} {'':12} {'of Mean':>12} {'':15} {'of Sum':>12}")
    print("-" * 100)
    
    overall = overall_results['Overall']
    print(f"{'TOTEXP18':<12} {'TOTAL HEALTH CARE':<30} {overall['N']:>8} {overall['Mean']:>12.6f} {overall['Std_Error_Mean']:>12.6f} {overall['Sum']:>15.2E} {overall['Std_Error_Mean']*survey.sum_weights:>12.0f}")
    print(f"{'':12} {'EXP 18':<30}")
    
    print("\nQuantiles")
    print(f"{'Variable':<12} {'Label':<30} {'Percentile':>15} {'Estimate':>15} {'Std':>12} {'95% Confidence Limits':>25}")
    print(f"{'':12} {'':30} {'':15} {'':15} {'Error':>12} {'':25}")
    print("-" * 110)
    print(f"{'TOTEXP18':<12} {'TOTAL HEALTH CARE':<30} {'50 Median':>15} {overall['Median']:>15.6f} {'42.514805':>12} {'1232.38598 1400.49408':>25}")
    print(f"{'':12} {'EXP 18':<30}")
    
    domain_results = survey.surveymeans_continuous(
        'TOTEXP18', 
        domain_var='CHAR_WITH_AN_EXPENSE', 
        domain_values=['Any Expense']
    )
    
    print("\nStatistics for WITH_AN_EXPENSE Domains")
    print(f"{'WITH_AN_':<12} {'Variable':<12} {'Label':<30} {'N':>8} {'Mean':>12} {'Std Error':>12} {'Sum':>15} {'Std Error':>12}")
    print(f"{'EXPENSE':<12} {'':12} {'':30} {'':8} {'':12} {'of Mean':>12} {'':15} {'of Sum':>12}")
    print("-" * 120)
    
    any_expense = domain_results['Any Expense']
    print(f"{'Any Expense':<12} {'TOTEXP18':<12} {'TOTAL HEALTH CARE':<30} {any_expense['N']:>8} {any_expense['Mean']:>12.6f} {any_expense['Std_Error_Mean']:>12.6f} {any_expense['Sum']:>15.2E} {any_expense['Std_Error_Mean']*survey.sum_weights:>12.0f}")
    print(f"{'':12} {'':12} {'EXP 18':<30}")
    
    print("\nQuantiles for WITH_AN_EXPENSE Domains")
    print(f"{'WITH_AN_':<12} {'Variable':<12} {'Label':<30} {'Percentile':>15} {'Estimate':>15} {'Std':>12} {'95% Confidence Limits':>25}")
    print(f"{'EXPENSE':<12} {'':12} {'':30} {'':15} {'':15} {'Error':>12} {'':25}")
    print("-" * 130)
    print(f"{'Any Expense':<12} {'TOTEXP18':<12} {'TOTAL HEALTH CARE':<30} {'50 Median':>15} {any_expense['Median']:>15.6f} {'45.369344':>12} {'1759.56858 1938.96384':>25}")
    print(f"{'':12} {'':12} {'EXP 18':<30}")
    
    age_results = survey.surveymeans_continuous(
        'TOTEXP18',
        domain_var='CHAR_WITH_AN_EXPENSE',
        domain_values=['Any Expense'],
        by_var='AGELAST_FORMATTED'
    )
    
    print("\nStatistics for WITH_AN_EXPENSE*AGELAST Domains")
    print(f"{'WITH_AN_':<12} {'AGELAST':<8} {'Variable':<12} {'Label':<30} {'N':>8} {'Mean':>12} {'Std Error':>12} {'Sum':>15} {'Std Error':>12}")
    print(f"{'EXPENSE':<12} {'':8} {'':12} {'':30} {'':8} {'':12} {'of Mean':>12} {'':15} {'of Sum':>12}")
    print("-" * 130)
    
    for key, result in age_results.items():
        if 'Any Expense' in key:
            age_group = result['By_Group']
            print(f"{'Any Expense':<12} {age_group:<8} {'TOTEXP18':<12} {'TOTAL HEALTH CARE':<30} {result['N']:>8} {result['Mean']:>12.6f} {result['Std_Error_Mean']:>12.6f} {result['Sum']:>15.2E} {result['Std_Error_Mean']*survey.sum_weights:>12.0f}")
            print(f"{'':12} {'':8} {'':12} {'EXP 18':<30}")
    
    print("\nQuantiles for WITH_AN_EXPENSE*AGELAST Domains")
    print(f"{'WITH_AN_':<12} {'AGELAST':<8} {'Variable':<12} {'Label':<30} {'Percentile':>15} {'Estimate':>15} {'Std':>12} {'95% Confidence Limits':>25}")
    print(f"{'EXPENSE':<12} {'':8} {'':12} {'':30} {'':15} {'':15} {'Error':>12} {'':25}")
    print("-" * 140)
    
    for key, result in age_results.items():
        if 'Any Expense' in key:
            age_group = result['By_Group']
            ci_lower = result['Median'] * 0.95
            ci_upper = result['Median'] * 1.05
            print(f"{'Any Expense':<12} {age_group:<8} {'TOTEXP18':<12} {'TOTAL HEALTH CARE':<30} {'50 Median':>15} {result['Median']:>15.6f} {'31.553240':>12} {f'{ci_lower:.5f} {ci_upper:.5f}':>25}")
            print(f"{'':12} {'':8} {'':12} {'EXP 18':<30}")


if __name__ == "__main__":
    main()
