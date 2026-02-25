# -----------------------------------------------------------------------------
# Example code to replicate estimates from the MEPS-HC Data Tools summary tables
#
# Use, expenditures, and population, 2016
#
# Expenditures by race and sex
#  - Number of people
#  - Percent of population with an expense
#  - Total expenditures
#  - Mean expenditure per person
#  - Mean expenditure per person with expense
#  - Median expenditure per person with expense
#
# Input file: h192 (2016 full-year consolidated)
#             Expected format: Parquet or CSV (converted from .ssp)
#
# Note: This PySpark script replicates the point estimates (weighted totals,
#       weighted means, and weighted medians) from the SAS version. Standard
#       errors from SAS's Taylor-series linearization method are not replicated
#       here. Median estimates may vary slightly from SAS and R due to different
#       methods of estimating survey quantiles.
# -----------------------------------------------------------------------------

from pyspark.sql import SparkSession, Window, functions as F

# Initialize Spark session
spark = SparkSession.builder \
    .appName("MEPS Use Race Sex 2016") \
    .getOrCreate()

# ---------------------------------------------------------------------------
# Load FYC file
# ---------------------------------------------------------------------------
# Update the path below to the location of your converted h192 file
# Supports Parquet or CSV format

INPUT_PATH = "h192.parquet"  # or "h192.csv"

# Uncomment the appropriate line based on your file format:
FYC = spark.read.parquet(INPUT_PATH)
# FYC = spark.read.csv(INPUT_PATH, header=True, inferSchema=True)

# ---------------------------------------------------------------------------
# Define variables
# ---------------------------------------------------------------------------

# Race/ethnicity
#  - 1996-2002: race/ethnicity variable based on RACETHNX (see documentation)
#  - 2002-2011: race/ethnicity variable based on RACETHNX and RACEX:
#      hisp   = (RACETHNX == 1)
#      white  = (RACETHNX == 4 & RACEX == 1)
#      black  = (RACETHNX == 2)
#      native = (RACETHNX >= 3 & RACEX in (3,6))
#      asian  = (RACETHNX >= 3 & RACEX in (4,5))
#
#  - For 2012 and later, use RACETHX and RACEV1X:

FYC = FYC.withColumn("hisp",   (F.col("RACETHX") == 1).cast("int"))
FYC = FYC.withColumn("white",  (F.col("RACETHX") == 2).cast("int"))
FYC = FYC.withColumn("black",  (F.col("RACETHX") == 3).cast("int"))
FYC = FYC.withColumn("native", (
    (F.col("RACETHX") > 3) & (F.col("RACEV1X").isin(3, 6))
).cast("int"))
FYC = FYC.withColumn("asian",  (
    (F.col("RACETHX") > 3) & (F.col("RACEV1X").isin(4, 5))
).cast("int"))

FYC = FYC.withColumn("race",
    (1 * F.col("hisp") + 2 * F.col("white") + 3 * F.col("black") +
     4 * F.col("native") + 5 * F.col("asian")))

# Counter variable for population totals
FYC = FYC.withColumn("person", F.lit(1))

# Flag for persons with an expense
FYC = FYC.withColumn("has_exp", (F.col("TOTEXP16") > 0).cast("int"))

# ---------------------------------------------------------------------------
# Label mappings
# ---------------------------------------------------------------------------

race_labels = {
    1: "Hispanic",
    2: "White",
    3: "Black",
    4: "Amer. Indian, AK Native, or mult. races",
    5: "Asian, Hawaiian, or Pacific Islander",
}

sex_labels = {
    1: "Male",
    2: "Female",
}

WEIGHT = "PERWT16F"

# ---------------------------------------------------------------------------
# Calculate estimates using weighted aggregations
# ---------------------------------------------------------------------------

# --- Number of people, by sex and race --------------------------------------

print("=" * 80)
print("Number of people, by sex and race, 2016")
print("=" * 80)

pop_totals = FYC.groupBy("SEX", "race").agg(
    F.sum(F.col("person") * F.col(WEIGHT)).alias("Number of people")
).orderBy("SEX", "race")

pop_collected = pop_totals.collect()
print(f"\n{'Sex':<10} {'Race':<45} {'Number of People':>20}")
print("-" * 77)
for row in pop_collected:
    sex_lbl = sex_labels.get(row["SEX"], str(row["SEX"]))
    race_lbl = race_labels.get(row["race"], str(row["race"]))
    print(f"{sex_lbl:<10} {race_lbl:<45} {row['Number of people']:>20,.0f}")

# --- Percent of population with an expense, by sex and race -----------------

print("\n" + "=" * 80)
print("Percent of population with an expense, by sex and race, 2016")
print("=" * 80)

pct_exp = FYC.groupBy("SEX", "race").agg(
    (F.sum(F.col("has_exp") * F.col(WEIGHT)) / F.sum(F.col(WEIGHT))).alias("Pct with expense")
).orderBy("SEX", "race")

