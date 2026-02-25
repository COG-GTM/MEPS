"""Exercise 5a: Constructing Family-Level Variables, 2015.

Migrated from: SAS/workshop_exercises/exercise_5a/Exercise5a.sas

Illustrates how to construct family-level variables from person-level data.
Uses CPS Family definition (DUID + CPSFAMID) with weight FAMWT15C.

Calculates family-level estimates for:
  - Family size
  - Family out-of-pocket expenditures (TOTSLF15)
  - Family income (TTLP15X)

Input: 2015 Full-Year Consolidated file (HC-181)

SAS → PySpark Migration Notes:
  - BY DUID CPSFAMID with FIRST./LAST. → Window functions / groupBy
  - Running sums (FAMSIZE + 1)          → groupBy().agg(count, sum)
  - OUTPUT PERS2 / OUTPUT FAM           → Two separate DataFrames
  - MERGE for family weights             → join
  - PROC SURVEYMEANS                     → survey_mean()
"""

from pathlib import Path
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F
from pyspark.sql import Window

from meps.utils.data_loader import load_meps_data
from meps.utils.survey_stats import survey_mean


def prepare_person_data(
    spark: SparkSession,
    data_path: Optional[Path] = None,
    input_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Read and prepare person-level data for family aggregation.

    Args:
        spark: Active SparkSession.
        data_path: Path to H181 data file.
        input_df: Pre-loaded DataFrame (for testing).

    Returns:
        Sorted person-level DataFrame.
    """
    columns = [
        "DUPERSID", "DUID", "CPSFAMID", "FAMWT15C",
        "VARSTR", "VARPSU", "TOTSLF15", "TTLP15X",
    ]

    if input_df is not None:
        df = input_df
    else:
        df = load_meps_data(spark, data_path, columns)

    return df.orderBy("DUID", "CPSFAMID")


def create_family_variables(person_df: DataFrame) -> tuple:
    """Create family-level variables from person-level data.

    Replicates the SAS BY-group processing with FIRST./LAST. logic
    using PySpark groupBy aggregation.

    Family-level variables created:
      - FAMSIZE: Number of persons per CPS family
      - FAMOOP: Total out-of-pocket expenditures per family
      - FAMINC: Total income per family

    Args:
        person_df: Person-level DataFrame sorted by DUID, CPSFAMID.

    Returns:
        Tuple of (person_with_running_totals, family_level DataFrame).
    """
    # Create family-level aggregates
    family_df = (
        person_df.groupBy("DUID", "CPSFAMID")
        .agg(
            F.count("*").alias("FAMSIZE"),
            F.sum("TOTSLF15").alias("FAMOOP"),
            F.sum("TTLP15X").alias("FAMINC"),
        )
    )

    # Create person-level with running totals using window functions
    w = Window.partitionBy("DUID", "CPSFAMID").orderBy("DUPERSID").rowsBetween(
        Window.unboundedPreceding, Window.currentRow
    )

    person_enriched = (
        person_df
        .withColumn("FAMSIZE_RUNNING", F.count("*").over(w))
        .withColumn("FAMOOP_RUNNING", F.sum("TOTSLF15").over(w))
        .withColumn("FAMINC_RUNNING", F.sum("TTLP15X").over(w))
    )

    return person_enriched, family_df


def add_family_weights(
    family_df: DataFrame,
    person_df: DataFrame,
) -> DataFrame:
    """Add family weights and survey design variables to family data.

    Replicates: PROC SORT WHERE=(FAMWT15C>0) NODUPKEY; MERGE;

    Args:
        family_df: Family-level DataFrame.
        person_df: Person-level DataFrame with FAMWT15C.

    Returns:
        Family DataFrame with weights and survey design variables.
    """
    # Get one weight record per family (first person with positive weight)
    fam_weights = (
        person_df
        .filter(F.col("FAMWT15C") > 0)
        .select("DUID", "CPSFAMID", "FAMWT15C", "VARSTR", "VARPSU")
        .dropDuplicates(["DUID", "CPSFAMID"])
    )

    return family_df.join(fam_weights, on=["DUID", "CPSFAMID"], how="inner")


def estimate_family_level(fam_df: DataFrame) -> DataFrame:
    """Calculate family-level estimates using survey weights.

    Replicates: PROC SURVEYMEANS VAR FAMSIZE FAMOOP FAMINC;

    Args:
        fam_df: Family DataFrame with weights.

    Returns:
        DataFrame with survey mean estimates.
    """
    return survey_mean(
        fam_df,
        var_cols=["FAMSIZE", "FAMOOP", "FAMINC"],
        weight_col="FAMWT15C",
    )


def run(
    spark: SparkSession,
    data_path: Optional[Path] = None,
    input_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full Exercise 5a analysis pipeline.

    Args:
        spark: Active SparkSession.
        data_path: Path to H181 data file.
        input_df: Pre-loaded DataFrame (for testing).

    Returns:
        Dictionary with all analysis results.
    """
    person_df = prepare_person_data(spark, data_path, input_df)
    person_enriched, family_df = create_family_variables(person_df)
    fam_with_weights = add_family_weights(family_df, person_df)
    estimates = estimate_family_level(fam_with_weights)

    return {
        "person_data": person_enriched,
        "family_data": family_df,
        "family_with_weights": fam_with_weights,
        "estimates": estimates,
    }
