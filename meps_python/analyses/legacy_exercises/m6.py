"""M6: Frequency tables and cross-tabulations, 2001.

Survey-weighted frequency tables and cross-tabulations.

Input file: C:/MEPS/h60.ssp (2001 Full-year consolidated)

Ported from: SAS/older_exercises_1996_to_2006/Misc_examples/M6/M6.sas
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_by


def main(data_dir: str = "C:/MEPS") -> None:
    fyc01 = read_meps(year=2001, file_type="FYC", data_dir=data_dir)

    # Insurance coverage
    ins_map = {1: "Any private", 2: "Public only", 3: "Uninsured"}
    fyc01 = fyc01.with_columns([
        pl.col("INSCOV01").replace_strict(ins_map, default="Missing").alias("insurance"),
        pl.col("SEX").replace_strict({1: "Male", 2: "Female"}, default="Missing").alias("sex"),
        (pl.col("TOTEXP01") > 0).cast(pl.Int32).alias("has_exp"),
    ])

    dsgn = MEPSSurveyDesign(
        data=fyc01, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT01F", nest=True,
    )

    print("=== Insurance Coverage Distribution ===")
    for est in survey_by(dsgn, ["has_exp"], by=["insurance"], fun="total"):
        print(f"  {est.by_value}: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    print("\n=== Insurance by Sex (Percent) ===")
    for est in survey_by(dsgn, ["insurance"], by=["sex"], fun="mean"):
        print(f"  {est.by_value} | {est.variable}: {est.estimate:.4f} (SE: {est.se:.4f})")


if __name__ == "__main__":
    main()
