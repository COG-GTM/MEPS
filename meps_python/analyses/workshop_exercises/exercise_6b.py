"""Exercise 6b: Multiple logistic regressions - COVID delay analysis, 2020.

Multiple logistic regressions for persons delaying care due to COVID:
 - Percentage of people who delayed care (medical, dental, PMED)
 - Three logistic regressions with same predictor set

Input file: C:/MEPS/h224.dta (2020 Full-year file)

Ported from: R/workshop_exercises/exercise_4b.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean
from meps.survey.regression import survey_glm


def main(data_dir: str = "C:/MEPS") -> None:
    fyc20 = read_meps(year=2020, file_type="FYC", data_dir=data_dir)

    # Keep needed variables
    fyc20_sub = fyc20.select([
        "DUPERSID", "VARPSU", "VARSTR", "PERWT20F",
        "CVDLAYCA53", "CVDLAYDN53", "CVDLAYPM53",
        "AGELAST", "SEX", "RACETHX", "INSCOV20", "REGION53",
    ])

    # Create variables
    fyc20x = fyc20_sub.with_columns([
        # Convert from 1/2 to 1/0
        pl.when(pl.col("CVDLAYCA53").cast(pl.Float64) == 1).then(1)
        .when(pl.col("CVDLAYCA53").cast(pl.Float64) == 2).then(0)
        .otherwise(pl.col("CVDLAYCA53").cast(pl.Float64))
        .alias("covid_delay_CARE"),

        pl.when(pl.col("CVDLAYDN53").cast(pl.Float64) == 1).then(1)
        .when(pl.col("CVDLAYDN53").cast(pl.Float64) == 2).then(0)
        .otherwise(pl.col("CVDLAYDN53").cast(pl.Float64))
        .alias("covid_delay_DENTAL"),

        pl.when(pl.col("CVDLAYPM53").cast(pl.Float64) == 1).then(1)
        .when(pl.col("CVDLAYPM53").cast(pl.Float64) == 2).then(0)
        .otherwise(pl.col("CVDLAYPM53").cast(pl.Float64))
        .alias("covid_delay_PMED"),

        # Subpopulations
        (pl.col("CVDLAYCA53").cast(pl.Float64) >= 0).cast(pl.Int32).alias("subpop_CARE"),
        (pl.col("CVDLAYDN53").cast(pl.Float64) >= 0).cast(pl.Int32).alias("subpop_DENTAL"),
        (pl.col("CVDLAYPM53").cast(pl.Float64) >= 0).cast(pl.Int32).alias("subpop_PMED"),

        # Factor variables
        pl.col("SEX").cast(pl.Utf8).alias("SEX_f"),
        pl.col("RACETHX").cast(pl.Utf8).alias("RACETHX_f"),
        pl.col("INSCOV20").cast(pl.Utf8).alias("INSCOV20_f"),
        pl.col("REGION53").cast(pl.Utf8).alias("REGION53_f"),
    ])

    # Survey design
    dsgn = MEPSSurveyDesign(
        data=fyc20x, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT20F", nest=True,
    )

    # Percentage delaying care
    print("=== Percentage delaying care ===")
    for outcome, subpop in [("covid_delay_CARE", "subpop_CARE"),
                            ("covid_delay_DENTAL", "subpop_DENTAL"),
                            ("covid_delay_PMED", "subpop_PMED")]:
        sub = dsgn.subset(pl.col(subpop) == 1)
        for est in survey_mean(sub, [outcome]):
            print(f"  {est.variable}: {est.estimate:.4f} (SE: {est.se:.4f})")

    # Logistic regressions
    predictors = "AGELAST + C(SEX_f) + C(RACETHX_f) + C(INSCOV20_f) + C(REGION53_f)"

    for outcome, subpop, label in [
        ("covid_delay_CARE", "subpop_CARE", "Delaying Medical Care"),
        ("covid_delay_DENTAL", "subpop_DENTAL", "Delaying Dental Care"),
        ("covid_delay_PMED", "subpop_PMED", "Delaying PMEDs"),
    ]:
        print(f"\n=== Logistic Regression: {label} ===")
        sub = dsgn.subset(pl.col(subpop) == 1)
        formula = f"{outcome} ~ {predictors}"
        result = survey_glm(formula, sub, family="quasibinomial")
        print(result.summary())


if __name__ == "__main__":
    main()
