"""Tests for summary table modules."""

import pytest
from pyspark.sql import functions as F
import pyspark.sql.types as T

from meps.summary_tables.use_expenditures_2016 import (
    prepare_data as prep_use_exp_2016,
    run as run_use_exp_2016,
)
from meps.summary_tables.use_race_sex_2016 import (
    prepare_data as prep_race_sex,
    run as run_race_sex,
)
from meps.summary_tables.use_events_2016 import (
    prepare_data as prep_events,
    run as run_events,
)
from meps.summary_tables.ins_age_2016 import (
    prepare_data as prep_ins_age,
    run as run_ins_age,
)
from meps.summary_tables.care_access_2019 import (
    prepare_data as prep_care_2019,
    run as run_care_2019,
)
from meps.summary_tables.care_diabetes_a1c_2016 import (
    prepare_data as prep_diabetes,
    run as run_diabetes,
)
from meps.summary_tables.care_quality_2016 import (
    prepare_data as prep_quality,
    run as run_quality,
)
from meps.summary_tables.pmed_prescribed_drug_2016 import (
    aggregate_to_person_drug,
    run as run_pmed_drug,
)
from meps.summary_tables.pmed_therapeutic_class_2016 import (
    aggregate_to_person_tc,
    run as run_pmed_tc,
)


class TestUseExpenditures2016:
    """Tests for use_expenditures_2016 summary table."""

    def test_prepare_data(self, spark, sample_fyc_2016):
        # Need some additional columns for OBV aggregates
        df = sample_fyc_2016.withColumn("OBVSLF16", F.lit(100.0))
        result = prep_use_exp_2016(spark, input_df=df)
        assert result is not None
        assert result.count() == sample_fyc_2016.count()

    def test_run(self, spark, sample_fyc_2016):
        df = sample_fyc_2016.withColumn("OBVSLF16", F.lit(100.0))
        result = run_use_exp_2016(spark, input_df=df)
        assert isinstance(result, dict)
        assert "prepared_data" in result
        assert "estimates" in result


class TestUseRaceSex2016:
    """Tests for use_race_sex_2016 summary table."""

    def test_prepare_creates_race(self, spark, sample_fyc_2016):
        result = prep_race_sex(spark, input_df=sample_fyc_2016)
        assert "RACE" in result.columns

    def test_race_labels(self, spark, sample_fyc_2016):
        result = prep_race_sex(spark, input_df=sample_fyc_2016)
        races = set(
            row["RACE"]
            for row in result.select("RACE").collect()
            if row["RACE"] is not None
        )
        valid_races = {
            "Hispanic", "White", "Black",
            "Amer. Indian, AK Native, or mult. races",
            "Asian, Hawaiian, or Pacific Islander",
        }
        assert races.issubset(valid_races)

    def test_creates_has_exp(self, spark, sample_fyc_2016):
        result = prep_race_sex(spark, input_df=sample_fyc_2016)
        assert "HAS_EXP" in result.columns
        values = set(row["HAS_EXP"] for row in result.select("HAS_EXP").collect())
        assert values.issubset({0, 1})

    def test_creates_person_counter(self, spark, sample_fyc_2016):
        result = prep_race_sex(spark, input_df=sample_fyc_2016)
        assert "PERSON" in result.columns

    def test_run(self, spark, sample_fyc_2016):
        result = run_race_sex(spark, input_df=sample_fyc_2016)
        assert isinstance(result, dict)


class TestUseEvents2016:
    """Tests for use_events_2016 summary table."""

    def test_run(self, spark, sample_fyc_2016):
        result = run_events(spark, input_df=sample_fyc_2016)
        assert isinstance(result, dict)
        assert "estimates" in result


