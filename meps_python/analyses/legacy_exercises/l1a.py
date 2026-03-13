"""L1A: Combine 2000 and 2001 Jobs files.

Append two years of jobs data and link with FYC for pooled analysis.

Input files:
 - C:/MEPS/h56.ssp (2001 Jobs file)
 - C:/MEPS/h40.ssp (2000 Jobs file)
 - C:/MEPS/h60.ssp (2001 FYC)
 - C:/MEPS/h50.ssp (2000 FYC)

Ported from: SAS/older_exercises_1996_to_2006/Linking_examples/L1A/L1A.sas
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean


def main(data_dir: str = "C:/MEPS") -> None:
    jobs01 = read_meps(year=2001, file_type="JOBS", data_dir=data_dir)
    jobs00 = read_meps(year=2000, file_type="JOBS", data_dir=data_dir)

    fyc01 = read_meps(year=2001, file_type="FYC", data_dir=data_dir)
    fyc00 = read_meps(year=2000, file_type="FYC", data_dir=data_dir)

    # Common columns for stacking
    common_cols = sorted(set(jobs01.columns) & set(jobs00.columns))
    jobs_pool = pl.concat([
        jobs01.select(common_cols),
        jobs00.select(common_cols),
    ])

    print(f"Combined jobs records: {jobs_pool.height}")

    # Pool FYC files
    fyc01_sub = fyc01.select([
        "DUPERSID", "VARSTR", "VARPSU",
        pl.col("PERWT01F").alias("perwt"),
        pl.col("TOTEXP01").alias("totexp"),
    ])
    fyc00_sub = fyc00.select([
        "DUPERSID", "VARSTR", "VARPSU",
        pl.col("PERWT00F").alias("perwt"),
        pl.col("TOTEXP00").alias("totexp"),
    ])

    pool = pl.concat([fyc01_sub, fyc00_sub]).with_columns(
        (pl.col("perwt") / 2).alias("poolwt")
    )

    # Merge pooled FYC with pooled jobs
    merged = pool.join(jobs_pool, on="DUPERSID", how="left")
    merged = merged.with_columns(
        pl.col("JOBSIDX").is_not_null().cast(pl.Int32).alias("has_job")
    )

    dsgn = MEPSSurveyDesign(
        data=merged, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="poolwt", nest=True,
    )

    print("\n=== Pooled Jobs Analysis, 2000-2001 ===")
    for est in survey_mean(dsgn, ["has_job"]):
        print(f"  Percent with job: {est.estimate:.4f} (SE: {est.se:.4f})")


if __name__ == "__main__":
    main()
