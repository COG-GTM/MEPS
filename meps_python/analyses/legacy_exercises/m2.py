"""M2: Variance estimation comparison, 2001.

Compares standard errors from different variance estimation methods.

Input file: C:/MEPS/h60.ssp (2001 Full-year consolidated)

Ported from: SAS/older_exercises_1996_to_2006/Misc_examples/M2/M2.sas
"""


from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean


def main(data_dir: str = "C:/MEPS") -> None:
    fyc01 = read_meps(year=2001, file_type="FYC", data_dir=data_dir)

    # Taylor linearization (standard method)
    dsgn = MEPSSurveyDesign(
        data=fyc01, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT01F", nest=True,
    )

    print("=== Taylor Linearization Variance Estimation ===")
    for est in survey_mean(dsgn, ["TOTEXP01"]):
        print(f"  Mean: {est.estimate:,.2f}")
        print(f"  SE (Taylor): {est.se:,.2f}")
        print(f"  95% CI: ({est.ci_lower:,.2f}, {est.ci_upper:,.2f})")

    # Simple random sample (incorrect for MEPS)
    import numpy as np
    data = fyc01.to_pandas()
    w = data["PERWT01F"]
    x = data["TOTEXP01"]
    weighted_mean = np.average(x, weights=w)
    # Naive SE (ignoring design)
    n = len(x)
    naive_se = np.sqrt(np.average((x - weighted_mean) ** 2, weights=w) / n)
    print("\n=== Simple Random Sample (Incorrect) ===")
    print(f"  Mean: {weighted_mean:,.2f}")
    print(f"  Naive SE: {naive_se:,.2f}")
    print("  Note: Naive SE underestimates true SE due to ignoring design effect")


if __name__ == "__main__":
    main()
