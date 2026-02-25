"""Data loading utilities for MEPS PySpark jobs.

Provides functions to load MEPS data from various formats (SAS7BDAT, CSV, SSP)
into PySpark DataFrames. Uses pathlib.Path for all file path handling.
"""

from pathlib import Path
from typing import List, Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import types as T


def get_spark_session(app_name: str = "MEPS-Analysis") -> SparkSession:
    """Get or create a SparkSession configured for MEPS analysis.

    Args:
        app_name: Name for the Spark application.

    Returns:
        A configured SparkSession instance.
    """
    return (
        SparkSession.builder
        .appName(app_name)
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )


def load_meps_data(
    spark: SparkSession,
    file_path: Path,
    columns: Optional[List[str]] = None,
) -> DataFrame:
    """Load MEPS data from a SAS7BDAT, Parquet, or CSV file.

    This is the primary entry point for loading MEPS data files into
    PySpark DataFrames. It automatically detects the file format based
    on the file extension.

    Args:
        spark: Active SparkSession.
        file_path: Path to the data file (.sas7bdat, .parquet, or .csv).
        columns: Optional list of column names to select. If None, all
            columns are loaded.

    Returns:
        A PySpark DataFrame with the requested data.

    Raises:
        ValueError: If the file format is not supported.
        FileNotFoundError: If the file does not exist.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Data file not found: {file_path}")

    suffix = file_path.suffix.lower()

    if suffix == ".sas7bdat":
        df = _load_sas7bdat(spark, file_path)
    elif suffix == ".parquet":
        df = spark.read.parquet(str(file_path))
    elif suffix == ".csv":
        df = spark.read.csv(str(file_path), header=True, inferSchema=True)
    elif suffix == ".ssp":
        df = _load_sas_transport(spark, file_path)
    else:
        raise ValueError(
            f"Unsupported file format: {suffix}. "
            "Supported formats: .sas7bdat, .parquet, .csv, .ssp"
        )

    if columns is not None:
        available = set(df.columns)
        missing = [c for c in columns if c not in available]
        if missing:
            raise ValueError(
                f"Columns not found in data: {missing}. "
                f"Available columns: {sorted(available)}"
            )
        df = df.select(columns)

    return df


def load_meps_csv(
    spark: SparkSession,
    file_path: Path,
    columns: Optional[List[str]] = None,
) -> DataFrame:
    """Load MEPS data from a CSV file.

    Convenience function for CSV-specific loading with schema inference.

    Args:
        spark: Active SparkSession.
        file_path: Path to the CSV file.
        columns: Optional list of column names to select.

    Returns:
        A PySpark DataFrame with the CSV data.
    """
    file_path = Path(file_path)
    df = spark.read.csv(str(file_path), header=True, inferSchema=True)

    if columns is not None:
        df = df.select(columns)

    return df


def _load_sas7bdat(spark: SparkSession, file_path: Path) -> DataFrame:
    """Load a SAS7BDAT file via pandas and convert to PySpark DataFrame.

    Uses pyreadstat to read SAS files when available, falling back
    to pandas for basic SAS file reading.

    Args:
        spark: Active SparkSession.
        file_path: Path to the SAS7BDAT file.

    Returns:
        A PySpark DataFrame with the SAS data.
    """
    try:
        import pyreadstat
        pdf, _ = pyreadstat.read_sas7bdat(str(file_path))
    except ImportError:
        import pandas as pd
        pdf = pd.read_sas(str(file_path), format="sas7bdat")

    return spark.createDataFrame(pdf)


def _load_sas_transport(spark: SparkSession, file_path: Path) -> DataFrame:
    """Load a SAS transport (.ssp) file via pandas.

    Args:
        spark: Active SparkSession.
        file_path: Path to the SAS transport file.

    Returns:
        A PySpark DataFrame with the SAS transport data.
    """
    import pandas as pd
    pdf = pd.read_sas(str(file_path), format="xport")
    return spark.createDataFrame(pdf)


def create_sample_fyc_data(spark: SparkSession, year: int = 2018) -> DataFrame:
    """Create a sample Full-Year Consolidated (FYC) DataFrame for testing.

    Generates synthetic MEPS-like data that can be used for unit testing
    and development without requiring actual MEPS data files.

    Args:
        spark: Active SparkSession.
        year: Data year for variable naming (e.g., 2018 -> TOTEXP18).

    Returns:
        A PySpark DataFrame with synthetic FYC-like data.
    """
    yr = str(year)[2:]

    schema = T.StructType([
        T.StructField("DUPERSID", T.StringType(), False),
        T.StructField(f"TOTEXP{yr}", T.DoubleType(), True),
        T.StructField(f"TOTSLF{yr}", T.DoubleType(), True),
        T.StructField("AGELAST", T.IntegerType(), True),
        T.StructField(f"AGE{yr}X", T.IntegerType(), True),
        T.StructField("AGE42X", T.IntegerType(), True),
        T.StructField("AGE31X", T.IntegerType(), True),
        T.StructField("SEX", T.IntegerType(), True),
        T.StructField("VARSTR", T.IntegerType(), True),
        T.StructField("VARPSU", T.IntegerType(), True),
        T.StructField(f"PERWT{yr}F", T.DoubleType(), True),
        T.StructField(f"INSCOV{yr}", T.IntegerType(), True),
        T.StructField(f"POVCAT{yr}", T.IntegerType(), True),
        T.StructField("RACETHX", T.IntegerType(), True),
        T.StructField("DUID", T.StringType(), True),
        T.StructField("PANEL", T.IntegerType(), True),
    ])

    rows = [
        ("P001", 5000.0, 500.0, 35, 35, 35, 35, 1, 1, 1, 15000.0, 1, 5, 2, "D001", 23),
        ("P002", 0.0, 0.0, 70, 70, 70, 70, 2, 1, 2, 20000.0, 1, 4, 1, "D001", 23),
        ("P003", 12000.0, 1200.0, 45, 45, 45, 45, 1, 2, 1, 18000.0, 2, 3, 3, "D002", 23),
        ("P004", 3000.0, 300.0, 25, 25, 25, 25, 2, 2, 2, 12000.0, 3, 5, 2, "D002", 24),
        ("P005", 85000.0, 8500.0, 80, 80, 80, 80, 1, 1, 1, 25000.0, 1, 2, 4, "D003", 24),
        ("P006", 200.0, 200.0, 10, 10, 10, 10, 2, 1, 2, 16000.0, 1, 4, 2, "D003", 24),
        ("P007", 0.0, 0.0, 55, 55, 55, 55, 1, 2, 1, 14000.0, 2, 3, 5, "D004", 23),
        ("P008", 7500.0, 750.0, 62, 62, 62, 62, 2, 2, 2, 22000.0, 1, 5, 2, "D004", 23),
    ]

    return spark.createDataFrame(rows, schema)
