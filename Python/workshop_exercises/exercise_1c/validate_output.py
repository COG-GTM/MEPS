#!/usr/bin/env python3
"""
Validation script to compare Python Exercise1c results with expected SAS output
Ensures Python output matches SAS output within 0.1% tolerance
"""

import json
import sys
from pathlib import Path

def validate_results():
    """
    Compare Python results with expected SAS output values
    Expected values from Exercise1c_OUTPUT.TXT:
    - 86.6703% with any expense (line 107)
    - $6,995.631273 mean expense for those with expenses (line 155)
    - $1,401.335930 median expense (0-64 years) (line 190)
    - $5,877.252297 median expense (65+ years) (line 192)
    """
    
    print("VALIDATION SCRIPT - Comparing Python vs SAS Results")
    print("=" * 60)
    
    results_file = Path(__file__).parent / "python_results.json"
    
    if not results_file.exists():
        print("ERROR: python_results.json not found. Run Exercise1c.py first.")
        return False
    
    with open(results_file, 'r') as f:
        python_results = json.load(f)
    
    expected_sas_values = {
        'pct_with_expense': 86.6703,  # Line 107
        'mean_expense_with_expense': 6995.631273,  # Line 155
        'median_expense_0_64': 1401.335930,  # Line 190
        'median_expense_65plus': 5877.252297,  # Line 192
    }
    
    tolerance_pct = 0.001  # 0.1%
    
    print("Comparing key statistics:")
    print("-" * 60)
    
    all_passed = True
    
    for key, expected_val in expected_sas_values.items():
        if key in python_results:
            actual_val = python_results[key]
            diff = abs(actual_val - expected_val)
            tolerance = abs(expected_val * tolerance_pct)
            pct_diff = (diff / abs(expected_val)) * 100 if expected_val != 0 else 0
            
            status = "PASS" if diff <= tolerance else "FAIL"
            if status == "FAIL":
                all_passed = False
            
            print(f"{key}:")
            print(f"  Expected (SAS): {expected_val}")
            print(f"  Actual (Python): {actual_val}")
            print(f"  Difference: {diff:.6f}")
            print(f"  Percent Difference: {pct_diff:.4f}%")
            print(f"  Tolerance: {tolerance:.6f}")
            print(f"  Status: {status}")
            print()
        else:
            print(f"ERROR: {key} not found in Python results")
            all_passed = False
    
    print("Additional validation checks:")
    print("-" * 60)
    
    if 'freq_with_expense' in python_results:
        freq_with = python_results['freq_with_expense']
        expected_freq_with = 25200  # From SAS output
        if freq_with == expected_freq_with:
            print(f"Frequency with expense: {freq_with} (PASS)")
        else:
            print(f"Frequency with expense: {freq_with}, expected {expected_freq_with} (FAIL)")
            all_passed = False
    
    if 'freq_without_expense' in python_results:
        freq_without = python_results['freq_without_expense']
        expected_freq_without = 4215  # From SAS output
        if freq_without == expected_freq_without:
            print(f"Frequency without expense: {freq_without} (PASS)")
        else:
            print(f"Frequency without expense: {freq_without}, expected {expected_freq_without} (FAIL)")
            all_passed = False
    
    if 'weighted_freq_with_expense' in python_results:
        weighted_freq = python_results['weighted_freq_with_expense']
        expected_weighted = 282829352  # From SAS output line 107
        diff = abs(weighted_freq - expected_weighted)
        tolerance = expected_weighted * 0.001  # 0.1% tolerance
        
        status = "PASS" if diff <= tolerance else "FAIL"
        if status == "FAIL":
            all_passed = False
        
        print(f"Weighted frequency with expense: {weighted_freq:,.0f}")
        print(f"  Expected: {expected_weighted:,.0f}")
        print(f"  Status: {status}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("VALIDATION RESULT: ALL TESTS PASSED ✓")
        print("Python results match SAS output within 0.1% tolerance")
    else:
        print("VALIDATION RESULT: SOME TESTS FAILED ✗")
        print("Python results do not match SAS output within tolerance")
    
    print("=" * 60)
    return all_passed

if __name__ == "__main__":
    success = validate_results()
    sys.exit(0 if success else 1)
