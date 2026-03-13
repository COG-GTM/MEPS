"""Use, expenditures, and population, 2016.

Utilization and expenditures by event type and source of payment (SOP):
 - Total number of events
 - Mean expenditure per event, by source of payment
 - Mean events per person, for office-based visits

Selected event types: OB visits, OB physician, OP visits, OP physician

Input files:
 - C:/MEPS/h192.ssp  (2016 FYC)
 - C:/MEPS/h188f.ssp (2016 OP event file)
 - C:/MEPS/h188g.ssp (2016 OB event file)

Ported from: R/summary_tables_examples/use_events_2016.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean, survey_total


def main(data_dir: str = "C:/MEPS") -> None:
    # Load FYC and keep only needed variables
    FYC = read_meps(year=2016, file_type="FYC", data_dir=data_dir).select(
        ["DUPERSID", "PERWT16F", "VARSTR", "VARPSU"]
    )

    # Load event files
    OP = read_meps(year=2016, file_type="OP", data_dir=data_dir)
    OB = read_meps(year=2016, file_type="OB", data_dir=data_dir)

    # Aggregate payment sources for OB
    OB = OB.with_columns([
        (pl.col("OBPV16X") + pl.col("OBTR16X")).alias("PR"),
        (pl.col("OBOF16X") + pl.col("OBSL16X") + pl.col("OBVA16X") +
         pl.col("OBOT16X") + pl.col("OBOR16X") + pl.col("OBOU16X") +
         pl.col("OBWC16X")).alias("OZ"),
    ]).filter(pl.col("OBXP16X") >= 0)

    # Aggregate payment sources for OP
    OP = OP.with_columns([
        (pl.col("OPFPV16X") + pl.col("OPFTR16X")).alias("PR_fac"),
        (pl.col("OPDPV16X") + pl.col("OPDTR16X")).alias("PR_sbd"),
        (pl.col("OPFOF16X") + pl.col("OPFSL16X") + pl.col("OPFOR16X") +
         pl.col("OPFOU16X") + pl.col("OPFVA16X") + pl.col("OPFOT16X") +
         pl.col("OPFWC16X")).alias("OZ_fac"),
        (pl.col("OPDOF16X") + pl.col("OPDSL16X") + pl.col("OPDOR16X") +
         pl.col("OPDOU16X") + pl.col("OPDVA16X") + pl.col("OPDOT16X") +
         pl.col("OPDWC16X")).alias("OZ_sbd"),
    ]).filter(pl.col("OPXP16X") >= 0)

    # Combine facility and SBD for OP
    OP = OP.with_columns([
        (pl.col("OPFSF16X") + pl.col("OPDSF16X")).alias("SF"),
        (pl.col("OPFMR16X") + pl.col("OPDMR16X")).alias("MR"),
        (pl.col("OPFMD16X") + pl.col("OPDMD16X")).alias("MD"),
        (pl.col("PR_fac") + pl.col("PR_sbd")).alias("PR"),
        (pl.col("OZ_fac") + pl.col("OZ_sbd")).alias("OZ"),
    ])

    # Merge with FYC to retain all PSUs
    OB_merged = OB.with_columns([
        pl.lit(1).alias("count"),
        pl.lit(1).alias("domain"),
    ]).drop(["VARSTR", "VARPSU", "PERWT16F"]).join(FYC, on="DUPERSID", how="full", coalesce=True)

    OP_merged = OP.with_columns([
        pl.lit(1).alias("count"),
        pl.lit(1).alias("domain"),
    ]).drop(["VARSTR", "VARPSU", "PERWT16F"]).join(FYC, on="DUPERSID", how="full", coalesce=True)

    # Define survey designs
    ob_dsgn = MEPSSurveyDesign(
        data=OB_merged, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT16F", nest=True,
    ).subset(pl.col("domain") == 1)

    op_dsgn = MEPSSurveyDesign(
        data=OP_merged, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT16F", nest=True,
    ).subset(pl.col("domain") == 1)

    # Physician visit subsets
    ob_doc_dsgn = ob_dsgn.subset(pl.col("SEEDOC") == 1)
    op_doc_dsgn = op_dsgn.subset(pl.col("SEEDOC") == 1)

    # Total number of events
    print("=== Total number of events ===")
    for label, design in [("OB visits", ob_dsgn), ("OB physician", ob_doc_dsgn),
                          ("OP visits", op_dsgn), ("OP physician", op_doc_dsgn)]:
        est = survey_total(design, ["count"])
        print(f"  {label}: {est[0].estimate:,.0f} (SE: {est[0].se:,.0f})")

    # Mean expenditure per event
    print("\n=== Mean expenditure per event ===")
    ob_sop = ["OBSF16X", "PR", "OBMR16X", "OBMD16X", "OZ"]
    op_sop = ["SF", "PR", "MR", "MD", "OZ"]

    print("  OB visits:")
    for est in survey_mean(ob_dsgn, ob_sop):
        print(f"    {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")

    print("  OP visits:")
    for est in survey_mean(op_dsgn, op_sop):
        print(f"    {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")

    # Mean events per person (aggregate to person level)
    print("\n=== Mean events per person (OB) ===")
    pers_OB = OB_merged.group_by(["DUPERSID", "VARSTR", "VARPSU"]).agg([
        pl.col("PERWT16F").mean(),
        pl.col("count").sum().alias("n_events"),
        (pl.col("count") * (pl.col("SEEDOC") == 1).cast(pl.Int32)).sum().alias("n_phys_events"),
    ])

    pers_ob_dsgn = MEPSSurveyDesign(
        data=pers_OB, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT16F", nest=True,
    )
    for est in survey_mean(pers_ob_dsgn, ["n_events", "n_phys_events"]):
        print(f"  {est.variable}: {est.estimate:,.4f} (SE: {est.se:,.4f})")


if __name__ == "__main__":
    main()
