"""Prescribed drugs, 2016.

Purchases and expenditures by generic drug name (RXDRGNAM):
 - Number of people with purchase
 - Total purchases
 - Total expenditures

Input file: C:/MEPS/h188a.ssp (2016 RX event file)

Ported from: R/summary_tables_examples/pmed_prescribed_drug_2016.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_by


def main(data_dir: str = "C:/MEPS") -> None:
    # Load RX file
    RX = read_meps(year=2016, file_type="RX", data_dir=data_dir)

    # Aggregate to person-level by drug name
    RX_pers = (
        RX.group_by(["DUPERSID", "VARSTR", "VARPSU", "RXDRGNAM"])
        .agg([
            pl.col("PERWT16F").mean(),
            pl.col("RXXP16X").sum().alias("pers_RXXP"),
            pl.len().alias("n_purchases"),
        ])
        .with_columns(pl.lit(1).alias("persons"))
    )

    # Define survey design
    dsgn = MEPSSurveyDesign(
        data=RX_pers, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT16F", nest=True,
    )

    # Totals by drug name
    print("=== Purchases and expenditures by drug name ===")
    results = survey_by(dsgn, ["persons", "n_purchases", "pers_RXXP"],
                        by=["RXDRGNAM"], fun="total")
    for est in results:
        print(f"  {est.by_value} | {est.variable}: {est.estimate:,.0f} (SE: {est.se:,.0f})")


if __name__ == "__main__":
    main()
