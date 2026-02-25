"""Tests for exercises 3a and 3b: Medical conditions (diabetes)."""

import pytest
from pyspark.sql import functions as F

from meps.workshop_exercises.exercise_3a import (
    identify_diabetes,
    get_diabetes_persons,
    create_diabetes_flag,
    run as run_3a,
)
from meps.workshop_exercises.exercise_3b import (
    identify_diabetes_events,
    combine_all_events,
    run as run_3b,
)


class TestExercise3aIdentifyDiabetes:
    """Tests for exercise_3a diabetes identification."""

    def test_filters_diabetes_ccs_codes(self, spark, sample_conditions_2015):
        result = identify_diabetes(spark, cond_df=sample_conditions_2015)
        assert result is not None
        # CCS codes 049 and 050 should match 3 records
        assert result.count() == 3

    def test_only_diabetes_codes(self, spark, sample_conditions_2015):
        result = identify_diabetes(spark, cond_df=sample_conditions_2015)
        codes = [row["CCCODEX"] for row in result.select("CCCODEX").collect()]
        assert all(c in ("049", "050") for c in codes)


class TestExercise3aGetDiabetesPersons:
    """Tests for getting unique diabetes persons."""

    def test_deduplicates_persons(self, spark, sample_conditions_2015):
        diab = identify_diabetes(spark, cond_df=sample_conditions_2015)
        persons = get_diabetes_persons(diab)
        # P001, P002, P003 have diabetes conditions
        assert persons.count() == 3


class TestExercise3aCreateDiabetesFlag:
    """Tests for creating DIABPERS flag."""

    def test_creates_flag_column(self, spark, sample_conditions_2015, sample_fyc_2015):
        diab = identify_diabetes(spark, cond_df=sample_conditions_2015)
        persons = get_diabetes_persons(diab)
        result = create_diabetes_flag(spark, persons, fyc_df=sample_fyc_2015)
        assert "DIABPERS" in result.columns

    def test_flag_values(self, spark, sample_conditions_2015, sample_fyc_2015):
        diab = identify_diabetes(spark, cond_df=sample_conditions_2015)
        persons = get_diabetes_persons(diab)
        result = create_diabetes_flag(spark, persons, fyc_df=sample_fyc_2015)
        flag_values = set(row["DIABPERS"] for row in result.select("DIABPERS").collect())
        assert flag_values.issubset({1, 2})

    def test_preserves_all_fyc_persons(self, spark, sample_conditions_2015, sample_fyc_2015):
        diab = identify_diabetes(spark, cond_df=sample_conditions_2015)
        persons = get_diabetes_persons(diab)
        result = create_diabetes_flag(spark, persons, fyc_df=sample_fyc_2015)
        assert result.count() == sample_fyc_2015.count()


class TestExercise3aRun:
    """Tests for exercise_3a full pipeline."""

    def test_returns_dict(self, spark, sample_conditions_2015, sample_fyc_2015):
        result = run_3a(
            spark,
            fyc_df=sample_fyc_2015,
            cond_df=sample_conditions_2015,
        )
        assert isinstance(result, dict)
        assert "diabetes_conditions" in result
        assert "diabetes_persons" in result
        assert "merged_data" in result


class TestExercise3bIdentifyDiabetesEvents:
    """Tests for exercise_3b event identification."""

    def test_links_diabetes_to_events(self, spark, sample_conditions_2015, sample_clnk):
        # Reuse conditions_2015 as it has CCCODEX
        result = identify_diabetes_events(
            spark,
            cond_df=sample_conditions_2015,
            clnk_df=sample_clnk,
        )
        assert result is not None
        assert result.count() > 0

    def test_deduplicates_events(self, spark, sample_conditions_2015, sample_clnk):
        result = identify_diabetes_events(
            spark,
            cond_df=sample_conditions_2015,
            clnk_df=sample_clnk,
        )
        # Should not have duplicate EVNTIDXs
        total = result.count()
        unique = result.dropDuplicates(["EVNTIDX"]).count()
        assert total == unique
