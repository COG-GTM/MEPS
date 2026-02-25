"""Summary Table: Use, Expenditures, and Population, 2019.

Migrated from: SAS/summary_tables_examples/use_expenditures_2019.sas

Similar to use_expenditures_2016 but for 2019 data.
Note: Starting in 2019, OPU and OPR are dropped from the files.

Input: 2019 Full-Year Consolidated file
"""

from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.data_loader import load_meps_data
from meps.utils.survey_stats import survey_mean


def prepare_data(
    spark: SparkSession,
    input_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Prepare 2019 FYC data with aggregated payment variables."""
    df = input_df

    # For 2019, OPU and OPR are not available
    if "OBVPRV19" in df.columns:
        df = df.withColumn("OBVPTR", F.col("OBVPRV19") + F.col("OBVTRI19"))

    return df


def run(
    spark: SparkSession,
    input_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full analysis pipeline."""
    df = prepare_data(spark, input_df)

    var_cols = [c for c in df.columns if c.startswith(("OBV", "OBD", "OPT"))]
    if not var_cols:
        var_cols = ["TOTEXP19"] if "TOTEXP19" in df.columns else []

    estimates = survey_mean(df, var_cols=var_cols or ["TOTEXP19"], weight_col="PERWT19F") if var_cols else None

    return {"prepared_data": df, "estimates": estimates}
