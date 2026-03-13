"""E4: Family-level estimates for healthcare expenditures, 2001.

Family-level expenditure estimates using CPS family aggregation.

Input file: C:/MEPS/h60.ssp (2001 Full-year consolidated)

Ported from: SAS/older_exercises_1996_to_2006/Estimation_examples/E4/E4.sas
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean, survey_total
from meps.transforms.family import aggregate_to_family


def main(data_dir: str = "C:/MEPS") -> None:
    fyc01 = read_meps(year=2001, file_type="FYC", data_dir=data_dir)

    fyc01 = fyc01.with_columns(
        (pl.col("DUID").cast(pl.Utf8) + pl.col("CPSFAMID").cast(pl.Utf8)).alias("FAMID")
    )

    fam01 = aggregate_to_family(
        data=fyc01,
        family_id_col="FAMID",
        expenditure_cols=["TOTEXP01"],
        count_cols=[],
        max_cols=[],
        weight_col="PERWT01F",
        strata_col="VARSTR",
        psu_col="VARPSU",
    )

    dsgn = MEPSSurveyDesign(
        data=fam01, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT01F", nest=True,
    )

    print("=== Family-level Total Expenditures, 2001 ===")
    for est in survey_total(dsgn, ["TOTEXP01"]):
        print(f"  {est.variable}: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    print("\n=== Mean Family Expenditure ===")
    for est in survey_mean(dsgn, ["TOTEXP01"]):
        print(f"  {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
