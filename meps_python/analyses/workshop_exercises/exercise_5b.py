"""Exercise 5b: Monthly insurance status construction, 2018.

Monthly insurance status construction from 12 monthly indicator arrays:
 - Construct annual insurance count variables (PRI_N, INS_N, UNINS_N, etc.)
 - Construct binary insurance flags (FULL_INSU, GROUP_INS1, etc.)
 - Survey-weighted estimates of insurance status

Input file: C:/MEPS/h209.dta (2018 Full-year file)

Ported from: SAS/workshop_exercises/exercise_5b/Exercise5b.sas
"""

from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean, survey_total
from meps.transforms.insurance import construct_insurance_flags, construct_insurance_status


def main(data_dir: str = "C:/MEPS") -> None:
    fyc18 = read_meps(year=2018, file_type="FYC", data_dir=data_dir)

    # Construct monthly insurance status counts
    fyc18 = construct_insurance_status(fyc18, year_suffix="18")

    # Construct insurance flags
    fyc18 = construct_insurance_flags(fyc18)

    # QC: Check distribution of insurance counts
    print("=== Insurance month counts ===")
    for col in ["PRI_N", "INS_N", "UNINS_N", "MCD_N", "MCR_N"]:
        if col in fyc18.columns:
            print(f"  {col}: mean={fyc18[col].mean():.2f}, "
                  f"min={fyc18[col].min()}, max={fyc18[col].max()}")

    # Define survey design
    dsgn = MEPSSurveyDesign(
        data=fyc18, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT18F", nest=True,
    )

    # Survey-weighted insurance estimates
    ins_vars = ["FULL_INSU", "GROUP_INS1", "GROUP_INS2", "NG_INS"]
    available_vars = [v for v in ins_vars if v in fyc18.columns]

    print("\n=== Insurance status (Percent) ===")
    for est in survey_mean(dsgn, available_vars):
        print(f"  {est.variable}: {est.estimate:.4f} (SE: {est.se:.4f})")

    print("\n=== Insurance status (Number) ===")
    for est in survey_total(dsgn, available_vars):
        print(f"  {est.variable}: {est.estimate:,.0f} (SE: {est.se:,.0f})")


if __name__ == "__main__":
    main()
