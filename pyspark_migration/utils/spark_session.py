"""Utility to create and manage SparkSession for MEPS ETL jobs."""

from pyspark.sql import SparkSession


def get_spark_session(app_name: str = "MEPS_PySpark_Migration") -> SparkSession:
    """Create or get an existing SparkSession.

    Args:
        app_name: Name of the Spark application.

    Returns:
        SparkSession instance.
    """
    return (
        SparkSession.builder
        .appName(app_name)
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.driver.memory", "4g")
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY")
        .getOrCreate()
    )
