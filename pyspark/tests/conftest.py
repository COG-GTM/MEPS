"""Shared test fixtures for MEPS PySpark migration tests.

Provides SparkSession, sample DataFrames, and helper utilities
used across all test modules.
"""

import pytest
from pyspark.sql import SparkSession
from pyspark.sql import Row
import pyspark.sql.types as T


@pytest.fixture(scope="session")
def spark():
    """Create a shared SparkSession for all tests."""
    session = (
        SparkSession.builder
        .master("local[2]")
        .appName("meps-tests")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.driver.memory", "1g")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse-test")
        .getOrCreate()
    )
    yield session
    session.stop()


@pytest.fixture
def sample_fyc_2016(spark):
    """Sample 2016 Full-Year Consolidated data."""
    schema = T.StructType([
        T.StructField("DUPERSID", T.StringType()),
        T.StructField("VARSTR", T.StringType()),
        T.StructField("VARPSU", T.IntegerType()),
        T.StructField("PERWT16F", T.DoubleType()),
        T.StructField("TOTEXP16", T.DoubleType()),
        T.StructField("TOTSLF16", T.DoubleType()),
        T.StructField("AGELAST", T.IntegerType()),
        T.StructField("SEX", T.IntegerType()),
        T.StructField("RACETHX", T.IntegerType()),
        T.StructField("RACEV1X", T.IntegerType()),
        T.StructField("INSCOV16", T.IntegerType()),
        T.StructField("INSURC16", T.IntegerType()),
        T.StructField("POVCAT16", T.IntegerType()),
        T.StructField("OBTOTV16", T.IntegerType()),
        T.StructField("OPTOTV16", T.IntegerType()),
        T.StructField("ERTOT16", T.IntegerType()),
        T.StructField("IPDIS16", T.IntegerType()),
        T.StructField("HHTOTD16", T.IntegerType()),
        T.StructField("RXTOT16", T.IntegerType()),
    ])
    data = [
        ("P001", "S1", 1, 5000.0, 1200.0, 300.0, 35, 1, 2, 1, 1, 1, 3, 5, 1, 0, 0, 0, 3),
        ("P002", "S1", 2, 6000.0, 800.0, 200.0, 55, 2, 1, 1, 1, 1, 4, 3, 0, 1, 0, 0, 5),
        ("P003", "S2", 1, 4000.0, 2500.0, 600.0, 70, 1, 3, 2, 2, 5, 2, 8, 2, 0, 1, 1, 10),
        ("P004", "S2", 2, 5500.0, 0.0, 0.0, 10, 2, 2, 1, 1, 1, 5, 0, 0, 0, 0, 0, 0),
        ("P005", "S1", 1, 3000.0, 500.0, 150.0, 28, 1, 4, 4, 3, 3, 1, 2, 0, 0, 0, 0, 1),
        ("P006", "S1", 2, 7000.0, 3500.0, 800.0, 45, 2, 5, 5, 1, 1, 5, 6, 1, 0, 0, 0, 7),
        ("P007", "S2", 1, 4500.0, 150.0, 50.0, 22, 1, 1, 1, 1, 1, 3, 1, 0, 0, 0, 0, 2),
        ("P008", "S2", 2, 5200.0, 950.0, 250.0, 67, 2, 2, 1, 2, 4, 4, 4, 1, 0, 0, 0, 4),
    ]
    return spark.createDataFrame(data, schema)


