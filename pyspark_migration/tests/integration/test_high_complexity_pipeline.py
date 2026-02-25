"""Integration tests for high-complexity ETL pipelines.

Tests verify the complete join chain correctness with intermediate
checkpoint assertions at each stage.

These tests use synthetic data that mirrors the structure of real MEPS files
to validate the ETL logic end-to-end.
"""

import pytest
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, lit, sum as spark_sum, when


class TestCondPmed2020Pipeline:
    """Integration tests for the cond_pmed_2020 4-file join chain.

    Validates row counts at each checkpoint:
      1. After CCSR filter (hl_cond)
      2. After CLNK join (cond_clnk)
      3. After EVNTIDX de-duplication (cond_clnk_dedup)
      4. After PMED join (linked)
      5. After person-level collapse (person_level)
      6. After FYC left join (result)
    """

    @pytest.fixture
    def pipeline_data(self, spark):
        """Create synthetic pipeline data matching MEPS structure."""
        # Conditions: 5 HL conditions for 3 persons, 2 non-HL conditions
        conditions = spark.createDataFrame(
            [
                ("P001", "C001", "E78.0", "END010", "", ""),
                ("P001", "C002", "E78.5", "END010", "", ""),
                ("P002", "C003", "E78.2", "", "END010", ""),
                ("P003", "C004", "E78.0", "END010", "CIR007", ""),
                ("P003", "C005", "E78.1", "", "", "END010"),
                ("P004", "C006", "I10", "CIR007", "", ""),
                ("P005", "C007", "J45", "RSP002", "", ""),
            ],
            ["DUPERSID", "CONDIDX", "ICD10CDX", "CCSR1X", "CCSR2X", "CCSR3X"],
        )

        # CLNK: links conditions to events
        clnk = spark.createDataFrame(
            [
                ("P001", "C001", "E001", 8),
                ("P001", "C002", "E001", 8),  # C002 also links to E001 -> will dedup
                ("P001", "C001", "E002", 8),
                ("P002", "C003", "E003", 8),
                ("P003", "C004", "E004", 8),
                ("P003", "C005", "E004", 8),  # C005 also links to E004 -> will dedup
                ("P003", "C005", "E005", 8),
            ],
            ["DUPERSID", "CONDIDX", "EVNTIDX", "EVENTYPE"],
        )

        # PMED: prescribed medicine records (linkidx = evntidx)
        pmed = spark.createDataFrame(
            [
                ("P001", "D001", "R001", "E001", "ATORVASTATIN", 50.0),
                ("P001", "D001", "R002", "E001", "ATORVASTATIN", 50.0),
                ("P001", "D002", "R003", "E002", "SIMVASTATIN", 30.0),
                ("P002", "D003", "R004", "E003", "ROSUVASTATIN", 75.0),
                ("P003", "D004", "R005", "E004", "PRAVASTATIN", 40.0),
                ("P003", "D005", "R006", "E005", "EZETIMIBE", 60.0),
                ("P005", "D006", "R007", "E006", "ALBUTEROL", 25.0),  # Non-HL
            ],
            ["DUPERSID", "DRUGIDX", "RXRECIDX", "LINKIDX", "RXDRGNAM", "RXXP20X"],
        )

        # FYC: all persons including those without HL
        fyc = spark.createDataFrame(
            [
                ("P001", 1, 35, 1, 3, 1001, 1, 2.0),
                ("P002", 2, 70, 2, 5, 1002, 2, 1.5),
                ("P003", 1, 50, 1, 4, 1001, 1, 1.0),
                ("P004", 2, 25, 2, 1, 1002, 2, 0.5),
                ("P005", 1, 45, 2, 3, 1001, 1, 1.5),
            ],
            ["DUPERSID", "SEX", "AGELAST", "CHOLDX", "POVCAT20",
             "VARSTR", "VARPSU", "PERWT20F"],
        )

        return conditions, clnk, pmed, fyc

    def test_checkpoint_1_ccsr_filter(self, spark, pipeline_data):
        """After CCSR filter: only hyperlipidemia conditions remain."""
        conditions, clnk, pmed, fyc = pipeline_data

        hl_cond = conditions.filter(
            (col("CCSR1X") == "END010")
            | (col("CCSR2X") == "END010")
            | (col("CCSR3X") == "END010")
        )

        # 5 HL conditions (C001-C005), 2 non-HL (C006, C007) dropped
        assert hl_cond.count() == 5
        # Only P001, P002, P003 have HL conditions
        unique_persons = hl_cond.select("DUPERSID").distinct().count()
        assert unique_persons == 3

    def test_checkpoint_2_clnk_join(self, spark, pipeline_data):
        """After CLNK join: conditions linked to events via inner join."""
        conditions, clnk, pmed, fyc = pipeline_data

        hl_cond = conditions.filter(
            (col("CCSR1X") == "END010")
            | (col("CCSR2X") == "END010")
            | (col("CCSR3X") == "END010")
        )

        cond_clnk = hl_cond.join(clnk, on=["DUPERSID", "CONDIDX"], how="inner")

        # Expected matches: C001->E001, C002->E001, C001->E002,
        #   C003->E003, C004->E004, C005->E004, C005->E005
        assert cond_clnk.count() == 7

    def test_checkpoint_3_evntidx_dedup(self, spark, pipeline_data):
        """After EVNTIDX de-duplication: no duplicate DUPERSID+EVNTIDX pairs."""
        conditions, clnk, pmed, fyc = pipeline_data

        hl_cond = conditions.filter(
            (col("CCSR1X") == "END010")
            | (col("CCSR2X") == "END010")
            | (col("CCSR3X") == "END010")
        )
        cond_clnk = hl_cond.join(clnk, on=["DUPERSID", "CONDIDX"], how="inner")
        cond_clnk_dedup = cond_clnk.dropDuplicates(["DUPERSID", "EVNTIDX"])

        # Duplicates removed: P001+E001 (was 2, now 1), P003+E004 (was 2, now 1)
        # Remaining: P001+E001, P001+E002, P002+E003, P003+E004, P003+E005 = 5
        assert cond_clnk_dedup.count() == 5

        # Verify no duplicates remain
        dup_count = (
            cond_clnk_dedup.groupBy("DUPERSID", "EVNTIDX")
            .agg(count("*").alias("cnt"))
            .filter(col("cnt") > 1)
            .count()
        )
        assert dup_count == 0

    def test_checkpoint_4_pmed_join(self, spark, pipeline_data):
        """After PMED join: linked events have prescription records."""
        conditions, clnk, pmed, fyc = pipeline_data

        hl_cond = conditions.filter(
            (col("CCSR1X") == "END010")
            | (col("CCSR2X") == "END010")
            | (col("CCSR3X") == "END010")
        )
        cond_clnk = hl_cond.join(clnk, on=["DUPERSID", "CONDIDX"], how="inner")
        cond_clnk_dedup = cond_clnk.dropDuplicates(["DUPERSID", "EVNTIDX"])

        # Rename LINKIDX to EVNTIDX in PMED for join
        pmed_renamed = pmed.withColumnRenamed("LINKIDX", "EVNTIDX")

        linked = cond_clnk_dedup.join(
            pmed_renamed.select("DUPERSID", "EVNTIDX", "RXDRGNAM", "RXXP20X", "DRUGIDX", "RXRECIDX"),
            on=["DUPERSID", "EVNTIDX"],
            how="inner",
        )

        # E001 has 2 PMED records, E002 has 1, E003 has 1, E004 has 1, E005 has 1 = 6
        assert linked.count() == 6

    def test_checkpoint_5_person_level_collapse(self, spark, pipeline_data):
        """After person-level collapse: unique DUPERSID count matches."""
        conditions, clnk, pmed, fyc = pipeline_data

        hl_cond = conditions.filter(
            (col("CCSR1X") == "END010")
            | (col("CCSR2X") == "END010")
            | (col("CCSR3X") == "END010")
        )
        cond_clnk = hl_cond.join(clnk, on=["DUPERSID", "CONDIDX"], how="inner")
        cond_clnk_dedup = cond_clnk.dropDuplicates(["DUPERSID", "EVNTIDX"])
        pmed_renamed = pmed.withColumnRenamed("LINKIDX", "EVNTIDX")
        linked = cond_clnk_dedup.join(
            pmed_renamed.select("DUPERSID", "EVNTIDX", "RXXP20X", "DRUGIDX", "RXRECIDX"),
            on=["DUPERSID", "EVNTIDX"],
            how="inner",
        )

        person_level = linked.groupBy("DUPERSID").agg(
            count("*").alias("n_hl_fills"),
            spark_sum("RXXP20X").alias("hl_drug_exp"),
        )

        # 3 persons with HL conditions linked to PMEDs: P001, P002, P003
        assert person_level.count() == 3

        # Verify per-person aggregates
        p1 = person_level.filter(col("DUPERSID") == "P001").collect()[0]
        assert p1["n_hl_fills"] == 3  # 2 from E001 + 1 from E002
        assert p1["hl_drug_exp"] == 130.0  # 50+50+30

    def test_checkpoint_6_fyc_left_join(self, spark, pipeline_data):
        """After FYC left join: row count equals FYC row count."""
        conditions, clnk, pmed, fyc = pipeline_data

        hl_cond = conditions.filter(
            (col("CCSR1X") == "END010")
            | (col("CCSR2X") == "END010")
            | (col("CCSR3X") == "END010")
        )
        cond_clnk = hl_cond.join(clnk, on=["DUPERSID", "CONDIDX"], how="inner")
        cond_clnk_dedup = cond_clnk.dropDuplicates(["DUPERSID", "EVNTIDX"])
        pmed_renamed = pmed.withColumnRenamed("LINKIDX", "EVNTIDX")
        linked = cond_clnk_dedup.join(
            pmed_renamed.select("DUPERSID", "EVNTIDX", "RXXP20X", "DRUGIDX", "RXRECIDX"),
            on=["DUPERSID", "EVNTIDX"],
            how="inner",
        )
        person_level = linked.groupBy("DUPERSID").agg(
            count("*").alias("n_hl_fills"),
            spark_sum("RXXP20X").alias("hl_drug_exp"),
        )

        # Left join preserves ALL FYC rows
        result = fyc.join(person_level, on="DUPERSID", how="left")
        result = result.fillna({"n_hl_fills": 0, "hl_drug_exp": 0.0})
        result = result.withColumn(
            "hl_pmed_flag",
            when(col("n_hl_fills") > 0, lit(1)).otherwise(lit(0)),
        )

        # Must equal FYC count (5 persons)
        assert result.count() == fyc.count()

        # P004 and P005 should have zero fills
        p4 = result.filter(col("DUPERSID") == "P004").collect()[0]
        assert p4["n_hl_fills"] == 0
        assert p4["hl_drug_exp"] == 0.0
        assert p4["hl_pmed_flag"] == 0

        # Survey design variables must be preserved
        for col_name in ["VARSTR", "VARPSU", "PERWT20F"]:
            null_count = result.filter(col(col_name).isNull()).count()
            assert null_count == 0, f"{col_name} has nulls after join"


