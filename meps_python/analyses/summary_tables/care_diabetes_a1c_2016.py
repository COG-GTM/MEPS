"""Accessibility and quality of care: Diabetes Care, 2016.

Diabetes care survey (DCS):
 - Number/percent of adults with diabetes receiving hemoglobin A1c blood test
 - By race/ethnicity

Input file: C:/MEPS/h192.ssp (2016 full-year consolidated)

Ported from: R/summary_tables_examples/care_diabetes_a1c_2016.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_by


def main(data_dir: str = "C:/MEPS") -> None:
    FYC = read_meps(year=2016, file_type="FYC", data_dir=data_dir)

    # Diabetes care: Hemoglobin A1c measurement
    FYC = FYC.with_columns(
        pl.when(pl.col("DSA1C53") == -1).then(pl.lit("Inapplicable"))
        .when(pl.col("DSA1C53") < 0).then(pl.lit("Don't know/Non-response"))
        .when(pl.col("DSA1C53") == 0).then(pl.lit("Did not have measurement"))
        .when(pl.col("DSA1C53") == 96).then(pl.lit("Did not have measurement"))
        .when((pl.col("DSA1C53") > 0) & (pl.col("DSA1C53") < 96)).then(pl.lit("Had measurement"))
        .otherwise(pl.lit("Missing"))
        .alias("diab_a1c")
    )

    # Race/ethnicity (2012+)
    FYC = FYC.with_columns([
        (pl.col("RACETHX") == 1).alias("hisp"),
        (pl.col("RACETHX") == 2).alias("white"),
        (pl.col("RACETHX") == 3).alias("black"),
        ((pl.col("RACETHX") > 3) & pl.col("RACEV1X").is_in([3, 6])).alias("native"),
        ((pl.col("RACETHX") > 3) & pl.col("RACEV1X").is_in([4, 5])).alias("asian"),
    ])

    FYC = FYC.with_columns(
        (pl.col("hisp").cast(pl.Int32) * 1 + pl.col("white").cast(pl.Int32) * 2 +
         pl.col("black").cast(pl.Int32) * 3 + pl.col("native").cast(pl.Int32) * 4 +
         pl.col("asian").cast(pl.Int32) * 5).alias("race_num")
    )

    race_map = {1: "Hispanic", 2: "White", 3: "Black",
                4: "Amer. Indian, AK Native, or mult. races",
                5: "Asian, Hawaiian, or Pacific Islander"}
    FYC = FYC.with_columns(
        pl.col("race_num").replace_strict(race_map, default="Other").alias("race")
    )

    # Survey design with DCS weight
    dsgn = MEPSSurveyDesign(
        data=FYC, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="DIABW16F", nest=True,
    )

    # Results by race
    print("=== A1c measurement by race (Number) ===")
    for est in survey_by(dsgn, ["diab_a1c"], by=["race"], fun="total"):
        print(f"  {est.by_value} | {est.variable}: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    print("\n=== A1c measurement by race (Percent) ===")
    for est in survey_by(dsgn, ["diab_a1c"], by=["race"], fun="mean"):
        print(f"  {est.by_value} | {est.variable}: {est.estimate:.4f} (SE: {est.se:.4f})")


if __name__ == "__main__":
    main()
