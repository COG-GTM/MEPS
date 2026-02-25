"""Tests for exercise_1a: National health care expenses, 2016."""

import pytest
import pyspark.sql.types as T
from pyspark.sql import functions as F

from meps.workshop_exercises.exercise_1a import (
    prepare_data,
    run_crosstabs,
    estimate_overall,
    estimate_by_age_group,
    run,
)


@pytest.fixture
def fyc_1a(spark):
    """FYC data with columns required by exercise_1a (AGE16X, AGE42X, AGE31X)."""
    schema = T.StructType([
        T.StructField("DUPERSID", T.StringType()),
        T.StructField("TOTEXP16", T.DoubleType()),
        T.StructField("AGE16X", T.IntegerType()),
        T.StructField("AGE42X", T.IntegerType()),
        T.StructField("AGE31X", T.IntegerType()),
        T.StructField("VARSTR", T.StringType()),
        T.StructField("VARPSU", T.IntegerType()),
        T.StructField("PERWT16F", T.DoubleType()),
    ])
    data = [
        ("P001", 1200.0, 35, 35, 35, "S1", 1, 5000.0),
        ("P002", 800.0, 55, 55, 55, "S1", 2, 6000.0),
        ("P003", 2500.0, 70, 70, 70, "S2", 1, 4000.0),
        ("P004", 0.0, 10, 10, 10, "S2", 2, 5500.0),
        ("P005", 500.0, 28, 28, 28, "S1", 1, 3000.0),
        ("P006", 3500.0, 45, 45, 45, "S1", 2, 7000.0),
    ]
    return spark.createDataFrame(data, schema)


class TestPrepareData:
    """Tests for prepare_data function."""

    def test_creates_total_column(self, spark, fyc_1a):
        result = prepare_data(spark, input_df=fyc_1a)
        assert "TOTAL" in result.columns

    def test_creates_age_category(self, spark, fyc_1a):
        result = prepare_data(spark, input_df=fyc_1a)
        assert "AGECAT" in result.columns
        assert "AGE" in result.columns

    def test_preserves_row_count(self, spark, fyc_1a):
        result = prepare_data(spark, input_df=fyc_1a)
        assert result.count() == fyc_1a.count()

    def test_creates_expense_flag(self, spark, fyc_1a):
        result = prepare_data(spark, input_df=fyc_1a)
        assert "X_ANYSVCE" in result.columns
        flags = set(row["X_ANYSVCE"] for row in result.select("X_ANYSVCE").collect())
        assert flags.issubset({0, 1})


class TestRun:
    """Tests for run function (full pipeline)."""

    def test_returns_dict(self, spark, fyc_1a):
        result = run(spark, input_df=fyc_1a)
        assert isinstance(result, dict)

    def test_has_expected_keys(self, spark, fyc_1a):
        result = run(spark, input_df=fyc_1a)
        assert "prepared_data" in result
        assert "overall_estimates" in result