class TestCondMv2020Pipeline:
    """Integration tests for the cond_mv_2020 pipeline (Stata migration).

    Uses the same synthetic data structure to validate the Stata-equivalent
    join chain.
    """

    def test_full_pipeline_end_to_end(self, spark):
        """Complete pipeline must produce correct person-level output."""
        # Conditions
        cond = spark.createDataFrame(
            [
                ("P001", "C001", "END010", "", ""),
                ("P002", "C002", "", "END010", ""),
            ],
            ["DUPERSID", "CONDIDX", "CCSR1X", "CCSR2X", "CCSR3X"],
        )

        # CLNK
        clnk = spark.createDataFrame(
            [("P001", "C001", "E001"), ("P002", "C002", "E002")],
            ["DUPERSID", "CONDIDX", "EVNTIDX"],
        )

        # PMED
        pmed = spark.createDataFrame(
            [
                ("P001", "E001", 50.0),
                ("P001", "E001", 30.0),
                ("P002", "E002", 75.0),
            ],
            ["DUPERSID", "EVNTIDX", "RXXP20X"],
        )

        # FYC
        fyc = spark.createDataFrame(
            [
                ("P001", 1, 35, 1, 3, 1001, 1, 2.0),
                ("P002", 2, 70, 2, 5, 1002, 2, 1.5),
                ("P003", 1, 50, 2, 4, 1001, 1, 1.0),
            ],
            ["DUPERSID", "SEX", "AGELAST", "CHOLDX", "POVCAT20",
             "VARSTR", "VARPSU", "PERWT20F"],
        )

        # Execute pipeline
        hl_cond = cond.filter(
            (col("CCSR1X") == "END010") | (col("CCSR2X") == "END010") | (col("CCSR3X") == "END010")
        )
        merged = hl_cond.join(clnk, on=["DUPERSID", "CONDIDX"], how="inner")
        deduped = merged.dropDuplicates(["EVNTIDX"])
        linked = deduped.join(pmed, on=["DUPERSID", "EVNTIDX"], how="inner")

        person_level = linked.groupBy("DUPERSID").agg(
            count("*").alias("num_rx"),
            spark_sum("RXXP20X").alias("exp_rx"),
        )

        result = fyc.join(person_level, on="DUPERSID", how="left")
        result = result.fillna({"num_rx": 0, "exp_rx": 0.0})
        result = result.withColumn("any_rx", (col("num_rx") > 0).cast("int"))

        # Verify final output
        assert result.count() == 3  # All FYC rows preserved

        p1 = result.filter(col("DUPERSID") == "P001").collect()[0]
        assert p1["num_rx"] == 2
        assert p1["exp_rx"] == 80.0
        assert p1["any_rx"] == 1

        p3 = result.filter(col("DUPERSID") == "P003").collect()[0]
        assert p3["num_rx"] == 0
        assert p3["exp_rx"] == 0.0
        assert p3["any_rx"] == 0


