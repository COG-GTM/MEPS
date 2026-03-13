"""Exercise 1c: National health care expenses by age group, 2018.

Variant of exercise 1b (from SAS), demonstrating survey-weighted frequencies
and means by age group and expense category.

Input file: C:/MEPS/h209.dta (2018 Full-year file)

Ported from: SAS/workshop_exercises/exercise_1c
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_by


def main(data_dir: str = "C:/MEPS") -> None:
    fyc18 = read_meps(year=2018, file_type="FYC", data_dir=data_dir)

    # Create age groups
    fyc18 = fyc18.with_columns(
        pl.when(pl.col("AGELAST") < 18).then(pl.lit("Under 18"))
        .when(pl.col("AGELAST") <= 64).then(pl.lit("18-64"))
        .otherwise(pl.lit("65+"))
        .alias("agegrps")
    )

    # Create expense categories
    fyc18 = fyc18.with_columns(
        pl.when(pl.col("TOTEXP18") == 0).then(pl.lit("No expense"))
        .when(pl.col("TOTEXP18") < 500).then(pl.lit("$1-$499"))
        .when(pl.col("TOTEXP18") < 2000).then(pl.lit("$500-$1,999"))
        .when(pl.col("TOTEXP18") < 5000).then(pl.lit("$2,000-$4,999"))
        .otherwise(pl.lit("$5,000+"))
        .alias("expense_cat")
    )

    # Define survey design
    dsgn = MEPSSurveyDesign(
        data=fyc18, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT18F", nest=True,
    )

    # Frequency distribution of expense categories
    print("=== Expense Category Distribution ===")
    for est in survey_by(dsgn, ["expense_cat"], by=["agegrps"], fun="mean"):
        print(f"  {est.by_value} | {est.variable}: {est.estimate:.4f} (SE: {est.se:.4f})")

    # Mean expense by age group
    print("\n=== Mean Expenditure by Age Group ===")
    for est in survey_by(dsgn, ["TOTEXP18"], by=["agegrps"], fun="mean"):
        print(f"  {est.by_value}: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
