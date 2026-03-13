"""Exercise 3d: Pooling across CAPI redesign with variance linkage, 2017-2019.

Pooling with Pooled Variance Linkage file:
 - Pool 2017, 2018, and 2019 FYC files
 - Use h36u19 linkage file for correct variance estimation
 - Uses PSU9619/STRA9619 instead of VARPSU/VARSTR

Input files:
 - C:/MEPS/h216.dta (2019 Full-year file)
 - C:/MEPS/h209.dta (2018 Full-year file)
 - C:/MEPS/h201.dta (2017 Full-year file)
 - C:/MEPS/h36u19.dta (Pooled Variance Linkage file)

Ported from: R/workshop_exercises/exercise_3d.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_by, survey_mean


def main(data_dir: str = "C:/MEPS") -> None:
    fyc19 = read_meps(year=2019, file_type="FYC", data_dir=data_dir)
    fyc18 = read_meps(year=2018, file_type="FYC", data_dir=data_dir)
    fyc17 = read_meps(year=2017, file_type="FYC", data_dir=data_dir)
    linkage = read_meps(file_type="Pooled linkage", data_dir=data_dir)

    # Create joint pain indicators
    fyc19x = fyc19.with_columns(
        pl.when((pl.col("JTPAIN31_M18") == 1) | (pl.col("ARTHDX") == 1)).then(pl.lit("1 Yes"))
        .when((pl.col("JTPAIN31_M18") < 0) & (pl.col("ARTHDX") < 0)).then(pl.lit("Missing"))
        .otherwise(pl.lit("2 No"))
        .alias("any_jtpain")
    )

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

    # Rename and select
    fyc19p = fyc19x.select([
        "DUPERSID", "PANEL", "VARSTR", "VARPSU", "AGELAST", "ARTHDX", "any_jtpain",
        pl.col("PERWT19F").alias("perwt"),
        pl.col("TOTSLF19").alias("totslf"),
        pl.col("TOTEXP19").alias("totexp"),
    ])
    fyc18p = fyc18x.select([
        "DUPERSID", "PANEL", "VARSTR", "VARPSU", "AGELAST", "ARTHDX", "any_jtpain",
        pl.col("PERWT18F").alias("perwt"),
        pl.col("TOTSLF18").alias("totslf"),
        pl.col("TOTEXP18").alias("totexp"),
    ])
    fyc17p = fyc17x.select([
        "DUPERSID", "PANEL", "VARSTR", "VARPSU", "AGELAST", "ARTHDX", "any_jtpain",
        pl.col("PERWT17F").alias("perwt"),
        pl.col("TOTSLF17").alias("totslf"),
        pl.col("TOTEXP17").alias("totexp"),
    ])

    # Stack and define pooled weight
    pool = pl.concat([fyc19p, fyc18p, fyc17p]).with_columns([
        (pl.col("perwt") / 3).alias("poolwt"),
        ((pl.col("AGELAST") >= 18) & (pl.col("any_jtpain") != "Missing")).cast(pl.Int32).alias("subpop"),
    ])

    # Merge Pooled Variance Linkage file
    linkage_sub = linkage.select(["DUPERSID", "PANEL", "STRA9619", "PSU9619"])
    pool_linked = pool.join(linkage_sub, on=["DUPERSID", "PANEL"], how="left")

    # QC
    print("=== Panel counts ===")
    print(pool_linked.group_by("PANEL").len())

    # Define survey design using linkage PSU/STRATA
    dsgn = MEPSSurveyDesign(
        data=pool_linked, psu_col="PSU9619", strata_col="STRA9619",
        weight_col="poolwt", nest=True,
    )
    sub_dsgn = dsgn.subset(pl.col("subpop") == 1)

    # Percent with any joint pain
    print("\n=== Percent with joint pain ===")
    for est in survey_mean(sub_dsgn, ["any_jtpain"]):
        print(f"  {est.variable}: {est.estimate:.4f} (SE: {est.se:.4f})")

    # Average expenditures by joint pain status
    print("\n=== Average expenditures by joint pain status ===")
    results = survey_by(sub_dsgn, ["totslf", "totexp"], by=["any_jtpain"], fun="mean")
    for est in results:
        print(f"  {est.by_value} | {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
