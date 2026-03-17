"""Accessibility and quality of care: Access to Care, 2017.

Reasons for difficulty receiving needed care:
 - Number/percent of people by poverty status

Input file: C:/MEPS/h201.dta (2017 full-year consolidated)

Ported from: R/summary_tables_examples/care_access_2017.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_by


def main(data_dir: str = "C:/MEPS") -> None:
    FYC = read_meps(year=2017, file_type="FYC", data_dir=data_dir)

    # Reasons for difficulty receiving needed care
    FYC = FYC.with_columns([
        ((pl.col("MDUNAB42") == 1) | (pl.col("MDDLAY42") == 1)).cast(pl.Int32).alias("delay_MD"),
        ((pl.col("DNUNAB42") == 1) | (pl.col("DNDLAY42") == 1)).cast(pl.Int32).alias("delay_DN"),
        ((pl.col("PMUNAB42") == 1) | (pl.col("PMDLAY42") == 1)).cast(pl.Int32).alias("delay_PM"),
        ((pl.col("MDDLRS42") == 1) | (pl.col("MDUNRS42") == 1)).cast(pl.Int32).alias("afford_MD"),
        ((pl.col("DNDLRS42") == 1) | (pl.col("DNUNRS42") == 1)).cast(pl.Int32).alias("afford_DN"),
        ((pl.col("PMDLRS42") == 1) | (pl.col("PMUNRS42") == 1)).cast(pl.Int32).alias("afford_PM"),
        (pl.col("MDDLRS42").is_in([2, 3]) | pl.col("MDUNRS42").is_in([2, 3])).cast(pl.Int32).alias("insure_MD"),
        (pl.col("DNDLRS42").is_in([2, 3]) | pl.col("DNUNRS42").is_in([2, 3])).cast(pl.Int32).alias("insure_DN"),
        (pl.col("PMDLRS42").is_in([2, 3]) | pl.col("PMUNRS42").is_in([2, 3])).cast(pl.Int32).alias("insure_PM"),
        ((pl.col("MDDLRS42") > 3) | (pl.col("MDUNRS42") > 3)).cast(pl.Int32).alias("other_MD"),
        ((pl.col("DNDLRS42") > 3) | (pl.col("DNUNRS42") > 3)).cast(pl.Int32).alias("other_DN"),
        ((pl.col("PMDLRS42") > 3) | (pl.col("PMUNRS42") > 3)).cast(pl.Int32).alias("other_PM"),
    ])

    FYC = FYC.with_columns([
        (
            (pl.col("delay_MD") == 1) | (pl.col("delay_DN") == 1) | (pl.col("delay_PM") == 1)
        ).cast(pl.Int32).alias("delay_ANY"),
        (
            (pl.col("afford_MD") == 1) | (pl.col("afford_DN") == 1) | (pl.col("afford_PM") == 1)
        ).cast(pl.Int32).alias("afford_ANY"),
        (
            (pl.col("insure_MD") == 1) | (pl.col("insure_DN") == 1) | (pl.col("insure_PM") == 1)
        ).cast(pl.Int32).alias("insure_ANY"),
        (
            (pl.col("other_MD") == 1) | (pl.col("other_DN") == 1) | (pl.col("other_PM") == 1)
        ).cast(pl.Int32).alias("other_ANY"),
    ])

    # Poverty status
    pov_map = {1: "Negative or poor", 2: "Near-poor", 3: "Low income",
               4: "Middle income", 5: "High income"}
    FYC = FYC.with_columns(
        pl.col("POVCAT17").replace_strict(pov_map, default="Missing").alias("poverty")
    )

    # Define survey design
    dsgn = MEPSSurveyDesign(
        data=FYC, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT17F", nest=True,
    )

    # Subset to eligible persons who experienced difficulty
    sub_dsgn = dsgn.subset((pl.col("ACCELI42") == 1) & (pl.col("delay_ANY") == 1))

    # Reasons by poverty status - number
    print("=== Reasons for difficulty (Number) ===")
    results = survey_by(sub_dsgn, ["afford_ANY", "insure_ANY", "other_ANY"],
                        by=["poverty"], fun="total")
    for est in results:
        print(f"  {est.by_value} | {est.variable}: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    # Reasons by poverty status - percent
    print("\n=== Reasons for difficulty (Percent) ===")
    results = survey_by(sub_dsgn, ["afford_ANY", "insure_ANY", "other_ANY"],
                        by=["poverty"], fun="mean")
    for est in results:
        print(f"  {est.by_value} | {est.variable}: {est.estimate:.4f} (SE: {est.se:.4f})")


if __name__ == "__main__":
    main()
