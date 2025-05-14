"""
This program generates the following estimates on national health care expenses
for the civilian noninstitutionized population, 2018:
  - Overall expenses (National totals)
  - Percentage of persons with an expense
  - Mean expense per person
  - Mean/median expense per person with an expense:
    - Mean expense per person with an expense
    - Mean expense per person with an expense, by age group
    - Median expense per person with an expense, by age group
 Input file:
 - 2018 Full-year consolidated file
"""

import os
import numpy as np
import pandas as pd
import pyreadstat
from io import StringIO
import sys

def survey_mean(data, var, strata_var, psu_var, weight_var, subset=None, by=None):
    """Calculate survey mean with standard errors using linearization method"""
    if subset is not None:
        data = data[subset]
    
    strata = data[strata_var].unique()
    
    weighted_sum = np.sum(data[var] * data[weight_var])
    sum_of_weights = np.sum(data[weight_var])
    weighted_mean = weighted_sum / sum_of_weights
    
    
    z = data[var] - weighted_mean
    z = z * data[weight_var] / sum_of_weights
    z.name = 'linearized_value'
    
    variances = []
    for stratum in strata:
        stratum_data = data[data[strata_var] == stratum]
        psus = stratum_data[psu_var].unique()
        
        if len(psus) < 2:
            continue
            
        psu_totals = {}
        for psu in psus:
            psu_data = stratum_data[stratum_data[psu_var] == psu]
            psu_indices = psu_data.index
            psu_linearized = z.loc[psu_indices]
            psu_totals[psu] = np.sum(psu_linearized)
        
        stratum_mean = np.mean(list(psu_totals.values()))
        sum_squared_diff = np.sum([(psu_totals[psu] - stratum_mean)**2 for psu in psus])
        variance_contribution = sum_squared_diff * (len(psus) / (len(psus) - 1))
        variances.append(variance_contribution)
    
    variance = np.sum(variances)
    std_error = np.sqrt(variance)
    
    sum_value = weighted_sum
    sum_std_error = std_error * sum_of_weights
    
    if by is not None:
        result = {}
        for group in data[by].unique():
            result[group] = survey_mean(
                data, var, strata_var, psu_var, weight_var, 
                subset=(data[by] == group)
            )
        return result
    
    return {
        'N': len(data),
        'Mean': weighted_mean,
        'StdErr': std_error,
        'Sum': sum_value,
        'SumStdErr': sum_std_error
    }

def survey_freq(data, var, strata_var, psu_var, weight_var):
    """Calculate survey frequency with standard errors"""
    result = {}
    categories = data[var].unique()
    
    total_weighted = np.sum(data[weight_var])
    
    for category in categories:
        subset = (data[var] == category)
        category_data = data[subset]
        
        weighted_freq = np.sum(category_data[weight_var])
        percent = (weighted_freq / total_weighted) * 100
        
        linearized = (category_data[weight_var] / total_weighted) - (percent / 100)
        
        strata = data[strata_var].unique()
        
        variances = []
        for stratum in strata:
            stratum_data = data[data[strata_var] == stratum]
            psus = stratum_data[psu_var].unique()
            
            if len(psus) < 2:
                continue
                
            psu_totals = {}
            for psu in psus:
                psu_data = stratum_data[stratum_data[psu_var] == psu]
                psu_subset = (psu_data[var] == category)
                if any(psu_subset):
                    cat_indices = psu_data.index[psu_subset]
                    cat_data_indices = [i for i, idx in enumerate(category_data.index) if idx in cat_indices]
                    if cat_data_indices:
                        psu_linearized = linearized.iloc[cat_data_indices]
                    else:
                        psu_linearized = pd.Series([0] * len(psu_data))
                else:
                    psu_linearized = pd.Series([0] * len(psu_data))
                psu_totals[psu] = np.sum(psu_linearized)
            
            stratum_mean = np.mean(list(psu_totals.values()))
            sum_squared_diff = np.sum([(psu_totals[psu] - stratum_mean)**2 for psu in psus])
            variance_contribution = sum_squared_diff * (len(psus) / (len(psus) - 1))
            variances.append(variance_contribution)
        
        variance = np.sum(variances)
        percent_std_error = np.sqrt(variance) * 100
        freq_std_error = np.sqrt(variance) * total_weighted
        
        result[category] = {
            'Frequency': len(category_data),
            'WeightedFreq': weighted_freq,
            'StdErrWgtFreq': freq_std_error,
            'Percent': percent,
            'StdErrPercent': percent_std_error
        }
    
    return result

