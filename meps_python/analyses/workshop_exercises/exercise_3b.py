"""Exercise 3b: Pooling MEPS longitudinal data, Panels 17-19.

Pooling longitudinal files with subpopulation:
 - Pool panels 17, 18, and 19
 - Subpopulation: age 26-30, uninsured, high income in first year
 - Insurance status in second year

Input files:
 - C:/MEPS/h183.ssp (Panel 19 longitudinal file)
 - C:/MEPS/h172.ssp (Panel 18 longitudinal file)
 - C:/MEPS/h164.ssp (Panel 17 longitudinal file)

Ported from: R/workshop_exercises/exercise_3b.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean


def main(data_dir: str = "C:/MEPS") -> None:
    varlist = ["DUPERSID", "INSCOVY1", "INSCOVY2",
               "LONGWT", "VARSTR", "VARPSU",
               "POVCATY1", "AGEY1X", "PANEL"]

    h183 = read_meps(year=2019, file_type="LONG", data_dir=data_dir).select(
        [c for c in varlist if c in read_meps(year=2019, file_type="LONG", data_dir=data_dir).columns]
    )
    h172 = read_meps(year=2018, file_type="LONG", data_dir=data_dir).select(
        [c for c in varlist if c in read_meps(year=2018, file_type="LONG", data_dir=data_dir).columns]
    )
    h164 = read_meps(year=2017, file_type="LONG", data_dir=data_dir).select(
        [c for c in varlist if c in read_meps(year=2017, file_type="LONG", data_dir=data_dir).columns]
    )

    # Stack and define pooled weight
    pool = pl.concat([h183, h172, h164]).with_columns([
        (pl.col("LONGWT") / 3).alias("poolwt"),
        (
            (pl.col("AGEY1X") >= 26) & (pl.col("AGEY1X") <= 30) &
            (pl.col("POVCATY1") == 5) & (pl.col("INSCOVY1") == 3)
        ).cast(pl.Int32).alias("subpop"),
    ])

    print(f"Pooled sample size: {pool.height}")

    # Define survey design
    dsgn = MEPSSurveyDesign(
        data=pool, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="poolwt", nest=True,
    )

    # Insurance status in second year for subpopulation
    sub_dsgn = dsgn.subset(pl.col("subpop") == 1)

    print("\n=== Insurance status in Year 2 ===")
    # Convert INSCOVY2 to factor-like indicator
    pool_sub = sub_dsgn
    for est in survey_mean(pool_sub, ["INSCOVY2"]):
        print(f"  {est.variable}: {est.estimate:.4f} (SE: {est.se:.4f})")


if __name__ == "__main__":
    main()
