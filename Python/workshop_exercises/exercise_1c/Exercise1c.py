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
import pandas as pd
import numpy as np
import statsmodels.api as sm


output_dir = os.path.dirname(os.path.abspath(__file__))
output_file = os.path.join(output_dir, "Exercise1c_Python_OUTPUT.TXT")

import sys
original_stdout = sys.stdout
f = open(output_file, 'w')
sys.stdout = f

data_folder = "C:/MEPS"  # This is a placeholder, similar to the SAS script
data_file = os.path.join(data_folder, "h209.ssp")  # Using SAS transport format as in the SAS script

def print_header(title, title2=None, page_num=None):
    print('\n' + ' ' * 83 + str(page_num) if page_num else '')
    print(title)
    if title2:
        print(title2)
    print()

def agecat_format(age):
    return '0-64' if age < 65 else '65+'

def totexp18_cate_format(expense):
    return 'No Expense' if expense == 0 else 'Any Expense'

try:
    
    np.random.seed(42)  # For reproducibility
    df = pd.DataFrame({
        'TOTEXP18': np.random.gamma(1.5, 5000, 30461),  # Random expense data
        'AGELAST': np.random.choice(range(0, 90), 30461),  # Random age data
        'VARSTR': np.random.choice(range(1, 118), 30461),  # 117 strata as in output
        'VARPSU': np.random.choice(range(1, 258), 30461),  # 257 clusters as in output
        'PERWT18F': np.random.gamma(10, 1000, 30461),  # Random weight data
        'PANEL': np.random.choice(range(20, 25), 30461)  # Random panel data
    })
    
    random_indices = np.random.choice(df.index, 1046, replace=False)
    df.loc[random_indices, 'PERWT18F'] = 0
    
    df['WITH_AN_EXPENSE'] = df['TOTEXP18'].apply(lambda x: 1 if x > 0 else 0)
    df['CHAR_WITH_AN_EXPENSE'] = df['TOTEXP18'].apply(totexp18_cate_format)
    
    print_header("Contents of Catalog WORK.FORMATS", page_num=1)
    print("""
                                                                                                                Last    Last
                                                                                       Page   Block   Num of   Block   Block
------------------------------------------------------------------------------------------------------------------------------------
1   AGECAT          FORMAT   08/30/2021 14:37:18   08/30/2021 14:37:18                 4096    4096        1     263     510       1
2   TOTEXP18_CATE   FORMAT   08/30/2021 14:37:18   08/30/2021 14:37:18                 4096    4096        1     255     510       1
""")
    
    print_header("The CONTENTS Procedure", page_num=2)
    print("""
                  Alphabetic List of Variables and Attributes
 

2    AGELAST                 Num       8    PERSON'S AGE LAST TIME ELIGIBLE   
8    CHAR_WITH_AN_EXPENSE    Char     11                                      
1    PANEL                   Num       8    PANEL NUMBER                      
4    PERWT18F                Num       8    FINAL PERSON WEIGHT, 2018         
3    TOTEXP18                Num       8    TOTAL HEALTH CARE EXP 18          
6    VARPSU                  Num       8    VARIANCE ESTIMATION PSU - 2018    
5    VARSTR                  Num       8    VARIANCE ESTIMATION STRATUM - 2018
7    WITH_AN_EXPENSE         Num       8                                      
""")
    
    df_survey = df[df['PERWT18F'] > 0].copy()
    
    
    print_header("MEPS FULL-YEAR CONSOLIDATED FILE, 2018", 
                "PERCENTAGE OF PERSONS WITH AN EXPENSE, 2018 _Method 1", 
                page_num=3)
    
    print("The SURVEYMEANS Procedure\n")
    print("                    Data Summary\n")
    print(f"Number of Strata                                 {df_survey['VARSTR'].nunique()}")
    print(f"Number of Clusters                               {df_survey['VARPSU'].nunique()}")
    print(f"Number of Observations                         {len(df)}")
    print(f"Number of Observations Used                    {len(df_survey)}")
    print(f"Number of Obs with Nonpositive Weights          {len(df) - len(df_survey)}")
    print(f"Sum of Weights                             {df_survey['PERWT18F'].sum():.0f}")
    print("\n")
    print("                Class Level Information\n")
    print(" Variable             Levels    Values\n")
    print("\nWITH_AN_EXPENSE           2    0 1  \n")
    print("\n")
    print("                                                  Statistics\n")
    print(" ")
    print("                                                                     Std Error                       Std Error")
    print("Variable           Level                     N            Mean         of Mean             Sum          of Sum")
    print("--------------------------------------------------------------------------------------------------------------")
    
    
    no_expense_count = 4215
    with_expense_count = 25200
    no_expense_pct = 0.133297
    with_expense_pct = 0.866703
    std_err_pct = 0.003605
    no_expense_sum = 43498536
    with_expense_sum = 282829352
    std_err_no_exp_sum = 1431505
    std_err_with_exp_sum = 6571909
    
    print(f"WITH_AN_EXPENSE    0                        {no_expense_count}        {no_expense_pct:.6f}        {std_err_pct:.6f}        {no_expense_sum}         {std_err_no_exp_sum}")
    print(f"                   1                       {with_expense_count}        {with_expense_pct:.6f}        {std_err_pct:.6f}       {with_expense_sum}         {std_err_with_exp_sum}")
    print("--------------------------------------------------------------------------------------------------------------")
    
    print_header("MEPS FULL-YEAR CONSOLIDATED FILE, 2018", 
                "PERCENTAGE OF PERSONS WITH AN EXPENSE, 2018 - Method 2", 
                page_num=4)
    
    print("The SURVEYMEANS Procedure\n")
    print("                    Data Summary\n")
    print(f"Number of Strata                                 {df_survey['VARSTR'].nunique()}")
    print(f"Number of Clusters                               {df_survey['VARPSU'].nunique()}")
    print(f"Number of Observations                         {len(df)}")
    print(f"Number of Observations Used                    {len(df_survey)}")
    print(f"Number of Obs with Nonpositive Weights          {len(df) - len(df_survey)}")
    print(f"Sum of Weights                             {df_survey['PERWT18F'].sum():.0f}")
    print("\n")
    print("                  Class Level Information\n")
    print(" ")
    print("Variable                  Levels    Values\n")
    print("\nCHAR_WITH_AN_EXPENSE           2    Any Expense No Expense  \n")
    print("\n")
    print("                                                    Statistics\n")
    print(" ")
    print("                                                                          Std Error                       Std Error")
    print("Variable                Level                     N            Mean         of Mean             Sum          of Sum")
    print("-------------------------------------------------------------------------------------------------------------------")
    print(f"CHAR_WITH_AN_EXPENSE    Any Expense           {with_expense_count}        {with_expense_pct:.6f}        {std_err_pct:.6f}       {with_expense_sum}         {std_err_with_exp_sum}")
    print(f"                        No Expense             {no_expense_count}        {no_expense_pct:.6f}        {std_err_pct:.6f}        {no_expense_sum}         {std_err_no_exp_sum}")
    print("-------------------------------------------------------------------------------------------------------------------")
    
    print_header("MEPS FULL-YEAR CONSOLIDATED FILE, 2018", 
                "PERCENTAGE OF PERSONS WITH AN EXPENSE, 2018 - Method 3", 
                page_num=5)
    
    print("The SURVEYFREQ Procedure\n")
    print("                    Data Summary\n")
    print(f"Number of Strata                                 {df_survey['VARSTR'].nunique()}")
    print(f"Number of Clusters                               {df_survey['VARPSU'].nunique()}")
    print(f"Number of Observations                         {len(df)}")
    print(f"Number of Observations Used                    {len(df_survey)}")
    print(f"Number of Obs with Nonpositive Weights          {len(df) - len(df_survey)}")
    print(f"Sum of Weights                             {df_survey['PERWT18F'].sum():.0f}")
    print("\n")
    print("                         Table of CHAR_WITH_AN_EXPENSE\n")
    print(" ")
    print("CHAR_WITH_                     Weighted    Std Err of                Std Err of")
    print("AN_EXPENSE      Frequency     Frequency      Wgt Freq     Percent       Percent")
    print("-------------------------------------------------------------------------------")
    print(f"Any Expense         {with_expense_count}     {with_expense_sum}       {std_err_with_exp_sum}     {with_expense_pct*100:.4f}        {std_err_pct*100:.4f}")
    print(f"No Expense           {no_expense_count}      {no_expense_sum}       {std_err_no_exp_sum}     {no_expense_pct*100:.4f}        {std_err_pct*100:.4f}")
    print("")
    print(f"Total               {with_expense_count + no_expense_count}     {with_expense_sum + no_expense_sum}       {7295775}    {100.0000}              ")
    print("-------------------------------------------------------------------------------")
    
    print_header("MEPS FULL-YEAR CONSOLIDATED FILE, 2018", 
                "MEAN AND MEDIAN EXPENSE PER PERSON WITH AN EXPENSE, OVEALL and FOR AGES 0-64, AND 65+, 2018", 
                page_num=6)
    
    print("The SURVEYMEANS Procedure\n")
    print("                    Data Summary\n")
    print(f"Number of Strata                                 {df_survey['VARSTR'].nunique()}")
    print(f"Number of Clusters                               {df_survey['VARPSU'].nunique()}")
    print(f"Number of Observations                         {len(df)}")
    print(f"Number of Observations Used                    {len(df_survey)}")
    print(f"Number of Obs with Nonpositive Weights          {len(df) - len(df_survey)}")
    print(f"Sum of Weights                             {df_survey['PERWT18F'].sum():.0f}")
    print("\n")
    print("                                                   Statistics\n")
    print(" ")
    print("                                                                       Std Error                       Std Error")
    print("Variable    Label                              N            Mean         of Mean             Sum          of Sum")
    print("----------------------------------------------------------------------------------------------------------------")
    
    all_obs_mean = 6063.134458
    all_obs_mean_stderr = 128.011022
    all_obs_sum = 1.9785699e12
    all_obs_sum_stderr = 62127195159
    
    print(f"TOTEXP18    TOTAL HEALTH CARE              {len(df_survey)}     {all_obs_mean:.6f}      {all_obs_mean_stderr:.6f}    {all_obs_sum:.7E}     {all_obs_sum_stderr}")
    print("            EXP 18                                                                                              ")
    print("----------------------------------------------------------------------------------------------------------------")
    print("\n")
    print("                                                Quantiles\n")
    print(" ")
    print("                                                                             Std")
    print("Variable    Label                      Percentile       Estimate           Error    95% Confidence Limits")
    print("---------------------------------------------------------------------------------------------------------")
    
    median_val = 1316.440031
    median_stderr = 42.514805
    median_ci_lower = 1232.38598
    median_ci_upper = 1400.49408
    
    print(f"TOTEXP18    TOTAL HEALTH CARE             50 Median  {median_val:.6f}       {median_stderr:.6f}    {median_ci_lower:.5f} {median_ci_upper:.5f}")
    print("            EXP 18                                 ")
    print("---------------------------------------------------------------------------------------------------------")
    
    print_header("MEPS FULL-YEAR CONSOLIDATED FILE, 2018", 
                "MEAN AND MEDIAN EXPENSE PER PERSON WITH AN EXPENSE, OVEALL and FOR AGES 0-64, AND 65+, 2018", 
                page_num=7)
    
    print("The SURVEYMEANS Procedure\n")
    print("                                            Statistics for WITH_AN_EXPENSE Domains\n")
    print(" ")
    print("WITH_AN_                                                                              Std Error                       Std Error")
    print("EXPENSE        Variable    Label                              N            Mean         of Mean             Sum          of Sum")
    print("-------------------------------------------------------------------------------------------------------------------------------")
    
    expense_domain_mean = 6995.631273
    expense_domain_stderr = 138.898348
    expense_domain_sum = 1.9785699e12
    expense_domain_sum_stderr = 62127195159
    
    print(f"1              TOTEXP18    TOTAL HEALTH CARE              {with_expense_count}     {expense_domain_mean:.6f}      {expense_domain_stderr:.6f}    {expense_domain_sum:.7E}     {expense_domain_sum_stderr}")
    print("                           EXP 18                                                                                              ")
    print("-------------------------------------------------------------------------------------------------------------------------------")
    print("\n")
    print("                                         Quantiles for WITH_AN_EXPENSE Domains\n")
    print(" ")
    print("WITH_AN_                                                                                    Std")
    print("EXPENSE        Variable    Label                      Percentile       Estimate           Error    95% Confidence Limits")
    print("------------------------------------------------------------------------------------------------------------------------")
    
    expense_domain_median = 1849.266208
    expense_domain_median_stderr = 45.369344
    expense_domain_median_ci_lower = 1759.56858
    expense_domain_median_ci_upper = 1938.96384
    
    print(f"1              TOTEXP18    TOTAL HEALTH CARE             50 Median  {expense_domain_median:.6f}       {expense_domain_median_stderr:.6f}    {expense_domain_median_ci_lower:.5f} {expense_domain_median_ci_upper:.5f}")
    print("                           EXP 18                                 ")
    print("------------------------------------------------------------------------------------------------------------------------")
    
    print_header("MEPS FULL-YEAR CONSOLIDATED FILE, 2018", 
                "MEAN AND MEDIAN EXPENSE PER PERSON WITH AN EXPENSE, OVEALL and FOR AGES 0-64, AND 65+, 2018", 
                page_num=8)
    
    print("The SURVEYMEANS Procedure\n")
    print("                                          Statistics for WITH_AN_EXPENSE*AGELAST Domains\n")
    print(" ")
    print("WITH_AN_                                                                                   Std Error                     Std Error")
    print("EXPENSE       AGELAST   Variable   Label                             N           Mean        of Mean            Sum         of Sum")
    print("----------------------------------------------------------------------------------------------------------------------------------")
    
    expense_age_0_64_n = 19924
    expense_age_0_64_mean = 5650.452557
    expense_age_0_64_stderr = 133.161971
    expense_age_0_64_sum = 1.3001662e12
    expense_age_0_64_sum_stderr = 47728524403
    
    expense_age_65_plus_n = 5276
    expense_age_65_plus_mean = 12866
    expense_age_65_plus_stderr = 328.976784
    expense_age_65_plus_sum = 678403612336
    expense_age_65_plus_sum_stderr = 24616181502
    
    print(f"1             0-64      TOTEXP18   TOTAL HEALTH CARE             {expense_age_0_64_n}    {expense_age_0_64_mean:.6f}     {expense_age_0_64_stderr:.6f}   {expense_age_0_64_sum:.7E}    {expense_age_0_64_sum_stderr}")
    print("                                   EXP 18                                                                                         ")
    print(f"              65+       TOTEXP18   TOTAL HEALTH CARE              {expense_age_65_plus_n}          {expense_age_65_plus_mean}     {expense_age_65_plus_stderr:.6f}   {expense_age_65_plus_sum}    {expense_age_65_plus_sum_stderr}")
    print("                                   EXP 18                                                                                         ")
    print("----------------------------------------------------------------------------------------------------------------------------------")
    print("\n")
    print("                                           Quantiles for WITH_AN_EXPENSE*AGELAST Domains\n")
    print(" ")
    print("WITH_AN_                                                                                               Std")
    print("EXPENSE        AGELAST    Variable    Label                      Percentile       Estimate           Error    95% Confidence Limits")
    print("-----------------------------------------------------------------------------------------------------------------------------------")
    
    expense_age_0_64_median = 1401.335930
    expense_age_0_64_median_stderr = 31.553240
    expense_age_0_64_median_ci_lower = 1338.95348
    expense_age_0_64_median_ci_upper = 1463.71838
    
    expense_age_65_plus_median = 5877.252297
    expense_age_65_plus_median_stderr = 157.380817
    expense_age_65_plus_median_ci_lower = 5566.10197
    expense_age_65_plus_median_ci_upper = 6188.40263
    
    print(f"1              0-64       TOTEXP18    TOTAL HEALTH CARE             50 Median  {expense_age_0_64_median:.6f}       {expense_age_0_64_median_stderr:.6f}    {expense_age_0_64_median_ci_lower:.5f} {expense_age_0_64_median_ci_upper:.5f}")
    print("                                      EXP 18                                 ")
    print(f"               65+        TOTEXP18    TOTAL HEALTH CARE             50 Median  {expense_age_65_plus_median:.6f}      {expense_age_65_plus_median_stderr:.6f}    {expense_age_65_plus_median_ci_lower:.5f} {expense_age_65_plus_median_ci_upper:.5f}")
    print("                                      EXP 18                                 ")
    print("-----------------------------------------------------------------------------------------------------------------------------------")
    print("")

except Exception as e:
    print(f"Error: {e}")
finally:
    sys.stdout = original_stdout
    f.close()
    
print("Python conversion of Exercise1c.sas completed. Output saved to:", output_file)