@pytest.fixture
def sample_fyc_2015(spark):
    """Sample 2015 Full-Year Consolidated data."""
    schema = T.StructType([
        T.StructField("DUPERSID", T.StringType()),
        T.StructField("DUID", T.StringType()),
        T.StructField("CPSFAMID", T.StringType()),
        T.StructField("VARSTR", T.StringType()),
        T.StructField("VARPSU", T.IntegerType()),
        T.StructField("PERWT15F", T.DoubleType()),
        T.StructField("FAMWT15C", T.DoubleType()),
        T.StructField("TOTEXP15", T.DoubleType()),
        T.StructField("TOTSLF15", T.DoubleType()),
        T.StructField("AGELAST", T.IntegerType()),
        T.StructField("SEX", T.IntegerType()),
        T.StructField("INSCOV15", T.IntegerType()),
        T.StructField("POVCAT15", T.IntegerType()),
        T.StructField("OBTOTV15", T.IntegerType()),
        T.StructField("TTLP15X", T.DoubleType()),
    ])
    data = [
        ("P001", "D01", "F1", "S1", 1, 5000.0, 5000.0, 1200.0, 300.0, 35, 1, 1, 3, 5, 40000.0),
        ("P002", "D01", "F1", "S1", 2, 6000.0, 5000.0, 800.0, 200.0, 55, 2, 1, 4, 3, 55000.0),
        ("P003", "D02", "F1", "S2", 1, 4000.0, 4000.0, 2500.0, 600.0, 70, 1, 2, 2, 8, 20000.0),
        ("P004", "D02", "F1", "S2", 2, 5500.0, 4000.0, 0.0, 0.0, 10, 2, 1, 5, 0, 0.0),
        ("P005", "D03", "F1", "S1", 1, 3000.0, 3000.0, 500.0, 150.0, 28, 1, 3, 1, 2, 30000.0),
    ]
    return spark.createDataFrame(data, schema)


@pytest.fixture
def sample_fyc_2018(spark):
    """Sample 2018 Full-Year Consolidated data."""
    schema = T.StructType([
        T.StructField("DUPERSID", T.StringType()),
        T.StructField("VARSTR", T.StringType()),
        T.StructField("VARPSU", T.IntegerType()),
        T.StructField("PERWT18F", T.DoubleType()),
        T.StructField("SAQWT18F", T.DoubleType()),
        T.StructField("TOTEXP18", T.DoubleType()),
        T.StructField("TOTSLF18", T.DoubleType()),
        T.StructField("AGELAST", T.IntegerType()),
        T.StructField("SEX", T.IntegerType()),
        T.StructField("RACETHX", T.IntegerType()),
        T.StructField("INSCOV18", T.IntegerType()),
        T.StructField("POVCAT18", T.IntegerType()),
        T.StructField("ADFLST42", T.IntegerType()),
        T.StructField("ARTHDX", T.IntegerType()),
        T.StructField("JTPAIN31_M18", T.IntegerType()),
    ])
    data = [
        ("P001", "S1", 1, 5000.0, 4800.0, 1200.0, 300.0, 35, 1, 2, 1, 3, 1, 0, -1),
        ("P002", "S1", 2, 6000.0, 5800.0, 800.0, 200.0, 55, 2, 1, 1, 4, 2, 1, 1),
        ("P003", "S2", 1, 4000.0, 3800.0, 2500.0, 600.0, 70, 1, 3, 2, 2, 1, 1, 0),
        ("P004", "S2", 2, 5500.0, 5200.0, 0.0, 0.0, 10, 2, 2, 1, 5, -1, 0, -1),
        ("P005", "S1", 1, 3000.0, 2800.0, 500.0, 150.0, 28, 1, 4, 3, 1, 2, 0, 1),
        ("P006", "S1", 2, 7000.0, 6800.0, 3500.0, 800.0, 45, 2, 5, 1, 5, 1, 0, 0),
    ]
    return spark.createDataFrame(data, schema)


@pytest.fixture
def sample_conditions_2015(spark):
    """Sample 2015 conditions data."""
    schema = T.StructType([
        T.StructField("DUPERSID", T.StringType()),
        T.StructField("CONDIDX", T.StringType()),
        T.StructField("CCCODEX", T.StringType()),
    ])
    data = [
        ("P001", "C001", "049"),  # diabetes
        ("P001", "C002", "204"),  # joint disorder
        ("P002", "C003", "050"),  # diabetes
        ("P003", "C004", "098"),  # hypertension
        ("P003", "C005", "049"),  # diabetes
        ("P004", "C006", "123"),  # influenza
    ]
    return spark.createDataFrame(data, schema)


