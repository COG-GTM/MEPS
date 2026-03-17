"""Exercise 3c: Pooling MEPS data across CAPI redesign, 2017-2018.

Pooling with discontinuity handling:
 - Pool 2017 and 2018 FYC files
 - Handle JTPAIN variable name change (JTPAIN31 vs JTPAIN31_M18)
 - Create combined joint pain/arthritis indicator
 - Percentage with joint pain and average expenditures by pain status

Input files:
 - C:/MEPS/h209.dta (2018 Full-year file)
 - C:/MEPS/h201.dta (2017 Full-year file)

Ported from: R/workshop_exercises/exercise_3c.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_by, survey_mean


def main(data_dir: str = "C:/MEPS") -> None:
    fyc18 = read_meps(year=2018, file_type="FYC", data_dir=data_dir)
    fyc17 = read_meps(year=2017, file_type="FYC", data_dir=data_dir)

    # Create joint pain indicator - handle variable name change
    fyc18x = fyc18.with_columns(
        pl.when((pl.col("JTPAIN31_M18") == 1) | (pl.col("ARTHDX") == 1)).then(pl.lit("1 Yes"))
        .when((pl.col("JTPAIN31_M18") < 0) & (pl.col("ARTHDX") < 0)).then(pl.lit("Missing"))
        .otherwise(pl.lit("2 No"))
        .alias("any_jtpain")
    )

    fyc17x = fyc17.with_columns(
        pl.when((pl.col("JTPAIN31") == 1) | (pl.col("ARTHDX") == 1)).then(pl.lit("1 Yes"))
        .when((pl.col("JTPAIN31") < 0) & (pl.col("ARTHDX") < 0)).then(pl.lit("Missing"))
        .otherwise(pl.lit("2 No"))
        .alias("any_jtpain")
    )

    # Rename year-specific variables and select
    fyc18p = fyc18x.select([
        "DUPERSID", "VARSTR", "VARPSU", "AGELAST", "any_jtpain",
        pl.col("PERWT18F").alias("perwt"),
        pl.col("TOTSLF18").alias("totslf"),
        pl.col("TOTEXP18").alias("totexp"),
    ])

    fyc17p = fyc17x.select([
        "DUPERSID", "VARSTR", "VARPSU", "AGELAST", "any_jtpain",
        pl.col("PERWT17F").alias("perwt"),
        pl.col("TOTSLF17").alias("totslf"),
        pl.col("TOTEXP17").alias("totexp"),
    ])

    # Stack and create pooled weight
    pool = pl.concat([fyc18p, fyc17p]).with_columns([
        (pl.col("perwt") / 2).alias("poolwt"),
        ((pl.col("AGELAST") >= 18) & (pl.col("any_jtpain") != "Missing")).cast(pl.Int32).alias("subpop"),
    ])

    # Define survey design
    dsgn = MEPSSurveyDesign(
        data=pool, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="poolwt", nest=True,
    )
    sub_dsgn = dsgn.subset(pl.col("subpop") == 1)

    # Percent with any joint pain
    print("=== Percent with joint pain ===")
    for est in survey_mean(sub_dsgn, ["any_jtpain"]):
        print(f"  {est.variable}: {est.estimate:.4f} (SE: {est.se:.4f})")

    # Average expenditures by joint pain status
    print("\n=== Average expenditures by joint pain status ===")
    results = survey_by(sub_dsgn, ["totslf", "totexp"], by=["any_jtpain"], fun="mean")
    for est in results:
        print(f"  {est.by_value} | {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
