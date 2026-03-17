"""EM2: Job change analysis, 2002.

Analysis of job changes and insurance coverage transitions.

Input file: C:/MEPS/h70.ssp (2002 Full-year consolidated)

Ported from: SAS/older_exercises_1996_to_2006/Employment_examples/EM2/EM2.sas
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_by, survey_mean, survey_total


def main(data_dir: str = "C:/MEPS") -> None:
    fyc02 = read_meps(year=2002, file_type="FYC", data_dir=data_dir)

    # Employment status transitions
    fyc02 = fyc02.with_columns([
        pl.col("EMPST31").cast(pl.Utf8).alias("emp_rd3"),
        pl.col("EMPST53").cast(pl.Utf8).alias("emp_rd5"),
        # Job change indicator
        (pl.col("EMPST31") != pl.col("EMPST53")).cast(pl.Int32).alias("job_change"),
    ])

    dsgn = MEPSSurveyDesign(
        data=fyc02, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT02F", nest=True,
    )

    # Adults 18-64
    sub = dsgn.subset((pl.col("AGELAST") >= 18) & (pl.col("AGELAST") <= 64))

    print("=== Job Change Analysis, Adults 18-64, 2002 ===")
    for est in survey_mean(sub, ["job_change"]):
        print(f"  Percent with job change: {est.estimate:.4f} (SE: {est.se:.4f})")
    for est in survey_total(sub, ["job_change"]):
        print(f"  Number with job change: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    print("\n=== Employment Status Distribution ===")
    for est in survey_by(sub, ["emp_rd5"], by=["emp_rd3"], fun="mean"):
        print(f"  Rd3={est.by_value} | {est.variable}: {est.estimate:.4f} (SE: {est.se:.4f})")


if __name__ == "__main__":
    main()
