"""Tests for exercise_1b: National health care expenses by service type, 2015."""

import pytest
import pyspark.sql.types as T

from meps.workshop_exercises.exercise_1b import (
    prepare_data,
    run,
)


@pytest.fixture
def fyc_1b(spark):
    """FYC data with all expense columns required by exercise_1b."""
    schema = T.StructType([
        T.StructField("DUPERSID", T.StringType()),
        T.StructField("TOTEXP15", T.DoubleType()),
        T.StructField("IPDEXP15", T.DoubleType()),
        T.StructField("IPFEXP15", T.DoubleType()),
        T.StructField("OBVEXP15", T.DoubleType()),
        T.StructField("RXEXP15", T.DoubleType()),
        T.StructField("OPDEXP15", T.DoubleType()),
        T.StructField("OPFEXP15", T.DoubleType()),
        T.StructField("DVTEXP15", T.DoubleType()),
        T.StructField("ERDEXP15", T.DoubleType()),
        T.StructField("ERFEXP15", T.DoubleType()),
        T.StructField("HHAEXP15", T.DoubleType()),
        T.StructField("HHNEXP15", T.DoubleType()),
        T.StructField("OTHEXP15", T.DoubleType()),
        T.StructField("VISEXP15", T.DoubleType()),
        T.StructField("AGE15X", T.IntegerType()),
        T.StructField("AGE42X", T.IntegerType()),
        T.StructField("AGE31X", T.IntegerType()),
        T.StructField("VARSTR", T.StringType()),
        T.StructField("VARPSU", T.IntegerType()),
        T.StructField("PERWT15F", T.DoubleType()),
    ])
    data = [
        ("P001", 1500.0, 0.0, 0.0, 500.0, 200.0, 100.0, 50.0, 300.0, 0.0, 0.0, 100.0, 50.0, 100.0, 100.0, 35, 35, 35, "S1", 1, 5000.0),
        ("P002", 800.0, 0.0, 0.0, 300.0, 100.0, 50.0, 0.0, 200.0, 50.0, 0.0, 50.0, 0.0, 50.0, 0.0, 55, 55, 55, "S1", 2, 6000.0),
        ("P003", 2500.0, 500.0, 200.0, 400.0, 300.0, 200.0, 100.0, 100.0, 100.0, 50.0, 200.0, 100.0, 150.0, 100.0, 70, 70, 70, "S2", 1, 4000.0),
        ("P004", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 10, 10, 10, "S2", 2, 5500.0),
    ]
    return spark.createDataFrame(data, schema)


class TestPrepareData:
    """Tests for prepare_data function."""

    def test_creates_service_variables(self, spark, fyc_1b):
        result = prepare_data(spark, input_df=fyc_1b)
        assert result is not None
        assert result.count() > 0
        assert "HOSPITAL_INPATIENT" in result.columns
        assert "AMBULATORY" in result.columns
        assert "PRESCRIBED_MEDICINES" in result.columns
        assert "DENTAL" in result.columns
        assert "HOME_HEALTH_OTHER" in result.columns

    def test_creates_flags(self, spark, fyc_1b):
        result = prepare_data(spark, input_df=fyc_1b)
        assert "X_ANYSVCE" in result.columns


class TestRun:
    """Tests for run function (full pipeline)."""

    def test_returns_dict(self, spark, fyc_1b):
        result = run(spark, input_df=fyc_1b)
        assert isinstance(result, dict)
        assert len(result) > 0
        assert "prepared_data" in result
