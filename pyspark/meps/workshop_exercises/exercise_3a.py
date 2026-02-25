"""Exercise 3a: Medical Conditions - Diabetes, 2015.

Migrated from: SAS/workshop_exercises/exercise_3a/Exercise3a.sas

Illustrates how to identify persons with a condition (diabetes) and
calculate estimates on use and expenditures:
  - Unweighted/weighted counts of persons with diabetes
  - Mean expenditures for persons with diabetes, by sex

Input files:
  - 2015 Condition PUF (HC-180)
  - 2015 Full-Year Consolidated file (HC-181)

SAS → PySpark Migration Notes:
  - CCCODEX IN ('049','050') → filter with isin()
  - PROC SORT NODUPKEY       → dropDuplicates()
  - MERGE with IN= flags     → join with indicator
  - PROC SURVEYMEANS DOMAIN  → survey_mean_by_domain()
"""

from pathlib import Path
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.data_loader import load_meps_data
from meps.utils.survey_stats import survey_mean_by_domain, survey_freq


def identify_diabetes(
    spark: SparkSession,
    cond_path: Optional[Path] = None,
    cond_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Pull out conditions with diabetes (CCS CODE='049','050').

    Args:
        spark: Active SparkSession.
        cond_path: Path to H180 condition file.
        cond_df: Pre-loaded conditions DataFrame (for testing).

    Returns:
        DataFrame filtered to diabetes conditions.
    """
    if cond_df is not None:
        df = cond_df
    else:
        df = load_meps_data(spark, cond_path)

    return df.filter(F.col("CCCODEX").isin("049", "050"))


def get_diabetes_persons(diab_df: DataFrame) -> DataFrame:
    """Get unique persons who reported diabetes.

    Replicates: PROC SORT NODUPKEY; BY DUPERSID;

    Args:
        diab_df: DataFrame of diabetes conditions.

    Returns:
        DataFrame with unique DUPERSID values.
    """
    return diab_df.select("DUPERSID").dropDuplicates()


def create_diabetes_flag(
    spark: SparkSession,
    diab_persons_df: DataFrame,
    fyc_path: Optional[Path] = None,
    fyc_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Create diabetes flag in the FYC file.

    Replicates the SAS MERGE with IN= to create DIABPERS flag.

    Args:
        spark: Active SparkSession.
        diab_persons_df: Unique diabetes person IDs.
        fyc_path: Path to H181 FYC file.
        fyc_df: Pre-loaded FYC DataFrame (for testing).

    Returns:
        FYC DataFrame with DIABPERS flag (1=Yes, 2=No).
    """
    if fyc_df is not None:
        fy = fyc_df
    else:
        fy = load_meps_data(spark, fyc_path)

    diab_flag = diab_persons_df.withColumn("_has_diabetes", F.lit(True))

    merged = fy.join(diab_flag, on="DUPERSID", how="left")

    merged = merged.withColumn(
        "DIABPERS",
        F.when(F.col("_has_diabetes") == True, 1).otherwise(2)
    ).drop("_has_diabetes")

    return merged


def estimate_diabetes_expenditures(df: DataFrame) -> DataFrame:
    """Calculate estimates on use and expenditures for diabetes persons.

    Replicates: PROC SURVEYMEANS DOMAIN DIABPERS('1') SEX*DIABPERS('1');

    Args:
        df: FYC DataFrame with DIABPERS flag.

    Returns:
        Tuple of (overall estimates, by-sex estimates).
    """
    overall = survey_mean_by_domain(
        df,
        var_cols=["TOTEXP15", "TOTSLF15", "OBTOTV15"],
        domain_col="DIABPERS",
        domain_value=1,
        weight_col="PERWT15F",
    )

    by_sex = survey_mean_by_domain(
        df,
        var_cols=["TOTEXP15", "TOTSLF15", "OBTOTV15"],
        domain_col="DIABPERS",
        domain_value=1,
        weight_col="PERWT15F",
        by_col="SEX",
    )

    return overall, by_sex


def run(
    spark: SparkSession,
    fyc_path: Optional[Path] = None,
    cond_path: Optional[Path] = None,
    fyc_df: Optional[DataFrame] = None,
    cond_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full Exercise 3a analysis pipeline.

    Args:
        spark: Active SparkSession.
        fyc_path: Path to H181 FYC file.
        cond_path: Path to H180 condition file.
        fyc_df: Pre-loaded FYC DataFrame (for testing).
        cond_df: Pre-loaded conditions DataFrame (for testing).

    Returns:
        Dictionary with all analysis results.
    """
    diab = identify_diabetes(spark, cond_path, cond_df)
    diab_persons = get_diabetes_persons(diab)
    merged = create_diabetes_flag(spark, diab_persons, fyc_path, fyc_df)

    # Frequency checks
    diab_freq = survey_freq(merged, "DIABPERS", "PERWT15F")

    overall, by_sex = estimate_diabetes_expenditures(merged)

    return {
        "diabetes_conditions": diab,
        "diabetes_persons": diab_persons,
        "merged_data": merged,
        "diabetes_frequency": diab_freq,
        "overall_estimates": overall,
        "by_sex_estimates": by_sex,
    }
