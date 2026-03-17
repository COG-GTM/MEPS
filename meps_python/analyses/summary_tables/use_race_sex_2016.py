"""Use, expenditures, and population, 2016.

Expenditure quantiles and means by race/ethnicity and sex:
 - Median expenditures (50th percentile)
 - Mean expenditures
 - Cross-tabulated by race/ethnicity and sex

Input file: C:/MEPS/h192.ssp (2016 full-year consolidated)

Ported from: R/summary_tables_examples/use_race_sex_2016.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_by, survey_quantile


def main(data_dir: str = "C:/MEPS") -> None:
    FYC = read_meps(year=2016, file_type="FYC", data_dir=data_dir)

    # Race/ethnicity
    race_map = {1: "Hispanic", 2: "White", 3: "Black",
                4: "Amer. Indian, AK Native, or mult. races",
                5: "Asian, Hawaiian, or Pacific Islander"}
    FYC = FYC.with_columns(
        pl.col("RACETHX").replace_strict(race_map, default="Other").alias("race")
    )

    # Sex
    sex_map = {1: "Male", 2: "Female"}
    FYC = FYC.with_columns(
        pl.col("SEX").replace_strict(sex_map, default="Missing").alias("sex")
    )

    # Define survey design
    dsgn = MEPSSurveyDesign(
        data=FYC, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT16F", nest=True,
    )

    # Overall median
    print("=== Overall expenditure quantiles ===")
    results = survey_quantile(dsgn, ["TOTEXP16"], quantiles=[0.25, 0.50, 0.75])
    for est in results:
        print(f"  {est.variable} q{est.quantile}: {est.estimate:,.2f} (SE: {est.se:,.2f})")

    # Median by race
    print("\n=== Median expenditure by race ===")
    for race_val in ["Hispanic", "White", "Black",
                     "Amer. Indian, AK Native, or mult. races",
                     "Asian, Hawaiian, or Pacific Islander"]:
        sub = dsgn.subset(pl.col("race") == race_val)
        results = survey_quantile(sub, ["TOTEXP16"], quantiles=[0.50])
        for est in results:
            print(f"  {race_val}: {est.estimate:,.2f} (SE: {est.se:,.2f})")

    # Median by sex
    print("\n=== Median expenditure by sex ===")
    for sex_val in ["Male", "Female"]:
        sub = dsgn.subset(pl.col("sex") == sex_val)
        results = survey_quantile(sub, ["TOTEXP16"], quantiles=[0.50])
        for est in results:
            print(f"  {sex_val}: {est.estimate:,.2f} (SE: {est.se:,.2f})")

    # Mean by race and sex (cross-tabulation)
    print("\n=== Mean expenditure by race and sex ===")
    results = survey_by(dsgn, ["TOTEXP16"], by=["race", "sex"], fun="mean")
    for est in results:
        print(f"  {est.by_value} | {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
