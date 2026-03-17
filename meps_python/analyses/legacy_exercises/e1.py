"""E1: Person-level estimates for healthcare expenditures, 2001.

National totals and per-person averages for total healthcare expenditures.

Input file: C:/MEPS/h60.ssp (2001 Full-year consolidated)

Ported from: SAS/older_exercises_1996_to_2006/Estimation_examples/E1/E1.sas
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean, survey_total


def main(data_dir: str = "C:/MEPS") -> None:
    fyc01 = read_meps(year=2001, file_type="FYC", data_dir=data_dir)

    # Create expense indicator
    fyc01 = fyc01.with_columns(
        (pl.col("TOTEXP01") > 0).cast(pl.Int32).alias("has_exp")
    )

    dsgn = MEPSSurveyDesign(
        data=fyc01, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT01F", nest=True,
    )

    # National totals
    print("=== National Total Expenditures, 2001 ===")
    for est in survey_total(dsgn, ["TOTEXP01"]):
        print(f"  {est.variable}: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    # Per-person averages
    print("\n=== Per-person Average Expenditure ===")
    for est in survey_mean(dsgn, ["TOTEXP01"]):
        print(f"  {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")

    # Among persons with expense
    print("\n=== Per-person Average (With Expense) ===")
    sub = dsgn.subset(pl.col("has_exp") == 1)
    for est in survey_mean(sub, ["TOTEXP01"]):
        print(f"  {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
