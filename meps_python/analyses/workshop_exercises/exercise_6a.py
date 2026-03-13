"""Exercise 6a: Logistic regression - Flu shot analysis, 2018.

Logistic regression with survey weights:
 - Percentage of people with a flu shot
 - Logistic regression: flu_shot ~ AGELAST + SEX + RACETHX + INSCOV18
 - Marginal effects

Input file: C:/MEPS/h209.dta (2018 Full-year file)

Ported from: R/workshop_exercises/exercise_4a.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean
from meps.survey.regression import survey_glm, survey_margins


def main(data_dir: str = "C:/MEPS") -> None:
    fyc18 = read_meps(year=2018, file_type="FYC", data_dir=data_dir)

    # Keep needed variables
    fyc18_sub = fyc18.select([
        "DUPERSID", "VARPSU", "VARSTR",
        "ADFLST42", "AGELAST", "SEX", "RACETHX", "INSCOV18", "SAQWT18F",
    ])

    # Create variables
    fyc18x = fyc18_sub.with_columns([
        # Convert ADFLST42 from 1/2 to 1/0
        pl.when(pl.col("ADFLST42") == 1).then(1)
        .when(pl.col("ADFLST42") == 2).then(0)
        .otherwise(pl.col("ADFLST42"))
        .alias("flu_shot"),
        # Subpop: exclude missing ADFLST42
        (pl.col("ADFLST42") >= 0).cast(pl.Int32).alias("subpop"),
    ])

    # Convert categorical variables to factors
    fyc18x = fyc18x.with_columns([
        pl.col("SEX").cast(pl.Utf8).alias("SEX_f"),
        pl.col("RACETHX").cast(pl.Utf8).alias("RACETHX_f"),
        pl.col("INSCOV18").cast(pl.Utf8).alias("INSCOV18_f"),
    ])

    # Define survey design with SAQ weight
    dsgn = MEPSSurveyDesign(
        data=fyc18x, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="SAQWT18F", nest=True,
    )
    flu_dsgn = dsgn.subset(pl.col("subpop") == 1)

    # Percentage with flu shot
    print("=== Percentage with flu shot ===")
    for est in survey_mean(flu_dsgn, ["flu_shot"]):
        print(f"  {est.variable}: {est.estimate:.4f} (SE: {est.se:.4f})")

    # Logistic regression
    print("\n=== Logistic Regression ===")
    formula = "flu_shot ~ AGELAST + C(SEX_f) + C(RACETHX_f) + C(INSCOV18_f)"
    result = survey_glm(formula, flu_dsgn, family="quasibinomial")
    print(result.summary())

    # Marginal effects
    print("\n=== Marginal Effects ===")
    margins = survey_margins(result, flu_dsgn, variables=["AGELAST", "SEX_f", "RACETHX_f", "INSCOV18_f"])
    print(margins)


if __name__ == "__main__":
    main()
