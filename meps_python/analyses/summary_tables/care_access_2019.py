"""Accessibility and quality of care: Access to Care, 2019.

Did not receive treatment because couldn't afford it:
 - Number/percent of people by poverty status

Input file: C:/MEPS/h216.dta (2019 full-year consolidated)

Ported from: R/summary_tables_examples/care_access_2019.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_by


def main(data_dir: str = "C:/MEPS") -> None:
    FYC = read_meps(year=2019, file_type="FYC", data_dir=data_dir)

    # Couldn't afford care
    FYC = FYC.with_columns([
        (pl.col("AFRDCA42") == 1).cast(pl.Int32).alias("afford_MD"),
        (pl.col("AFRDDN42") == 1).cast(pl.Int32).alias("afford_DN"),
        (pl.col("AFRDPM42") == 1).cast(pl.Int32).alias("afford_PM"),
    ])
    FYC = FYC.with_columns(
        ((pl.col("afford_MD") == 1) | (pl.col("afford_DN") == 1) |
         (pl.col("afford_PM") == 1)).cast(pl.Int32).alias("afford_ANY")
    )

    # Poverty status
    pov_map = {1: "Negative or poor", 2: "Near-poor", 3: "Low income",
               4: "Middle income", 5: "High income"}
    FYC = FYC.with_columns(
        pl.col("POVCAT19").replace_strict(pov_map, default="Missing").alias("poverty")
    )

    # Survey design
    dsgn = MEPSSurveyDesign(
        data=FYC, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT19F", nest=True,
    )

    # Subset to eligible persons
    sub_dsgn = dsgn.subset(pl.col("ACCELI42") == 1)

    afford_vars = ["afford_ANY", "afford_MD", "afford_DN", "afford_PM"]

    print("=== Couldn't afford care (Number) ===")
    for est in survey_by(sub_dsgn, afford_vars, by=["poverty"], fun="total"):
        print(f"  {est.by_value} | {est.variable}: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    print("\n=== Couldn't afford care (Percent) ===")
    for est in survey_by(sub_dsgn, afford_vars, by=["poverty"], fun="mean"):
        print(f"  {est.by_value} | {est.variable}: {est.estimate:.4f} (SE: {est.se:.4f})")


if __name__ == "__main__":
    main()
