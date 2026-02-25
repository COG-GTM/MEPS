"""Tests for exercises 5a and 5b: Constructing variables."""

import pytest
from pyspark.sql import functions as F

from meps.workshop_exercises.exercise_5a import (
    prepare_person_data,
    create_family_variables,
    add_family_weights,
    run as run_5a,
)


class TestExercise5aPreparePersonData:
    """Tests for exercise_5a person data preparation."""

    def test_returns_dataframe(self, spark, sample_fyc_2015):
        result = prepare_person_data(spark, input_df=sample_fyc_2015)
        assert result is not None
        assert result.count() > 0


class TestExercise5aCreateFamilyVariables:
    """Tests for exercise_5a family variable construction."""

    def test_creates_family_level_data(self, spark, sample_fyc_2015):
        person_df = prepare_person_data(spark, input_df=sample_fyc_2015)
        person_enriched, family_df = create_family_variables(person_df)
        assert "FAMSIZE" in family_df.columns
        assert "FAMOOP" in family_df.columns
        assert "FAMINC" in family_df.columns

    def test_family_size_correct(self, spark, sample_fyc_2015):
        person_df = prepare_person_data(spark, input_df=sample_fyc_2015)
        _, family_df = create_family_variables(person_df)
        # D01/F1 has 2 persons (P001, P002)
        d01_f1 = family_df.filter(
            (F.col("DUID") == "D01") & (F.col("CPSFAMID") == "F1")
        ).collect()
        if len(d01_f1) > 0:
            assert d01_f1[0]["FAMSIZE"] == 2

    def test_family_oop_is_sum(self, spark, sample_fyc_2015):
        person_df = prepare_person_data(spark, input_df=sample_fyc_2015)
        _, family_df = create_family_variables(person_df)
        # D01/F1: P001=300 + P002=200 = 500
        d01_f1 = family_df.filter(
            (F.col("DUID") == "D01") & (F.col("CPSFAMID") == "F1")
        ).collect()
        if len(d01_f1) > 0:
            assert abs(d01_f1[0]["FAMOOP"] - 500.0) < 0.01


class TestExercise5aAddFamilyWeights:
    """Tests for exercise_5a family weight assignment."""

    def test_adds_weight_columns(self, spark, sample_fyc_2015):
        person_df = prepare_person_data(spark, input_df=sample_fyc_2015)
        _, family_df = create_family_variables(person_df)
        result = add_family_weights(family_df, person_df)
        assert "FAMWT15C" in result.columns
        assert "VARSTR" in result.columns
        assert "VARPSU" in result.columns


class TestExercise5aRun:
    """Tests for exercise_5a full pipeline."""

    def test_returns_dict(self, spark, sample_fyc_2015):
        result = run_5a(spark, input_df=sample_fyc_2015)
        assert isinstance(result, dict)
        assert "family_data" in result
        assert "estimates" in result