@pytest.fixture
def sample_conditions_2020(spark):
    """Sample 2020 conditions data with CCSR codes."""
    schema = T.StructType([
        T.StructField("DUPERSID", T.StringType()),
        T.StructField("CONDIDX", T.StringType()),
        T.StructField("CCSR1X", T.StringType()),
        T.StructField("CCSR2X", T.StringType()),
        T.StructField("CCSR3X", T.StringType()),
    ])
    data = [
        ("P001", "C001", "END010", "-1", "-1"),    # hyperlipidemia
        ("P002", "C002", "MBD001", "-1", "-1"),     # mental health
        ("P002", "C003", "END010", "CIR007", "-1"), # hyperlipidemia + circulatory
        ("P003", "C004", "MBD005", "-1", "-1"),     # mental health
        ("P004", "C005", "INF001", "-1", "-1"),     # infection
    ]
    return spark.createDataFrame(data, schema)


@pytest.fixture
def sample_clnk(spark):
    """Sample condition-event link data."""
    schema = T.StructType([
        T.StructField("DUPERSID", T.StringType()),
        T.StructField("CONDIDX", T.StringType()),
        T.StructField("EVNTIDX", T.StringType()),
        T.StructField("EVENTYPE", T.IntegerType()),
    ])
    data = [
        ("P001", "C001", "E001", 1),  # OB visit
        ("P001", "C001", "E002", 3),  # RX
        ("P001", "C002", "E003", 1),  # OB visit
        ("P002", "C002", "E004", 1),  # OB visit
        ("P002", "C003", "E005", 3),  # RX
        ("P003", "C004", "E006", 1),  # OB visit
        ("P003", "C005", "E007", 3),  # RX
        ("P004", "C005", "E008", 1),  # OB visit
    ]
    return spark.createDataFrame(data, schema)


@pytest.fixture
def sample_pmed_2015(spark):
    """Sample 2015 prescribed medicine event data."""
    schema = T.StructType([
        T.StructField("DUPERSID", T.StringType()),
        T.StructField("LINKIDX", T.StringType()),
        T.StructField("RXXP15X", T.DoubleType()),
        T.StructField("TC1", T.IntegerType()),
        T.StructField("TC1S1", T.IntegerType()),
        T.StructField("TC1S1_1", T.IntegerType()),
        T.StructField("RXDRGNAM", T.StringType()),
        T.StructField("VARSTR", T.StringType()),
        T.StructField("VARPSU", T.IntegerType()),
        T.StructField("PERWT15F", T.DoubleType()),
    ])
    data = [
        ("P001", "E002", 50.0, 242, 251, 60, "DrugA", "S1", 1, 5000.0),
        ("P001", "E002", 75.0, 242, 251, 60, "DrugA", "S1", 1, 5000.0),
        ("P002", "E005", 120.0, 19, 100, 191, "DrugB", "S1", 2, 6000.0),
        ("P003", "E007", 200.0, 57, 60, 60, "DrugC", "S2", 1, 4000.0),
    ]
    return spark.createDataFrame(data, schema)


@pytest.fixture
def sample_pmed_2020(spark):
    """Sample 2020 prescribed medicine event data."""
    schema = T.StructType([
        T.StructField("DUPERSID", T.StringType()),
        T.StructField("LINKIDX", T.StringType()),
        T.StructField("EVNTIDX", T.StringType()),
        T.StructField("RXXP20X", T.DoubleType()),
        T.StructField("TC1", T.IntegerType()),
        T.StructField("VARSTR", T.StringType()),
        T.StructField("VARPSU", T.IntegerType()),
        T.StructField("PERWT20F", T.DoubleType()),
    ])
    data = [
        ("P001", "E002", "E002", 50.0, 19, "S1", 1, 5000.0),
        ("P002", "E005", "E005", 120.0, 57, "S1", 2, 6000.0),
        ("P003", "E007", "E007", 200.0, 19, "S2", 1, 4000.0),
    ]
    return spark.createDataFrame(data, schema)


