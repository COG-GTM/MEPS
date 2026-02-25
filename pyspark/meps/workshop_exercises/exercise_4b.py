"""Exercise 4b: Pooling MEPS Longitudinal Data Files from Different Panels.

Migrated from: SAS/workshop_exercises/exercise_4b/Exercise4b.sas

Illustrates how to pool MEPS longitudinal data files from different panels.
Example: Panels 17-19, population age 26-30, uninsured, high income in first year.

Input files:
  - Panel 19 Longitudinal file (HC-183)
  - Panel 18 Longitudinal file (HC-172)
  - Panel 17 Longitudinal file (HC-164)

SAS → PySpark Migration Notes:
  - SET with multiple datasets → union()
  - POOLWT = LONGWT/3 → withColumn arithmetic
  - PROC SURVEYMEANS CLASS → survey_freq()
  - DOMAIN SUBPOP('1') → survey_mean_by_domain()
"""

from pathlib import Path
from typing import List, Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.data_loader import load_meps_data
from meps.utils.survey_stats import survey_mean_by_domain, survey_freq


def pool_panels(
    panel_dfs: List[DataFrame],
    n_panels: int = 3,
) -> DataFrame:
    """Pool longitudinal panel data with adjusted weights.

    Creates:
      - POOLWT = LONGWT / n_panels
      - SUBPOP = 1 if age 26-30 in year 1, uninsured in year 1, high income

    Args:
        panel_dfs: List of panel DataFrames with standardized columns.
        n_panels: Number of panels being pooled (for weight adjustment).

    Returns:
        Pooled DataFrame with SUBPOP flag and POOLWT.
    """
    columns = [
        "DUPERSID", "INSCOVY1", "INSCOVY2", "LONGWT",
        "VARSTR", "VARPSU", "POVCATY1", "AGEY1X", "PANEL",
    ]

    result = panel_dfs[0].select(
        [c for c in columns if c in panel_dfs[0].columns]
    )
    for df in panel_dfs[1:]:
        result = result.union(
            df.select([c for c in columns if c in df.columns])
        )

    result = result.withColumn("POOLWT", F.col("LONGWT") / F.lit(n_panels))

    result = result.withColumn(
        "SUBPOP",
        F.when(
            (F.col("INSCOVY1") == 3)
            & (F.col("AGEY1X") >= 26)
            & (F.col("AGEY1X") <= 30)
            & (F.col("POVCATY1") == 5),
            1
        ).otherwise(2)
    )

    return result


def estimate_insurance_year2(df: DataFrame) -> DataFrame:
    """Estimate insurance status in year 2 for the subpopulation.

    Replicates: PROC SURVEYMEANS VAR INSCOVY2; CLASS INSCOVY2;
                DOMAIN SUBPOP('1');

    Args:
        df: Pooled DataFrame.

    Returns:
        DataFrame with domain estimates for insurance status in year 2.
    """
    return survey_mean_by_domain(
        df,
        var_cols=["INSCOVY2"],
        domain_col="SUBPOP",
        domain_value=1,
        weight_col="POOLWT",
    )


def run(
    spark: SparkSession,
    panel_dfs: Optional[List[DataFrame]] = None,
) -> dict:
    """Execute the full Exercise 4b analysis pipeline.

    Args:
        spark: Active SparkSession.
        panel_dfs: List of panel DataFrames (for testing).

    Returns:
        Dictionary with all analysis results.
    """
    pooled = pool_panels(panel_dfs)
    estimates = estimate_insurance_year2(pooled)

    return {
        "pooled_data": pooled,
        "estimates": estimates,
    }
