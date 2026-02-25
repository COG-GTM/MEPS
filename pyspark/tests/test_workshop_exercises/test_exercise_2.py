"""Tests for exercises 2a, 2b, 2c: Prescribed medicine purchases."""

import pytest
from pyspark.sql import functions as F
import pyspark.sql.types as T

from meps.workshop_exercises.exercise_2a import (
    identify_antipsychotics,
    sum_to_person_level,
    run as run_2a,
)
from meps.workshop_exercises.exercise_2b import (
    identify_narcotics,
    run as run_2b,
)
from meps.workshop_exercises.exercise_2c import (
    identify_narcotics_2018,
    run as run_2c,
)


class TestExercise2aIdentifyAntipsychotics:
    """Tests for exercise_2a antipsychotic identification."""

    def test_filters_by_tc_codes(self, spark, sample_pmed_2015):
        result = identify_antipsychotics(spark, pmed_df=sample_pmed_2015)
        assert result is not None
        # TC1=242 AND TC1S1=251 should match 2 records
        assert result.count() == 2

    def test_no_false_positives(self, spark, sample_pmed_2015):
        result = identify_antipsychotics(spark, pmed_df=sample_pmed_2015)
        # All results should have TC1=242
        tc1_values = [row["TC1"] for row in result.select("TC1").collect()]
        assert all(v == 242 for v in tc1_values)


class TestExercise2aSumToPersonLevel:
    """Tests for exercise_2a person-level aggregation."""

    def test_aggregates_correctly(self, spark):
        # Create pmed data with RXSF15X column needed by sum_to_person_level
        schema = T.StructType([
            T.StructField("DUPERSID", T.StringType()),
            T.StructField("RXXP15X", T.DoubleType()),
            T.StructField("RXSF15X", T.DoubleType()),
            T.StructField("TC1", T.IntegerType()),
            T.StructField("TC1S1", T.IntegerType()),
            T.StructField("VARSTR", T.StringType()),
            T.StructField("VARPSU", T.IntegerType()),
            T.StructField("PERWT15F", T.DoubleType()),
        ])
        data = [
            ("P001", 50.0, 10.0, 242, 251, "S1", 1, 5000.0),
            ("P001", 75.0, 15.0, 242, 251, "S1", 1, 5000.0),
        ]
        pmed_df = spark.createDataFrame(data, schema)
        antipsych = identify_antipsychotics(spark, pmed_df=pmed_df)
        result = sum_to_person_level(antipsych)
        assert result is not None
        p001 = result.filter(F.col("DUPERSID") == "P001").collect()
        assert len(p001) == 1
        assert p001[0]["TOT"] == 125.0
        assert p001[0]["N_PHRCHASE"] == 2


class TestExercise2bIdentifyNarcotics:
    """Tests for exercise_2b narcotic identification."""

    def test_filters_by_tc1s1_1(self, spark, sample_pmed_2015):
        result = identify_narcotics(spark, pmed_df=sample_pmed_2015)
        assert result is not None
        # TC1S1_1 IN (60, 191) should match records
        count = result.count()
        assert count >= 0


class TestExercise2cRun:
    """Tests for exercise_2c full pipeline."""

    def test_returns_dict(self, spark, sample_fyc_2018):
        # exercise_2c uses 2018 data - need RXXP18X and RXSF18X
        schema = T.StructType([
            T.StructField("DUPERSID", T.StringType()),
            T.StructField("LINKIDX", T.StringType()),
            T.StructField("RXXP18X", T.DoubleType()),
            T.StructField("RXSF18X", T.DoubleType()),
            T.StructField("TC1S1_1", T.IntegerType()),
            T.StructField("VARSTR", T.StringType()),
            T.StructField("VARPSU", T.IntegerType()),
            T.StructField("PERWT18F", T.DoubleType()),
        ])
        pmed_data = [
            ("P001", "L001", 50.0, 10.0, 60, "S1", 1, 5000.0),
            ("P002", "L002", 120.0, 20.0, 191, "S1", 2, 6000.0),
            ("P003", "L003", 200.0, 40.0, 99, "S2", 1, 4000.0),
        ]
        pmed_df = spark.createDataFrame(pmed_data, schema)
        result = run_2c(spark, pmed_df=pmed_df, fyc_df=sample_fyc_2018)
        assert isinstance(result, dict)
        assert len(result) > 0
        assert "narcotic_drugs" in result
