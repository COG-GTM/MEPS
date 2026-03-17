"""E8: Expenditures for inpatient stays by source of payment, 2005.

Inpatient expenditures broken down by source of payment.

Input file: C:/MEPS/h97.ssp (2005 Full-year consolidated)

Ported from: SAS/older_exercises_1996_to_2006/Estimation_examples/E8/E8.sas
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean, survey_total


def main(data_dir: str = "C:/MEPS") -> None:
    fyc05 = read_meps(year=2005, file_type="FYC", data_dir=data_dir)

    # Inpatient expenditure variables by SOP
    ip_vars = ["IPTEXP05", "IPTSLF05", "IPTMCR05", "IPTMCD05", "IPTPRV05",
               "IPTVA05", "IPTOTR05"]
    available = [v for v in ip_vars if v in fyc05.columns]

    fyc05 = fyc05.with_columns(
        (pl.col("IPTEXP05") > 0).cast(pl.Int32).alias("has_ip")
    )

    dsgn = MEPSSurveyDesign(
        data=fyc05, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT05F", nest=True,
    )

    print("=== Inpatient Expenditures by SOP, 2005 ===")
    print("\nTotal expenditures:")
    for est in survey_total(dsgn, available):
        print(f"  {est.variable}: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    print("\nMean per person:")
    for est in survey_mean(dsgn, available):
        print(f"  {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")

    print("\nMean per person with IP stay:")
    sub = dsgn.subset(pl.col("has_ip") == 1)
    for est in survey_mean(sub, available):
        print(f"  {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
