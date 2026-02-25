"""I/O helper functions for reading/writing MEPS data files."""

from pathlib import Path
from typing import Optional, List

from pyspark.sql import SparkSession, DataFrame


def read_meps_file(
    spark: SparkSession,
    file_path: str,
    fmt: str = "parquet",
    keep_columns: Optional[List[str]] = None,
) -> DataFrame:
    """Read a MEPS data file into a Spark DataFrame.

    Supports parquet, csv, and sas7bdat (via pandas fallback) formats.

    Args:
        spark: Active SparkSession.
        file_path: Path to the data file (local, S3, ADLS, or DBFS).
        fmt: File format - 'parquet', 'csv', or 'sas7bdat'.
        keep_columns: Optional list of columns to keep after loading.

    Returns:
        Spark DataFrame with the loaded data.
    """
    if fmt == "parquet":
        df = spark.read.parquet(file_path)
    elif fmt == "csv":
        df = spark.read.option("header", "true").option("inferSchema", "true").csv(file_path)
    elif fmt in ("sas7bdat", "sas"):
        import pandas as pd
        pdf = pd.read_sas(file_path, format="sas7bdat")
        df = spark.createDataFrame(pdf)
    elif fmt in ("ssp", "xport"):
        import pandas as pd
        pdf = pd.read_sas(file_path, format="xport")
        df = spark.createDataFrame(pdf)
    elif fmt == "dta":
        import pandas as pd
        pdf = pd.read_stata(file_path)
        df = spark.createDataFrame(pdf)
    else:
        raise ValueError(f"Unsupported format: {fmt}")

    if keep_columns:
        upper_cols = {c.upper(): c for c in df.columns}
        select_cols = []
        for col_name in keep_columns:
            if col_name in df.columns:
                select_cols.append(col_name)
            elif col_name.upper() in upper_cols:
                select_cols.append(upper_cols[col_name.upper()])
        df = df.select(select_cols)

    return df


def write_parquet(df: DataFrame, output_path: str, mode: str = "overwrite") -> None:
    """Write a Spark DataFrame to Parquet format.

    Args:
        df: Spark DataFrame to write.
        output_path: Destination path for the Parquet file(s).
        mode: Write mode ('overwrite', 'append', 'error', 'ignore').
    """
    df.write.mode(mode).parquet(output_path)


def ensure_output_dir(path: str) -> None:
    """Ensure the output directory exists (local filesystem only).

    Args:
        path: Directory path to create if it doesn't exist.
    """
    Path(path).mkdir(parents=True, exist_ok=True)