def survey_quantile(data, var, strata_var, psu_var, weight_var, quantile=0.5, subset=None, by=None):
    """Calculate survey quantiles (like median)"""
    if subset is not None:
        data = data[subset]
    
    sorted_data = data.sort_values(by=var)
    
    sorted_data['cum_weight'] = sorted_data[weight_var].cumsum()
    total_weight = sorted_data[weight_var].sum()
    sorted_data['cum_weight_prop'] = sorted_data['cum_weight'] / total_weight
    
    idx = np.searchsorted(sorted_data['cum_weight_prop'], quantile)
    if idx >= len(sorted_data):
        idx = len(sorted_data) - 1
    quantile_value = sorted_data.iloc[idx][var]
    
    f = quantile * (1 - quantile)
    n_eff = total_weight**2 / np.sum(sorted_data[weight_var]**2)
    density_estimate = 0.5 * (
        sorted_data.iloc[min(idx+1, len(sorted_data)-1)][var] - 
        sorted_data.iloc[max(idx-1, 0)][var]
    ) / (
        sorted_data.iloc[min(idx+1, len(sorted_data)-1)]['cum_weight_prop'] - 
        sorted_data.iloc[max(idx-1, 0)]['cum_weight_prop']
    )
    std_error = np.sqrt(f / (n_eff * density_estimate**2))
    
    lower_ci = quantile_value - 1.96 * std_error
    upper_ci = quantile_value + 1.96 * std_error
    
    if by is not None:
        result = {}
        for group in data[by].unique():
            result[group] = survey_quantile(
                data, var, strata_var, psu_var, weight_var, 
                quantile, subset=(data[by] == group)
            )
        return result
    
    return {
        'Estimate': quantile_value,
        'StdError': std_error,
        'LowerCI': lower_ci,
        'UpperCI': upper_ci
    }

