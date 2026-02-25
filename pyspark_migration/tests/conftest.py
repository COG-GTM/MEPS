"""Pytest configuration and shared fixtures for MEPS PySpark migration tests.

Provides a shared SparkSession fixture (session-scoped) and helper functions
for creating test DataFrames.
"""

import pytest
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark():
    """Create a session-scoped SparkSession for all tests.

    Uses local mode with minimal resources for testing.
    """
    session = (
        SparkSession.builder
        .appName("MEPS_PySpark_Migration_Tests")
        .master("local[2]")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.driver.memory", "2g")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY")
        .getOrCreate()
    )
    yield session
    session.stop()


@pytest.fixture
def sample_fyc_2016(spark):
    """Create a minimal FYC 2016-like DataFrame for testing."""
    data = [
        ("P001", 100.0, 50.0, 50.0, 30, 30, 30, 1001, 1, 1.0),
        ("P002", 0.0, 0.0, 0.0, 70, 70, 70, 1002, 2, 1.0),
        ("P003", 500.0, 200.0, 300.0, 45, -1, 45, 1001, 1, 2.0),
        ("P004", 250.0, 100.0, 150.0, 20, 20, 20, 1002, 2, 1.5),
    ]
    schema = [
        "DUPERSID", "TOTEXP16", "IPDEXP16", "RXEXP16",
        "AGE16X", "AGE42X", "AGE31X", "VARSTR", "VARPSU", "PERWT16F",
    ]
    return spark.createDataFrame(data, schema)


@pytest.fixture
def sample_fyc_2020(spark):
    """Create a minimal FYC 2020-like DataFrame for testing."""
    data = [
        ("P001", 1, 35, 1, 3, 1001, 1, 1.0),
        ("P002", 2, 70, 2, 5, 1002, 2, 1.5),
        ("P003", 1, 50, 1, 4, 1001, 1, 2.0),
        ("P004", 2, 25, 2, 1, 1002, 2, 0.5),
    ]
    schema = [
        "DUPERSID", "SEX", "AGELAST", "CHOLDX", "POVCAT20",
        "VARSTR", "VARPSU", "PERWT20F",
    ]
    return spark.createDataFrame(data, schema)


@pytest.fixture
def sample_pmed_2020(spark):
    """Create a minimal PMED 2020-like DataFrame for testing."""
    data = [
        ("P001", "D001", "R001", "E001", "ATORVASTATIN", 50.0),
        ("P001", "D001", "R002", "E001", "ATORVASTATIN", 50.0),
        ("P001", "D002", "R003", "E002", "SIMVASTATIN", 30.0),
        ("P003", "D003", "R004", "E003", "ROSUVASTATIN", 75.0),
    ]
    schema = ["DUPERSID", "DRUGIDX", "RXRECIDX", "LINKIDX", "RXDRGNAM", "RXXP20X"]
    return spark.createDataFrame(data, schema)


@pytest.fixture
def sample_conditions_2020(spark):
    """Create a minimal Conditions 2020-like DataFrame for testing."""
    data = [
        ("P001", "C001", "E78", "END010", "", ""),
        ("P001", "C002", "E78", "END010", "", ""),
        ("P003", "C003", "E78", "", "END010", ""),
        ("P004", "C004", "I10", "CIR007", "", ""),
    ]
    schema = ["DUPERSID", "CONDIDX", "ICD10CDX", "CCSR1X", "CCSR2X", "CCSR3X"]
    return spark.createDataFrame(data, schema)


@pytest.fixture
def sample_clnk_2020(spark):
    """Create a minimal CLNK 2020-like DataFrame for testing."""
    data = [
        ("P001", "C001", "E001", 8),
        ("P001", "C002", "E001", 8),
        ("P001", "C001", "E002", 8),
        ("P003", "C003", "E003", 8),
    ]
    schema = ["DUPERSID", "CONDIDX", "EVNTIDX", "EVENTYPE"]
    return spark.createDataFrame(data, schema)
