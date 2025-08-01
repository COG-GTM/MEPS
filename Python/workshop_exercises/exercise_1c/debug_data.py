#!/usr/bin/env python3
"""
Debug script to examine MEPS data structure and samplics requirements
"""

import pandas as pd
import numpy as np
import pyreadstat

def main():
    print("Debugging MEPS data structure...")
    
    data_file = "/home/ubuntu/attachments/f7c05e0e-0670-4077-8658-ea9e22b91083/h209.sas7bdat"
    
    df, meta = pyreadstat.read_sas7bdat(
        data_file,
        usecols=['TOTEXP18', 'AGELAST', 'VARSTR', 'VARPSU', 'PERWT18F', 'PANEL']
    )
    
    print(f"Initial observations: {len(df)}")
    
    df = df[df['PERWT18F'] > 0].copy()
    print(f"Observations with positive weights: {len(df)}")
    
    print("\nVARPSU (Primary Sampling Units) Analysis:")
    print(f"VARPSU unique values: {df['VARPSU'].nunique()}")
    print(f"VARPSU value counts:\n{df['VARPSU'].value_counts().head(10)}")
    print(f"VARPSU range: {df['VARPSU'].min()} to {df['VARPSU'].max()}")
    
    print("\nVARSTR (Strata) Analysis:")
    print(f"VARSTR unique values: {df['VARSTR'].nunique()}")
    print(f"VARSTR range: {df['VARSTR'].min()} to {df['VARSTR'].max()}")
    print(f"VARSTR value counts (first 10):\n{df['VARSTR'].value_counts().head(10)}")
    
    print("\nPERWT18F (Weights) Analysis:")
    print(f"Weight range: {df['PERWT18F'].min()} to {df['PERWT18F'].max()}")
    print(f"Weight mean: {df['PERWT18F'].mean():.2f}")
    print(f"Weight std: {df['PERWT18F'].std():.2f}")
    
    print("\nTOTEXP18 (Total Expenses) Analysis:")
    print(f"Expense range: {df['TOTEXP18'].min()} to {df['TOTEXP18'].max()}")
    print(f"Expense mean: {df['TOTEXP18'].mean():.2f}")
    print(f"People with expenses: {(df['TOTEXP18'] > 0).sum()}")
    print(f"People without expenses: {(df['TOTEXP18'] == 0).sum()}")
    
    print("\nMissing values check:")
    for col in ['TOTEXP18', 'AGELAST', 'VARSTR', 'VARPSU', 'PERWT18F']:
        missing = df[col].isna().sum()
        print(f"{col}: {missing} missing values")
    
    try:
        from samplics.estimation import TaylorEstimator
        from samplics.utils.types import PopParam
        print("\nSamplics import successful")
        
        taylor_est = TaylorEstimator(PopParam.mean)
        print("TaylorEstimator created successfully")
        
        has_expense = (df['TOTEXP18'] > 0).astype(int)
        
        print("\nTesting samplics with small subset...")
        subset = df.head(1000).copy()
        
        result = taylor_est.estimate(
            y=subset['TOTEXP18'].values,
            samp_weight=subset['PERWT18F'].values,
            stratum=subset['VARSTR'].values,
            psu=subset['VARPSU'].values
        )
        
        if result is None:
            print("ERROR: TaylorEstimator returned None even with subset")
        else:
            print(f"SUCCESS: TaylorEstimator returned result: {result.point_est}")
            
    except Exception as e:
        print(f"ERROR with samplics: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
