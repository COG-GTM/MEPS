"""Exercise 6b: Logistic Regression for Delayed Care due to COVID, 2020.

Migrated from: SAS/workshop_exercises/exercise_6b/exercise6.sas

Includes 3 logistic regression models, each with a separate dependent variable:
  - DELAYED_CARE_MED: Delayed medical care for COVID
  - DELAYED_CARE_DENTAL: Delayed dental care for COVID
  - DELAYED_CARE_PMEDS: Delayed prescribed medicines for COVID

Covariates: age, gender, race/ethnicity, insurance coverage, region

Input: 2020 Full-Year Consolidated file (HC-224)

SAS → PySpark Migration Notes:
  - ARRAY x[3] / ARRAY y[3] / DO loop → Column-wise recoding
  - REGION53 recode (-1 → null) → F.when()
  - Three PROC SURVEYLOGISTIC → Three survey_logistic_regression() calls
"""

from pathlib import Path
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.data_loader import load_meps_data
from meps.utils.survey_stats import survey_mean
from meps.utils.survey_logistic import survey_logistic_regression


DELAYED_CARE_VARS = [
    "DELAYED_CARE_MED",
    "DELAYED_CARE_DENTAL",
    "DELAYED_CARE_PMEDS",
]


def prepare_data(
    spark: SparkSession,
    data_path: Optional[Path] = None,
    input_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Read and prepare 2020 FYC data for delayed care analysis.

    Recodes CVDLAY* variables from 1/2 to 1/0 (Yes/No).
    Recodes REGION53 (-1 → null).

    Args:
        spark: Active SparkSession.
        data_path: Path to H224 data file.
        input_df: Pre-loaded DataFrame (for testing).

    Returns:
        Prepared DataFrame with recoded variables.
    """
    columns = [
        "VARSTR", "VARPSU", "PERWT20F",
        "CVDLAYCA53", "CVDLAYPM53", "CVDLAYDN53",
        "AGELAST", "SEX", "RACETHX", "POVCAT20",
        "INSCOV20", "REGION53",
    ]

    if input_df is not None:
        df = input_df
    else:
        df = load_meps_data(spark, data_path, columns)

    # Recode region
    df = df.withColumn(
        "REGION",
        F.when(F.col("REGION53") == -1, None).otherwise(F.col("REGION53"))
    )

    # Recode delayed care variables (1=Yes, 2→0=No, <0→null)
    recode_mapping = [
        ("CVDLAYCA53", "DELAYED_CARE_MED"),
        ("CVDLAYDN53", "DELAYED_CARE_DENTAL"),
        ("CVDLAYPM53", "DELAYED_CARE_PMEDS"),
    ]

    for src_col, dst_col in recode_mapping:
        df = df.withColumn(
            dst_col,
            F.when(F.col(src_col) == 1, 1)
            .when(F.col(src_col) == 2, 0)
            .when(F.col(src_col) < 0, None)
        )

    return df


def estimate_proportions(df: DataFrame) -> DataFrame:
    """Estimate proportion of persons with delayed care events.

    Replicates: PROC SURVEYMEANS VAR delayed_care_*;

    Args:
        df: Prepared DataFrame.

    Returns:
        DataFrame with proportion estimates.
    """
    return survey_mean(
        df,
        var_cols=DELAYED_CARE_VARS,
        weight_col="PERWT20F",
    )


def run_logistic_regressions(df: DataFrame) -> dict:
    """Run 3 survey logistic regressions for delayed care outcomes.

    Each model uses the same covariates:
      CLASS sex(ref='1. male') racethx(ref='1. hispanic')
            inscov20(ref='1. any private') region(ref='1. northeast')
      MODEL delayed_care_*(ref='0') = agelast sex racethx inscov20 region

    Args:
        df: Prepared DataFrame.

    Returns:
        Dictionary mapping outcome variable name to regression results.
    """
    results = {}

    common_args = dict(
        independent_vars=["AGELAST", "SEX", "RACETHX", "INSCOV20", "REGION"],
        class_vars=["SEX", "RACETHX", "INSCOV20", "REGION"],
        ref_levels={
            "SEX": "1",         # Male
            "RACETHX": "1",     # Hispanic
            "INSCOV20": "1",    # Any Private
            "REGION": "1",      # Northeast
        },
        weight_col="PERWT20F",
    )

    for var in DELAYED_CARE_VARS:
        valid_df = df.filter(F.col(var).isNotNull() & F.col("REGION").isNotNull())
        results[var] = survey_logistic_regression(
            valid_df,
            dependent_var=var,
            **common_args,
        )

    return results


def run(
    spark: SparkSession,
    data_path: Optional[Path] = None,
    input_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full Exercise 6b analysis pipeline.

    Args:
        spark: Active SparkSession.
        data_path: Path to H224 data file.
        input_df: Pre-loaded DataFrame (for testing).

    Returns:
        Dictionary with all analysis results.
    """
    df = prepare_data(spark, data_path, input_df)
    proportions = estimate_proportions(df)
    regressions = run_logistic_regressions(df)

    return {
        "prepared_data": df,
        "proportions": proportions,
        "logistic_regressions": regressions,
    }
