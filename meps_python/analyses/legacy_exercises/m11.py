"""M11: BRR (Balanced Repeated Replication) weight demonstration.

Demonstrates BRR as an alternative variance estimation method.

Input file: C:/MEPS/h60.ssp (2001 Full-year consolidated)

Ported from: SAS/older_exercises_1996_to_2006/Misc_examples/M11/M11.sas
"""


from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean


def main(data_dir: str = "C:/MEPS") -> None:
    fyc01 = read_meps(year=2001, file_type="FYC", data_dir=data_dir)

    # Standard Taylor linearization
    dsgn = MEPSSurveyDesign(
        data=fyc01, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT01F", nest=True,
    )

    print("=== Taylor Linearization ===")
    for est in survey_mean(dsgn, ["TOTEXP01"]):
        print(f"  Mean: {est.estimate:,.2f} (SE: {est.se:,.2f})")

    # BRR replicate weights (if available)
    brr_cols = [c for c in fyc01.columns if c.startswith("BRR") or c.startswith("REPWT")]

    if brr_cols:
        print(f"\n=== BRR Replicate Weights Found: {len(brr_cols)} ===")
        # Compute BRR variance manually
        import numpy as np
        data = fyc01.to_pandas()
        theta_full = np.average(data["TOTEXP01"], weights=data["PERWT01F"])
        theta_reps = []
        for col in brr_cols:
            theta_r = np.average(data["TOTEXP01"], weights=data[col])
            theta_reps.append(theta_r)
        theta_reps = np.array(theta_reps)
        brr_var = np.mean((theta_reps - theta_full) ** 2)
        brr_se = np.sqrt(brr_var)
        print(f"  Mean: {theta_full:,.2f} (BRR SE: {brr_se:,.2f})")
    else:
        print("\nNote: BRR replicate weights not found in 2001 FYC.")
        print("BRR weights are available in some MEPS files as an alternative")
        print("to Taylor linearization for variance estimation.")


if __name__ == "__main__":
    main()
