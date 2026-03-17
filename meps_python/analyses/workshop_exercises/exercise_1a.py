"""Exercise 1a: National health care expenses, 2018.

Basic survey means and totals with subpopulation:
 - Overall expenses (National totals, per-person averages)
 - Expenses for mutual exclusive subgroups (Persons with Expense, Persons without)

Input file: C:/MEPS/h209.dta (2018 Full-year file)

Ported from: R/workshop_exercises/exercise_1a.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean, survey_total


def main(data_dir: str = "C:/MEPS") -> None:
    fyc18 = read_meps(year=2018, file_type="FYC", data_dir=data_dir)

    # Create subpopulation indicators
    fyc18 = fyc18.with_columns([
        (pl.col("TOTEXP18") > 0).cast(pl.Int32).alias("has_exp"),
    ])

    # Define survey design
    dsgn = MEPSSurveyDesign(
        data=fyc18, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT18F", nest=True,
    )

    # Overall expenses: National totals
    print("=== National Totals ===")
    for est in survey_total(dsgn, ["TOTEXP18"]):
        print(f"  {est.variable}: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    # Overall expenses: Per-person averages
    print("\n=== Per-person Averages (Overall) ===")
    for est in survey_mean(dsgn, ["TOTEXP18"]):
        print(f"  {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")

    # Persons with expense
    print("\n=== Per-person Averages (With Expense) ===")
    sub_dsgn = dsgn.subset(pl.col("has_exp") == 1)
    for est in survey_mean(sub_dsgn, ["TOTEXP18"]):
        print(f"  {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")

    # Number of persons with/without expense
    print("\n=== Number of Persons ===")
    for est in survey_total(dsgn, ["has_exp"]):
        print(f"  With expense: {est.estimate:,.0f} (SE: {est.se:,.0f})")


if __name__ == "__main__":
    main()
