"""M1: Weight demonstration, 2001.

Demonstrates the effect of survey weights on population estimates.

Input file: C:/MEPS/h60.ssp (2001 Full-year consolidated)

Ported from: SAS/older_exercises_1996_to_2006/Misc_examples/M1/M1.sas
"""


from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean, survey_total


def main(data_dir: str = "C:/MEPS") -> None:
    fyc01 = read_meps(year=2001, file_type="FYC", data_dir=data_dir)

    print(f"Sample size: {fyc01.height}")

    # Unweighted mean
    unweighted_mean = fyc01["TOTEXP01"].mean()
    print(f"\nUnweighted mean expenditure: {unweighted_mean:,.2f}")

    # Weighted mean using survey design
    dsgn = MEPSSurveyDesign(
        data=fyc01, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT01F", nest=True,
    )

    print("\n=== Weighted Estimates ===")
    for est in survey_mean(dsgn, ["TOTEXP01"]):
        print(f"  Weighted mean: {est.estimate:,.2f} (SE: {est.se:,.2f})")
    for est in survey_total(dsgn, ["TOTEXP01"]):
        print(f"  Population total: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    # Sum of weights = population total
    pop_total = fyc01["PERWT01F"].sum()
    print(f"\n  Sum of weights (est. population): {pop_total:,.0f}")


if __name__ == "__main__":
    main()
