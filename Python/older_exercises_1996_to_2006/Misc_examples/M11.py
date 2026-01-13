"""
AHRQ MEPS Data Users Workshop - Misc Example M11

This example shows the process for merging parent's information to
children's records. The mother's and father's employment status (EMPST31)
is merged to children ages 0-17. A new variable PAR_WORK is constructed
to summarize if the child has two working parents, one working parent,
or no working parents.

Input file: h105.sas7bdat (2006 Full-Year Data File)

Python equivalent of: SAS/older_exercises_1996_to_2006/Misc_examples/M11/M11.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_freq


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS/DATA")
    
    print("=" * 80)
    print("AHRQ MEPS DATA USERS WORKSHOP")
    print("MERGING PARENT'S INFORMATION TO CHILDREN'S RECORDS")
    print("=" * 80)
    
    # Labels
    kid_labels = {1: 'Child, Age 0-17', 0: 'Not a Child'}
    par_work_labels = {
        1: 'Both Parents Work',
        2: 'One Parent Works',
        3: 'No Working Parent',
        0: 'Not a Child'
    }
    empst_labels = {
        -9: 'Not Reported', -8: 'Not Reported', -7: 'Not Reported', -1: 'Not Reported',
        0: 'No Mom/Dad in MEPS',
        1: 'Employed',
        2: 'Job to Return To',
        3: 'Job During Round',
        4: 'Not Employed'
    }
    
    # Load Full-Year file
    fyc_file = data_dir / "h105.sas7bdat"
    print(f"\nLoading data from: {fyc_file}")
    
    all_fy06 = load_sas_data(fyc_file, columns=[
        'DUPERSID', 'DUID', 'PID', 'AGE31X', 'MOPID31X', 'DAPID31X',
        'EMPST31', 'PERWT06F', 'VARSTR', 'VARPSU'
    ])
    
    # Filter to positive weight
    all_fy06 = all_fy06[all_fy06['PERWT06F'] > 0].copy()
    print(f"Total persons with positive weight: {len(all_fy06):,}")
    
    # Create kids dataset with linking IDs to both mom and dad
    print("\n" + "-" * 60)
    print("CREATE KIDS DATASET WITH LINKING IDS")
    print("-" * 60)
    
    kids = all_fy06[(all_fy06['AGE31X'] >= 0) & (all_fy06['AGE31X'] <= 17)].copy()
    print(f"Children ages 0-17: {len(kids):,}")
    
    # Create linking IDs
    # MOMLINK = DUID (5 digits) + MOPID31X (3 digits)
    # DADLINK = DUID (5 digits) + DAPID31X (3 digits)
    kids['MOMLINK'] = np.where(
        kids['MOPID31X'] != -1,
        kids['DUID'].astype(str).str.zfill(5) + kids['MOPID31X'].astype(int).astype(str).str.zfill(3),
        None
    )
    kids['DADLINK'] = np.where(
        kids['DAPID31X'] != -1,
        kids['DUID'].astype(str).str.zfill(5) + kids['DAPID31X'].astype(int).astype(str).str.zfill(3),
        None
    )
    
    kids = kids[['DUPERSID', 'MOMLINK', 'DADLINK', 'MOPID31X', 'DAPID31X', 'AGE31X']]
    
    print("\nSample of kids dataset:")
    print(kids.head(10).to_string(index=False))
    
    # Create DADS dataset
    print("\n" + "-" * 60)
    print("CREATE DADS AND MOMS DATASETS")
    print("-" * 60)
    
    dads = all_fy06[['DUPERSID', 'EMPST31']].copy()
    dads = dads.rename(columns={'DUPERSID': 'DADLINK', 'EMPST31': 'DAD_EMPST31'})
    
    moms = all_fy06[['DUPERSID', 'EMPST31']].copy()
    moms = moms.rename(columns={'DUPERSID': 'MOMLINK', 'EMPST31': 'MOM_EMPST31'})
    
    print(f"Potential dads: {len(dads):,}")
    print(f"Potential moms: {len(moms):,}")
    
    # Merge kids with dads
    print("\n" + "-" * 60)
    print("MERGE KIDS WITH PARENTS")
    print("-" * 60)
    
    kids2 = kids.merge(dads, on='DADLINK', how='left')
    kids2['DAD_EMPST31'] = kids2['DAD_EMPST31'].fillna(0)  # 0 = No dad in MEPS
    
    kids_wparents = kids2.merge(moms, on='MOMLINK', how='left')
    kids_wparents['MOM_EMPST31'] = kids_wparents['MOM_EMPST31'].fillna(0)  # 0 = No mom in MEPS
    
    print(f"Kids with parent info: {len(kids_wparents):,}")
    
    print("\nSample of kids with parents information:")
    print(kids_wparents.head(10).to_string(index=False))
    
    # Merge back to full sample
    print("\n" + "-" * 60)
    print("MERGE BACK TO FULL SAMPLE")
    print("-" * 60)
    
    all2_fy06 = all_fy06.merge(
        kids_wparents[['DUPERSID', 'MOMLINK', 'DADLINK', 'MOM_EMPST31', 'DAD_EMPST31']],
        on='DUPERSID',
        how='left'
    )
    
    # Create POP_KID and PAR_WORK variables
    all2_fy06['POP_KID'] = np.where(all2_fy06['MOMLINK'].notna() | all2_fy06['DADLINK'].notna(), 1, 0)
    
    # For children, determine working parent status
    all2_fy06['PAR_WORK'] = np.where(
        all2_fy06['POP_KID'] == 1,
        np.where(
            (all2_fy06['MOM_EMPST31'] == 1) & (all2_fy06['DAD_EMPST31'] == 1), 1,
            np.where(
                (all2_fy06['MOM_EMPST31'] == 1) | (all2_fy06['DAD_EMPST31'] == 1), 2, 3
            )
        ),
        0
    )
    
    # Fill missing values for non-children
    all2_fy06['DAD_EMPST31'] = all2_fy06['DAD_EMPST31'].fillna(-1)
    all2_fy06['MOM_EMPST31'] = all2_fy06['MOM_EMPST31'].fillna(-1)
    
    print(f"Total persons: {len(all2_fy06):,}")
    print(f"Children (POP_KID=1): {(all2_fy06['POP_KID'] == 1).sum():,}")
    
    # Frequency tables
    print("\n" + "=" * 80)
    print("FREQUENCY FOR PARENT'S EMPLOYMENT STATUS")
    print("=" * 80)
    
    # Cross-tabulation
    print("\nPOP_KID * PAR_WORK * MOM_EMPST31 * DAD_EMPST31:")
    ct = pd.crosstab(
        [all2_fy06['POP_KID'].map(kid_labels), all2_fy06['PAR_WORK'].map(par_work_labels)],
        [all2_fy06['MOM_EMPST31'], all2_fy06['DAD_EMPST31']],
        margins=True
    )
    print(ct)
    
    # Survey frequency for PAR_WORK
    print("\n" + "=" * 80)
    print("WEIGHTED FREQUENCY FOR PARENT'S EMPLOYMENT STATUS")
    print("=" * 80)
    
    # Filter to children only for this analysis
    children = all2_fy06[all2_fy06['POP_KID'] == 1].copy()
    
    design = SurveyDesign(
        data=children,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT06F'
    )
    
    total_wt = children['PERWT06F'].sum()
    
    print(f"\n{'Parent Work Status':<25} {'N':>10} {'Weighted':>15} {'Row %':>10}")
    print("-" * 60)
    
    for par_work in [1, 2, 3]:
        subset = children[children['PAR_WORK'] == par_work]
        if len(subset) > 0:
            wt = subset['PERWT06F'].sum()
            pct = wt / total_wt * 100
            print(f"{par_work_labels[par_work]:<25} {len(subset):>10,} {wt:>15,.0f} {pct:>9.1f}%")
    
    print("-" * 60)
    print(f"{'Total':<25} {len(children):>10,} {total_wt:>15,.0f} {100.0:>9.1f}%")
    
    print("\n" + "=" * 80)
    print("KEY TAKEAWAY")
    print("=" * 80)
    print("""
This example demonstrates how to link family members in MEPS data:

1. Use MOPID31X and DAPID31X to identify mother's and father's PID
2. Create linking IDs by combining DUID with parent's PID
3. Merge parent's characteristics (e.g., employment status) to children
4. Create derived variables summarizing family characteristics

This technique can be used to analyze how parent characteristics
affect children's health outcomes, healthcare utilization, etc.
""")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
