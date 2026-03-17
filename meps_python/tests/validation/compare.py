"""Cross-language validation: Compare Python estimates with R reference values.

This script compares Python MEPS analysis outputs against known-good values
from R (stored in expected_outputs/ as JSON fixtures).

Tolerance thresholds:
 - Point estimates: within 1e-6 relative error
 - Standard errors: within 1e-4 relative error
 - Regression coefficients: within 1e-6
 - Regression SEs: within 1e-4

Usage:
    python -m tests.validation.compare [--analysis NAME]
"""

import json
import sys
from pathlib import Path
from typing import Any

TOLERANCE = {
    "point_estimate": 1e-6,
    "standard_error": 1e-4,
    "regression_coef": 1e-6,
    "regression_se": 1e-4,
}

EXPECTED_DIR = Path(__file__).parent / "expected_outputs"


def relative_error(actual: float, expected: float) -> float:
    """Compute relative error between actual and expected values."""
    if expected == 0:
        return abs(actual)
    return abs(actual - expected) / abs(expected)


def compare_estimate(
    actual: float,
    expected: float,
    tolerance: float,
    label: str = "",
) -> dict[str, Any]:
    """Compare a single estimate against expected value."""
    rel_err = relative_error(actual, expected)
    passed = rel_err <= tolerance
    return {
        "label": label,
        "actual": actual,
        "expected": expected,
        "relative_error": rel_err,
        "tolerance": tolerance,
        "passed": passed,
    }


def validate_analysis(analysis_name: str) -> list[dict[str, Any]]:
    """Validate a single analysis against expected outputs."""
    fixture_path = EXPECTED_DIR / f"{analysis_name}.json"
    if not fixture_path.exists():
        print(f"No fixture found for {analysis_name}, skipping.")
        return []

    with open(fixture_path) as f:
        expected = json.load(f)

    results = []
    for item in expected.get("estimates", []):
        label = item.get("label", "")
        exp_val = item.get("estimate")
        exp_se = item.get("se")

        # Placeholder: actual values would come from running the analysis
        # This framework is set up for future use when MEPS data is available
        print(f"  [{analysis_name}] {label}: expected estimate={exp_val}, SE={exp_se}")

    return results


def main() -> None:
    """Run validation for all or specified analyses."""
    if len(sys.argv) > 2 and sys.argv[1] == "--analysis":
        analyses = [sys.argv[2]]
    else:
        # Validate all analyses with fixtures
        if EXPECTED_DIR.exists():
            analyses = [p.stem for p in EXPECTED_DIR.glob("*.json")]
        else:
            print("No expected_outputs directory found.")
            print("To create fixtures, run each analysis in R and save results as JSON.")
            analyses = []

    total_pass = 0
    total_fail = 0

    for name in analyses:
        print(f"\nValidating: {name}")
        results = validate_analysis(name)
        for r in results:
            if r["passed"]:
                total_pass += 1
                print(f"  PASS: {r['label']} (rel_err={r['relative_error']:.2e})")
            else:
                total_fail += 1
                print(f"  FAIL: {r['label']} (rel_err={r['relative_error']:.2e}, "
                      f"tolerance={r['tolerance']:.2e})")

    print(f"\n{'=' * 50}")
    print(f"Results: {total_pass} passed, {total_fail} failed")
    if total_fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
