"""
AHRQ MEPS Data Users Workshop - Estimation Example E4

This example shows how to compute family-level estimates, using the MEPS
definition of family rather than the CPS definition.

This program generates the following family-level estimates:
(1) Mean number of persons per family
(2) 2001 mean total healthcare expenses per family
(3) 2001 mean total healthcare expenses per family size

Input file: h60.sas7bdat (2001 MEPS Full-Year File)

Python equivalent of: SAS/older_exercises_1996_to_2006/Estimation_examples/E4/E4.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_mean


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS/DATA")
    
    print("=" * 80)
    print("AHRQ MEPS DATA USERS WORKSHOP (ESTIMATION)")
    print("COMPUTING FAMILY-LEVEL ESTIMATES")
    print("=" * 80)
    
    # Load FYC file
    fyc_file = data_dir / "h60.sas7bdat"
    print(f"\nLoading data from: {fyc_file}")
    
    h60 = load_sas_data(fyc_file, columns=[
        'DUID', 'FAMIDYR', 'DUPERSID', 'FAMWT01F',
        'VARSTR01', 'VARPSU01', 'FAMRFPYR', 'FAMSZEYR', 'TOTEXP01'
    ])
    
    # Create family ID
    h60['DUIDFAMY'] = h60['DUID'].astype(str).str.zfill(5) + h60['FAMIDYR'].astype(str)
    
    print(f"Total person records: {len(h60):,}")
    print(f"Unique families: {h60['DUIDFAMY'].nunique():,}")
    
    # Create family-level file by summing expenses to family level
    fam_h60 = h60.groupby('DUIDFAMY').agg({
        'TOTEXP01': 'sum',
        'FAMWT01F': 'first',
        'VARSTR01': 'first',
        'VARPSU01': 'first',
        'FAMSZEYR': 'first'
    }).reset_index()
    
    fam_h60 = fam_h60.rename(columns={'TOTEXP01': 'FAMTOT01'})
    
    # Subset to families with positive weight
    fam_h60 = fam_h60[fam_h60['FAMWT01F'] > 0].copy()
    
    print(f"\nFamilies with positive weight: {len(fam_h60):,}")
    
    # Frequency count of family size
    print("\n" + "=" * 80)
    print("FREQUENCY COUNT OF FAMILY SIZE VARIABLE (UNWEIGHTED)")
    print("=" * 80)
    
    print(fam_h60['FAMSZEYR'].value_counts().sort_index())
    
    # Sample print of families
    print("\n" + "=" * 80)
    print("SAMPLE PRINT OF FAMILIES")
    print("=" * 80)
    
    sample_families = ['40001A', '40006A', '40007A', '40010A', '40011A']
    
    # Person-level view
    print("\nPerson-level data (showing how TOTEXP01 is summed):")
    for fam_id in sample_families:
        fam_data = h60[h60['DUIDFAMY'] == fam_id]
        if len(fam_data) > 0:
            print(f"\nFamily {fam_id}:")
            for idx, row in fam_data.iterrows():
                print(f"  {row['DUPERSID']}: ${row['TOTEXP01']:,.2f}")
            print(f"  Family Total: ${fam_data['TOTEXP01'].sum():,.2f}")
    
    # Family-level view
    print("\nFamily-level data:")
    for fam_id in sample_families:
        fam_data = fam_h60[fam_h60['DUIDFAMY'] == fam_id]
        if len(fam_data) > 0:
            print(f"  {fam_id}: ${fam_data['FAMTOT01'].values[0]:,.2f}")
    
    # Survey estimates
    print("\n" + "=" * 80)
    print("FAMILY-LEVEL ESTIMATES")
    print("=" * 80)
    
    design = SurveyDesign(
        data=fam_h60,
        strata='VARSTR01',
        cluster='VARPSU01',
        weight='FAMWT01F'
    )
    
    # Mean family size
    mean_size = survey_mean(design, 'FAMSZEYR')
    print(f"\nMean number of persons per family: {mean_size['mean'].values[0]:.2f}")
    print(f"  SE: {mean_size['se'].values[0]:.3f}")
    
    # Mean family expenses
    mean_exp = survey_mean(design, 'FAMTOT01')
    print(f"\nMean total healthcare expenses per family: ${mean_exp['mean'].values[0]:,.2f}")
    print(f"  SE: ${mean_exp['se'].values[0]:.2f}")
    
    # Mean expenses by family size
    print("\n" + "=" * 80)
    print("TOTAL HEALTHCARE EXPENSES PER FAMILY SIZE")
    print("=" * 80)
    
    # Create family size categories
    fam_h60['FAMSIZE_CAT'] = np.where(fam_h60['FAMSZEYR'] >= 5, '5+', fam_h60['FAMSZEYR'].astype(str))
    
    for size_cat in ['1', '2', '3', '4', '5+']:
        subset = fam_h60[fam_h60['FAMSIZE_CAT'] == size_cat].copy()
        
        if len(subset) > 0:
            design_sub = SurveyDesign(
                data=subset,
                strata='VARSTR01',
                cluster='VARPSU01',
                weight='FAMWT01F'
            )
            
            mean_result = survey_mean(design_sub, 'FAMTOT01')
            print(f"\nFamily size {size_cat}:")
            print(f"  N: {len(subset):,}")
            print(f"  Mean expenses: ${mean_result['mean'].values[0]:,.2f}")
            print(f"  SE: ${mean_result['se'].values[0]:.2f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
