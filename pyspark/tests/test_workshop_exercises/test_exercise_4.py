"""Tests for exercises 4a-4d: Pooling data files."""

import pytest
from pyspark.sql import functions as F
import pyspark.sql.types as T

from meps.workshop_exercises.exercise_4a import (
    prepare_year1,
    prepare_year2,
    pool_data,
    run as run_4a,
)
from meps.workshop_exercises.exercise_4c import (
    prepare_2017,
    prepare_2018,
    pool_and_estimate,
    run as run_4c,
)


class TestExercise4aPrepareYear:
    """Tests for exercise_4a year preparation."""

    def test_year1_renames_columns(self, spark, sample_fyc_2015):
        result = prepare_year1(spark, input_df=sample_fyc_2015)
        assert "INSCOV" in result.columns
        assert "PERWT" in result.columns
        assert "POVCAT" in result.columns

    def test_year2_renames_columns(self, spark, sample_fyc_2016):
        result = prepare_year2(spark, input_df=sample_fyc_2016)
        assert "INSCOV" in result.columns
        assert "PERWT" in result.columns
        assert "POVCAT" in result.columns


class TestExercise4aPoolData:
    """Tests for exercise_4a pooling."""

    def test_creates_poolwt(self, spark, sample_fyc_2015, sample_fyc_2016):
        yr1 = prepare_year1(spark, input_df=sample_fyc_2015)
        yr2 = prepare_year2(spark, input_df=sample_fyc_2016)
        pooled = pool_data(yr1, yr2)
        assert "POOLWT" in pooled.columns

    def test_poolwt_is_half_perwt(self, spark, sample_fyc_2015, sample_fyc_2016):
        yr1 = prepare_year1(spark, input_df=sample_fyc_2015)
        yr2 = prepare_year2(spark, input_df=sample_fyc_2016)
        pooled = pool_data(yr1, yr2)
        row = pooled.select("PERWT", "POOLWT").first()
        assert abs(row["POOLWT"] - row["PERWT"] / 2.0) < 0.01

    def test_creates_subpop(self, spark, sample_fyc_2015, sample_fyc_2016):
        yr1 = prepare_year1(spark, input_df=sample_fyc_2015)
        yr2 = prepare_year2(spark, input_df=sample_fyc_2016)
        pooled = pool_data(yr1, yr2)
        assert "SUBPOP" in pooled.columns
        subpop_values = set(
            row["SUBPOP"]
            for row in pooled.select("SUBPOP").collect()
        )
        assert subpop_values.issubset({1, 2})


class TestExercise4aRun:
    """Tests for exercise_4a full pipeline."""

    def test_returns_dict(self, spark, sample_fyc_2015, sample_fyc_2016):
        result = run_4a(spark, yr1_df=sample_fyc_2015, yr2_df=sample_fyc_2016)
        assert isinstance(result, dict)
        assert "pooled_data" in result
        assert "estimates" in result


class TestExercise4cPrepare:
    """Tests for exercise_4c year preparation."""

    def test_prepare_2018_standardizes_vars(self, spark, sample_fyc_2018):
        result = prepare_2018(spark, input_df=sample_fyc_2018)
        assert "TOTEXP" in result.columns
        assert "JTPAIN" in result.columns
        assert "SPOP" in result.columns
        assert "JOINT_PAIN" in result.columns

    def test_spop_values(self, spark, sample_fyc_2018):
        result = prepare_2018(spark, input_df=sample_fyc_2018)
        spop_values = set(row["SPOP"] for row in result.select("SPOP").collect())
        assert spop_values.issubset({1, 2})
