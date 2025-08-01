#!/usr/bin/env python3
"""
Validation script to programmatically compare Python output with SAS output
for Exercise1c to ensure statistical parity and correctness.

This script captures the Python output and compares key statistics with
the expected SAS output from Exercise1c_OUTPUT.TXT
"""

import subprocess
import sys
import re
from pathlib import Path
import pandas as pd
import numpy as np

def capture_python_output():
    """Run the Python script and capture its output"""
    try:
        result = subprocess.run(
            [sys.executable, "Exercise1c.py"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        if result.returncode != 0:
            print(f"Error running Python script: {result.stderr}")
            return None
        return result.stdout
    except Exception as e:
        print(f"Error capturing Python output: {e}")
        return None

def load_sas_output():
    """Load the expected SAS output file"""
    sas_output_path = Path("../../../SAS/workshop_exercises/exercise_1c/Exercise1c_OUTPUT.TXT")
    try:
        with open(sas_output_path, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading SAS output: {e}")
        return None

def extract_key_statistics(text, source=""):
    """Extract key numerical statistics from output text with improved parsing"""
    stats = {}
    
    strata_match = re.search(r'Number of Strata\s+(\d+)', text)
    if strata_match:
        stats['n_strata'] = int(strata_match.group(1))
    
    clusters_match = re.search(r'Number of Clusters\s+(\d+)', text)
    if clusters_match:
        stats['n_clusters'] = int(clusters_match.group(1))
    
    obs_match = re.search(r'Number of Observations\s+(\d+)', text)
    if obs_match:
        stats['n_observations'] = int(obs_match.group(1))
    
    weight_sum_match = re.search(r'Sum of Weights\s+([\d,]+)', text)
    if weight_sum_match:
        stats['sum_weights'] = int(weight_sum_match.group(1).replace(',', ''))
    
    any_expense_stats = re.search(r'Any Expense\s+(\d+)\s+(0\.\d+)\s+(0\.\d+)\s+(\d+)\s+(\d+)', text)
    if any_expense_stats:
        stats['any_expense_n'] = int(any_expense_stats.group(1))
        stats['any_expense_mean'] = float(any_expense_stats.group(2))
        stats['any_expense_sum'] = int(any_expense_stats.group(4))
    
    no_expense_stats = re.search(r'No Expense\s+(\d+)\s+(0\.\d+)\s+(0\.\d+)\s+(\d+)\s+(\d+)', text)
    if no_expense_stats:
        stats['no_expense_n'] = int(no_expense_stats.group(1))
        stats['no_expense_mean'] = float(no_expense_stats.group(2))
        stats['no_expense_sum'] = int(no_expense_stats.group(4))
    
    freq_any_expense = re.search(r'Any Expense\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)', text)
    if freq_any_expense:
        stats['any_expense_freq'] = int(freq_any_expense.group(1))
        stats['any_expense_weighted_freq'] = int(freq_any_expense.group(2))
        stats['any_expense_percent'] = float(freq_any_expense.group(4))
    
    overall_pattern = r'TOTEXP18\s+TOTAL HEALTH CARE EXP 18\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.E+]+)'
    overall_match = re.search(overall_pattern, text)
    if overall_match:
        stats['overall_n'] = int(overall_match.group(1))
        stats['overall_mean'] = float(overall_match.group(2))
        stats['overall_sum'] = float(overall_match.group(4))
    
    overall_median = re.search(r'TOTEXP18\s+TOTAL HEALTH CARE EXP 18\s+50 Median\s+([\d.]+)', text)
    if overall_median:
        stats['overall_median'] = float(overall_median.group(1))
    
    domain_pattern = r'Any Expense\s+TOTEXP18\s+TOTAL HEALTH CARE EXP 18\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.E+]+)'
    domain_match = re.search(domain_pattern, text)
    if domain_match:
        stats['domain_any_expense_n'] = int(domain_match.group(1))
        stats['domain_any_expense_mean'] = float(domain_match.group(2))
        stats['domain_any_expense_sum'] = float(domain_match.group(4))
    
    domain_median = re.search(r'Any Expense\s+TOTEXP18\s+TOTAL HEALTH CARE EXP 18\s+50 Median\s+([\d.]+)', text)
    if domain_median:
        stats['domain_any_expense_median'] = float(domain_median.group(1))
    
    age_0_64_pattern = r'Any Expense\s+0-64\s+TOTEXP18\s+TOTAL HEALTH CARE EXP 18\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.E+]+)'
    age_0_64_match = re.search(age_0_64_pattern, text)
    if age_0_64_match:
        stats['age_0_64_n'] = int(age_0_64_match.group(1))
        stats['age_0_64_mean'] = float(age_0_64_match.group(2))
        stats['age_0_64_sum'] = float(age_0_64_match.group(4))
    
    age_65_plus_pattern = r'Any Expense\s+65\+\s+TOTEXP18\s+TOTAL HEALTH CARE EXP 18\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.E+]+)'
    age_65_plus_match = re.search(age_65_plus_pattern, text)
    if age_65_plus_match:
        stats['age_65_plus_n'] = int(age_65_plus_match.group(1))
        stats['age_65_plus_mean'] = float(age_65_plus_match.group(2))
        stats['age_65_plus_sum'] = float(age_65_plus_match.group(4))
    
    age_0_64_median = re.search(r'Any Expense\s+0-64\s+TOTEXP18\s+TOTAL HEALTH CARE EXP 18\s+50 Median\s+([\d.]+)', text)
    if age_0_64_median:
        stats['age_0_64_median'] = float(age_0_64_median.group(1))
    
    age_65_plus_median = re.search(r'Any Expense\s+65\+\s+TOTEXP18\s+TOTAL HEALTH CARE EXP 18\s+50 Median\s+([\d.]+)', text)
    if age_65_plus_median:
        stats['age_65_plus_median'] = float(age_65_plus_median.group(1))
    
    print(f"\n{source} Statistics extracted:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    return stats

def compare_statistics(python_stats, sas_stats, tolerance=0.01):
    """Compare Python and SAS statistics with specified tolerance"""
    print("\n" + "="*80)
    print("STATISTICAL COMPARISON RESULTS")
    print("="*80)
    
    all_keys = set(python_stats.keys()) | set(sas_stats.keys())
    matches = 0
    total_comparisons = 0
    mismatches = []
    
    for key in sorted(all_keys):
        if key in python_stats and key in sas_stats:
            python_val = python_stats[key]
            sas_val = sas_stats[key]
            
            if isinstance(python_val, int) and isinstance(sas_val, int):
                match = python_val == sas_val
                diff = abs(python_val - sas_val)
                rel_diff = diff / max(abs(sas_val), 1) if sas_val != 0 else diff
            else:
                diff = abs(python_val - sas_val)
                rel_diff = diff / max(abs(sas_val), 1) if sas_val != 0 else diff
                match = rel_diff <= tolerance
            
            status = "✅ MATCH" if match else "❌ MISMATCH"
            print(f"{key:25} | Python: {python_val:>15} | SAS: {sas_val:>15} | Diff: {diff:>10.6f} | {status}")
            
            if match:
                matches += 1
            else:
                mismatches.append((key, python_val, sas_val, diff, rel_diff))
            
            total_comparisons += 1
        elif key in python_stats:
            print(f"{key:25} | Python: {python_stats[key]:>15} | SAS: {'N/A':>15} | ❌ MISSING IN SAS")
        else:
            print(f"{key:25} | Python: {'N/A':>15} | SAS: {sas_stats[key]:>15} | ❌ MISSING IN PYTHON")
    
    print("\n" + "="*80)
    print(f"SUMMARY: {matches}/{total_comparisons} statistics match within tolerance ({tolerance*100}%)")
    
    if mismatches:
        print(f"\n❌ MISMATCHES FOUND ({len(mismatches)}):")
        for key, py_val, sas_val, diff, rel_diff in mismatches:
            print(f"  {key}: Python={py_val}, SAS={sas_val}, Diff={diff:.6f}, RelDiff={rel_diff:.6f}")
        return False
    else:
        print("\n✅ ALL STATISTICS MATCH! Python output is statistically equivalent to SAS output.")
        return True

def validate_output_structure(python_output, sas_output):
    """Validate that the output structure matches"""
    print("\n" + "="*80)
    print("OUTPUT STRUCTURE VALIDATION")
    print("="*80)
    
    required_sections = [
        "Method 1",
        "Method 2", 
        "Method 3",
        "Data Summary",
        "Statistics",
        "Quantiles"
    ]
    
    structure_valid = True
    for section in required_sections:
        python_has = section in python_output
        sas_has = section in sas_output
        
        if python_has and sas_has:
            print(f"✅ {section}: Present in both outputs")
        elif python_has:
            print(f"❌ {section}: Present in Python but missing in SAS")
            structure_valid = False
        elif sas_has:
            print(f"❌ {section}: Present in SAS but missing in Python")
            structure_valid = False
        else:
            print(f"❌ {section}: Missing in both outputs")
            structure_valid = False
    
    return structure_valid

def main():
    """Main validation function"""
    print("MEPS Exercise1c Output Validation")
    print("="*80)
    print("Comparing Python output with SAS reference output...")
    
    print("\n1. Capturing Python script output...")
    python_output = capture_python_output()
    if not python_output:
        print("❌ Failed to capture Python output")
        return False
    
    print("2. Loading SAS reference output...")
    sas_output = load_sas_output()
    if not sas_output:
        print("❌ Failed to load SAS output")
        return False
    
    print("3. Validating output structure...")
    structure_valid = validate_output_structure(python_output, sas_output)
    
    print("4. Extracting key statistics...")
    python_stats = extract_key_statistics(python_output, "PYTHON")
    sas_stats = extract_key_statistics(sas_output, "SAS")
    
    print("5. Comparing statistics...")
    stats_match = compare_statistics(python_stats, sas_stats, tolerance=0.001)  # 0.1% tolerance
    
    print("\n" + "="*80)
    print("FINAL VALIDATION RESULT")
    print("="*80)
    
    if structure_valid and stats_match:
        print("✅ VALIDATION PASSED: Python output matches SAS output!")
        print("   - Output structure is correct")
        print("   - All key statistics match within tolerance")
        print("   - Migration from SAS to Python was successful")
        return True
    else:
        print("❌ VALIDATION FAILED:")
        if not structure_valid:
            print("   - Output structure issues found")
        if not stats_match:
            print("   - Statistical differences exceed tolerance")
        print("   - Review and fix the Python implementation")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
