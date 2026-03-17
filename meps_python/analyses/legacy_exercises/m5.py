"""M5: Confidence intervals and hypothesis testing, 2001.

Demonstrates confidence intervals and hypothesis testing for survey estimates.

Input file: C:/MEPS/h60.ssp (2001 Full-year consolidated)

Ported from: SAS/older_exercises_1996_to_2006/Misc_examples/M5/M5.sas
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean
from scipy import stats


def main(data_dir: str = "C:/MEPS") -> None:
    fyc01 = read_meps(year=2001, file_type="FYC", data_dir=data_dir)

    fyc01 = fyc01.with_columns([
        (pl.col("SEX") == 1).cast(pl.Int32).alias("male"),
        (pl.col("SEX") == 2).cast(pl.Int32).alias("female"),
    ])

    dsgn = MEPSSurveyDesign(
        data=fyc01, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT01F", nest=True,
    )

    # Mean expenditure by sex
    print("=== Mean Expenditure by Sex ===")
    male_dsgn = dsgn.subset(pl.col("male") == 1)
    female_dsgn = dsgn.subset(pl.col("female") == 1)

    male_est = list(survey_mean(male_dsgn, ["TOTEXP01"]))[0]
    female_est = list(survey_mean(female_dsgn, ["TOTEXP01"]))[0]

    print(f"  Male:   {male_est.estimate:,.2f} (SE: {male_est.se:,.2f})")
    print(f"  Female: {female_est.estimate:,.2f} (SE: {female_est.se:,.2f})")

    # Test difference
    diff = male_est.estimate - female_est.estimate
    se_diff = (male_est.se ** 2 + female_est.se ** 2) ** 0.5
    t_stat = diff / se_diff
    p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=100))

    print("\n=== Hypothesis Test: Male vs Female ===")
    print(f"  Difference: {diff:,.2f}")
    print(f"  SE of difference: {se_diff:,.2f}")
    print(f"  t-statistic: {t_stat:.4f}")
    print(f"  p-value: {p_value:.4f}")


if __name__ == "__main__":
    main()
