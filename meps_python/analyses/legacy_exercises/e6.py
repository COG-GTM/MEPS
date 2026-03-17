"""E6: National health care expenditures by type of service, 2005.

Total and mean expenditures by service type (IP, ER, OP, OB, RX, DV, HH).

Input file: C:/MEPS/h97.ssp (2005 Full-year consolidated)

Ported from: SAS/older_exercises_1996_to_2006/Estimation_examples/E6/E6.sas
"""


from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean, survey_total


def main(data_dir: str = "C:/MEPS") -> None:
    fyc05 = read_meps(year=2005, file_type="FYC", data_dir=data_dir)

    dsgn = MEPSSurveyDesign(
        data=fyc05, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT05F", nest=True,
    )

    exp_vars = ["TOTEXP05", "IPTEXP05", "ERTEXP05", "OPTEXP05",
                "OBVEXP05", "RXEXP05", "DVTEXP05", "HHAEXP05", "HHNEXP05"]
    available = [v for v in exp_vars if v in fyc05.columns]

    print("=== National Total Expenditures by Type of Service, 2005 ===")
    for est in survey_total(dsgn, available):
        print(f"  {est.variable}: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    print("\n=== Mean Expenditure per Person ===")
    for est in survey_mean(dsgn, available):
        print(f"  {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