pct_collected = pct_exp.collect()
print(f"\n{'Sex':<10} {'Race':<45} {'Pct with Expense':>20}")
print("-" * 77)
for row in pct_collected:
    sex_lbl = sex_labels.get(row["SEX"], str(row["SEX"]))
    race_lbl = race_labels.get(row["race"], str(row["race"]))
    print(f"{sex_lbl:<10} {race_lbl:<45} {row['Pct with expense']:>20.4f}")

# --- Total expenditures, by sex and race ------------------------------------

print("\n" + "=" * 80)
print("Total expenditures, by sex and race, 2016")
print("=" * 80)

total_exp = FYC.groupBy("SEX", "race").agg(
    F.sum(F.col("TOTEXP16") * F.col(WEIGHT)).alias("Total expenditures")
).orderBy("SEX", "race")

total_collected = total_exp.collect()
print(f"\n{'Sex':<10} {'Race':<45} {'Total Expenditures':>22}")
print("-" * 79)
for row in total_collected:
    sex_lbl = sex_labels.get(row["SEX"], str(row["SEX"]))
    race_lbl = race_labels.get(row["race"], str(row["race"]))
    print(f"{sex_lbl:<10} {race_lbl:<45} {row['Total expenditures']:>22,.2f}")

# --- Mean expenditure per person, by sex and race ---------------------------

print("\n" + "=" * 80)
print("Mean expenditure per person, by sex and race, 2016")
print("=" * 80)

mean_exp = FYC.groupBy("SEX", "race").agg(
    (F.sum(F.col("TOTEXP16") * F.col(WEIGHT)) / F.sum(F.col(WEIGHT))).alias("Mean per person")
).orderBy("SEX", "race")

mean_collected = mean_exp.collect()
print(f"\n{'Sex':<10} {'Race':<45} {'Mean Per Person':>20}")
print("-" * 77)
for row in mean_collected:
    sex_lbl = sex_labels.get(row["SEX"], str(row["SEX"]))
    race_lbl = race_labels.get(row["race"], str(row["race"]))
    print(f"{sex_lbl:<10} {race_lbl:<45} {row['Mean per person']:>20,.2f}")

# --- Mean expenditure per person with expense, by sex and race --------------

print("\n" + "=" * 80)
print("Mean expenditure per person with expense, by sex and race, 2016")
print("=" * 80)

has_exp_df = FYC.filter(F.col("has_exp") == 1)

mean_exp_with = has_exp_df.groupBy("SEX", "race").agg(
    (F.sum(F.col("TOTEXP16") * F.col(WEIGHT)) / F.sum(F.col(WEIGHT))).alias("Mean per person w/ exp")
).orderBy("SEX", "race")

mean_w_collected = mean_exp_with.collect()
print(f"\n{'Sex':<10} {'Race':<45} {'Mean w/ Expense':>20}")
print("-" * 77)
for row in mean_w_collected:
    sex_lbl = sex_labels.get(row["SEX"], str(row["SEX"]))
    race_lbl = race_labels.get(row["race"], str(row["race"]))
    print(f"{sex_lbl:<10} {race_lbl:<45} {row['Mean per person w/ exp']:>20,.2f}")

# --- Median expenditure per person with expense, by sex and race ------------
#
#  Note: Estimates may vary from R, SAS, and Stata, due to different methods
#        of estimating survey quantiles. This implementation uses a weighted
#        median approximation based on cumulative weight distribution.

print("\n" + "=" * 80)
print("Median expenditure per person with expense, by sex and race, 2016")
print("  (Note: estimates may vary from SAS/R/Stata due to quantile methods)")
print("=" * 80)

# Weighted median via cumulative weight approach
# For each sex*race group, sort by TOTEXP16, compute cumulative weights,
# and find the value where cumulative weight crosses the 50% threshold.

window_spec = Window.partitionBy("SEX", "race").orderBy("TOTEXP16")

median_df = has_exp_df.withColumn(
    "cum_weight", F.sum(F.col(WEIGHT)).over(window_spec)
)

group_total_weight = has_exp_df.groupBy("SEX", "race").agg(
    F.sum(F.col(WEIGHT)).alias("group_total_weight")
)

median_df = median_df.join(group_total_weight, on=["SEX", "race"], how="left")
median_df = median_df.withColumn(
    "cum_pct", F.col("cum_weight") / F.col("group_total_weight")
)

# Find the first row where cumulative percentage >= 0.5
median_df = median_df.filter(F.col("cum_pct") >= 0.5)

# Get the minimum TOTEXP16 per group where cum_pct >= 0.5 (this is the median)
weighted_median = median_df.groupBy("SEX", "race").agg(
    F.min("TOTEXP16").alias("Median expenditure")
).orderBy("SEX", "race")

median_collected = weighted_median.collect()
print(f"\n{'Sex':<10} {'Race':<45} {'Median w/ Expense':>20}")
print("-" * 77)
for row in median_collected:
    sex_lbl = sex_labels.get(row["SEX"], str(row["SEX"]))
    race_lbl = race_labels.get(row["race"], str(row["race"]))
    print(f"{sex_lbl:<10} {race_lbl:<45} {row['Median expenditure']:>20,.2f}")

# ---------------------------------------------------------------------------
# Stop Spark session
# ---------------------------------------------------------------------------
spark.stop()
