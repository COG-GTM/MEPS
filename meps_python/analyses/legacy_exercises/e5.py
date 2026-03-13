"""E5: Event-level expenditure estimates for IP stays and OB visits, 2001.

Event-level expenditures by type of service.

Input files:
 - C:/MEPS/h60.ssp (2001 FYC)
 - C:/MEPS/h59d.ssp (2001 IP event file)
 - C:/MEPS/h59g.ssp (2001 OB event file)

Ported from: SAS/older_exercises_1996_to_2006/Estimation_examples/E5/E5.sas
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean, survey_total


def main(data_dir: str = "C:/MEPS") -> None:
    fyc01 = read_meps(year=2001, file_type="FYC", data_dir=data_dir).select(
        ["DUPERSID", "PERWT01F", "VARSTR", "VARPSU"]
    )
    ip01 = read_meps(year=2001, file_type="IP", data_dir=data_dir)
    ob01 = read_meps(year=2001, file_type="OB", data_dir=data_dir)

    # IP events
    ip01 = ip01.select([
        "DUPERSID", "EVNTIDX", pl.col("IPXP01X").alias("XP"),
    ]).with_columns([pl.lit(1).alias("count"), pl.lit("IP").alias("event_type")])

    # OB events
    ob01 = ob01.select([
        "DUPERSID", "EVNTIDX", pl.col("OBXP01X").alias("XP"),
    ]).with_columns([pl.lit(1).alias("count"), pl.lit("OB").alias("event_type")])

    for label, events in [("Inpatient Stays", ip01), ("Office-Based Visits", ob01)]:
        merged = events.join(fyc01, on="DUPERSID", how="full", coalesce=True)
        merged = merged.with_columns([
            pl.col("count").fill_null(0),
            pl.col("XP").fill_null(0),
        ])

        dsgn = MEPSSurveyDesign(
            data=merged, psu_col="VARPSU", strata_col="VARSTR",
            weight_col="PERWT01F", nest=True,
        )
        sub = dsgn.subset(pl.col("count") == 1)

        print(f"=== {label} ===")
        for est in survey_total(sub, ["count"]):
            print(f"  Total events: {est.estimate:,.0f} (SE: {est.se:,.0f})")
        for est in survey_total(sub, ["XP"]):
            print(f"  Total expenditures: ${est.estimate:,.0f} (SE: ${est.se:,.0f})")
        for est in survey_mean(sub, ["XP"]):
            print(f"  Mean exp per event: ${est.estimate:,.2f} (SE: ${est.se:,.2f})")
        print()


if __name__ == "__main__":
    main()
