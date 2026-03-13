"""L1: Merge FYC with Jobs file, 2001.

Link person-level FYC data with jobs file for employment analysis.

Input files:
 - C:/MEPS/h60.ssp (2001 FYC)
 - C:/MEPS/h56.ssp (2001 Jobs file)

Ported from: SAS/older_exercises_1996_to_2006/Linking_examples/L1/L1.sas
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean, survey_total


def main(data_dir: str = "C:/MEPS") -> None:
    fyc01 = read_meps(year=2001, file_type="FYC", data_dir=data_dir)
    jobs01 = read_meps(year=2001, file_type="JOBS", data_dir=data_dir)

    # Select key variables from FYC
    fyc_sub = fyc01.select([
        "DUPERSID", "VARSTR", "VARPSU", "PERWT01F",
        "AGELAST", "SEX", "TOTEXP01",
    ])

    # Select job variables
    job_cols = ["DUPERSID", "JOBSIDX"] + [
        c for c in jobs01.columns
        if any(x in c for x in ["OFFER", "HELD", "WAGE", "HOUR", "SUBTYPE"])
    ][:10]
    jobs_sub = jobs01.select([c for c in job_cols if c in jobs01.columns])

    # Merge: keep all FYC persons, bring in job info
    merged = fyc_sub.join(jobs_sub, on="DUPERSID", how="left")

    # Create indicator for having a job record
    merged = merged.with_columns(
        pl.col("JOBSIDX").is_not_null().cast(pl.Int32).alias("has_job")
    )

    dsgn = MEPSSurveyDesign(
        data=merged, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT01F", nest=True,
    )

    print("=== FYC-Jobs Merge, 2001 ===")
    print(f"Total records after merge: {merged.height}")
    for est in survey_total(dsgn, ["has_job"]):
        print(f"  Persons with job record: {est.estimate:,.0f} (SE: {est.se:,.0f})")
    for est in survey_mean(dsgn, ["has_job"]):
        print(f"  Percent with job record: {est.estimate:.4f} (SE: {est.se:.4f})")


if __name__ == "__main__":
    main()
