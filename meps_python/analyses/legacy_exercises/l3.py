"""L3: Merge OB visits with FYC, 2001.

Link office-based visit event file with person-level FYC data.

Input files:
 - C:/MEPS/h60.ssp (2001 FYC)
 - C:/MEPS/h59g.ssp (2001 OB event file)

Ported from: SAS/older_exercises_1996_to_2006/Linking_examples/L3/L3.sas
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean, survey_total


def main(data_dir: str = "C:/MEPS") -> None:
    fyc01 = read_meps(year=2001, file_type="FYC", data_dir=data_dir).select(
        ["DUPERSID", "VARSTR", "VARPSU", "PERWT01F", "AGELAST", "SEX"]
    )
    ob01 = read_meps(year=2001, file_type="OB", data_dir=data_dir)

    # Count OB visits per person
    ob_pers = (
        ob01.group_by("DUPERSID")
        .agg([
            pl.len().alias("n_ob_visits"),
            pl.col("OBXP01X").sum().alias("ob_totexp"),
        ])
        .with_columns(pl.lit(1).alias("any_ob"))
    )

    # Merge with FYC
    merged = fyc01.join(ob_pers, on="DUPERSID", how="left")
    merged = merged.with_columns([
        pl.col("any_ob").fill_null(0),
        pl.col("n_ob_visits").fill_null(0),
        pl.col("ob_totexp").fill_null(0.0),
    ])

    dsgn = MEPSSurveyDesign(
        data=merged, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT01F", nest=True,
    )

    print("=== OB Visit Analysis, 2001 ===")
    for est in survey_total(dsgn, ["any_ob"]):
        print(f"  Persons with OB visit: {est.estimate:,.0f} (SE: {est.se:,.0f})")
    for est in survey_mean(dsgn, ["any_ob"]):
        print(f"  Percent with OB visit: {est.estimate:.4f} (SE: {est.se:.4f})")

    sub = dsgn.subset(pl.col("any_ob") == 1)
    for est in survey_mean(sub, ["n_ob_visits"]):
        print(f"  Mean visits per person: {est.estimate:,.2f} (SE: {est.se:,.2f})")
    for est in survey_mean(sub, ["ob_totexp"]):
        print(f"  Mean OB exp per person: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
