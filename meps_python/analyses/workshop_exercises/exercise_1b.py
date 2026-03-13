"""Exercise 1b: National health care expenses by age group, 2018.

Survey means, medians, and quantiles by age group:
 - Per-person averages by age group
 - Median expenses by age group
 - Distribution of expenses (25th, 50th, 75th percentiles)

Input file: C:/MEPS/h209.dta (2018 Full-year file)

Ported from: R/workshop_exercises/exercise_1b.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_by, survey_quantile


def main(data_dir: str = "C:/MEPS") -> None:
    fyc18 = read_meps(year=2018, file_type="FYC", data_dir=data_dir)

    # Create age groups
    fyc18 = fyc18.with_columns(
        pl.when(pl.col("AGELAST") < 18).then(pl.lit("Under 18"))
        .when(pl.col("AGELAST") <= 64).then(pl.lit("18-64"))
        .otherwise(pl.lit("65+"))
        .alias("agegrps")
    )

    # Create indicator for persons with expense
    fyc18 = fyc18.with_columns(
        (pl.col("TOTEXP18") > 0).cast(pl.Int32).alias("has_exp")
    )

    # Define survey design
    dsgn = MEPSSurveyDesign(
        data=fyc18, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT18F", nest=True,
    )

    # Per-person averages by age group
    print("=== Mean Expenditure by Age Group ===")
    results = survey_by(dsgn, ["TOTEXP18"], by=["agegrps"], fun="mean")
    for est in results:
        print(f"  {est.by_value}: {est.estimate:,.2f} (SE: {est.se:,.2f})")

    # Among those with expense
    print("\n=== Mean Expenditure by Age Group (With Expense) ===")
    sub_dsgn = dsgn.subset(pl.col("has_exp") == 1)
    results = survey_by(sub_dsgn, ["TOTEXP18"], by=["agegrps"], fun="mean")
    for est in results:
        print(f"  {est.by_value}: {est.estimate:,.2f} (SE: {est.se:,.2f})")

    # Median expenditures by age group (among those with expense)
    print("\n=== Median Expenditure by Age Group (With Expense) ===")
    for age in ["Under 18", "18-64", "65+"]:
        age_dsgn = sub_dsgn.subset(pl.col("agegrps") == age)
        results = survey_quantile(age_dsgn, ["TOTEXP18"], quantiles=[0.50])
        for est in results:
            print(f"  {age}: {est.estimate:,.2f} (SE: {est.se:,.2f})")

    # Distribution of expenses
    print("\n=== Expenditure Quantiles (25th, 50th, 75th) ===")
    results = survey_quantile(sub_dsgn, ["TOTEXP18"], quantiles=[0.25, 0.50, 0.75])
    for est in results:
        print(f"  q{est.quantile}: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