class TestInsAge2016:
    """Tests for ins_age_2016 summary table."""

    def test_creates_age_category(self, spark, sample_fyc_2016):
        result = prep_ins_age(spark, input_df=sample_fyc_2016)
        assert "AGECAT" in result.columns

    def test_age_group_labels(self, spark, sample_fyc_2016):
        result = prep_ins_age(spark, input_df=sample_fyc_2016)
        ages = set(
            row["AGECAT"]
            for row in result.select("AGECAT").collect()
            if row["AGECAT"] is not None
        )
        valid_ages = {"Under 5", "5-17", "18-44", "45-64", "65+"}
        assert ages.issubset(valid_ages)

    def test_creates_insurance_label(self, spark, sample_fyc_2016):
        result = prep_ins_age(spark, input_df=sample_fyc_2016)
        assert "INSURANCE" in result.columns

    def test_run(self, spark, sample_fyc_2016):
        result = run_ins_age(spark, input_df=sample_fyc_2016)
        assert isinstance(result, dict)
        assert "estimates" in result


class TestCareAccess2019:
    """Tests for care_access_2019 summary table."""

    def test_creates_afford_variables(self, spark):
        schema = T.StructType([
            T.StructField("DUPERSID", T.StringType()),
            T.StructField("VARSTR", T.StringType()),
            T.StructField("VARPSU", T.IntegerType()),
            T.StructField("PERWT19F", T.DoubleType()),
            T.StructField("AFRDCA42", T.IntegerType()),
            T.StructField("AFRDDN42", T.IntegerType()),
            T.StructField("AFRDPM42", T.IntegerType()),
            T.StructField("ACCELI42", T.IntegerType()),
            T.StructField("POVCAT19", T.IntegerType()),
        ])
        data = [
            ("P001", "S1", 1, 5000.0, 1, 2, 2, 1, 3),
            ("P002", "S1", 2, 6000.0, 2, 2, 2, 1, 4),
            ("P003", "S2", 1, 4000.0, 2, 1, 2, 1, 2),
            ("P004", "S2", 2, 5500.0, 2, 2, 2, 0, 5),
        ]
        df = spark.createDataFrame(data, schema)
        result = prep_care_2019(spark, input_df=df)
        assert "AFFORD_MD" in result.columns
        assert "AFFORD_DN" in result.columns
        assert "AFFORD_PM" in result.columns
        assert "AFFORD_ANY" in result.columns
        assert "DOMAIN" in result.columns

    def test_afford_md_values(self, spark):
        schema = T.StructType([
            T.StructField("DUPERSID", T.StringType()),
            T.StructField("VARSTR", T.StringType()),
            T.StructField("VARPSU", T.IntegerType()),
            T.StructField("PERWT19F", T.DoubleType()),
            T.StructField("AFRDCA42", T.IntegerType()),
            T.StructField("AFRDDN42", T.IntegerType()),
            T.StructField("AFRDPM42", T.IntegerType()),
            T.StructField("ACCELI42", T.IntegerType()),
            T.StructField("POVCAT19", T.IntegerType()),
        ])
        data = [
            ("P001", "S1", 1, 5000.0, 1, 2, 2, 1, 3),
            ("P002", "S1", 2, 6000.0, 2, 2, 2, 1, 4),
        ]
        df = spark.createDataFrame(data, schema)
        result = prep_care_2019(spark, input_df=df)
        p001 = result.filter(F.col("DUPERSID") == "P001").collect()
        assert p001[0]["AFFORD_MD"] == 1
        p002 = result.filter(F.col("DUPERSID") == "P002").collect()
        assert p002[0]["AFFORD_MD"] == 0