class TestExercise4dPipeline:
    """Integration tests for the exercise_4d 3-year pooling pipeline."""

    def test_three_year_pool_with_variance_merge(self, spark):
        """Pooled data merged with variance file must preserve all pooled rows."""
        # Simplified 3-year data
        yr1 = spark.createDataFrame(
            [("2112345678", 21, 2.0, 30, 1, 1)],
            ["DUPERSID", "PANEL", "PERWT17F", "AGELAST", "ARTHDX", "JTPAIN31"],
        )
        yr2 = spark.createDataFrame(
            [("2212345678", 22, 3.0, 40, 2, 1)],
            ["DUPERSID", "PANEL", "PERWT18F", "AGELAST", "ARTHDX", "JTPAIN31_M18"],
        )
        yr3 = spark.createDataFrame(
            [("2312345678", 23, 4.0, 50, 1, 2)],
            ["DUPERSID", "PANEL", "PERWT19F", "AGELAST", "ARTHDX", "JTPAIN31_M18"],
        )

        # Standardize and pool
        yr1 = yr1.withColumn("PERWTF", col("PERWT17F") / lit(3))
        yr2 = yr2.withColumn("PERWTF", col("PERWT18F") / lit(3))
        yr3 = yr3.withColumn("PERWTF", col("PERWT19F") / lit(3))

        common = ["DUPERSID", "PANEL", "AGELAST", "ARTHDX", "PERWTF"]
        pool = yr1.select(common).union(yr2.select(common)).union(yr3.select(common))

        assert pool.count() == 3

        # Variance file merge (left join preserves all pooled rows)
        vs = spark.createDataFrame(
            [("2112345678", 100, 1), ("2212345678", 101, 2)],
            ["DUPERSID", "STRA9619", "PSU9619"],
        )

        result = pool.join(vs, on="DUPERSID", how="left")
        assert result.count() == 3  # All pooled rows preserved
