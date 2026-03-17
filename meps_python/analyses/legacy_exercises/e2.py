"""E2: Average total healthcare expenditures for children ages 0-5, 1996-1999.

Multi-year pooling for children's healthcare expenditures.

Input files: C:/MEPS/h12.ssp through h38.ssp (1996-1999 FYC files)

Ported from: SAS/older_exercises_1996_to_2006/Estimation_examples/E2/E2.sas
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean


def main(data_dir: str = "C:/MEPS") -> None:
    datasets = []
    for year in [1996, 1997, 1998, 1999]:
        suffix = str(year)[2:]
        fyc = read_meps(year=year, file_type="FYC", data_dir=data_dir)
        wt_col = f"PERWT{suffix}F"
        exp_col = f"TOTEXP{suffix}"
        selected = fyc.select([
            "DUPERSID", "VARSTR", "VARPSU", "AGELAST",
            pl.col(wt_col).alias("perwt"),
            pl.col(exp_col).alias("totexp"),
        ])
        datasets.append(selected)

    # Pool and adjust weights
    pool = pl.concat(datasets).with_columns([
        (pl.col("perwt") / 4).alias("poolwt"),
        ((pl.col("AGELAST") >= 0) & (pl.col("AGELAST") <= 5)).cast(pl.Int32).alias("child_0_5"),
    ])

    dsgn = MEPSSurveyDesign(
        data=pool, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="poolwt", nest=True,
    )
    sub = dsgn.subset(pl.col("child_0_5") == 1)

    print("=== Average Total Expenditures, Children 0-5, 1996-1999 ===")
    for est in survey_mean(sub, ["totexp"]):
        print(f"  {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
