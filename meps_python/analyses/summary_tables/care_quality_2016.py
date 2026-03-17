"""Accessibility and quality of care: Quality of Care, 2016.

Self-administered questionnaire (SAQ):
 - Number/percent of adults by ability to schedule a routine appointment
 - By insurance coverage status

Input file: C:/MEPS/h192.ssp (2016 full-year consolidated)

Ported from: R/summary_tables_examples/care_quality_2016.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_by


def main(data_dir: str = "C:/MEPS") -> None:
    FYC = read_meps(year=2016, file_type="FYC", data_dir=data_dir)

    # Ability to schedule a routine appointment
    routine_map = {
        4: "Always", 3: "Usually", 2: "Sometimes/Never", 1: "Sometimes/Never",
        -7: "Don't know/Non-response", -8: "Don't know/Non-response",
        -9: "Don't know/Non-response", -1: "Inapplicable",
    }
    FYC = FYC.with_columns(
        pl.col("ADRTWW42").replace_strict(routine_map, default="Missing").alias("adult_routine")
    )

    # Insurance coverage
    ins_map = {
        1: "<65, Any private", 2: "<65, Public only", 3: "<65, Uninsured",
        4: "65+, Medicare only", 5: "65+, Medicare and private",
        6: "65+, Medicare and other public", 7: "65+, No medicare", 8: "65+, No medicare",
    }
    FYC = FYC.with_columns(
        pl.col("INSURC16").replace_strict(ins_map, default="Missing").alias("insurance")
    )

    # Survey design with SAQ weight
    dsgn = MEPSSurveyDesign(
        data=FYC, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="SAQWT16F", nest=True,
    )

    # Subset to adults who made an appointment
    sub_dsgn = dsgn.subset((pl.col("ADRTCR42") == 1) & (pl.col("AGELAST") >= 18))

    print("=== Routine appointment scheduling by insurance (Number) ===")
    for est in survey_by(sub_dsgn, ["adult_routine"], by=["insurance"], fun="total"):
        print(f"  {est.by_value} | {est.variable}: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    print("\n=== Routine appointment scheduling by insurance (Percent) ===")
    for est in survey_by(sub_dsgn, ["adult_routine"], by=["insurance"], fun="mean"):
        print(f"  {est.by_value} | {est.variable}: {est.estimate:.4f} (SE: {est.se:.4f})")


if __name__ == "__main__":
    main()
