"""Health insurance, 2016.

Number/percent of people by insurance coverage and age groups.

Input file: C:/MEPS/h192.ssp (2016 full-year consolidated)

Ported from: R/summary_tables_examples/ins_age_2016.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_by


def main(data_dir: str = "C:/MEPS") -> None:
    # Load FYC file
    FYC = read_meps(year=2016, file_type="FYC", data_dir=data_dir)

    # Age groups
    FYC = FYC.with_columns(
        pl.when(pl.col("AGELAST") < 5).then(pl.lit("Under 5"))
        .when(pl.col("AGELAST") <= 17).then(pl.lit("5-17"))
        .when(pl.col("AGELAST") <= 44).then(pl.lit("18-44"))
        .when(pl.col("AGELAST") <= 64).then(pl.lit("45-64"))
        .otherwise(pl.lit("65+"))
        .alias("agegrps")
    )

    # Insurance coverage
    ins_map = {
        1: "<65, Any private",
        2: "<65, Public only",
        3: "<65, Uninsured",
        4: "65+, Medicare only",
        5: "65+, Medicare and private",
        6: "65+, Medicare and other public",
        7: "65+, No Medicare",
        8: "65+, No Medicare",
    }
    FYC = FYC.with_columns(
        pl.col("INSURC16").replace_strict(ins_map, default="Missing").alias("insurance")
    )

    # Define survey design
    dsgn = MEPSSurveyDesign(
        data=FYC, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT16F", nest=True,
    )

    # Insurance coverage by age groups - totals (number)
    print("=== Insurance by age (Number) ===")
    results = survey_by(dsgn, ["insurance"], by=["agegrps"], fun="total")
    for est in results:
        print(f"  {est.by_value} | {est.variable}: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    # Insurance coverage by age groups - proportions (percent)
    print("\n=== Insurance by age (Percent) ===")
    results = survey_by(dsgn, ["insurance"], by=["agegrps"], fun="mean")
    for est in results:
        print(f"  {est.by_value} | {est.variable}: {est.estimate:.4f} (SE: {est.se:.4f})")


if __name__ == "__main__":
    main()