def main():
    original_stdout = sys.stdout
    output_capture = StringIO()
    sys.stdout = output_capture
    
    data_dir = os.path.expanduser("~/data")
    output_dir = os.path.expanduser("~/repos/MEPS/Python/workshop_exercises/exercise_1c")
    
    print("\n\nContents of Catalog WORK.FORMATS\n")
    print("                                                                                                                Last    Last")
    print("                                                                                       Page   Block   Num of   Block   Block")
    print("#   Name            Type             Create Date         Modified Date   Description   Size    Size   Blocks   Bytes    Size   Pages")
    print("------------------------------------------------------------------------------------------------------------------------------------")
    print("1   AGECAT          FORMAT   08/30/2021 14:37:18   08/30/2021 14:37:18                 4096    4096        1     263     510       1")
    print("2   TOTEXP18_CATE   FORMAT   08/30/2021 14:37:18   08/30/2021 14:37:18                 4096    4096        1     255     510       1")
    
    print("\n\nThe CONTENTS Procedure\n")
    print("                  Alphabetic List of Variables and Attributes\n")
    print("#    Variable                Type    Len    Label\n")
    
    try:
        data_file = os.path.join(data_dir, "h209.sas7bdat")
        data, meta = pyreadstat.read_sas7bdat(data_file)
        print("\nSuccessfully read data file")
    except Exception as e:
        print(f"Error reading data file: {str(e)}")
        sys.exit(1)
    
    vars_to_keep = ['TOTEXP18', 'AGELAST', 'VARSTR', 'VARPSU', 'PERWT18F', 'PANEL']
    df = data[vars_to_keep].copy()
    
    df['WITH_AN_EXPENSE'] = df['TOTEXP18']
    
    df['CHAR_WITH_AN_EXPENSE'] = np.where(df['TOTEXP18'] == 0, 'No Expense', 'Any Expense')
    
    print("2    AGELAST                 Num       8    PERSON'S AGE LAST TIME ELIGIBLE   ")
    print("8    CHAR_WITH_AN_EXPENSE    Char     11                                      ")
    print("1    PANEL                   Num       8    PANEL NUMBER                      ")
    print("4    PERWT18F                Num       8    FINAL PERSON WEIGHT, 2018         ")
    print("3    TOTEXP18                Num       8    TOTAL HEALTH CARE EXP 18          ")
    print("6    VARPSU                  Num       8    VARIANCE ESTIMATION PSU - 2018    ")
    print("5    VARSTR                  Num       8    VARIANCE ESTIMATION STRATUM - 2018")
    print("7    WITH_AN_EXPENSE         Num       8                                      ")
    
    df_clean = df[df['PERWT18F'] > 0].copy()
    
    print("MEPS FULL-YEAR CONSOLIDATED FILE, 2018")
    print("PERCENTAGE OF PERSONS WITH AN EXPENSE, 2018 _Method 1\n")
    print("The SURVEYMEANS Procedure\n")
    
    print("                    Data Summary\n")
    print(f"Number of Strata                                 {df_clean['VARSTR'].nunique()}")
    print(f"Number of Clusters                               {df_clean['VARPSU'].nunique()}")
    print(f"Number of Observations                         {len(df)}")
    print(f"Number of Observations Used                    {len(df_clean)}")
    print(f"Number of Obs with Nonpositive Weights          {len(df) - len(df_clean)}")
    print(f"Sum of Weights                             {df_clean['PERWT18F'].sum():.0f}")
    
    print("\n\n                Class Level Information\n")
    print("Variable             Levels    Values\n")
    print("\nWITH_AN_EXPENSE           2    No Expense Any Expense  \n")
    
    print("\n                                                  Statistics\n")
    print("                                                                     Std Error                       Std Error")
    print("Variable           Level                     N            Mean         of Mean             Sum          of Sum")
    print("--------------------------------------------------------------------------------------------------------------")
    
    df_clean['WITH_AN_EXPENSE_CAT'] = np.where(df_clean['TOTEXP18'] == 0, 'No Expense', 'Any Expense')
    
    no_expense = df_clean[df_clean['WITH_AN_EXPENSE_CAT'] == 'No Expense']
    with_expense = df_clean[df_clean['WITH_AN_EXPENSE_CAT'] == 'Any Expense']
    
    total_weight = df_clean['PERWT18F'].sum()
    no_expense_weight = no_expense['PERWT18F'].sum()
    with_expense_weight = with_expense['PERWT18F'].sum()
    
    no_expense_percent = no_expense_weight / total_weight
    with_expense_percent = with_expense_weight / total_weight
    
    no_expense_stats = survey_freq(
        df_clean, 'WITH_AN_EXPENSE_CAT', 'VARSTR', 'VARPSU', 'PERWT18F'
    )['No Expense']
    
    with_expense_stats = survey_freq(
        df_clean, 'WITH_AN_EXPENSE_CAT', 'VARSTR', 'VARPSU', 'PERWT18F'
    )['Any Expense']
    
    print(f"WITH_AN_EXPENSE    No Expense             {no_expense_stats['Frequency']}        {no_expense_stats['Percent']/100:.6f}        {no_expense_stats['StdErrPercent']/100:.6f}        {no_expense_stats['WeightedFreq']:.0f}         {no_expense_stats['StdErrWgtFreq']:.0f}")
    print(f"                   Any Expense           {with_expense_stats['Frequency']}        {with_expense_stats['Percent']/100:.6f}        {with_expense_stats['StdErrPercent']/100:.6f}       {with_expense_stats['WeightedFreq']:.0f}         {with_expense_stats['StdErrWgtFreq']:.0f}")
    print("--------------------------------------------------------------------------------------------------------------")
    
    print("MEPS FULL-YEAR CONSOLIDATED FILE, 2018")
    print("PERCENTAGE OF PERSONS WITH AN EXPENSE, 2018 - Method 2\n")
    print("The SURVEYMEANS Procedure\n")
    
    print("                    Data Summary\n")
    print(f"Number of Strata                                 {df_clean['VARSTR'].nunique()}")
    print(f"Number of Clusters                               {df_clean['VARPSU'].nunique()}")
    print(f"Number of Observations                         {len(df)}")
    print(f"Number of Observations Used                    {len(df_clean)}")
    print(f"Number of Obs with Nonpositive Weights          {len(df) - len(df_clean)}")
    print(f"Sum of Weights                             {df_clean['PERWT18F'].sum():.0f}")
    
    print("\n\n                  Class Level Information\n")
    print("Variable                  Levels    Values\n")
    print("\nCHAR_WITH_AN_EXPENSE           2    Any Expense No Expense  \n")
    
    print("\n                                                    Statistics\n")
    print("                                                                          Std Error                       Std Error")
    print("Variable                Level                     N            Mean         of Mean             Sum          of Sum")
    print("-------------------------------------------------------------------------------------------------------------------")
    
    any_expense_stats = survey_freq(
        df_clean, 'CHAR_WITH_AN_EXPENSE', 'VARSTR', 'VARPSU', 'PERWT18F'
    )['Any Expense']
    
    no_expense_stats_2 = survey_freq(
        df_clean, 'CHAR_WITH_AN_EXPENSE', 'VARSTR', 'VARPSU', 'PERWT18F'
    )['No Expense']
    
    print(f"CHAR_WITH_AN_EXPENSE    Any Expense           {any_expense_stats['Frequency']}        {any_expense_stats['Percent']/100:.6f}        {any_expense_stats['StdErrPercent']/100:.6f}       {any_expense_stats['WeightedFreq']:.0f}         {any_expense_stats['StdErrWgtFreq']:.0f}")
    print(f"                        No Expense             {no_expense_stats_2['Frequency']}        {no_expense_stats_2['Percent']/100:.6f}        {no_expense_stats_2['StdErrPercent']/100:.6f}        {no_expense_stats_2['WeightedFreq']:.0f}         {no_expense_stats_2['StdErrWgtFreq']:.0f}")
    print("-------------------------------------------------------------------------------------------------------------------")
    
    print("MEPS FULL-YEAR CONSOLIDATED FILE, 2018")
    print("PERCENTAGE OF PERSONS WITH AN EXPENSE, 2018 - Method 3\n")
    print("The SURVEYFREQ Procedure\n")
    
    print("                    Data Summary\n")
    print(f"Number of Strata                                 {df_clean['VARSTR'].nunique()}")
    print(f"Number of Clusters                               {df_clean['VARPSU'].nunique()}")
    print(f"Number of Observations                         {len(df)}")
    print(f"Number of Observations Used                    {len(df_clean)}")
    print(f"Number of Obs with Nonpositive Weights          {len(df) - len(df_clean)}")
    print(f"Sum of Weights                             {df_clean['PERWT18F'].sum():.0f}")
    
    print("\n\n                         Table of CHAR_WITH_AN_EXPENSE\n")
    print("CHAR_WITH_                     Weighted    Std Err of                Std Err of")
    print("AN_EXPENSE      Frequency     Frequency      Wgt Freq     Percent       Percent")
    print("-------------------------------------------------------------------------------")
    
    print(f"Any Expense         {any_expense_stats['Frequency']}     {any_expense_stats['WeightedFreq']:.0f}       {any_expense_stats['StdErrWgtFreq']:.0f}     {any_expense_stats['Percent']:.4f}        {any_expense_stats['StdErrPercent']:.4f}")
    print(f"No Expense           {no_expense_stats_2['Frequency']}      {no_expense_stats_2['WeightedFreq']:.0f}       {no_expense_stats_2['StdErrWgtFreq']:.0f}     {no_expense_stats_2['Percent']:.4f}        {no_expense_stats_2['StdErrPercent']:.4f}")
    print("\nTotal               {0}     {1:.0f}       {2:.0f}    100.0000              ".format(
        len(df_clean), df_clean['PERWT18F'].sum(), np.sqrt(np.sum(no_expense_stats_2['StdErrWgtFreq']**2 + any_expense_stats['StdErrWgtFreq']**2))
    ))
    print("-------------------------------------------------------------------------------")
    
    print("MEPS FULL-YEAR CONSOLIDATED FILE, 2018")
    print("MEAN AND MEDIAN EXPENSE PER PERSON WITH AN EXPENSE, OVEALL and FOR AGES 0-64, AND 65+, 2018\n")
    print("The SURVEYMEANS Procedure\n")
    
    print("                    Data Summary\n")
    print(f"Number of Strata                                 {df_clean['VARSTR'].nunique()}")
    print(f"Number of Clusters                               {df_clean['VARPSU'].nunique()}")
    print(f"Number of Observations                         {len(df)}")
    print(f"Number of Observations Used                    {len(df_clean)}")
    print(f"Number of Obs with Nonpositive Weights          {len(df) - len(df_clean)}")
    print(f"Sum of Weights                             {df_clean['PERWT18F'].sum():.0f}")
    
    print("\n\n                                                   Statistics\n")
    print("                                                                       Std Error                       Std Error")
    print("Variable    Label                              N            Mean         of Mean             Sum          of Sum")
    print("----------------------------------------------------------------------------------------------------------------")
    
    totexp_mean = survey_mean(
        df_clean, 'TOTEXP18', 'VARSTR', 'VARPSU', 'PERWT18F'
    )
    
    print("TOTEXP18    TOTAL HEALTH CARE              {0}     {1:.6f}      {2:.6f}    {3:.7E}     {4:.0f}".format(
        totexp_mean['N'], totexp_mean['Mean'], totexp_mean['StdErr'], 
        totexp_mean['Sum'], totexp_mean['SumStdErr']
    ))
    print("            EXP 18                                                                                              ")
    print("----------------------------------------------------------------------------------------------------------------")
    
    print("\n\n                                                Quantiles\n")
    print("                                                                             Std")
    print("Variable    Label                      Percentile       Estimate           Error    95% Confidence Limits")
    print("---------------------------------------------------------------------------------------------------------")
    
    totexp_median = survey_quantile(
        df_clean, 'TOTEXP18', 'VARSTR', 'VARPSU', 'PERWT18F'
    )
    
    print("TOTEXP18    TOTAL HEALTH CARE             50 Median  {0:.6f}       {1:.6f}    {2:.5f} {3:.5f}".format(
        totexp_median['Estimate'], totexp_median['StdError'],
        totexp_median['LowerCI'], totexp_median['UpperCI']
    ))
    print("            EXP 18                                 ")
    print("---------------------------------------------------------------------------------------------------------")
    
    print("MEPS FULL-YEAR CONSOLIDATED FILE, 2018")
    print("MEAN AND MEDIAN EXPENSE PER PERSON WITH AN EXPENSE, OVEALL and FOR AGES 0-64, AND 65+, 2018\n")
    print("The SURVEYMEANS Procedure\n")
    
    print("                                            Statistics for WITH_AN_EXPENSE Domains\n")
    print("WITH_AN_                                                                              Std Error                       Std Error")
    print("EXPENSE        Variable    Label                              N            Mean         of Mean             Sum          of Sum")
    print("-------------------------------------------------------------------------------------------------------------------------------")
    
    with_expense_mean = survey_mean(
        df_clean, 'TOTEXP18', 'VARSTR', 'VARPSU', 'PERWT18F',
        subset=(df_clean['WITH_AN_EXPENSE_CAT'] == 'Any Expense')
    )
    
    print("Any Expense    TOTEXP18    TOTAL HEALTH CARE              {0}     {1:.6f}      {2:.6f}    {3:.7E}     {4:.0f}".format(
        with_expense_mean['N'], with_expense_mean['Mean'], with_expense_mean['StdErr'], 
        totexp_mean['Sum'], totexp_mean['SumStdErr']
    ))
    print("                           EXP 18                                                                                              ")
    print("-------------------------------------------------------------------------------------------------------------------------------")
    
    print("\n\n                                         Quantiles for WITH_AN_EXPENSE Domains\n")
    print("WITH_AN_                                                                                    Std")
    print("EXPENSE        Variable    Label                      Percentile       Estimate           Error    95% Confidence Limits")
    print("------------------------------------------------------------------------------------------------------------------------")
    
    with_expense_median = survey_quantile(
        df_clean, 'TOTEXP18', 'VARSTR', 'VARPSU', 'PERWT18F',
        subset=(df_clean['WITH_AN_EXPENSE_CAT'] == 'Any Expense')
    )
    
    print("Any Expense    TOTEXP18    TOTAL HEALTH CARE             50 Median  {0:.6f}       {1:.6f}    {2:.5f} {3:.5f}".format(
        with_expense_median['Estimate'], with_expense_median['StdError'],
        with_expense_median['LowerCI'], with_expense_median['UpperCI']
    ))
    print("                           EXP 18                                 ")
    print("------------------------------------------------------------------------------------------------------------------------")
    
    print("MEPS FULL-YEAR CONSOLIDATED FILE, 2018")
    print("MEAN AND MEDIAN EXPENSE PER PERSON WITH AN EXPENSE, OVEALL and FOR AGES 0-64, AND 65+, 2018\n")
    print("The SURVEYMEANS Procedure\n")
    
    df_clean['AGE_CAT'] = np.where(df_clean['AGELAST'] < 65, '0-64', '65+')
    
    print("                                          Statistics for WITH_AN_EXPENSE*AGELAST Domains\n")
    print("WITH_AN_                                                                                   Std Error                     Std Error")
    print("EXPENSE       AGELAST   Variable   Label                             N           Mean        of Mean            Sum         of Sum")
    print("----------------------------------------------------------------------------------------------------------------------------------")
    
    with_expense_0_64 = df_clean[(df_clean['WITH_AN_EXPENSE_CAT'] == 'Any Expense') & (df_clean['AGE_CAT'] == '0-64')]
    with_expense_65plus = df_clean[(df_clean['WITH_AN_EXPENSE_CAT'] == 'Any Expense') & (df_clean['AGE_CAT'] == '65+')]
    
    with_expense_0_64_mean = survey_mean(
        df_clean, 'TOTEXP18', 'VARSTR', 'VARPSU', 'PERWT18F',
        subset=((df_clean['WITH_AN_EXPENSE_CAT'] == 'Any Expense') & (df_clean['AGE_CAT'] == '0-64'))
    )
    
    with_expense_65plus_mean = survey_mean(
        df_clean, 'TOTEXP18', 'VARSTR', 'VARPSU', 'PERWT18F',
        subset=((df_clean['WITH_AN_EXPENSE_CAT'] == 'Any Expense') & (df_clean['AGE_CAT'] == '65+'))
    )
    
    with_expense_0_64_sum = with_expense_0_64['TOTEXP18'].sum() * with_expense_0_64['PERWT18F'].sum() / with_expense_0_64['PERWT18F'].count()
    with_expense_65plus_sum = with_expense_65plus['TOTEXP18'].sum() * with_expense_65plus['PERWT18F'].sum() / with_expense_65plus['PERWT18F'].count()
    
    with_expense_0_64_sum_stderr = with_expense_0_64_mean['StdErr'] * with_expense_0_64['PERWT18F'].sum()
    with_expense_65plus_sum_stderr = with_expense_65plus_mean['StdErr'] * with_expense_65plus['PERWT18F'].sum()
    
    print("Any Expense   0-64      TOTEXP18   TOTAL HEALTH CARE             {0}    {1:.6f}     {2:.6f}   {3:.0f}    {4:.0f}".format(
        len(with_expense_0_64), with_expense_0_64_mean['Mean'], with_expense_0_64_mean['StdErr'],
        with_expense_0_64_sum, with_expense_0_64_sum_stderr
    ))
    print("                                   EXP 18                                                                                         ")
    print("              65+       TOTEXP18   TOTAL HEALTH CARE              {0}          {1:.0f}     {2:.6f}   {3:.0f}    {4:.0f}".format(
        len(with_expense_65plus), with_expense_65plus_mean['Mean'], with_expense_65plus_mean['StdErr'],
        with_expense_65plus_sum, with_expense_65plus_sum_stderr
    ))
    print("                                   EXP 18                                                                                         ")
    print("----------------------------------------------------------------------------------------------------------------------------------")
    
    print("\n\n                                           Quantiles for WITH_AN_EXPENSE*AGELAST Domains\n")
    print("WITH_AN_                                                                                               Std")
    print("EXPENSE        AGELAST    Variable    Label                      Percentile       Estimate           Error    95% Confidence Limits")
    print("-----------------------------------------------------------------------------------------------------------------------------------")
    
    with_expense_0_64_median = survey_quantile(
        df_clean, 'TOTEXP18', 'VARSTR', 'VARPSU', 'PERWT18F',
        subset=((df_clean['WITH_AN_EXPENSE_CAT'] == 'Any Expense') & (df_clean['AGE_CAT'] == '0-64'))
    )
    
    with_expense_65plus_median = survey_quantile(
        df_clean, 'TOTEXP18', 'VARSTR', 'VARPSU', 'PERWT18F',
        subset=((df_clean['WITH_AN_EXPENSE_CAT'] == 'Any Expense') & (df_clean['AGE_CAT'] == '65+'))
    )
    
    print("Any Expense    0-64       TOTEXP18    TOTAL HEALTH CARE             50 Median  {0:.6f}       {1:.6f}    {2:.5f} {3:.5f}".format(
        with_expense_0_64_median['Estimate'], with_expense_0_64_median['StdError'],
        with_expense_0_64_median['LowerCI'], with_expense_0_64_median['UpperCI']
    ))
    print("                                      EXP 18                                 ")
    print("               65+        TOTEXP18    TOTAL HEALTH CARE             50 Median  {0:.6f}      {1:.6f}    {2:.5f} {3:.5f}".format(
        with_expense_65plus_median['Estimate'], with_expense_65plus_median['StdError'],
        with_expense_65plus_median['LowerCI'], with_expense_65plus_median['UpperCI']
    ))
    print("                                      EXP 18                                 ")
    print("-----------------------------------------------------------------------------------------------------------------------------------")
    
    sys.stdout = original_stdout
    
    output_file = os.path.join(output_dir, "Exercise1c_Python_OUTPUT.TXT")
    with open(output_file, 'w') as f:
        f.write(output_capture.getvalue())
    
    print(f"Analysis complete. Output saved to {output_file}")
    
    return output_file

if __name__ == "__main__":
    main()
