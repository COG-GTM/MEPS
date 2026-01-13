import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data, SurveyDesign, survey_freq

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP -- SEPTEMBER 2009")
print("MERGING PARENT'S INFORMATION TO CHILDREN'S RECORDS")
print("=" * 80)

kid_labels = {0: 'NOT A CHILD', 1: 'CHILD, AGE 0-17'}
par_work_labels = {
    0: 'NOT A CHILD',
    1: 'BOTH PARENTS WORK',
    2: 'ONE PARENT WORK',
    3: 'NO WORKING PARENT'
}
empst_labels = {
    -9: 'NOT REPORTED', -8: 'NOT REPORTED', -7: 'NOT REPORTED', -1: 'NOT REPORTED',
    0: 'NO MOM OR DAD IN MEPS',
    1: 'EMPLOYED',
    2: 'JOB TO RETURN TO',
    3: 'JOB DURING ROUND',
    4: 'NOT EMPLOYED'
}

print("\n" + "-" * 80)
print("Read 2006 Consolidated Full Year File")
print("-" * 80)

fyc = load_sas_data(f'{data_path}/h105.sas7bdat', columns=[
    'DUPERSID', 'DUID', 'PID', 'AGE31X', 'MOPID31X', 'DAPID31X',
    'EMPST31', 'PERWT06F', 'VARSTR', 'VARPSU'
])

fyc = fyc[fyc['PERWT06F'] > 0].copy()

print(f"\nTotal persons with positive weight: {len(fyc):,}")

print("\n" + "-" * 80)
print("Create Kids Dataset with Linking IDs to Both Mom and Dad")
print("-" * 80)

kids = fyc[(fyc['AGE31X'] >= 0) & (fyc['AGE31X'] <= 17)].copy()

kids['MOMLINK'] = kids.apply(
    lambda row: f"{int(row['DUID']):05d}{int(row['MOPID31X']):03d}" if row['MOPID31X'] != -1 else None,
    axis=1
)

kids['DADLINK'] = kids.apply(
    lambda row: f"{int(row['DUID']):05d}{int(row['DAPID31X']):03d}" if row['DAPID31X'] != -1 else None,
    axis=1
)

print(f"\nChildren (age 0-17): {len(kids):,}")
print(f"Children with mom link: {kids['MOMLINK'].notna().sum():,}")
print(f"Children with dad link: {kids['DADLINK'].notna().sum():,}")

print("\n" + "-" * 80)
print("Create Dads and Moms Datasets")
print("-" * 80)

dads = fyc[['DUPERSID', 'EMPST31']].copy()
dads = dads.rename(columns={'DUPERSID': 'DADLINK', 'EMPST31': 'DAD_EMPST31'})

moms = fyc[['DUPERSID', 'EMPST31']].copy()
moms = moms.rename(columns={'DUPERSID': 'MOMLINK', 'EMPST31': 'MOM_EMPST31'})

print(f"\nPotential dads: {len(dads):,}")
print(f"Potential moms: {len(moms):,}")

print("\n" + "-" * 80)
print("Merge Kids with Dads and Moms")
print("-" * 80)

kids2 = kids.merge(dads, on='DADLINK', how='left')
kids2['DAD_EMPST31'] = kids2['DAD_EMPST31'].fillna(0)

kids_wparents = kids2.merge(moms, on='MOMLINK', how='left')
kids_wparents['MOM_EMPST31'] = kids_wparents['MOM_EMPST31'].fillna(0)

print(f"\nKids with parent info: {len(kids_wparents):,}")

print("\n" + "-" * 80)
print("Merge Back to Full FY File and Create PAR_WORK Variable")
print("-" * 80)

all2_fy06 = fyc.merge(
    kids_wparents[['DUPERSID', 'DAD_EMPST31', 'MOM_EMPST31', 'MOMLINK', 'DADLINK']],
    on='DUPERSID',
    how='left'
)

all2_fy06['POP_KID'] = np.where(
    (all2_fy06['AGE31X'] >= 0) & (all2_fy06['AGE31X'] <= 17),
    1, 0
)

def get_par_work(row):
    if row['POP_KID'] == 0:
        return 0
    mom_works = row['MOM_EMPST31'] == 1
    dad_works = row['DAD_EMPST31'] == 1
    if mom_works and dad_works:
        return 1
    elif mom_works or dad_works:
        return 2
    else:
        return 3

all2_fy06['PAR_WORK'] = all2_fy06.apply(get_par_work, axis=1)

all2_fy06.loc[all2_fy06['POP_KID'] == 0, 'DAD_EMPST31'] = -1
all2_fy06.loc[all2_fy06['POP_KID'] == 0, 'MOM_EMPST31'] = -1

print(f"\nTotal persons: {len(all2_fy06):,}")
print(f"Children: {(all2_fy06['POP_KID'] == 1).sum():,}")
print(f"Non-children: {(all2_fy06['POP_KID'] == 0).sum():,}")

print("\n" + "-" * 80)
print("Unweighted Frequency: POP_KID * PAR_WORK * MOM_EMPST31 * DAD_EMPST31")
print("-" * 80)

crosstab = pd.crosstab(
    [all2_fy06['POP_KID'], all2_fy06['PAR_WORK']],
    [all2_fy06['MOM_EMPST31'].apply(lambda x: 'EMPLOYED' if x == 1 else ('NOT EMPLOYED' if x in [2,3,4] else 'NO MOM/NOT REPORTED')),
     all2_fy06['DAD_EMPST31'].apply(lambda x: 'EMPLOYED' if x == 1 else ('NOT EMPLOYED' if x in [2,3,4] else 'NO DAD/NOT REPORTED'))],
    margins=True
)
print(crosstab.to_string())

print("\n" + "-" * 80)
print("FREQUENCY FOR PARENT'S EMPLOYMENT STATUS RD 3/1")
print("WEIGHT = PERWT06F")
print("-" * 80)

design = SurveyDesign(all2_fy06, strata='VARSTR', cluster='VARPSU', weight='PERWT06F')

total_weight = all2_fy06['PERWT06F'].sum()

print("\nBy POP_KID and PAR_WORK:")
print("-" * 60)

for pop_kid in [0, 1]:
    subset_kid = all2_fy06[all2_fy06['POP_KID'] == pop_kid]
    kid_weight = subset_kid['PERWT06F'].sum()
    kid_pct = (kid_weight / total_weight * 100) if total_weight > 0 else 0
    
    print(f"\n{kid_labels[pop_kid]}: {kid_weight:,.0f} ({kid_pct:.1f}%)")
    
    for par_work in [0, 1, 2, 3]:
        if pop_kid == 0 and par_work != 0:
            continue
        if pop_kid == 1 and par_work == 0:
            continue
            
        subset = subset_kid[subset_kid['PAR_WORK'] == par_work]
        if len(subset) > 0:
            weight = subset['PERWT06F'].sum()
            row_pct = (weight / kid_weight * 100) if kid_weight > 0 else 0
            print(f"  {par_work_labels[par_work]}: {weight:,.0f} ({row_pct:.1f}%)")
