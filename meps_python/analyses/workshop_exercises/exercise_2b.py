"""Exercise 2b: Prescribed medicine purchases (person-level merge), 2018.

Person-level merge of narcotic analgesic purchases with FYC file:
 - National totals and per-person averages for number of purchases,
   total expenditures, out-of-pocket payments, and third-party payments

Input files:
 - C:/MEPS/h209.dta (2018 Full-year file)
 - C:/MEPS/h206a.dta (2018 Prescribed medicines file)

Ported from: R/workshop_exercises/exercise_2b.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean, survey_total


def main(data_dir: str = "C:/MEPS") -> None:
    fyc18 = read_meps(year=2018, file_type="FYC", data_dir=data_dir)
    rx18 = read_meps(year=2018, file_type="RX", data_dir=data_dir)

    # Keep FYC variables
    fyc18_sub = fyc18.select(["DUPERSID", "VARSTR", "VARPSU", "PERWT18F"])

    # Identify narcotics (TC1S1_1 in [60, 191])
    narc = rx18.filter(pl.col("TC1S1_1").is_in([60, 191])).select(
        ["DUPERSID", "RXRECIDX", "LINKIDX", "TC1S1_1", "RXXP18X", "RXSF18X"]
    )

    # Sum to person-level
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

    # Merge person-level expenditures to FYC
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
    sub_dsgn = dsgn.subset(pl.col("any_narc") == 1)

    est_vars = ["n_purchase", "tot", "oop", "third_payer"]

    # National totals
    print("=== National Totals ===")
    for est in survey_total(sub_dsgn, est_vars):
        print(f"  {est.variable}: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    # Per-person averages
    print("\n=== Average per person ===")
    for est in survey_mean(sub_dsgn, est_vars):
        print(f"  {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
