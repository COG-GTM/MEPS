"""EM1: Health status and weekly earnings regression, 2002.

Regression analysis of weekly earnings on health status and demographics.

Input file: C:/MEPS/h70.ssp (2002 Full-year consolidated)

Ported from: SAS/older_exercises_1996_to_2006/Employment_examples/EM1/EM1.sas
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean
from meps.survey.regression import survey_glm


def main(data_dir: str = "C:/MEPS") -> None:
    fyc02 = read_meps(year=2002, file_type="FYC", data_dir=data_dir)

    # Create variables for regression
    fyc02 = fyc02.with_columns([
        pl.col("RTHLTH53").cast(pl.Utf8).alias("health_status"),
        pl.col("SEX").cast(pl.Utf8).alias("SEX_f"),
        pl.col("RACETHX").cast(pl.Utf8).alias("RACETHX_f"),
        # Employed indicator
        (pl.col("EMPST53") == 1).cast(pl.Int32).alias("employed"),
    ])

    # Subset to employed adults with positive earnings
    wage_col = "WAGEP" + "53X" if "WAGEP53X" in fyc02.columns else "TTLP02X"
    if wage_col not in fyc02.columns:
        for c in fyc02.columns:
            if "WAGE" in c or "TTLP" in c:
                wage_col = c
                break

    dsgn = MEPSSurveyDesign(
        data=fyc02, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT02F", nest=True,
    )

    sub = dsgn.subset((pl.col("employed") == 1) & (pl.col("AGELAST") >= 18))

    # Mean health status
    print("=== Mean Health Status among Employed Adults ===")
    for est in survey_mean(sub, ["RTHLTH53"]):
        print(f"  {est.variable}: {est.estimate:.4f} (SE: {est.se:.4f})")

    # Regression: earnings ~ health + demographics
    print("\n=== Regression: Earnings ~ Health + Demographics ===")
    if wage_col in fyc02.columns:
        formula = f"{wage_col} ~ AGELAST + C(SEX_f) + C(RACETHX_f) + C(health_status)"
        result = survey_glm(formula, sub, family="gaussian")
        print(result.summary())


if __name__ == "__main__":
    main()
