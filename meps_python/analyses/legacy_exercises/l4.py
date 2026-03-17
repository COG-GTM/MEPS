"""L4: Merge Medical Conditions with FYC, 2001.

Link medical conditions file with person-level FYC data.

Input files:
 - C:/MEPS/h60.ssp (2001 FYC)
 - C:/MEPS/h59.ssp (2001 Medical Conditions file)

Ported from: SAS/older_exercises_1996_to_2006/Linking_examples/L4/L4.sas
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean, survey_total


def main(data_dir: str = "C:/MEPS") -> None:
    fyc01 = read_meps(year=2001, file_type="FYC", data_dir=data_dir).select(
        ["DUPERSID", "VARSTR", "VARPSU", "PERWT01F", "TOTEXP01"]
    )
    cond01 = read_meps(year=2001, file_type="COND", data_dir=data_dir)

    # Count conditions per person
    cond_pers = (
        cond01.group_by("DUPERSID")
        .agg([
            pl.len().alias("n_conditions"),
        ])
        .with_columns(pl.lit(1).alias("any_cond"))
    )

    # Merge with FYC
    merged = fyc01.join(cond_pers, on="DUPERSID", how="left")
    merged = merged.with_columns([
        pl.col("any_cond").fill_null(0),
        pl.col("n_conditions").fill_null(0),
    ])

    dsgn = MEPSSurveyDesign(
        data=merged, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT01F", nest=True,
    )

    print("=== Conditions Analysis, 2001 ===")
    for est in survey_total(dsgn, ["any_cond"]):
        print(f"  Persons with conditions: {est.estimate:,.0f} (SE: {est.se:,.0f})")
    for est in survey_mean(dsgn, ["any_cond"]):
        print(f"  Percent with conditions: {est.estimate:.4f} (SE: {est.se:.4f})")
    for est in survey_mean(dsgn, ["n_conditions"]):
        print(f"  Mean conditions per person: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
