"""Exercise 2a: Prescribed medicine purchases, 2018.

Event-level aggregation and therapeutic class filtering:
 - Total purchases and expenditures for narcotic analgesics
 - Per-person averages among purchasers

Input files:
 - C:/MEPS/h209.dta (2018 Full-year file)
 - C:/MEPS/h206a.dta (2018 Prescribed medicines file)

Ported from: R/workshop_exercises/exercise_2a.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean, survey_total


def main(data_dir: str = "C:/MEPS") -> None:
    fyc18 = read_meps(year=2018, file_type="FYC", data_dir=data_dir)
    rx18 = read_meps(year=2018, file_type="RX", data_dir=data_dir)

    # Keep only needed variables from FYC
    fyc18_sub = fyc18.select(["DUPERSID", "VARSTR", "VARPSU", "PERWT18F"])

    # Identify narcotics (TC1S1_1 in [60, 191])
    narc = rx18.filter(pl.col("TC1S1_1").is_in([60, 191])).select(
        ["DUPERSID", "RXRECIDX", "LINKIDX", "TC1S1_1", "RXXP18X", "RXSF18X"]
    )

    print(f"Number of narcotic purchases: {narc.height}")
    print(narc.group_by("TC1S1_1").len())

    # Aggregate to person-level
    narc_pers = (
        narc.group_by("DUPERSID")
        .agg([
            pl.col("RXXP18X").sum().alias("tot"),
            pl.col("RXSF18X").sum().alias("oop"),
            pl.len().alias("n_purchase"),
        ])
        .with_columns([
            (pl.col("tot") - pl.col("oop")).alias("third_payer"),
            pl.lit(1).alias("any_narc"),
        ])
    )

    # Merge with FYC for complete survey design
    narc_fyc = fyc18_sub.join(narc_pers, on="DUPERSID", how="full", coalesce=True)
    narc_fyc = narc_fyc.with_columns([
        pl.col("any_narc").fill_null(0),
        pl.col("tot").fill_null(0),
        pl.col("oop").fill_null(0),
        pl.col("third_payer").fill_null(0),
        pl.col("n_purchase").fill_null(0),
    ])

    # Define survey design
    dsgn = MEPSSurveyDesign(
        data=narc_fyc, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT18F", nest=True,
    )

    # Subset to narcotic users
    sub_dsgn = dsgn.subset(pl.col("any_narc") == 1)

    # National totals
    print("\n=== National Totals ===")
    est_vars = ["n_purchase", "tot", "oop", "third_payer"]
    for est in survey_total(sub_dsgn, est_vars):
        print(f"  {est.variable}: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    # Per-person averages
    print("\n=== Per-person Averages ===")
    for est in survey_mean(sub_dsgn, est_vars):
        print(f"  {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
