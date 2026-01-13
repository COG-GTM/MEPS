"""
MEPS-HC: Prescribed medicine utilization and expenditures for the treatment of hyperlipidemia

This example code shows how to link the MEPS-HC Medical Conditions file to the
Prescribed Medicines file for data year 2020 in order to estimate the following:

National totals:
    - Total number of people w/ at least one PMED fill for hyperlipidemia (HL)
    - Total PMED fills for HL
    - Total PMED expenditures for HL

Per-person averages among people with at least one PMED fill for HL:
    - Avg PMED fills for HL, by sex and poverty (POVCAT20)
    - Avg PMED expenditures for HL, by sex and poverty (POVCAT20)

Input files:
    - h220a.sas7bdat (2020 Prescribed Medicines file)
    - h222.sas7bdat (2020 Conditions file)
    - h220if1.sas7bdat (2020 CLNK: Condition-Event Link file)
    - h224.sas7bdat (2020 Full-Year Consolidated file)

Resources:
    - CCSR codes: https://github.com/HHS-AHRQ/MEPS/blob/master/Quick_Reference_Guides/meps_ccsr_conditions.csv
    - MEPS-HC Public Use Files: https://meps.ahrq.gov/mepsweb/data_stats/download_data_files.jsp

Python equivalent of: SAS/workshop_exercises/cond_pmed_2020.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS")
    
    print("=" * 80)
    print("MEPS-HC: PRESCRIBED MEDICINE UTILIZATION AND EXPENDITURES")
    print("FOR THE TREATMENT OF HYPERLIPIDEMIA, 2020")
    print("=" * 80)
    
    # Read in data files
    print("\nLoading data files...")
    
    # PMED file (record = rx fill or refill for a person)
    pmed_file = data_dir / "h220a.sas7bdat"
    pmed20 = load_sas_data(pmed_file)
    pmed20['EVNTIDX'] = pmed20['LINKIDX']  # Rename LINKIDX to EVNTIDX for merging
    pmed20 = pmed20[['DUPERSID', 'DRUGIDX', 'RXRECIDX', 'EVNTIDX', 'RXDRGNAM', 'RXXP20X']]
    print(f"  PMED records: {len(pmed20):,}")
    
    # Conditions file (record = medical condition for a person)
    cond_file = data_dir / "h222.sas7bdat"
    cond20 = load_sas_data(cond_file)
    cond20 = cond20[['DUPERSID', 'CONDIDX', 'ICD10CDX', 'CCSR1X', 'CCSR2X', 'CCSR3X']]
    print(f"  Condition records: {len(cond20):,}")
    
    # Conditions-event link file
    clnk_file = data_dir / "h220if1.sas7bdat"
    clnk20 = load_sas_data(clnk_file)
    print(f"  CLNK records: {len(clnk20):,}")
    
    # Full-year consolidated file
    fyc_file = data_dir / "h224.sas7bdat"
    fyc20 = load_sas_data(
        fyc_file,
        columns=['DUPERSID', 'AGELAST', 'SEX', 'POVCAT20', 'CHOLDX', 'PERWT20F', 'VARPSU', 'VARSTR']
    )
    print(f"  FYC records: {len(fyc20):,}")
    
    # Prepare data for estimation
    print("\n" + "-" * 60)
    print("PREPARE DATA FOR ESTIMATION")
    print("-" * 60)
    
    # Subset conditions file to only hyperlipidemia records (any CCSR = "END010")
    hl = cond20[
        (cond20['CCSR1X'] == 'END010') | 
        (cond20['CCSR2X'] == 'END010') | 
        (cond20['CCSR3X'] == 'END010')
    ].copy()
    print(f"\nHyperlipidemia condition records: {len(hl):,}")
    
    # Example of duplicate hyperlipidemia conditions
    hl_dup = hl.groupby('DUPERSID').size()
    dup_persons = hl_dup[hl_dup > 1]
    print(f"Persons with multiple HL conditions: {len(dup_persons):,}")
    
    if len(dup_persons) > 0:
        example_id = dup_persons.index[0]
        print(f"\nExample of duplicate HL conditions (DUPERSID={example_id}):")
        print(hl[hl['DUPERSID'] == example_id][['DUPERSID', 'CONDIDX', 'ICD10CDX', 'CCSR1X']].to_string(index=False))
    
    # Get EVNTIDX values for hyperlipidemia records from CLNK file
    hl = hl.sort_values(['DUPERSID', 'CONDIDX'])
    clnk20 = clnk20.sort_values(['DUPERSID', 'CONDIDX'])
    
    clnk_hl = hl[['DUPERSID', 'CONDIDX', 'CCSR1X']].merge(
        clnk20[['DUPERSID', 'CONDIDX', 'EVNTIDX', 'EVENTYPE']],
        on=['DUPERSID', 'CONDIDX'],
        how='inner'
    )
    print(f"\nCondition-event links for HL: {len(clnk_hl):,}")
    
    # De-duplicate by EVNTIDX to avoid double-counting
    clnk_hl_dedup = clnk_hl.drop_duplicates(subset=['DUPERSID', 'EVNTIDX'])
    print(f"Unique events for HL (after dedup): {len(clnk_hl_dedup):,}")
    
    # Look at event types
    print("\nEvent types linked to hyperlipidemia:")
    print(clnk_hl_dedup['EVENTYPE'].value_counts())
    
    # Get PMED events linked to hyperlipidemia
    pmed20 = pmed20.sort_values(['DUPERSID', 'EVNTIDX'])
    
    hl_merged = clnk_hl_dedup.merge(
        pmed20,
        on=['DUPERSID', 'EVNTIDX'],
        how='inner'
    )
    print(f"\nPMED events linked to HL: {len(hl_merged):,}")
    
    # QC: Check event types (should all be 8 for PMED)
    print("\nEvent types in merged data (should be 8=PMED):")
    print(hl_merged['EVENTYPE'].value_counts())
    
    # QC: Top PMEDs for hyperlipidemia
    print("\nTop 10 PMEDs for hyperlipidemia (by unweighted # fills):")
    top_drugs = hl_merged['RXDRGNAM'].value_counts().head(10)
    print(top_drugs)
    
    # Create dummy variable for each fill
    hl_merged['HL_FILL'] = 1
    
    # Roll up to person level
    drugs_by_pers = hl_merged.groupby('DUPERSID').agg(
        N_HL_FILLS=('HL_FILL', 'sum'),
        HL_DRUG_EXP=('RXXP20X', 'sum')
    ).reset_index()
    print(f"\nPersons with PMED fills for HL: {len(drugs_by_pers):,}")
    
    # Merge person-level totals back to FYC
    fyc_hl = fyc20.merge(drugs_by_pers, on='DUPERSID', how='left')
    
    # Create flag for persons with any PMED fills for HL
    fyc_hl['HL_PMED_FLAG'] = np.where(fyc_hl['N_HL_FILLS'] > 0, 1, 0)
    
    # Set missing values to zero
    fyc_hl['N_HL_FILLS'] = fyc_hl['N_HL_FILLS'].fillna(0)
    fyc_hl['HL_DRUG_EXP'] = fyc_hl['HL_DRUG_EXP'].fillna(0)
    
    # QC: Compare CHOLDX with HL_PMED_FLAG
    print("\n" + "-" * 60)
    print("QC: CHOLDX (ever diagnosed) vs HL_PMED_FLAG (PMED in 2020)")
    print("-" * 60)
    print(pd.crosstab(fyc_hl['CHOLDX'], fyc_hl['HL_PMED_FLAG'], margins=True))
    
    # QC: Check HL_PMED_FLAG distribution
    print("\nHL_PMED_FLAG distribution:")
    print(fyc_hl['HL_PMED_FLAG'].value_counts())
    
    # ESTIMATION
    print("\n" + "=" * 60)
    print("NATIONAL TOTALS")
    print("=" * 60)
    
    design = SurveyDesign(
        data=fyc_hl,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT20F'
    )
    
    # Total people with any rx fills for HL
    total_people = survey_total(design, 'HL_PMED_FLAG')
    print(f"\nTotal people with any PMED fills for HL:")
    print(f"  Total: {total_people['total'].values[0]:,.0f}")
    print(f"  SE: {total_people['se'].values[0]:,.0f}")
    
    # Total number of rx fills for HL
    total_fills = survey_total(design, 'N_HL_FILLS')
    print(f"\nTotal PMED fills for HL:")
    print(f"  Total: {total_fills['total'].values[0]:,.0f}")
    print(f"  SE: {total_fills['se'].values[0]:,.0f}")
    
    # Total rx expenditures for HL
    total_exp = survey_total(design, 'HL_DRUG_EXP')
    print(f"\nTotal PMED expenditures for HL:")
    print(f"  Total: ${total_exp['total'].values[0]:,.0f}")
    print(f"  SE: ${total_exp['se'].values[0]:,.0f}")
    
    # Per-person averages for people with at least one PMED fill for HL
    print("\n" + "=" * 60)
    print("PER-PERSON AVERAGES (among people with PMED fills for HL)")
    print("=" * 60)
    
    # Subset to persons with HL PMED fills
    fyc_hl_sub = fyc_hl[fyc_hl['HL_PMED_FLAG'] == 1].copy()
    
    design_sub = SurveyDesign(
        data=fyc_hl_sub,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT20F'
    )
    
    # Overall averages
    mean_fills = survey_mean(design_sub, 'N_HL_FILLS')
    mean_exp = survey_mean(design_sub, 'HL_DRUG_EXP')
    
    print(f"\nOverall:")
    print(f"  Avg PMED fills: {mean_fills['mean'].values[0]:.2f} (SE: {mean_fills['se'].values[0]:.4f})")
    print(f"  Avg PMED expenditures: ${mean_exp['mean'].values[0]:,.2f} (SE: ${mean_exp['se'].values[0]:.2f})")
    
    # By Sex
    print("\nBy Sex:")
    for sex_val, sex_label in [(1, 'Male'), (2, 'Female')]:
        subset = fyc_hl_sub[fyc_hl_sub['SEX'] == sex_val].copy()
        if len(subset) > 0:
            design_sex = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT20F'
            )
            mean_fills = survey_mean(design_sex, 'N_HL_FILLS')
            mean_exp = survey_mean(design_sex, 'HL_DRUG_EXP')
            print(f"  {sex_label}:")
            print(f"    Avg fills: {mean_fills['mean'].values[0]:.2f}, Avg exp: ${mean_exp['mean'].values[0]:,.2f}")
    
    # By Poverty Category
    print("\nBy Poverty Category:")
    povcat_labels = {1: 'Poor/Negative', 2: 'Near Poor', 3: 'Low Income', 4: 'Middle Income', 5: 'High Income'}
    for pov_val, pov_label in povcat_labels.items():
        subset = fyc_hl_sub[fyc_hl_sub['POVCAT20'] == pov_val].copy()
        if len(subset) > 0:
            design_pov = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT20F'
            )
            mean_fills = survey_mean(design_pov, 'N_HL_FILLS')
            mean_exp = survey_mean(design_pov, 'HL_DRUG_EXP')
            print(f"  {pov_label}:")
            print(f"    Avg fills: {mean_fills['mean'].values[0]:.2f}, Avg exp: ${mean_exp['mean'].values[0]:,.2f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
