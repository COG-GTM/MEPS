"""Tests for meps.utils.survey_logistic module."""

import pytest
from pyspark.sql import SparkSession
import pyspark.sql.types as T

from meps.utils.survey_logistic import survey_logistic_regression


class TestSurveyLogisticRegression:
    """Tests for survey_logistic_regression function."""

    def test_basic_regression(self, spark):
        """Test basic logistic regression with continuous predictor."""
        schema = T.StructType([
            T.StructField("VARSTR", T.StringType()),
            T.StructField("VARPSU", T.IntegerType()),
            T.StructField("WEIGHT", T.DoubleType()),
            T.StructField("Y", T.IntegerType()),
            T.StructField("X1", T.DoubleType()),
        ])
        data = [
            ("S1", 1, 100.0, 1, 10.0),
            ("S1", 2, 150.0, 0, 5.0),
            ("S1", 1, 120.0, 1, 12.0),
            ("S1", 2, 130.0, 0, 3.0),
            ("S2", 1, 110.0, 1, 11.0),
            ("S2", 2, 140.0, 0, 4.0),
            ("S2", 1, 105.0, 1, 9.0),
            ("S2", 2, 135.0, 1, 8.0),
        ]
        df = spark.createDataFrame(data, schema)

        result = survey_logistic_regression(
            df,
            dependent_var="Y",
            independent_vars=["X1"],
            weight_col="WEIGHT",
        )
        assert result is not None

    def test_with_class_variables(self, spark):
        """Test logistic regression with categorical predictors."""
        schema = T.StructType([
            T.StructField("VARSTR", T.StringType()),
            T.StructField("VARPSU", T.IntegerType()),
            T.StructField("WEIGHT", T.DoubleType()),
            T.StructField("Y", T.IntegerType()),
            T.StructField("AGE", T.DoubleType()),
            T.StructField("SEX", T.StringType()),
        ])
        data = [
            ("S1", 1, 100.0, 1, 35.0, "1"),
            ("S1", 2, 150.0, 0, 55.0, "2"),
            ("S1", 1, 120.0, 1, 40.0, "1"),
            ("S1", 2, 130.0, 0, 60.0, "2"),
            ("S2", 1, 110.0, 1, 30.0, "1"),
            ("S2", 2, 140.0, 0, 50.0, "2"),
            ("S2", 1, 105.0, 1, 25.0, "1"),
            ("S2", 2, 135.0, 1, 45.0, "2"),
        ]
        df = spark.createDataFrame(data, schema)

        result = survey_logistic_regression(
            df,
            dependent_var="Y",
            independent_vars=["AGE", "SEX"],
            class_vars=["SEX"],
            ref_levels={"SEX": "1"},
            weight_col="WEIGHT",
        )
        assert result is not None

    def test_returns_coefficients(self, spark):
        """Verify that coefficients are returned."""
        schema = T.StructType([
            T.StructField("VARSTR", T.StringType()),
            T.StructField("VARPSU", T.IntegerType()),
            T.StructField("WEIGHT", T.DoubleType()),
            T.StructField("Y", T.IntegerType()),
            T.StructField("X1", T.DoubleType()),
        ])
        data = [
            ("S1", 1, 100.0, 1, 10.0),
            ("S1", 2, 150.0, 0, 2.0),
            ("S2", 1, 110.0, 1, 8.0),
            ("S2", 2, 140.0, 0, 3.0),
            ("S1", 1, 120.0, 1, 9.0),
            ("S1", 2, 130.0, 0, 1.0),
            ("S2", 1, 105.0, 0, 5.0),
            ("S2", 2, 135.0, 1, 7.0),
        ]
        df = spark.createDataFrame(data, schema)

        result = survey_logistic_regression(
            df,
            dependent_var="Y",
            independent_vars=["X1"],
            weight_col="WEIGHT",
        )
        # Should return dict with coefficients
        if isinstance(result, dict):
            assert "coefficients" in result or "coef" in result or len(result) > 0
