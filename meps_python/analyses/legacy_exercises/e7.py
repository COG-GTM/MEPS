"""E7: Colonoscopy screening estimates, 2005.

Percentage of adults age 50+ who had a colonoscopy in the past 10 years.

Input file: C:/MEPS/h97.ssp (2005 Full-year consolidated)

Ported from: SAS/older_exercises_1996_to_2006/Estimation_examples/E7/E7.sas
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean, survey_total


def main(data_dir: str = "C:/MEPS") -> None:
    fyc05 = read_meps(year=2005, file_type="FYC", data_dir=data_dir)

    # Create colonoscopy indicator
    fyc05 = fyc05.with_columns([
        (pl.col("AGELAST") >= 50).cast(pl.Int32).alias("age50plus"),
    ])

    # Check for colonoscopy variable (CLNTST53 or similar)
    colon_var = None
    for v in ["CLNTST53", "COLONOS53", "COLNOS53"]:
        if v in fyc05.columns:
            colon_var = v
            break

    if colon_var is None:
        print("Colonoscopy variable not found in 2005 FYC file.")
        return

    fyc05 = fyc05.with_columns(
        (pl.col(colon_var) == 1).cast(pl.Int32).alias("had_colonoscopy")
    )

    dsgn = MEPSSurveyDesign(
        data=fyc05, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT05F", nest=True,
    )
    sub = dsgn.subset(pl.col("age50plus") == 1)

    print("=== Colonoscopy Screening, Adults 50+, 2005 ===")
    for est in survey_mean(sub, ["had_colonoscopy"]):
        print(f"  Percent: {est.estimate:.4f} (SE: {est.se:.4f})")
    for est in survey_total(sub, ["had_colonoscopy"]):
        print(f"  Number: {est.estimate:,.0f} (SE: {est.se:,.0f})")


if __name__ == "__main__":
    main()
