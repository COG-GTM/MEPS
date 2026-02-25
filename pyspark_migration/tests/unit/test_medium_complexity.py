"""Unit tests for medium complexity ETL jobs.

Tests cover:
  - Person-drug level aggregation correctness
  - Multi-year pooling and variable renaming
  - Family-level aggregation
  - Monthly insurance variable counting
  - COVID delay variable recoding
"""

import pytest
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, lit, sum as spark_sum, when


# ---------------------------------------------------------------------------
# pmed_prescribed_drug_2016 tests
# ---------------------------------------------------------------------------

class TestPmedPrescribedDrug2016:
    """Tests for pmed_prescribed_drug_2016 ETL."""

    def test_person_drug_aggregation(self, spark):
        """Aggregation must produce correct sum and count per person-drug."""
        data = [
            ("P001", 1001, 1, 1.0, "DrugA", 50.0),
            ("P001", 1001, 1, 1.0, "DrugA", 30.0),
            ("P001", 1001, 1, 1.0, "DrugB", 100.0),
            ("P002", 1002, 2, 1.5, "DrugA", 75.0),
        ]
        schema = ["DUPERSID", "VARSTR", "VARPSU", "PERWT16F", "RXDRGNAM", "RXXP16X"]
        rx = spark.createDataFrame(data, schema)

        rx_pers = rx.groupBy("DUPERSID", "VARSTR", "VARPSU", "PERWT16F", "RXDRGNAM").agg(
            spark_sum("RXXP16X").alias("pers_RXXP"),
            count("RXXP16X").alias("n_purchases"),
        ).withColumn("person", lit(1))

        # P001-DrugA: sum=80, count=2
        p1_drugA = rx_pers.filter(
            (col("DUPERSID") == "P001") & (col("RXDRGNAM") == "DrugA")
        ).collect()[0]
        assert p1_drugA["pers_RXXP"] == 80.0
        assert p1_drugA["n_purchases"] == 2
        assert p1_drugA["person"] == 1

        # Total rows: P001-DrugA, P001-DrugB, P002-DrugA = 3
        assert rx_pers.count() == 3

    def test_person_indicator_always_one(self, spark):
        """person column must always be 1 for counting unique persons."""
        data = [("P001", 1001, 1, 1.0, "DrugA", 50.0)]
        schema = ["DUPERSID", "VARSTR", "VARPSU", "PERWT16F", "RXDRGNAM", "RXXP16X"]
        rx = spark.createDataFrame(data, schema)

        rx_pers = rx.groupBy("DUPERSID", "VARSTR", "VARPSU", "PERWT16F", "RXDRGNAM").agg(
            spark_sum("RXXP16X").alias("pers_RXXP"),
            count("RXXP16X").alias("n_purchases"),
        ).withColumn("person", lit(1))

        assert all(row["person"] == 1 for row in rx_pers.collect())


# ---------------------------------------------------------------------------
# exercise_4a tests (Pooling 2015+2016)
# ---------------------------------------------------------------------------

class TestExercise4a:
    """Tests for exercise_4a ETL (pooling FYC files)."""

    def test_pooled_weight_calculation(self, spark):
        """POOLWT must equal PERWT / 2 for 2-year pooling."""
        data = [
            ("P001", 2.0),
            ("P002", 4.0),
        ]
        df = spark.createDataFrame(data, ["DUPERSID", "PERWT"])
        df = df.withColumn("POOLWT", col("PERWT") / lit(2))

        results = {row["DUPERSID"]: row["POOLWT"] for row in df.collect()}
        assert results["P001"] == 1.0
        assert results["P002"] == 2.0

    def test_variable_renaming_consistency(self, spark):
        """Renamed variables must match between year 1 and year 2."""
        yr1 = spark.createDataFrame(
            [("P001", 1, 2.0, 3, 100.0)],
            ["DUPERSID", "INSCOV15", "PERWT15F", "POVCAT15", "TOTSLF15"],
        )
        yr2 = spark.createDataFrame(
            [("P002", 2, 3.0, 4, 200.0)],
            ["DUPERSID", "INSCOV16", "PERWT16F", "POVCAT16", "TOTSLF16"],
        )

        yr1x = (
            yr1.withColumnRenamed("INSCOV15", "INSCOV")
            .withColumnRenamed("PERWT15F", "PERWT")
            .withColumnRenamed("POVCAT15", "POVCAT")
            .withColumnRenamed("TOTSLF15", "TOTSLF")
        )
        yr2x = (
            yr2.withColumnRenamed("INSCOV16", "INSCOV")
            .withColumnRenamed("PERWT16F", "PERWT")
            .withColumnRenamed("POVCAT16", "POVCAT")
            .withColumnRenamed("TOTSLF16", "TOTSLF")
        )

        assert set(yr1x.columns) == set(yr2x.columns)

    def test_subpop_flag_creation(self, spark):
        """SUBPOP=1 only for age 26-30, INSCOV=3, POVCAT=5."""
        data = [
            ("P001", 28, 3, 5),  # Qualifies -> SUBPOP=1
            ("P002", 28, 1, 5),  # Not uninsured -> SUBPOP=2
            ("P003", 35, 3, 5),  # Age out of range -> SUBPOP=2
            ("P004", 28, 3, 3),  # Not high income -> SUBPOP=2
        ]
        df = spark.createDataFrame(data, ["DUPERSID", "AGELAST", "INSCOV", "POVCAT"])
        df = df.withColumn(
            "SUBPOP",
            when(
                (col("AGELAST") >= 26) & (col("AGELAST") <= 30)
                & (col("POVCAT") == 5) & (col("INSCOV") == 3),
                lit(1),
            ).otherwise(lit(2)),
        )

        results = {row["DUPERSID"]: row["SUBPOP"] for row in df.collect()}
        assert results["P001"] == 1
        assert results["P002"] == 2
        assert results["P003"] == 2
        assert results["P004"] == 2

    def test_union_preserves_all_rows(self, spark):
        """Union of two DataFrames must contain all rows from both."""
        yr1 = spark.createDataFrame([("P001",), ("P002",)], ["DUPERSID"])
        yr2 = spark.createDataFrame([("P003",), ("P004",)], ["DUPERSID"])
        pool = yr1.union(yr2)
        assert pool.count() == 4


