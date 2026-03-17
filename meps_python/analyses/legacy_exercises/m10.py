"""M10: Longitudinal weight demonstration.

Demonstrates use of longitudinal weights vs cross-sectional weights.

Input file: C:/MEPS/h65.ssp (Panel 4 longitudinal file)

Ported from: SAS/older_exercises_1996_to_2006/Misc_examples/M10/M10.sas
"""


from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean


def main(data_dir: str = "C:/MEPS") -> None:
    long04 = read_meps(year=2000, file_type="LONG", data_dir=data_dir)

    # Use longitudinal design variables
    psu_col = "VARPSUP4" if "VARPSUP4" in long04.columns else "VARPSU"
    str_col = "VARSTRP4" if "VARSTRP4" in long04.columns else "VARSTR"
    wt_col = "LONGWTP4" if "LONGWTP4" in long04.columns else "LONGWT"

    print(f"Longitudinal sample size: {long04.height}")
    print(f"Using: PSU={psu_col}, STRATA={str_col}, WEIGHT={wt_col}")

    dsgn = MEPSSurveyDesign(
        data=long04, psu_col=psu_col, strata_col=str_col,
        weight_col=wt_col, nest=True,
    )

    exp_cols = [c for c in long04.columns if "TOTEXP" in c]
    if exp_cols:
        print("\n=== Longitudinal Expenditure Estimates ===")
        for est in survey_mean(dsgn, exp_cols[:2]):
            print(f"  {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")

    ins_cols = [c for c in long04.columns if "INSCOV" in c]
    if ins_cols:
        print("\n=== Insurance Coverage ===")
        for est in survey_mean(dsgn, ins_cols[:2]):
            print(f"  {est.variable}: {est.estimate:.4f} (SE: {est.se:.4f})")


if __name__ == "__main__":
    main()
