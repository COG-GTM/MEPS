"""M3: Design effect demonstration, 2001.

Demonstrates the design effect (DEFF) for MEPS survey estimates.

Input file: C:/MEPS/h60.ssp (2001 Full-year consolidated)

Ported from: SAS/older_exercises_1996_to_2006/Misc_examples/M3/M3.sas
"""


from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean


def main(data_dir: str = "C:/MEPS") -> None:
    fyc01 = read_meps(year=2001, file_type="FYC", data_dir=data_dir)

    dsgn = MEPSSurveyDesign(
        data=fyc01, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT01F", nest=True,
    )

    exp_vars = ["TOTEXP01", "IPTEXP01", "RXEXP01", "OBVEXP01"]
    available = [v for v in exp_vars if v in fyc01.columns]

    print("=== Design Effects for Expenditure Variables, 2001 ===")
    for est in survey_mean(dsgn, available):
        print(f"  {est.variable}: Mean={est.estimate:,.2f}, SE={est.se:,.2f}")

    # Simple variance for DEFF comparison
    import numpy as np
    data = fyc01.to_pandas()
    w = data["PERWT01F"]
    for var in available:
        x = data[var]
        wmean = np.average(x, weights=w)
        srs_var = np.average((x - wmean) ** 2, weights=w) / len(x)
        print(f"  {var}: SRS SE={np.sqrt(srs_var):,.2f}")


if __name__ == "__main__":
    main()
