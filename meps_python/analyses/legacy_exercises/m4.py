"""M4: Subpopulation analysis demonstration, 2001.

Demonstrates correct vs incorrect subpopulation analysis.

Input file: C:/MEPS/h60.ssp (2001 Full-year consolidated)

Ported from: SAS/older_exercises_1996_to_2006/Misc_examples/M4/M4.sas
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean


def main(data_dir: str = "C:/MEPS") -> None:
    fyc01 = read_meps(year=2001, file_type="FYC", data_dir=data_dir)

    fyc01 = fyc01.with_columns(
        (pl.col("AGELAST") >= 65).cast(pl.Int32).alias("elderly")
    )

    # CORRECT: Use domain/subset on full design
    dsgn = MEPSSurveyDesign(
        data=fyc01, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT01F", nest=True,
    )
    sub = dsgn.subset(pl.col("elderly") == 1)

    print("=== CORRECT: Subpopulation via domain (elderly 65+) ===")
    for est in survey_mean(sub, ["TOTEXP01"]):
        print(f"  Mean: {est.estimate:,.2f} (SE: {est.se:,.2f})")

    # INCORRECT: Filter data before survey design
    filtered = fyc01.filter(pl.col("elderly") == 1)
    dsgn_wrong = MEPSSurveyDesign(
        data=filtered, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT01F", nest=True,
    )

    print("\n=== INCORRECT: Filtered before design (elderly 65+) ===")
    for est in survey_mean(dsgn_wrong, ["TOTEXP01"]):
        print(f"  Mean: {est.estimate:,.2f} (SE: {est.se:,.2f})")

    print("\nNote: SEs differ because filtering removes PSUs/strata,")
    print("which distorts the variance estimation.")


if __name__ == "__main__":
    main()
