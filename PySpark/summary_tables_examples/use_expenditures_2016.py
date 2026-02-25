# -----------------------------------------------------------------------------
# Example code to replicate estimates from the MEPS-HC Data Tools summary tables
#
# Use, expenditures, and population, 2016
#
# Expenditures by event type and source of payment (SOP)
#  - Total expenditures
#  - Mean expenditure per person
#  - Mean out-of-pocket (SLF) payment per person with an out-of-pocket expense
#
# Selected event types:
#  - Office-based medical visits (OBV)
#  - Office-based physician visits (OBD)
#  - Outpatient visits (OPT)
#  - Outpatient physician visits (OPV)
#
# Input file: h192 (2016 full-year consolidated)
#             Expected format: Parquet or CSV (converted from .ssp)
#
# Note: This PySpark script replicates the point estimates (weighted totals
#       and weighted means) from the SAS version. Standard errors from SAS's
#       Taylor-series linearization method are not replicated here.
# -----------------------------------------------------------------------------

from pyspark.sql import SparkSession, functions as F

# Initialize Spark session
spark = SparkSession.builder \
    .appName("MEPS Use Expenditures 2016") \
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
# Aggregate payment sources
# ---------------------------------------------------------------------------
#
#  Notes:
#   - For 1996-1999: TRICARE label is CHM (changed to TRI in 2000)
#   - For 1996-2006: combined facility + SBD variables for hospital-type
#     events are not on PUF
#   - Starting in 2019, 'Other public' (OPU) and 'Other private' (OPR)
#     are dropped from the files
#
#  PTR = Private (PRV) + TRICARE (TRI)
#
#  OTZ = other federal (OFD)  + State/local (STL) + other private (OPR) +
#         other public (OPU)  + other unclassified sources (OSR) +
#         worker's comp (WCP) + Veteran's (VA)

# Office-based visits
FYC = FYC.withColumn("OBVPTR", F.col("OBVPRV16") + F.col("OBVTRI16"))
FYC = FYC.withColumn("OBVOTZ",
    F.col("OBVOFD16") + F.col("OBVSTL16") + F.col("OBVOPR16") +
    F.col("OBVOPU16") + F.col("OBVOSR16") + F.col("OBVWCP16") + F.col("OBVVA16"))

# Office-based physician visits
FYC = FYC.withColumn("OBDPTR", F.col("OBDPRV16") + F.col("OBDTRI16"))
FYC = FYC.withColumn("OBDOTZ",
    F.col("OBDOFD16") + F.col("OBDSTL16") + F.col("OBDOPR16") +
    F.col("OBDOPU16") + F.col("OBDOSR16") + F.col("OBDWCP16") + F.col("OBDVA16"))

# Outpatient visits (facility + SBD expenses)
#  - For 1996-2006: combined facility + SBD variables are not on PUF
FYC = FYC.withColumn("OPTPTR", F.col("OPTPRV16") + F.col("OPTTRI16"))
FYC = FYC.withColumn("OPTOTZ",
    F.col("OPTOFD16") + F.col("OPTSTL16") + F.col("OPTOPR16") +
    F.col("OPTOPU16") + F.col("OPTOSR16") + F.col("OPTWCP16") + F.col("OPTVA16"))

# Outpatient physician visits (facility expense)
FYC = FYC.withColumn("OPVPTR", F.col("OPVPRV16") + F.col("OPVTRI16"))
FYC = FYC.withColumn("OPVOTZ",
    F.col("OPVOFD16") + F.col("OPVSTL16") + F.col("OPVOPR16") +
    F.col("OPVOPU16") + F.col("OPVOSR16") + F.col("OPVWCP16") + F.col("OPVVA16"))

# Outpatient physician visits (SBD expense)
FYC = FYC.withColumn("OPSPTR", F.col("OPSPRV16") + F.col("OPSTRI16"))
FYC = FYC.withColumn("OPSOTZ",
    F.col("OPSOFD16") + F.col("OPSSTL16") + F.col("OPSOPR16") +
    F.col("OPSOPU16") + F.col("OPSOSR16") + F.col("OPSWCP16") + F.col("OPSVA16"))

# ---------------------------------------------------------------------------
# Combine facility and SBD expenses for hospital-type events
# ---------------------------------------------------------------------------
#  Note: for 1996-2006, also need to create OPT*** = OPF*** + OPD***

FYC = FYC.withColumn("OPpSLF", F.col("OPVSLF16") + F.col("OPSSLF16"))  # out-of-pocket
FYC = FYC.withColumn("OPpMCR", F.col("OPVMCR16") + F.col("OPSMCR16"))  # Medicare
FYC = FYC.withColumn("OPpMCD", F.col("OPVMCD16") + F.col("OPSMCD16"))  # Medicaid
FYC = FYC.withColumn("OPpPTR", F.col("OPVPTR") + F.col("OPSPTR"))      # private (incl. TRICARE)
FYC = FYC.withColumn("OPpOTZ", F.col("OPVOTZ") + F.col("OPSOTZ"))      # other sources

