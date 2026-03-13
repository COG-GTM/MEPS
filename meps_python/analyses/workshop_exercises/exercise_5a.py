"""Exercise 5a: Family-level variable construction, 2018.

Family-level expenditure aggregation from person-level data:
 - Aggregate person-level variables to CPS family level
 - Family-level expenditure summation

Input file: C:/MEPS/h209.dta (2018 Full-year file)

Ported from: SAS/workshop_exercises/exercise_5a
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean, survey_total
from meps.transforms.family import aggregate_to_family, create_family_expenditure_vars


def main(data_dir: str = "C:/MEPS") -> None:
    fyc18 = read_meps(year=2018, file_type="FYC", data_dir=data_dir)

    # Select needed variables
    fyc18_sub = fyc18.select([
        "DUPERSID", "CPSFAMID", "DUID", "VARSTR", "VARPSU", "PERWT18F",
        "TOTEXP18", "TOTSLF18", "AGELAST", "SEX",
    ])

    # Create family ID
    fyc18_sub = fyc18_sub.with_columns(
        (pl.col("DUID").cast(pl.Utf8) + pl.col("CPSFAMID").cast(pl.Utf8)).alias("FAMID")
    )

    # Aggregate to family level
    fam18 = aggregate_to_family(
        data=fyc18_sub,
        family_id_col="FAMID",
        expenditure_cols=["TOTEXP18", "TOTSLF18"],
        count_cols=[],
        max_cols=[],
        weight_col="PERWT18F",
        strata_col="VARSTR",
        psu_col="VARPSU",
    )

    # Create per-capita variables
    fam18 = create_family_expenditure_vars(fam18, year_suffix="18")

    print(f"Number of families: {fam18.height}")
    print(fam18.head())

    # Define survey design at family level
    fam_dsgn = MEPSSurveyDesign(
        data=fam18, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT18F", nest=True,
    )

    # Family-level estimates
    print("\n=== Family-level Total Expenditures ===")
    for est in survey_total(fam_dsgn, ["TOTEXP18"]):
        print(f"  {est.variable}: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    print("\n=== Mean Family Expenditure ===")
    for est in survey_mean(fam_dsgn, ["TOTEXP18"]):
        print(f"  {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
