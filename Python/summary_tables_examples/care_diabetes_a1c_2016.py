"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Accessibility and quality of care: Diabetes Care, 2016

Diabetes care survey (DCS):
    - Number/percent of adults with diabetes receiving hemoglobin A1c blood test
    - By race/ethnicity

Input file: h192.ssp (2016 full-year consolidated)

Python equivalent of: SAS/summary_tables_examples/care_diabetes_a1c_2016.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_freq


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS")
    
    print("=" * 80)
    print("ACCESSIBILITY AND QUALITY OF CARE: DIABETES CARE, 2016")
    print("Adults with Diabetes Receiving Hemoglobin A1c Blood Test")
    print("=" * 80)
    
    # Load FYC file
    fyc_file = data_dir / "h192.ssp"
    print(f"\nLoading data from: {fyc_file}")
    
    meps = load_sas_data(fyc_file)
    
    # Define domain - persons with positive diabetes weight
    meps['DOMAIN'] = (meps['DIABW16F'] > 0).astype(int)
    
    # Adjust weights so observations aren't dropped
    meps.loc[meps['DOMAIN'] == 0, 'DIABW16F'] = 1
    
    # Race/ethnicity (for 2012 and later, use RACETHX and RACEV1X)
    meps['HISP'] = (meps['RACETHX'] == 1).astype(int)
    meps['WHITE'] = (meps['RACETHX'] == 2).astype(int)
    meps['BLACK'] = (meps['RACETHX'] == 3).astype(int)
    meps['NATIVE'] = ((meps['RACETHX'] > 3) & (meps['RACEV1X'].isin([3, 6]))).astype(int)
    meps['ASIAN'] = ((meps['RACETHX'] > 3) & (meps['RACEV1X'].isin([4, 5]))).astype(int)
    
    meps['RACE'] = (1 * meps['HISP'] + 2 * meps['WHITE'] + 3 * meps['BLACK'] + 
                   4 * meps['NATIVE'] + 5 * meps['ASIAN'])
    
    # Define A1c measurement variable
    # 1-95 = Had measurement, 0 or 96 = Did not have measurement
    meps['HAD_A1C'] = np.where(
        (meps['DSA1C53'] >= 1) & (meps['DSA1C53'] <= 95), 1,
        np.where((meps['DSA1C53'] == 0) | (meps['DSA1C53'] == 96), 0, np.nan)
    )
    
    # Define labels
    race_labels = {
        1: 'Hispanic',
        2: 'White',
        3: 'Black',
        4: 'Amer. Indian, AK Native, or mult. races',
        5: 'Asian, Hawaiian, or Pacific Islander'
    }
    
    a1c_labels = {
        1: 'Had measurement',
        0: 'Did not have measurement'
    }
    
    # QC new variables
    print("\n" + "-" * 60)
    print("QC: RACE VARIABLE")
    print("-" * 60)
    print(meps['RACE'].value_counts().sort_index())
    
    # Calculate estimates
    print("\n" + "=" * 80)
    print("ADULTS WITH DIABETES WITH HEMOGLOBIN A1C MEASUREMENT, 2016")
    print("By Race/Ethnicity")
    print("=" * 80)
    
    # Subset to domain (persons with diabetes)
    domain_data = meps[meps['DOMAIN'] == 1].copy()
    
    print(f"\nN (unweighted): {len(domain_data):,}")
    
    # Overall distribution
    print("\n" + "-" * 60)
    print("OVERALL")
    print("-" * 60)
    
    valid_data = domain_data[domain_data['HAD_A1C'].notna()].copy()
    
    design = SurveyDesign(
        data=valid_data,
        strata='VARSTR',
        cluster='VARPSU',
        weight='DIABW16F'
    )
    
    freq_result = survey_freq(design, 'HAD_A1C')
    
    print(f"\n{'A1c Status':<30} {'Count':>15} {'Percent':>10}")
    print("-" * 60)
    
    for idx, row in freq_result.iterrows():
        level = row['level']
        if pd.notna(level):
            label = a1c_labels.get(int(level), str(level))
            print(f"{label:<30} {row['count']:>15,.0f} {row['proportion']*100:>9.2f}%")
    
    # By race/ethnicity
    print("\n" + "-" * 60)
    print("BY RACE/ETHNICITY")
    print("-" * 60)
    
    for race_val, race_label in race_labels.items():
        subset = valid_data[valid_data['RACE'] == race_val].copy()
        
        if len(subset) > 0:
            design_race = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='DIABW16F'
            )
            
            freq_result = survey_freq(design_race, 'HAD_A1C')
            
            print(f"\n{race_label}:")
            print(f"  N: {len(subset):,}")
            
            for idx, row in freq_result.iterrows():
                level = row['level']
                if pd.notna(level):
                    label = a1c_labels.get(int(level), str(level))
                    print(f"  {label}: {row['count']:,.0f} ({row['proportion']*100:.2f}%)")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
