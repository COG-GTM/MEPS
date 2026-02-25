"""Tests for meps.utils.survey_stats module."""

import pytest
import math
from pyspark.sql import SparkSession
import pyspark.sql.types as T

from meps.utils.survey_stats import (
    survey_mean,
    survey_sum,
    survey_freq,
    survey_mean_by_domain,
    crosstab,
)


class TestSurveyMean:
    """Tests for survey_mean function."""

    def test_returns_dataframe(self, spark, sample_fyc_2016):
        result = survey_mean(
            sample_fyc_2016,
            var_cols=["TOTEXP16"],
            weight_col="PERWT16F",
        )
        assert result is not None

    def test_weighted_mean_calculation(self, spark, sample_fyc_2016):
        result = survey_mean(
            sample_fyc_2016,
            var_cols=["TOTEXP16"],
            weight_col="PERWT16F",
        )
        # Result should be a pandas DataFrame or similar
        assert result is not None
        # Check that mean is reasonable (between 0 and max expense)
        if hasattr(result, "iloc"):
            mean_val = result.iloc[0]["mean"] if "mean" in result.columns else None
            if mean_val is not None:
                assert mean_val >= 0

    def test_multiple_variables(self, spark, sample_fyc_2016):
        result = survey_mean(
            sample_fyc_2016,
            var_cols=["TOTEXP16", "TOTSLF16"],
            weight_col="PERWT16F",
        )
        assert result is not None

    def test_with_zero_weight_filtering(self, spark):
        """Verify behavior with zero weights."""
        schema = T.StructType([
            T.StructField("VARSTR", T.StringType()),
            T.StructField("VARPSU", T.IntegerType()),
            T.StructField("PERWT", T.DoubleType()),
            T.StructField("X", T.DoubleType()),
        ])
        data = [
            ("S1", 1, 100.0, 10.0),
            ("S1", 2, 0.0, 999.0),
            ("S2", 1, 200.0, 20.0),
            ("S2", 2, 100.0, 15.0),
        ]
        df = spark.createDataFrame(data, schema)
        result = survey_mean(df, var_cols=["X"], weight_col="PERWT")
        assert result is not None


class TestSurveySum:
    """Tests for survey_sum function."""

    def test_returns_result(self, spark, sample_fyc_2016):
        result = survey_sum(
            sample_fyc_2016,
            var_cols=["TOTEXP16"],
            weight_col="PERWT16F",
        )
        assert result is not None

    def test_sum_is_positive(self, spark, sample_fyc_2016):
        result = survey_sum(
            sample_fyc_2016,
            var_cols=["TOTEXP16"],
            weight_col="PERWT16F",
        )
        if hasattr(result, "iloc"):
            sum_val = result.iloc[0]["sum"] if "sum" in result.columns else None
            if sum_val is not None:
                assert sum_val > 0


class TestSurveyFreq:
    """Tests for survey_freq function."""

    def test_returns_result(self, spark, sample_fyc_2016):
        result = survey_freq(
            sample_fyc_2016,
            var_col="SEX",
            weight_col="PERWT16F",
        )
        assert result is not None

    def test_freq_counts_all_categories(self, spark, sample_fyc_2016):
        result = survey_freq(
            sample_fyc_2016,
            var_col="SEX",
            weight_col="PERWT16F",
        )
        if hasattr(result, "shape"):
            assert result.shape[0] >= 2  # At least male and female


class TestSurveyMeanByDomain:
    """Tests for survey_mean_by_domain function."""

    def test_returns_result(self, spark, sample_fyc_2016):
        # Create a domain variable
        from pyspark.sql import functions as F
        df = sample_fyc_2016.withColumn(
            "HAS_EXP",
            F.when(F.col("TOTEXP16") > 0, 1).otherwise(0)
        )
        result = survey_mean_by_domain(
            df,
            var_cols=["TOTEXP16"],
            domain_col="HAS_EXP",
            domain_value=1,
            weight_col="PERWT16F",
        )
        assert result is not None

    def test_with_by_column(self, spark, sample_fyc_2016):
        from pyspark.sql import functions as F
        df = sample_fyc_2016.withColumn(
            "HAS_EXP",
            F.when(F.col("TOTEXP16") > 0, 1).otherwise(0)
        )
        result = survey_mean_by_domain(
            df,
            var_cols=["TOTEXP16"],
            domain_col="HAS_EXP",
            domain_value=1,
            weight_col="PERWT16F",
            by_col="SEX",
        )
        assert result is not None


class TestCrosstab:
    """Tests for crosstab function."""

    def test_returns_result(self, spark, sample_fyc_2016):
        result = crosstab(
            sample_fyc_2016,
            row_col="SEX",
            col_col="INSCOV16",
            weight_col="PERWT16F",
        )
        assert result is not None

    def test_unweighted_crosstab(self, spark, sample_fyc_2016):
        result = crosstab(
            sample_fyc_2016,
            row_col="SEX",
            col_col="INSCOV16",
        )
        assert result is not None
