"""M8: Person weight trimming demonstration, 2001.

Demonstrates the effect of weight trimming on estimates.

Input file: C:/MEPS/h60.ssp (2001 Full-year consolidated)

Ported from: SAS/older_exercises_1996_to_2006/Misc_examples/M8/M8.sas
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean


def main(data_dir: str = "C:/MEPS") -> None:
    fyc01 = read_meps(year=2001, file_type="FYC", data_dir=data_dir)

    # Original weight statistics
    wt = fyc01["PERWT01F"]
    print("=== Original Weight Distribution ===")
    print(f"  N: {len(wt)}")
    print(f"  Mean: {wt.mean():,.2f}")
    print(f"  Min: {wt.min():,.2f}")
    print(f"  Max: {wt.max():,.2f}")
    print(f"  Sum: {wt.sum():,.0f}")

    # Original estimate
    dsgn = MEPSSurveyDesign(
        data=fyc01, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT01F", nest=True,
    )

    print("\n=== Original Estimate ===")
    for est in survey_mean(dsgn, ["TOTEXP01"]):
        print(f"  Mean: {est.estimate:,.2f} (SE: {est.se:,.2f})")

    # Trimmed weights (cap at 99th percentile)
    p99 = wt.quantile(0.99)
    fyc01 = fyc01.with_columns(
        pl.when(pl.col("PERWT01F") > p99)
        .then(p99)
        .otherwise(pl.col("PERWT01F"))
        .alias("TRIMWT")
    )

    dsgn_trim = MEPSSurveyDesign(
        data=fyc01, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="TRIMWT", nest=True,
    )

    print(f"\n=== Trimmed Estimate (capped at p99={p99:,.2f}) ===")
    for est in survey_mean(dsgn_trim, ["TOTEXP01"]):
        print(f"  Mean: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
