"""E3: Longitudinal estimates of insurance coverage and expenditures, 1999-2000.

Uses longitudinal weights (LONGWTP4) for panel-based analysis.

Input file: C:/MEPS/h65.ssp (Panel 4 longitudinal file)

Ported from: SAS/older_exercises_1996_to_2006/Estimation_examples/E3/E3.sas
"""


from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_by, survey_mean


def main(data_dir: str = "C:/MEPS") -> None:
    long04 = read_meps(year=2000, file_type="LONG", data_dir=data_dir)

    # Select variables
    cols = ["DUPERSID", "INSCOVY1", "INSCOVY2", "TOTEXPY1", "TOTEXPY2",
            "LONGWTP4", "VARPSUP4", "VARSTRP4"]
    available = [c for c in cols if c in long04.columns]
    long04 = long04.select(available)

    # Use longitudinal design variables
    psu_col = "VARPSUP4" if "VARPSUP4" in long04.columns else "VARPSU"
    str_col = "VARSTRP4" if "VARSTRP4" in long04.columns else "VARSTR"
    wt_col = "LONGWTP4" if "LONGWTP4" in long04.columns else "LONGWT"

    dsgn = MEPSSurveyDesign(
        data=long04, psu_col=psu_col, strata_col=str_col,
        weight_col=wt_col, nest=True,
    )

    # Insurance coverage in Year 1 and Year 2
    print("=== Insurance Coverage, Year 1 ===")
    for est in survey_mean(dsgn, ["INSCOVY1"]):
        print(f"  {est.variable}: {est.estimate:.4f} (SE: {est.se:.4f})")

    print("\n=== Insurance Coverage, Year 2 ===")
    for est in survey_mean(dsgn, ["INSCOVY2"]):
        print(f"  {est.variable}: {est.estimate:.4f} (SE: {est.se:.4f})")

    # Mean expenditures by insurance status
    print("\n=== Mean Expenditures by Year 1 Insurance Status ===")
    for est in survey_by(dsgn, ["TOTEXPY1", "TOTEXPY2"], by=["INSCOVY1"], fun="mean"):
        print(f"  {est.by_value} | {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