# ---------------------------------------------------------------------------
# Define domains for persons with out-of-pocket expense
# ---------------------------------------------------------------------------

FYC = FYC.withColumn("has_OBVSLF", (F.col("OBVSLF16") > 0).cast("int"))
FYC = FYC.withColumn("has_OBDSLF", (F.col("OBDSLF16") > 0).cast("int"))
FYC = FYC.withColumn("has_OPTSLF", (F.col("OPTSLF16") > 0).cast("int"))
FYC = FYC.withColumn("has_OPpSLF", (F.col("OPpSLF") > 0).cast("int"))

# ---------------------------------------------------------------------------
# Calculate estimates using weighted aggregations
# ---------------------------------------------------------------------------
#
# Sources of payment (SOP) abbreviations:
#  SLF: Out-of-pocket
#  PTR: Private insurance, including TRICARE
#  MCR: Medicare
#  MCD: Medicaid
#  OTZ: Other

# Variables to aggregate, organized by event type and source of payment
expenditure_vars = {
    # Office-based visits
    "OBVSLF16": ("Office-based visits", "Out-of-pocket"),
    "OBVPTR":   ("Office-based visits", "Private"),
    "OBVMCR16": ("Office-based visits", "Medicare"),
    "OBVMCD16": ("Office-based visits", "Medicaid"),
    "OBVOTZ":   ("Office-based visits", "Other"),
    # Office-based physician visits
    "OBDSLF16": ("Office-based physician visits", "Out-of-pocket"),
    "OBDPTR":   ("Office-based physician visits", "Private"),
    "OBDMCR16": ("Office-based physician visits", "Medicare"),
    "OBDMCD16": ("Office-based physician visits", "Medicaid"),
    "OBDOTZ":   ("Office-based physician visits", "Other"),
    # Outpatient visits
    "OPTSLF16": ("Outpatient visits", "Out-of-pocket"),
    "OPTPTR":   ("Outpatient visits", "Private"),
    "OPTMCR16": ("Outpatient visits", "Medicare"),
    "OPTMCD16": ("Outpatient visits", "Medicaid"),
    "OPTOTZ":   ("Outpatient visits", "Other"),
    # Outpatient physician visits
    "OPpSLF":   ("Outpatient physician visits", "Out-of-pocket"),
    "OPpPTR":   ("Outpatient physician visits", "Private"),
    "OPpMCR":   ("Outpatient physician visits", "Medicare"),
    "OPpMCD":   ("Outpatient physician visits", "Medicaid"),
    "OPpOTZ":   ("Outpatient physician visits", "Other"),
}

WEIGHT = "PERWT16F"

# --- Total expenditures and mean expenditure per person ---------------------
#     by event type and source of payment

print("=" * 80)
print("Total expenditures and mean expenditure per person")
print("by event type and source of payment, 2016")
print("=" * 80)

agg_exprs = []
for var_name in expenditure_vars:
    agg_exprs.append(
        F.sum(F.col(var_name) * F.col(WEIGHT)).alias(f"{var_name}_total")
    )
    agg_exprs.append(
        (F.sum(F.col(var_name) * F.col(WEIGHT)) / F.sum(F.col(WEIGHT))).alias(f"{var_name}_mean")
    )

result = FYC.agg(*agg_exprs).collect()[0]

print(f"\n{'Event Type':<35} {'Source of Payment':<18} {'Total Expenditures':>22} {'Mean Per Person':>18}")
print("-" * 95)
for var_name, (event_label, sop_label) in expenditure_vars.items():
    total_val = result[f"{var_name}_total"]
    mean_val = result[f"{var_name}_mean"]
    print(f"{event_label:<35} {sop_label:<18} {total_val:>22,.2f} {mean_val:>18,.2f}")

# --- Mean out-of-pocket expense per person with an out-of-pocket expense ----

print("\n" + "=" * 80)
print("Mean out-of-pocket expense per person with an out-of-pocket expense")
print("=" * 80)

domain_vars = {
    "OBVSLF16": ("has_OBVSLF", "Office-based visits"),
    "OBDSLF16": ("has_OBDSLF", "Office-based physician visits"),
    "OPTSLF16": ("has_OPTSLF", "Outpatient visits"),
    "OPpSLF":   ("has_OPpSLF", "Outpatient physician visits"),
}

print(f"\n{'Event Type':<40} {'Mean OOP Per Person w/ Expense':>35}")
print("-" * 77)

for exp_var, (domain_flag, event_label) in domain_vars.items():
    domain_df = FYC.filter(F.col(domain_flag) == 1)
    domain_result = domain_df.agg(
        (F.sum(F.col(exp_var) * F.col(WEIGHT)) / F.sum(F.col(WEIGHT))).alias("weighted_mean")
    ).collect()[0]
    mean_val = domain_result["weighted_mean"]
    print(f"{event_label:<40} {mean_val:>35,.2f}")

# ---------------------------------------------------------------------------
# Stop Spark session
# ---------------------------------------------------------------------------
spark.stop()
