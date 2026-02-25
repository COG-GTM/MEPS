"""Tests for exercises 6a and 6b: Regression."""

import pytest
from pyspark.sql import functions as F

from meps.workshop_exercises.exercise_6a import (
    prepare_data as prepare_6a,
    run as run_6a,
)
from meps.workshop_exercises.exercise_6b import (
    prepare_data as prepare_6b,
    run as run_6b,
)


class TestExercise6aPrepareData:
    """Tests for exercise_6a data preparation."""

    def test_creates_flushot_variable(self, spark, sample_fyc_2018):
        result = prepare_6a(spark, input_df=sample_fyc_2018)
        assert "FLUSHOT" in result.columns

    def test_flushot_values(self, spark, sample_fyc_2018):
        result = prepare_6a(spark, input_df=sample_fyc_2018)
        # FLUSHOT should be 1, 0, or null
        values = set(
            row["FLUSHOT"]
            for row in result.select("FLUSHOT").collect()
            if row["FLUSHOT"] is not None
        )
        assert values.issubset({0, 1})

    def test_creates_age_flag(self, spark, sample_fyc_2018):
        result = prepare_6a(spark, input_df=sample_fyc_2018)
        assert "AGE18P" in result.columns

    def test_creates_labels(self, spark, sample_fyc_2018):
        result = prepare_6a(spark, input_df=sample_fyc_2018)
        assert "SEX_LABEL" in result.columns
        assert "RACETHX_LABEL" in result.columns
        assert "INSCOV18_LABEL" in result.columns


class TestExercise6aRun:
    """Tests for exercise_6a full pipeline."""

    def test_returns_dict(self, spark, sample_fyc_2018):
        result = run_6a(spark, input_df=sample_fyc_2018)
        assert isinstance(result, dict)
        assert "prepared_data" in result
        assert "flu_shot_percentage" in result


class TestExercise6bPrepareData:
    """Tests for exercise_6b data preparation."""

    def test_creates_delayed_care_variables(self, spark, sample_fyc_2020):
        result = prepare_6b(spark, input_df=sample_fyc_2020)
        assert "DELAYED_CARE_MED" in result.columns
        assert "DELAYED_CARE_DENTAL" in result.columns
        assert "DELAYED_CARE_PMEDS" in result.columns

    def test_recodes_region(self, spark, sample_fyc_2020):
        result = prepare_6b(spark, input_df=sample_fyc_2020)
        assert "REGION" in result.columns
        # -1 should become null
        p005 = result.filter(F.col("DUPERSID") == "P005").collect()
        if len(p005) > 0:
            assert p005[0]["REGION"] is None

    def test_delayed_care_values(self, spark, sample_fyc_2020):
        result = prepare_6b(spark, input_df=sample_fyc_2020)
        for col in ["DELAYED_CARE_MED", "DELAYED_CARE_DENTAL", "DELAYED_CARE_PMEDS"]:
            values = set(
                row[col]
                for row in result.select(col).collect()
                if row[col] is not None
            )
            assert values.issubset({0, 1})


class TestExercise6bRun:
    """Tests for exercise_6b full pipeline."""

    def test_returns_dict(self, spark, sample_fyc_2020):
        result = run_6b(spark, input_df=sample_fyc_2020)
        assert isinstance(result, dict)
        assert "prepared_data" in result
        assert "proportions" in result