# ---------------------------------------------------------------------------
# exercise_5a tests (Family-level variables)
# ---------------------------------------------------------------------------

class TestExercise5a:
    """Tests for exercise_5a ETL (family-level aggregation)."""

    def test_family_size_count(self, spark):
        """FAMSIZE must equal number of persons per CPS family."""
        data = [
            ("D001", "F01", 100.0, 5000.0),
            ("D001", "F01", 200.0, 3000.0),
            ("D001", "F02", 150.0, 4000.0),
        ]
        df = spark.createDataFrame(data, ["DUID", "CPSFAMID", "TOTSLF15", "TTLP15X"])

        fam = df.groupBy("DUID", "CPSFAMID").agg(
            count("*").alias("FAMSIZE"),
            spark_sum("TOTSLF15").alias("FAMOOP"),
            spark_sum("TTLP15X").alias("FAMINC"),
        )

        f01 = fam.filter((col("DUID") == "D001") & (col("CPSFAMID") == "F01")).collect()[0]
        assert f01["FAMSIZE"] == 2
        assert f01["FAMOOP"] == 300.0
        assert f01["FAMINC"] == 8000.0

        f02 = fam.filter((col("DUID") == "D001") & (col("CPSFAMID") == "F02")).collect()[0]
        assert f02["FAMSIZE"] == 1

    def test_family_oop_sum(self, spark):
        """FAMOOP must equal sum of TOTSLF15 within the family."""
        data = [
            ("D001", "F01", 100.0),
            ("D001", "F01", 200.0),
            ("D001", "F01", 50.0),
        ]
        df = spark.createDataFrame(data, ["DUID", "CPSFAMID", "TOTSLF15"])

        fam = df.groupBy("DUID", "CPSFAMID").agg(
            spark_sum("TOTSLF15").alias("FAMOOP"),
        )

        result = fam.collect()[0]
        assert result["FAMOOP"] == 350.0


# ---------------------------------------------------------------------------
# exercise_5b tests (Insurance status from monthly variables)
# ---------------------------------------------------------------------------

class TestExercise5b:
    """Tests for exercise_5b ETL (monthly insurance counting)."""

    def test_full_insurance_flag(self, spark):
        """FULL_INSU=1 only when UNINS_N=0 (no uninsured months)."""
        data = [(0,), (1,), (6,), (12,)]
        df = spark.createDataFrame(data, ["UNINS_N"])
        df = df.withColumn("FULL_INSU", when(col("UNINS_N") == 0, 1).otherwise(0))

        results = [row["FULL_INSU"] for row in df.orderBy("UNINS_N").collect()]
        assert results == [1, 0, 0, 0]

    def test_group_ins_flags(self, spark):
        """GROUP_INS1=1 if GRP_N>0; GROUP_INS2=1 if GRP_N>0 and GRP_N==REF_N."""
        data = [
            (0, 12),   # No group -> both 0
            (6, 12),   # Some group -> INS1=1, INS2=0
            (12, 12),  # Full year group -> both 1
        ]
        df = spark.createDataFrame(data, ["GRP_N", "REF_N"])
        df = df.withColumn("GROUP_INS1", when(col("GRP_N") > 0, 1).otherwise(0))
        df = df.withColumn(
            "GROUP_INS2",
            when((col("GRP_N") > 0) & (col("GRP_N") == col("REF_N")), 1).otherwise(0),
        )

        results = [(row["GROUP_INS1"], row["GROUP_INS2"]) for row in df.orderBy("GRP_N").collect()]
        assert results == [(0, 0), (1, 0), (1, 1)]


# ---------------------------------------------------------------------------
# exercise_4b tests (COVID care delay)
# ---------------------------------------------------------------------------

class TestExercise4b:
    """Tests for exercise_4b ETL (COVID care delay regression prep)."""

    def test_cvdlay_recoding_1_2_to_1_0(self, spark):
        """CVDLAY variables must be recoded from 1/2 to 1/0."""
        data = [(1,), (2,), (-1,), (-7,)]
        df = spark.createDataFrame(data, ["CVDLAYCA53"])
        df = df.withColumn(
            "covid_delay_CARE",
            when(col("CVDLAYCA53") == 1, lit(1))
            .when(col("CVDLAYCA53") == 2, lit(0))
            .otherwise(col("CVDLAYCA53")),
        )

        result_map = {row["CVDLAYCA53"]: row["covid_delay_CARE"] for row in df.collect()}
        assert result_map[1] == 1
        assert result_map[2] == 0
        assert result_map[-1] == -1
        assert result_map[-7] == -7

    def test_subpop_flag_excludes_missing(self, spark):
        """subpop_CARE=1 only when CVDLAYCA53 >= 0."""
        data = [(1,), (2,), (-1,), (0,)]
        df = spark.createDataFrame(data, ["CVDLAYCA53"])
        df = df.withColumn("subpop_CARE", (col("CVDLAYCA53") >= 0).cast("int"))

        results = {row["CVDLAYCA53"]: row["subpop_CARE"] for row in df.collect()}
        assert results[1] == 1
        assert results[2] == 1
        assert results[-1] == 0
        assert results[0] == 1
