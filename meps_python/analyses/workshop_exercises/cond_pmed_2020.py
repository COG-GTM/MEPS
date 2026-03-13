"""Condition-PMED linkage: Hyperlipidemia prescriptions, 2020.

4-file PMED linkage for hyperlipidemia analysis:
 - Total number of people with PMED purchase for hyperlipidemia
 - Total PMED fills and expenditures for hyperlipidemia
 - Average PMED fills and expenditures by SEX and Poverty (POVCAT)

Input files:
 - C:/MEPS/h220a.dta (2020 Prescribed Medicines file)
 - C:/MEPS/h222.dta (2020 Conditions file)
 - C:/MEPS/h220if1.dta (2020 CLNK file)
 - C:/MEPS/h224.dta (2020 Full-Year Consolidated file)

Ported from: R/workshop_exercises/cond_pmed_2020.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_by, survey_mean, survey_total


def main(data_dir: str = "C:/MEPS") -> None:
    # Load datasets
    pmed20 = read_meps(year=2020, file_type="RX", data_dir=data_dir).rename({"LINKIDX": "EVNTIDX"})
    cond20 = read_meps(year=2020, file_type="COND", data_dir=data_dir)
    clnk20 = read_meps(year=2020, file_type="CLNK", data_dir=data_dir)
    fyc20 = read_meps(year=2020, file_type="FYC", data_dir=data_dir)

    # Keep needed variables
    pmed20x = pmed20.select(["DUPERSID", "RXRECIDX", "EVNTIDX", "RXDRGNAM", "RXXP20X"])

    ccsr_cols = [c for c in ["CCSR1X", "CCSR2X", "CCSR3X"] if c in cond20.columns]
    cond20x = cond20.select(["DUPERSID", "CONDIDX", "ICD10CDX"] + ccsr_cols)

    fyc20x = fyc20.select([
        "DUPERSID", "AGELAST", "SEX", "POVCAT20", "CHOLDX",
        "VARSTR", "VARPSU", "PERWT20F",
    ])

    # Subset conditions to hyperlipidemia (CCSR = "END010")
    hl_filter = pl.lit(False)
    for col in ccsr_cols:
        hl_filter = hl_filter | (pl.col(col) == "END010")
    hl = cond20x.filter(hl_filter)

    print(f"Hyperlipidemia conditions: {hl.height}")

    # Merge with CLNK
    hl_clnk = hl.join(clnk20, on=["DUPERSID", "CONDIDX"], how="inner")

    # De-duplicate on EVNTIDX
    hl_clnk_distinct = hl_clnk.unique(
        subset=["DUPERSID", "EVNTIDX"], keep="first"
    )

    # Merge with PMED file
    hl_merged = hl_clnk_distinct.join(pmed20x, on=["DUPERSID", "EVNTIDX"], how="inner")

    # Top drugs for HL
    print("\nTop drugs for hyperlipidemia:")
    print(hl_merged.group_by("RXDRGNAM").len().sort("len", descending=True).head(10))

    # Roll up to person-level
    drugs_by_pers = (
        hl_merged.group_by("DUPERSID")
        .agg([
            pl.col("RXRECIDX").n_unique().alias("n_hl_fills"),
            pl.col("RXXP20X").sum().alias("hl_drug_exp"),
        ])
        .with_columns(pl.lit(1).alias("hl_pmed_flag"))
    )

    # Merge onto FYC
    fyc_hl_merged = fyc20x.join(drugs_by_pers, on="DUPERSID", how="full", coalesce=True)
    fyc_hl_merged = fyc_hl_merged.with_columns(
        pl.col("hl_pmed_flag").fill_null(0)
    )

    # Survey design
    dsgn = MEPSSurveyDesign(
        data=fyc_hl_merged, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT20F", nest=True,
    )
    hl_dsgn = dsgn.subset(pl.col("hl_pmed_flag") == 1)

    # National totals
    print("\n=== National Totals ===")
    for est in survey_total(hl_dsgn, ["hl_pmed_flag", "n_hl_fills", "hl_drug_exp"]):
        print(f"  {est.variable}: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    # Per-person averages
    print("\n=== Per-person Averages ===")
    for est in survey_mean(hl_dsgn, ["n_hl_fills", "hl_drug_exp"]):
        print(f"  {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")

    # By SEX
    print("\n=== By SEX ===")
    for est in survey_by(hl_dsgn, ["n_hl_fills", "hl_drug_exp"], by=["SEX"], fun="mean"):
        print(f"  {est.by_value} | {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")

    # By POVCAT
    print("\n=== By POVCAT ===")
    for est in survey_by(hl_dsgn, ["n_hl_fills", "hl_drug_exp"], by=["POVCAT20"], fun="mean"):
        print(f"  {est.by_value} | {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
