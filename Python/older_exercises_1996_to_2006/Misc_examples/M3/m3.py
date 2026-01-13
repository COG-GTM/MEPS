import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP -- SEPTEMBER 2008")
print("ILLUSTRATING THE USE OF ID VARIABLES (DUPERSID, CONDIDX)")
print("=" * 80)

sex_labels = {1: 'MALE', 2: 'FEMALE'}
yesno_labels = {-9: 'NOT ASCERTAINED', -1: 'INAPPLICABLE', 1: 'YES', 2: 'NO'}

print("\n" + "-" * 80)
print("GET DUPERSID AND OTHER VARIABLES FROM HC-097")
print("-" * 80)

fyc = load_sas_data(f'{data_path}/h97.sas7bdat', columns=[
    'DUID', 'PID', 'DUPERSID', 'PANEL', 'AGE05X', 'SEX',
    'PERWT05F', 'VARSTR', 'VARPSU'
])

fyc_sorted = fyc.sort_values(['DUPERSID', 'PANEL'])

print("\nPrint of Selected HC-097 (2005 Full-Year File) Records to Show DUPERSID:")
print("-" * 80)
print(fyc_sorted[['DUID', 'PID', 'DUPERSID', 'PANEL', 'AGE05X', 'SEX']].iloc[39:90].to_string())

print("\n" + "-" * 80)
print("GET DUPERSID, CONDIDX AND OTHER VARIABLES FROM HC-096")
print("-" * 80)

cond = load_sas_data(f'{data_path}/h96.sas7bdat', columns=[
    'DUPERSID', 'PANEL', 'CONDN', 'CONDIDX', 'INJURY', 'ICD9CODX'
])

cond_sorted = cond.sort_values(['DUPERSID', 'PANEL', 'CONDIDX'])

print("\nPrint of Selected HC-096 (2005 Conditions File) Records to Show")
print("DUPERSID and CONDIDX:")
print("-" * 80)
print(cond_sorted[['DUPERSID', 'PANEL', 'CONDN', 'CONDIDX', 'INJURY', 'ICD9CODX']].iloc[139:190].to_string())

print("\n" + "-" * 80)
print("MERGE FILES TO CONNECT PERSON INFO WITH CONDITION INFO")
print("-" * 80)

condinfo = fyc_sorted.merge(cond_sorted, on=['DUPERSID', 'PANEL'], how='outer')

print("\nPrint of Selected Records from Merged, Condition-Level, File:")
print("-" * 80)
print(condinfo[['DUPERSID', 'PANEL', 'CONDIDX', 'AGE05X', 'SEX', 'INJURY', 'ICD9CODX']].iloc[139:190].to_string())

print("\n" + "-" * 80)
print("MERGE FILES BUT NOW ONLY KEEP MATCHING RECORDS")
print("-" * 80)

condinfo_b = fyc_sorted.merge(cond_sorted, on=['DUPERSID', 'PANEL'], how='inner')

print("\nPrint of Selected Records from Merged, Condition-Level, File")
print("Where Only Matched Records Were Kept:")
print("-" * 80)
print(condinfo_b[['DUPERSID', 'PANEL', 'CONDIDX', 'AGE05X', 'SEX', 'INJURY', 'ICD9CODX']].iloc[139:190].to_string())

print("\n" + "-" * 80)
print("Summary Statistics")
print("-" * 80)

print(f"\nFull-Year File Records: {len(fyc):,}")
print(f"Conditions File Records: {len(cond):,}")
print(f"Outer Merge Records: {len(condinfo):,}")
print(f"Inner Merge Records: {len(condinfo_b):,}")
