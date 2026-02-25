"""Tests for meps.utils.formatting module."""

import pytest
from pyspark.sql import SparkSession
import pyspark.sql.functions as F

from meps.utils.formatting import (
    age_category,
    gt_zero_format,
    yes_no_format,
    sex_format,
    poverty_category_format,
    insurance_coverage_format,
    race_ethnicity_format,
    region_format,
    flag_format,
    apply_format,
)


class TestAgeCategory:
    """Tests for age_category formatting."""

    def test_under_65(self, spark):
        df = spark.createDataFrame([(30,)], ["age"])
        result = df.withColumn("cat", age_category(F.col("age"))).collect()
        assert result[0]["cat"] == "0-64"

    def test_65_plus(self, spark):
        df = spark.createDataFrame([(70,)], ["age"])
        result = df.withColumn("cat", age_category(F.col("age"))).collect()
        assert result[0]["cat"] == "65+"

    def test_boundary_64(self, spark):
        df = spark.createDataFrame([(64,)], ["age"])
        result = df.withColumn("cat", age_category(F.col("age"))).collect()
        assert result[0]["cat"] == "0-64"

    def test_boundary_65(self, spark):
        df = spark.createDataFrame([(65,)], ["age"])
        result = df.withColumn("cat", age_category(F.col("age"))).collect()
        assert result[0]["cat"] == "65+"


class TestGtZeroFormat:
    """Tests for gt_zero_format."""

    def test_positive_value(self, spark):
        df = spark.createDataFrame([(100.0,)], ["val"])
        result = df.withColumn("fmt", gt_zero_format(F.col("val"))).collect()
        assert result[0]["fmt"] == ">0"

    def test_zero_value(self, spark):
        df = spark.createDataFrame([(0.0,)], ["val"])
        result = df.withColumn("fmt", gt_zero_format(F.col("val"))).collect()
        assert result[0]["fmt"] == "0"

    def test_negative_value(self, spark):
        df = spark.createDataFrame([(-5.0,)], ["val"])
        result = df.withColumn("fmt", gt_zero_format(F.col("val"))).collect()
        # gt_zero_format: when col == 0 -> "0", otherwise ">0"
        assert result[0]["fmt"] == ">0"


class TestYesNoFormat:
    """Tests for yes_no_format."""

    def test_yes(self, spark):
        df = spark.createDataFrame([(1,)], ["val"])
        result = df.withColumn("fmt", yes_no_format(F.col("val"))).collect()
        assert result[0]["fmt"] == "Yes"

    def test_no(self, spark):
        df = spark.createDataFrame([(2,)], ["val"])
        result = df.withColumn("fmt", yes_no_format(F.col("val"))).collect()
        assert result[0]["fmt"] == "No"


class TestSexFormat:
    """Tests for sex_format."""

    def test_male(self, spark):
        df = spark.createDataFrame([(1,)], ["sex"])
        result = df.withColumn("fmt", sex_format(F.col("sex"))).collect()
        assert result[0]["fmt"] == "Male"

    def test_female(self, spark):
        df = spark.createDataFrame([(2,)], ["sex"])
        result = df.withColumn("fmt", sex_format(F.col("sex"))).collect()
        assert result[0]["fmt"] == "Female"


class TestPovertyFormat:
    """Tests for poverty_category_format."""

    def test_all_categories(self, spark):
        df = spark.createDataFrame([(i,) for i in range(1, 6)], ["pov"])
        results = df.withColumn("fmt", poverty_category_format(F.col("pov"))).collect()
        assert len(results) == 5
        # All should have non-null labels
        for row in results:
            assert row["fmt"] is not None


class TestInsuranceCoverageFormat:
    """Tests for insurance_coverage_format."""

    def test_private(self, spark):
        df = spark.createDataFrame([(1,)], ["ins"])
        result = df.withColumn("fmt", insurance_coverage_format(F.col("ins"))).collect()
        assert "private" in result[0]["fmt"].lower() or "Private" in result[0]["fmt"]

    def test_uninsured(self, spark):
        df = spark.createDataFrame([(3,)], ["ins"])
        result = df.withColumn("fmt", insurance_coverage_format(F.col("ins"))).collect()
        assert "uninsured" in result[0]["fmt"].lower() or "Uninsured" in result[0]["fmt"]


class TestRaceEthnicityFormat:
    """Tests for race_ethnicity_format."""

    def test_hispanic(self, spark):
        df = spark.createDataFrame([(1,)], ["race"])
        result = df.withColumn("fmt", race_ethnicity_format(F.col("race"))).collect()
        assert "hispanic" in result[0]["fmt"].lower() or "Hispanic" in result[0]["fmt"]


class TestRegionFormat:
    """Tests for region_format."""

    def test_northeast(self, spark):
        df = spark.createDataFrame([(1,)], ["region"])
        result = df.withColumn("fmt", region_format(F.col("region"))).collect()
        assert result[0]["fmt"] is not None


class TestFlagFormat:
    """Tests for flag_format."""

    def test_yes_flag(self, spark):
        df = spark.createDataFrame([(1,)], ["flag"])
        result = df.withColumn("fmt", flag_format(F.col("flag"))).collect()
        assert result[0]["fmt"] is not None


class TestApplyFormat:
    """Tests for apply_format (DataFrame-level function)."""

    def test_custom_mapping(self, spark):
        mapping = {1: "One", 2: "Two", 3: "Three"}
        df = spark.createDataFrame([(1,), (2,), (3,)], ["val"])
        result = apply_format(df, "val", mapping)
        rows = result.collect()
        assert rows[0]["val"] == "One"
        assert rows[1]["val"] == "Two"
        assert rows[2]["val"] == "Three"

    def test_unmapped_value_returns_null(self, spark):
        mapping = {1: "One"}
        df = spark.createDataFrame([(99,)], ["val"])
        result = apply_format(df, "val", mapping)
        rows = result.collect()
        assert rows[0]["val"] is None

    def test_custom_output_column(self, spark):
        mapping = {1: "One"}
        df = spark.createDataFrame([(1,)], ["val"])
        result = apply_format(df, "val", mapping, output_col="label")
        assert "label" in result.columns
        rows = result.collect()
        assert rows[0]["label"] == "One"
        assert rows[0]["val"] == 1