class TestCareDiabetesA1c2016:
    """Tests for care_diabetes_a1c_2016 summary table."""

    def test_creates_race_variable(self, spark, sample_fyc_2016):
        df = sample_fyc_2016.withColumn("DIABW16F", F.lit(1000.0))
        df = df.withColumn("DSA1C53", F.lit(50))
        result = prep_diabetes(spark, input_df=df)
        assert "RACE" in result.columns

    def test_creates_domain(self, spark, sample_fyc_2016):
        df = sample_fyc_2016.withColumn("DIABW16F", F.lit(1000.0))
        df = df.withColumn("DSA1C53", F.lit(50))
        result = prep_diabetes(spark, input_df=df)
        assert "DOMAIN" in result.columns
        # All have DIABW16F > 0 so DOMAIN should be 1
        domains = set(row["DOMAIN"] for row in result.select("DOMAIN").collect())
        assert 1 in domains

    def test_a1c_status_labels(self, spark, sample_fyc_2016):
        df = sample_fyc_2016.withColumn("DIABW16F", F.lit(1000.0))
        df = df.withColumn("DSA1C53", F.lit(50))
        result = prep_diabetes(spark, input_df=df)
        assert "A1C_STATUS" in result.columns
        # Value 50 should map to "Had measurement"
        statuses = set(
            row["A1C_STATUS"]
            for row in result.select("A1C_STATUS").collect()
            if row["A1C_STATUS"] is not None
        )
        assert "Had measurement" in statuses


class TestCareQuality2016:
    """Tests for care_quality_2016 summary table."""

    def test_creates_domain(self, spark, sample_fyc_2016):
        df = sample_fyc_2016.withColumn("ADRTCR42", F.lit(1))
        df = df.withColumn("SAQWT16F", F.lit(1000.0))
        df = df.withColumn("ADRTWW42", F.lit(4))
        result = prep_quality(spark, input_df=df)
        assert "DOMAIN" in result.columns

    def test_creates_appt_freq_label(self, spark, sample_fyc_2016):
        df = sample_fyc_2016.withColumn("ADRTCR42", F.lit(1))
        df = df.withColumn("SAQWT16F", F.lit(1000.0))
        df = df.withColumn("ADRTWW42", F.lit(4))
        result = prep_quality(spark, input_df=df)
        assert "APPT_FREQ" in result.columns
        # Value 4 should map to "Always"
        freqs = set(
            row["APPT_FREQ"]
            for row in result.select("APPT_FREQ").collect()
            if row["APPT_FREQ"] is not None
        )
        assert "Always" in freqs


class TestPmedPrescribedDrug2016:
    """Tests for pmed_prescribed_drug_2016 summary table."""

    def test_aggregates_to_person_drug(self, spark, sample_rx_2016):
        result = aggregate_to_person_drug(spark, rx_df=sample_rx_2016)
        assert "PERSON" in result.columns
        assert "N_PURCHASES" in result.columns
        assert "PERS_RXXP" in result.columns
        assert result.count() > 0

    def test_person_drug_deduplication(self, spark, sample_rx_2016):
        result = aggregate_to_person_drug(spark, rx_df=sample_rx_2016)
        # Each DUPERSID+RXDRGNAM combo should appear once
        dup_check = result.groupBy("DUPERSID", "RXDRGNAM").count()
        max_count = dup_check.agg(F.max("count")).collect()[0][0]
        assert max_count == 1

    def test_run(self, spark, sample_rx_2016):
        result = run_pmed_drug(spark, rx_df=sample_rx_2016)
        assert isinstance(result, dict)
        assert "person_drug_level" in result
        assert "estimates" in result


class TestPmedTherapeuticClass2016:
    """Tests for pmed_therapeutic_class_2016 summary table."""

    def test_aggregates_to_person_tc(self, spark, sample_rx_2016):
        result = aggregate_to_person_tc(spark, rx_df=sample_rx_2016)
        assert "TC1_LABEL" in result.columns
        assert "PERSON" in result.columns

    def test_tc_labels_correct(self, spark, sample_rx_2016):
        result = aggregate_to_person_tc(spark, rx_df=sample_rx_2016)
        labels = set(
            row["TC1_LABEL"]
            for row in result.select("TC1_LABEL").collect()
            if row["TC1_LABEL"] is not None
        )
        # TC1=57 -> Central nervous system agents
        assert "Central nervous system agents" in labels

    def test_run(self, spark, sample_rx_2016):
        result = run_pmed_tc(spark, rx_df=sample_rx_2016)
        assert isinstance(result, dict)
        assert "person_tc_level" in result
        assert "estimates" in result
