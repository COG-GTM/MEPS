"""Exercise 3a: Pooling MEPS data files, 2015-2016.

Multi-year pooling with weight division:
 - Pool 2015 and 2016 FYC files
 - Subpopulation: age 26-30, uninsured, high income
 - Weighted estimate on out-of-pocket expenses (TOTSLF)

Input files:
 - C:/MEPS/h192.ssp (2016 Full-year file)
 - C:/MEPS/h181.ssp (2015 Full-year file)

Ported from: R/workshop_exercises/exercise_3a.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean


def main(data_dir: str = "C:/MEPS") -> None:
    h192 = read_meps(year=2016, file_type="FYC", data_dir=data_dir)
    h181 = read_meps(year=2015, file_type="FYC", data_dir=data_dir)

    # Rename year-specific variables
    h192x = h192.select([
        "DUPERSID", "VARSTR", "VARPSU", "AGELAST",
        pl.col("INSCOV16").alias("inscov"),
        pl.col("PERWT16F").alias("perwt"),
        pl.col("POVCAT16").alias("povcat"),
        pl.col("TOTSLF16").alias("totslf"),
    ])

    h181x = h181.select([
        "DUPERSID", "VARSTR", "VARPSU", "AGELAST",
        pl.col("INSCOV15").alias("inscov"),
        pl.col("PERWT15F").alias("perwt"),
        pl.col("POVCAT15").alias("povcat"),
        pl.col("TOTSLF15").alias("totslf"),
    ])

    # Stack data and define pooled weight
    pool = pl.concat([h192x, h181x]).with_columns([
        (pl.col("perwt") / 2).alias("poolwt"),
        (
            (pl.col("AGELAST") >= 26) & (pl.col("AGELAST") <= 30) &
            (pl.col("povcat") == 5) & (pl.col("inscov") == 3)
        ).cast(pl.Int32).alias("subpop"),
    ])

    # QC subpop
    print("=== Subpopulation QC ===")
    qc = pool.filter(pl.col("subpop") == 1).group_by(["AGELAST", "povcat", "inscov"]).len()
    print(qc)

    # Define survey design
    dsgn = MEPSSurveyDesign(
        data=pool, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="poolwt", nest=True,
    )

    # Weighted estimate on totslf for subpopulation
    sub_dsgn = dsgn.subset(pl.col("subpop") == 1)

    print("\n=== Weighted estimate: Mean out-of-pocket expenses ===")
    for est in survey_mean(sub_dsgn, ["totslf"]):
        print(f"  {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
