"""
MEPS-HC: Prescribed medicine utilization and expenditures for the treatment of hyperlipidemia

This example code shows how to link the MEPS-HC Medical Conditions file to the Prescribed Medicines file for data year
2020 in order to estimate the following:

National totals:
   - Total number of people w/ at least one PMED fill for hyperlipidemia (HL)
   - Total PMED fills for HL
   - Total PMED expenditures for HL

Per-person averages among people with at least one PMED fill for HL:
   - Avg PMED fills for HL, by sex and poverty (POVCAT20)
   - Avg PMED expenditures for HL, by sex and poverty (POVCAT20)

Input files:
  - h220a.sas7bdat        (2020 Prescribed Medicines file)
  - h222.sas7bdat         (2020 Conditions file)
  - h220if1.sas7bdat      (2020 CLNK: Condition-Event Link file)
  - h224.sas7bdat         (2020 Full-Year Consolidated file)

Resources:
  - CCSR codes:
    https://github.com/HHS-AHRQ/MEPS/blob/master/Quick_Reference_Guides/meps_ccsr_conditions.csv

  - MEPS-HC Public Use Files:
    https://meps.ahrq.gov/mepsweb/data_stats/download_data_files.jsp

  - MEPS-HC online data tools:
    https://datatools.ahrq.gov/meps-hc
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total, print_results


def main(meps_data_path: str = "C:/MEPS"):
    """
    Main function to run the analysis.
    
    Parameters
    ----------
    meps_data_path : str
        Path to directory containing MEPS data files
    """
    
    # Read in data files
    print("Loading datasets...")
    
    # PMED file (record = rx fill or refill for a person)
    pmed20 = load_sas_data(os.path.join(meps_data_path, "h220a.sas7bdat"))
    pmed20['EVNTIDX'] = pmed20['LINKIDX']  # rename LINKIDX to EVNTIDX for merging to conditions
    pmed20 = pmed20[['DUPERSID', 'DRUGIDX', 'RXRECIDX', 'EVNTIDX', 'RXDRGNAM', 'RXXP20X']].copy()
    
    # Conditions file (record = medical condition for a person)
    cond20 = load_sas_data(os.path.join(meps_data_path, "h222.sas7bdat"))
    cond20 = cond20[['DUPERSID', 'CONDIDX', 'ICD10CDX', 'CCSR1X', 'CCSR2X', 'CCSR3X']].copy()
    
    # Conditions-event link file (crosswalk between conditions and medical events, including PMEDs)
    clnk20 = load_sas_data(os.path.join(meps_data_path, "h220if1.sas7bdat"))
    
    # Full-year consolidated (person-level) file (record = MEPS sample member)
    fyc20 = load_sas_data(os.path.join(meps_data_path, "h224.sas7bdat"))
    fyc20 = fyc20[['DUPERSID', 'AGELAST', 'SEX', 'POVCAT20', 'CHOLDX', 'PERWT20F', 'VARPSU', 'VARSTR']].copy()
    
    # Prepare data for estimation
    
    # Subset conditions file to only hyperlipidemia records (any CCSR = "END010")
    hl = cond20[
        (cond20['CCSR1X'] == 'END010') |
        (cond20['CCSR2X'] == 'END010') |
        (cond20['CCSR3X'] == 'END010')
    ].copy()
    
    print(f"\nHyperlipidemia conditions: {len(hl)} records")
    
    # Example to show someone with 'duplicate' hyperlipidemia conditions
    dup_hl = hl[hl.duplicated(subset=['DUPERSID'], keep=False)]
    if len(dup_hl) > 0:
        example_id = dup_hl['DUPERSID'].iloc[0]
        print(f"\nExample of duplicate hyperlipidemia conditions (DUPERSID = {example_id}):")
        print(hl[hl['DUPERSID'] == example_id])
    
    # Get EVNTIDX values for hyperlipidemia records from CLNK file
    hl = hl.sort_values(['DUPERSID', 'CONDIDX'])
    clnk20 = clnk20.sort_values(['DUPERSID', 'CONDIDX'])
    
    clnk_hl = pd.merge(
        hl,
        clnk20,
        on=['DUPERSID', 'CONDIDX'],
        how='inner'
    )
    
    print(f"\nAfter merging with CLNK: {len(clnk_hl)} records")
    
    # Revisit duplicate example after merging to CLNK
    if len(dup_hl) > 0:
        print(f"\nDuplicate example after CLNK merge (DUPERSID = {example_id}):")
        print(clnk_hl[clnk_hl['DUPERSID'] == example_id])
    
    # De-duplicate clnk_hl by EVNTIDX
    clnk_hl_dedup = clnk_hl.drop_duplicates(subset=['DUPERSID', 'EVNTIDX'])
    
    print(f"\nAfter de-duplicating by EVNTIDX: {len(clnk_hl_dedup)} records")
    
    # Look at event types
    print("\nEvent types in clnk_hl_dedup:")
    print(clnk_hl_dedup['EVENTYPE'].value_counts())
    
    # Sort pmed20 data to prepare for merge
    pmed20 = pmed20.sort_values(['DUPERSID', 'EVNTIDX'])
    
    # Get PMED events linked to hyperlipidemia
    hl_merged = pd.merge(
        clnk_hl_dedup,
        pmed20,
        on=['DUPERSID', 'EVNTIDX'],
        how='inner'
    )
    
    print(f"\nAfter merging with PMED: {len(hl_merged)} records")
    
    # QC: Make sure all events have EVNTYPE = 8 (for PMED event)
    print("\nEvent types after PMED merge (should all be 8):")
    print(hl_merged['EVENTYPE'].value_counts())
    
    # QC: Look at top PMEDs for hyperlipidemia
    print("\nTop 10 PMEDs for hyperlipidemia (by unweighted # fills):")
    print(hl_merged['RXDRGNAM'].value_counts().head(10))
    
    # Create dummy variable for each unique fill
    hl_merged['hl_fill'] = 1
    
    # Roll up to person level
    drugs_by_pers = hl_merged.groupby('DUPERSID').agg({
        'hl_fill': 'sum',
        'RXXP20X': 'sum'
    }).reset_index()
    drugs_by_pers.columns = ['DUPERSID', 'n_hl_fills', 'hl_drug_exp']
    
    print(f"\nPerson-level drug data: {len(drugs_by_pers)} persons with HL PMEDs")
    
    # Merge person-level totals back to FYC
    fyc_hl = pd.merge(
        fyc20,
        drugs_by_pers,
        on='DUPERSID',
        how='left'
    )
    
    # Create flag for whether a person has any pmed fills for hyperlipidemia
    fyc_hl['hl_pmed_flag'] = (fyc_hl['n_hl_fills'] > 0).astype(int)
    
    # Set system missings to zeroes
    fyc_hl['n_hl_fills'] = fyc_hl['n_hl_fills'].fillna(0)
    fyc_hl['hl_drug_exp'] = fyc_hl['hl_drug_exp'].fillna(0)
    
    # QC: compare adults ever diagnosed with hyperlipidemia (CHOLDX = 1) with people who have PMEDs
    print("\nCHOLDX vs hl_pmed_flag crosstab:")
    print(pd.crosstab(fyc_hl['CHOLDX'], fyc_hl['hl_pmed_flag'], margins=True))
    
    # QC: check counts of hl_pmed_flag
    print("\nhl_pmed_flag frequency:")
    print(fyc_hl['hl_pmed_flag'].value_counts())
    
    # QC: There should be no records where hl_pmed_flag=0 and (hl_drug_exp > 0 or n_hl_fills > 0)
    qc_check = fyc_hl[(fyc_hl['hl_pmed_flag'] == 0) & 
                       ((fyc_hl['hl_drug_exp'] > 0) | (fyc_hl['n_hl_fills'] > 0))]
    print(f"\nQC check (should be 0): {len(qc_check)} records with flag=0 but positive fills/exp")
    
    # ESTIMATION
    print("\n" + "="*80)
    print("NATIONAL TOTALS")
    print("="*80)
    
    # Create survey design
    design = SurveyDesign(
        data=fyc_hl,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT20F'
    )
    
    # National totals
    # - sum of hl_pmed_flag = 1 -> total people with any rx fills for HL
    # - sum of n_hl_fills -> total number of rx fills for HL
    # - sum of hl_drug_exp -> total rx expenditures for HL
    
    totals = survey_total(design, ['hl_pmed_flag', 'n_hl_fills', 'hl_drug_exp'])
    print("\nNational totals:")
    print_results(totals, format_dict={
        'Sum': '{:,.0f}',
        'StdDev': '{:,.0f}'
    })
    
    # Per-person averages for people with at least one PMED fill for hyperlipidemia
    print("\n" + "="*80)
    print("PER-PERSON AVERAGES (among people with HL PMEDs)")
    print("="*80)
    
    # Filter to people with HL PMEDs
    fyc_hl_pmed = fyc_hl[fyc_hl['hl_pmed_flag'] == 1].copy()
    design_pmed = SurveyDesign(
        data=fyc_hl_pmed,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT20F'
    )
    
    # Overall means
    means_overall = survey_mean(design_pmed, ['n_hl_fills', 'hl_drug_exp'])
    print("\nOverall means (hl_pmed_flag = 1):")
    print_results(means_overall, format_dict={
        'Mean': '{:,.2f}',
        'StdErr': '{:,.2f}'
    })
    
    # By sex
    print("\nMeans by sex (hl_pmed_flag = 1):")
    means_by_sex = survey_mean(design_pmed, ['n_hl_fills', 'hl_drug_exp'], domain='SEX')
    print_results(means_by_sex, format_dict={
        'Mean': '{:,.2f}',
        'StdErr': '{:,.2f}'
    })
    
    # By poverty status
    print("\nMeans by poverty status (hl_pmed_flag = 1):")
    means_by_pov = survey_mean(design_pmed, ['n_hl_fills', 'hl_drug_exp'], domain='POVCAT20')
    print_results(means_by_pov, format_dict={
        'Mean': '{:,.2f}',
        'StdErr': '{:,.2f}'
    })


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Hyperlipidemia PMED Analysis')
    parser.add_argument('--data-path', type=str, default='C:/MEPS',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
