"""Exercise 2c: Prescribed medicine purchases (SAS variant), 2018.

Variant of exercises 2a/2b demonstrating prescribed medicine analysis
with different therapeutic class filtering and aggregation approaches.

Input files:
 - C:/MEPS/h209.dta (2018 Full-year file)
 - C:/MEPS/h206a.dta (2018 Prescribed medicines file)

Ported from: SAS/workshop_exercises/exercise_2c
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean, survey_total


def main(data_dir: str = "C:/MEPS") -> None:
    fyc18 = read_meps(year=2018, file_type="FYC", data_dir=data_dir)
    rx18 = read_meps(year=2018, file_type="RX", data_dir=data_dir)

    fyc18_sub = fyc18.select(["DUPERSID", "VARSTR", "VARPSU", "PERWT18F"])

    # Identify antidepressants (TC1S1 = 249)
    antidep = rx18.filter(pl.col("TC1S1") == 249).select(
        ["DUPERSID", "RXRECIDX", "RXXP18X", "RXSF18X"]
    )

    # Aggregate to person-level
    antidep_pers = (
        antidep.group_by("DUPERSID")
        .agg([
            pl.col("RXXP18X").sum().alias("tot_exp"),
            pl.col("RXSF18X").sum().alias("oop_exp"),
            pl.len().alias("n_fills"),
        ])
        .with_columns([
            (pl.col("tot_exp") - pl.col("oop_exp")).alias("third_payer"),
            pl.lit(1).alias("any_antidep"),
        ])
    )

    # Merge with FYC
    merged = fyc18_sub.join(antidep_pers, on="DUPERSID", how="full", coalesce=True)
    merged = merged.with_columns([
        pl.col("any_antidep").fill_null(0),
        pl.col("tot_exp").fill_null(0),
        pl.col("oop_exp").fill_null(0),
        pl.col("third_payer").fill_null(0),
        pl.col("n_fills").fill_null(0),
    ])

    # Survey design
    dsgn = MEPSSurveyDesign(
        data=merged, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT18F", nest=True,
    )
    sub_dsgn = dsgn.subset(pl.col("any_antidep") == 1)

    est_vars = ["n_fills", "tot_exp", "oop_exp", "third_payer"]

    print("=== National Totals (Antidepressants) ===")
    for est in survey_total(sub_dsgn, est_vars):
        print(f"  {est.variable}: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    print("\n=== Per-person Averages (Antidepressants) ===")
    for est in survey_mean(sub_dsgn, est_vars):
        print(f"  {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
