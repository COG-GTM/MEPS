"""Tests for meps.utils.data_loader module."""

import pytest
from pyspark.sql import SparkSession

from meps.utils.data_loader import (
    get_spark_session,
    create_sample_fyc_data,
)


class TestGetSparkSession:
    """Tests for get_spark_session function."""

    def test_returns_spark_session(self, spark):
        # Use shared fixture; do NOT stop session
        session = get_spark_session(app_name="test-session")
        assert session is not None

    def test_custom_app_name(self, spark):
        session = get_spark_session(app_name="custom-test")
        assert session is not None


class TestCreateSampleFycData:
    """Tests for create_sample_fyc_data function."""

    def test_returns_dataframe(self, spark):
        df = create_sample_fyc_data(spark)
        assert df is not None
        assert df.count() > 0

    def test_has_required_columns(self, spark):
        df = create_sample_fyc_data(spark)
        columns = df.columns
        # Should have at least DUPERSID and weight columns
        assert "DUPERSID" in columns

    def test_data_types(self, spark):
        df = create_sample_fyc_data(spark)
        assert df.count() > 0

    def test_correct_year_suffix(self, spark):
        df = create_sample_fyc_data(spark, year=2016)
        columns = df.columns
        assert "TOTEXP16" in columns
        assert "PERWT16F" in columns
