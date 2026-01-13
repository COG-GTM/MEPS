"""
AHRQ MEPS Data Users Workshop - Estimation Example E2

This example shows how to:
(1) Compute average total healthcare expenditures for children 0-5 for 1996-1999
(2) Compute average total expenditures for 1996-1997 and 1998-1999 using pooled data

Expenditures are standardized to 1999 dollars using the annual CPI for all urban
consumers (CPI-U).

Input files:
    - h12.sas7bdat (1996 Full-Year Data File)
    - h20.sas7bdat (1997 Full-Year Data File)
    - h28.sas7bdat (1998 Full-Year Data File)
    - h38.sas7bdat (1999 Full-Year Data File)
    - h36.sas7bdat (1996-2002 Pooled Estimation File)

Python equivalent of: SAS/older_exercises_1996_to_2006/Estimation_examples/E2/E2.sas
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
    print("AVERAGE TOTAL HEALTHCARE EXPENDITURES, 1996 - 1999")
    print("=" * 80)
    
    # CPI values for standardization to 1999 dollars
    CPI_1996 = 156.9
    CPI_1997 = 160.5
    CPI_1998 = 163.0
    CPI_1999 = 166.6
    
    # Load and process 1996 data
    print("\n" + "-" * 60)
    print("1996 DATA")
    print("-" * 60)
    
    h12 = load_sas_data(data_dir / "h12.sas7bdat", columns=[
        'DUPERSID', 'TOTEXP96', 'WTDPER96', 'VARPSU96', 'VARSTR96', 'AGE96X'
    ])
    h12['TOTEXP'] = h12['TOTEXP96'] * (CPI_1999 / CPI_1996)
    h12['AGEGRP'] = np.where((h12['AGE96X'] >= 0) & (h12['AGE96X'] <= 5), 'AGE 0-5', 'OTHER')
    
    # Subset to children 0-5
    h12_05 = h12[h12['AGEGRP'] == 'AGE 0-5'].copy()
    
    design_96 = SurveyDesign(
        data=h12_05,
        strata='VARSTR96',
        cluster='VARPSU96',
        weight='WTDPER96'
    )
    
    mean_96 = survey_mean(design_96, 'TOTEXP96')
    print(f"\nChildren 0-5:")
    print(f"  N: {len(h12_05):,}")
    print(f"  Mean Expenditure: ${mean_96['mean'].values[0]:,.2f}")
    print(f"  SE: ${mean_96['se'].values[0]:.2f}")
    
    # Load and process 1997 data
    print("\n" + "-" * 60)
    print("1997 DATA")
    print("-" * 60)
    
    h20 = load_sas_data(data_dir / "h20.sas7bdat", columns=[
        'DUPERSID', 'TOTEXP97', 'WTDPER97', 'VARPSU97', 'VARSTR97', 'AGE97X'
    ])
    h20['TOTEXP'] = h20['TOTEXP97'] * (CPI_1999 / CPI_1997)
    h20['AGEGRP'] = np.where((h20['AGE97X'] >= 0) & (h20['AGE97X'] <= 5), 'AGE 0-5', 'OTHER')
    
    h20_05 = h20[h20['AGEGRP'] == 'AGE 0-5'].copy()
    
    design_97 = SurveyDesign(
        data=h20_05,
        strata='VARSTR97',
        cluster='VARPSU97',
        weight='WTDPER97'
    )
    
    mean_97 = survey_mean(design_97, 'TOTEXP97')
    print(f"\nChildren 0-5:")
    print(f"  N: {len(h20_05):,}")
    print(f"  Mean Expenditure: ${mean_97['mean'].values[0]:,.2f}")
    print(f"  SE: ${mean_97['se'].values[0]:.2f}")
    
    # Load and process 1998 data
    print("\n" + "-" * 60)
    print("1998 DATA")
    print("-" * 60)
    
    h28 = load_sas_data(data_dir / "h28.sas7bdat", columns=[
        'DUPERSID', 'TOTEXP98', 'WTDPER98', 'VARPSU98', 'VARSTR98', 'AGE98X'
    ])
    h28['TOTEXP'] = h28['TOTEXP98'] * (CPI_1999 / CPI_1998)
    h28['AGEGRP'] = np.where((h28['AGE98X'] >= 0) & (h28['AGE98X'] <= 5), 'AGE 0-5', 'OTHER')
    
    h28_05 = h28[h28['AGEGRP'] == 'AGE 0-5'].copy()
    
    design_98 = SurveyDesign(
        data=h28_05,
        strata='VARSTR98',
        cluster='VARPSU98',
        weight='WTDPER98'
    )
    
    mean_98 = survey_mean(design_98, 'TOTEXP98')
    print(f"\nChildren 0-5:")
    print(f"  N: {len(h28_05):,}")
    print(f"  Mean Expenditure: ${mean_98['mean'].values[0]:,.2f}")
    print(f"  SE: ${mean_98['se'].values[0]:.2f}")
    
    # Load and process 1999 data
    print("\n" + "-" * 60)
    print("1999 DATA")
    print("-" * 60)
    
    h38 = load_sas_data(data_dir / "h38.sas7bdat", columns=[
        'DUPERSID', 'TOTEXP99', 'PERWT99F', 'VARPSU99', 'VARSTR99', 'AGE99X'
    ])
    h38['AGEGRP'] = np.where((h38['AGE99X'] >= 0) & (h38['AGE99X'] <= 5), 'AGE 0-5', 'OTHER')
    
    h38_05 = h38[h38['AGEGRP'] == 'AGE 0-5'].copy()
    
    design_99 = SurveyDesign(
        data=h38_05,
        strata='VARSTR99',
        cluster='VARPSU99',
        weight='PERWT99F'
    )
    
    mean_99 = survey_mean(design_99, 'TOTEXP99')
    print(f"\nChildren 0-5:")
    print(f"  N: {len(h38_05):,}")
    print(f"  Mean Expenditure: ${mean_99['mean'].values[0]:,.2f}")
    print(f"  SE: ${mean_99['se'].values[0]:.2f}")
    
    # Pooled 1996-1997 data
    print("\n" + "=" * 80)
    print("POOLED 1996-1997 DATA")
    print("EXPENDITURES STANDARDIZED TO 1999 DOLLARS")
    print("=" * 80)
    
    # Load pooled estimation file for strata/PSU
    h36 = load_sas_data(data_dir / "h36.sas7bdat", columns=['DUPERSID', 'STRA9602', 'PSU9602'])
    
    # Pool 1996 and 1997 data
    pool_9697 = pd.concat([
        h12[['DUPERSID', 'TOTEXP', 'WTDPER96', 'AGE96X']].rename(columns={'WTDPER96': 'POOLWT', 'AGE96X': 'AGE'}),
        h20[['DUPERSID', 'TOTEXP', 'WTDPER97', 'AGE97X']].rename(columns={'WTDPER97': 'POOLWT', 'AGE97X': 'AGE'})
    ], ignore_index=True)
    
    # Divide weight by 2 for pooling
    pool_9697.loc[pool_9697['POOLWT'] > 0, 'POOLWT'] = pool_9697.loc[pool_9697['POOLWT'] > 0, 'POOLWT'] / 2
    
    # Merge with pooled estimation file
    pool_9697 = pool_9697.merge(h36, on='DUPERSID', how='inner')
    
    # Subset to children 0-5
    pool_9697['AGEGRP'] = np.where((pool_9697['AGE'] >= 0) & (pool_9697['AGE'] <= 5), 'AGE 0-5', 'OTHER')
    pool_9697_05 = pool_9697[pool_9697['AGEGRP'] == 'AGE 0-5'].copy()
    
    design_pool_9697 = SurveyDesign(
        data=pool_9697_05,
        strata='STRA9602',
        cluster='PSU9602',
        weight='POOLWT'
    )
    
    mean_pool_9697 = survey_mean(design_pool_9697, 'TOTEXP')
    print(f"\nChildren 0-5:")
    print(f"  N: {len(pool_9697_05):,}")
    print(f"  Mean Expenditure (1999$): ${mean_pool_9697['mean'].values[0]:,.2f}")
    print(f"  SE: ${mean_pool_9697['se'].values[0]:.2f}")
    
    # Pooled 1998-1999 data
    print("\n" + "=" * 80)
    print("POOLED 1998-1999 DATA")
    print("EXPENDITURES STANDARDIZED TO 1999 DOLLARS")
    print("=" * 80)
    
    # Pool 1998 and 1999 data
    h38['TOTEXP'] = h38['TOTEXP99']  # 1999 is already in 1999 dollars
    
    pool_9899 = pd.concat([
        h28[['DUPERSID', 'TOTEXP', 'WTDPER98', 'AGE98X']].rename(columns={'WTDPER98': 'POOLWT', 'AGE98X': 'AGE'}),
        h38[['DUPERSID', 'TOTEXP', 'PERWT99F', 'AGE99X']].rename(columns={'PERWT99F': 'POOLWT', 'AGE99X': 'AGE'})
    ], ignore_index=True)
    
    # Divide weight by 2 for pooling
    pool_9899.loc[pool_9899['POOLWT'] > 0, 'POOLWT'] = pool_9899.loc[pool_9899['POOLWT'] > 0, 'POOLWT'] / 2
    
    # Merge with pooled estimation file
    pool_9899 = pool_9899.merge(h36, on='DUPERSID', how='inner')
    
    # Subset to children 0-5
    pool_9899['AGEGRP'] = np.where((pool_9899['AGE'] >= 0) & (pool_9899['AGE'] <= 5), 'AGE 0-5', 'OTHER')
    pool_9899_05 = pool_9899[pool_9899['AGEGRP'] == 'AGE 0-5'].copy()
    
    design_pool_9899 = SurveyDesign(
        data=pool_9899_05,
        strata='STRA9602',
        cluster='PSU9602',
        weight='POOLWT'
    )
    
    mean_pool_9899 = survey_mean(design_pool_9899, 'TOTEXP')
    print(f"\nChildren 0-5:")
    print(f"  N: {len(pool_9899_05):,}")
    print(f"  Mean Expenditure (1999$): ${mean_pool_9899['mean'].values[0]:,.2f}")
    print(f"  SE: ${mean_pool_9899['se'].values[0]:.2f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