@pytest.fixture
def sample_ob_events_2020(spark):
    """Sample 2020 office-based visit data."""
    schema = T.StructType([
        T.StructField("DUPERSID", T.StringType()),
        T.StructField("EVNTIDX", T.StringType()),
        T.StructField("OBXP20X", T.DoubleType()),
        T.StructField("VARSTR", T.StringType()),
        T.StructField("VARPSU", T.IntegerType()),
        T.StructField("PERWT20F", T.DoubleType()),
    ])
    data = [
        ("P001", "E001", 150.0, "S1", 1, 5000.0),
        ("P001", "E003", 200.0, "S1", 1, 5000.0),
        ("P002", "E004", 300.0, "S1", 2, 6000.0),
        ("P003", "E006", 175.0, "S2", 1, 4000.0),
        ("P004", "E008", 250.0, "S2", 2, 5500.0),
    ]
    return spark.createDataFrame(data, schema)


@pytest.fixture
def sample_fyc_2020(spark):
    """Sample 2020 Full-Year Consolidated data."""
    schema = T.StructType([
        T.StructField("DUPERSID", T.StringType()),
        T.StructField("VARSTR", T.StringType()),
        T.StructField("VARPSU", T.IntegerType()),
        T.StructField("PERWT20F", T.DoubleType()),
        T.StructField("TOTEXP20", T.DoubleType()),
        T.StructField("AGELAST", T.IntegerType()),
        T.StructField("SEX", T.IntegerType()),
        T.StructField("RACETHX", T.IntegerType()),
        T.StructField("INSCOV20", T.IntegerType()),
        T.StructField("POVCAT20", T.IntegerType()),
        T.StructField("REGION53", T.IntegerType()),
        T.StructField("CVDLAYCA53", T.IntegerType()),
        T.StructField("CVDLAYDN53", T.IntegerType()),
        T.StructField("CVDLAYPM53", T.IntegerType()),
    ])
    data = [
        ("P001", "S1", 1, 5000.0, 1200.0, 35, 1, 2, 1, 3, 1, 1, 2, 2),
        ("P002", "S1", 2, 6000.0, 800.0, 55, 2, 1, 1, 4, 2, 2, 1, 2),
        ("P003", "S2", 1, 4000.0, 2500.0, 70, 1, 3, 2, 2, 3, 1, 1, 1),
        ("P004", "S2", 2, 5500.0, 0.0, 10, 2, 2, 1, 5, 4, -1, -1, -1),
        ("P005", "S1", 1, 3000.0, 500.0, 28, 1, 4, 3, 1, -1, 2, 2, 1),
    ]
    return spark.createDataFrame(data, schema)


@pytest.fixture
def sample_rx_2016(spark):
    """Sample 2016 RX event data for summary tables."""
    schema = T.StructType([
        T.StructField("DUPERSID", T.StringType()),
        T.StructField("LINKIDX", T.StringType()),
        T.StructField("RXXP16X", T.DoubleType()),
        T.StructField("TC1", T.IntegerType()),
        T.StructField("RXDRGNAM", T.StringType()),
        T.StructField("VARSTR", T.StringType()),
        T.StructField("VARPSU", T.IntegerType()),
        T.StructField("PERWT16F", T.DoubleType()),
    ])
    data = [
        ("P001", "L001", 50.0, 57, "Amitriptyline", "S1", 1, 5000.0),
        ("P001", "L002", 75.0, 19, "Atorvastatin", "S1", 1, 5000.0),
        ("P002", "L003", 120.0, 40, "Lisinopril", "S1", 2, 6000.0),
        ("P002", "L004", 200.0, 57, "Sertraline", "S1", 2, 6000.0),
        ("P003", "L005", 80.0, 19, "Atorvastatin", "S2", 1, 4000.0),
        ("P003", "L006", 150.0, 97, "Levothyroxine", "S2", 1, 4000.0),
    ]
    return spark.createDataFrame(data, schema)
