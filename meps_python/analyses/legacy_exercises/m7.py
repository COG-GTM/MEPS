"""M7: DCS (Diabetes Care Survey) weight demonstration, 2001.

Demonstrates using special DCS weights for diabetes-specific analyses.

Input file: C:/MEPS/h60.ssp (2001 Full-year consolidated)

Ported from: SAS/older_exercises_1996_to_2006/Misc_examples/M7/M7.sas
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean, survey_total


def main(data_dir: str = "C:/MEPS") -> None:
    fyc01 = read_meps(year=2001, file_type="FYC", data_dir=data_dir)

    # Find DCS weight column
    dcs_wt = None
    for c in fyc01.columns:
        if "DIABW" in c or "DCSW" in c:
            dcs_wt = c
            break

    if dcs_wt is None:
        print("DCS weight variable not found in 2001 FYC.")
        print("Using PERWT01F with diabetes indicator instead.")
        dcs_wt = "PERWT01F"

    # Diabetes indicator
    fyc01 = fyc01.with_columns(
        (pl.col("DIABDX") == 1).cast(pl.Int32).alias("has_diabetes")
        if "DIABDX" in fyc01.columns
        else pl.lit(0).alias("has_diabetes")
    )

    dsgn = MEPSSurveyDesign(
        data=fyc01, psu_col="VARPSU", strata_col="VARSTR",
        weight_col=dcs_wt, nest=True,
    )

    sub = dsgn.subset(pl.col("has_diabetes") == 1)

    print("=== Diabetes Population Estimates, 2001 ===")
    for est in survey_total(sub, ["has_diabetes"]):
        print(f"  Persons with diabetes: {est.estimate:,.0f} (SE: {est.se:,.0f})")
    for est in survey_mean(sub, ["TOTEXP01"]):
        print(f"  Mean expenditure: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
