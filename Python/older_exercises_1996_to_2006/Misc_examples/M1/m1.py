import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP -- SEPTEMBER 2008")
print("EFFECT OF WEIGHT VARIABLE ON RACE/ETHNICITY PERCENTAGE")
print("=" * 80)

racethn_labels = {
    0: 'TOTAL',
    1: 'HISPANIC',
    2: 'BLACK-NO OTH RACE/NOT HISPANIC',
    3: 'ASIAN-NO OTH RACE/NOT HISPANIC',
    4: 'OTHER/NOT HISPANIC'
}

fyc = load_sas_data(f'{data_path}/h97.sas7bdat', columns=[
    'RACETHNX', 'PERWT05F'
])

def recode_racethn(x):
    if x == 1:
        return 1
    elif x == 2:
        return 2
    elif x == 3:
        return 3
    else:
        return 4

fyc['RACETHNX_RECODED'] = fyc['RACETHNX'].apply(recode_racethn)

print("\n" + "-" * 80)
print("Unweighted Percentages")
print("-" * 80)

unweighted = fyc['RACETHNX_RECODED'].value_counts(normalize=True) * 100
unweighted = unweighted.sort_index()

print("\nRace/Ethnicity Distribution (Unweighted):")
for race in [1, 2, 3, 4]:
    pct = unweighted.get(race, 0)
    print(f"  {racethn_labels[race]}: {pct:.2f}%")

print("\n" + "-" * 80)
print("Weighted Percentages")
print("-" * 80)

total_weight = fyc['PERWT05F'].sum()
weighted = fyc.groupby('RACETHNX_RECODED')['PERWT05F'].sum() / total_weight * 100

print("\nRace/Ethnicity Distribution (Weighted):")
for race in [1, 2, 3, 4]:
    pct = weighted.get(race, 0)
    print(f"  {racethn_labels[race]}: {pct:.2f}%")

print("\n" + "-" * 80)
print("Comparison: Unweighted vs Weighted")
print("-" * 80)

print("\n{:<40} {:>15} {:>15}".format('Race/Ethnicity', 'Unweighted %', 'Weighted %'))
print("-" * 70)

for race in [1, 2, 3, 4]:
    unwt_pct = unweighted.get(race, 0)
    wt_pct = weighted.get(race, 0)
    print(f"{racethn_labels[race]:<40} {unwt_pct:>15.2f} {wt_pct:>15.2f}")

print("\n" + "-" * 80)
print("Note: Weighted percentages should be used for national estimates.")
print("Unweighted percentages reflect the sample composition, not the")
print("U.S. civilian noninstitutionalized population.")
print("-" * 80)
