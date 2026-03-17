"""Use, expenditures, and population, 2016.

Expenditures by event type and source of payment (SOP):
 - Total expenditures
 - Mean expenditure per person
 - Mean out-of-pocket (SLF) payment per person with an out-of-pocket expense

Selected event types:
 - Office-based medical visits (OBV)
 - Office-based physician visits (OBD)
 - Outpatient visits (OPT)
 - Outpatient physician visits (OPV)

Input file: C:/MEPS/h192.ssp (2016 full-year consolidated)

Ported from: R/summary_tables_examples/use_expenditures_2016.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean, survey_total


def main(data_dir: str = "C:/MEPS") -> None:
    # Load FYC file
    FYC = read_meps(year=2016, file_type="FYC", data_dir=data_dir)

    # Aggregate payment sources
    # PTR = Private (PRV) + TRICARE (TRI)
    # OTZ = OFD + STL + OPR + OPU + OSR + WCP + VA
    FYC = FYC.with_columns([
        # Office-based visits
        (pl.col("OBVPRV16") + pl.col("OBVTRI16")).alias("OBVPTR"),
        (pl.col("OBVOFD16") + pl.col("OBVSTL16") + pl.col("OBVOPR16") +
         pl.col("OBVOPU16") + pl.col("OBVOSR16") + pl.col("OBVWCP16") +
         pl.col("OBVVA16")).alias("OBVOTZ"),
        # Office-based physician visits
        (pl.col("OBDPRV16") + pl.col("OBDTRI16")).alias("OBDPTR"),
        (pl.col("OBDOFD16") + pl.col("OBDSTL16") + pl.col("OBDOPR16") +
         pl.col("OBDOPU16") + pl.col("OBDOSR16") + pl.col("OBDWCP16") +
         pl.col("OBDVA16")).alias("OBDOTZ"),
        # Outpatient visits (facility + SBD)
        (pl.col("OPTPRV16") + pl.col("OPTTRI16")).alias("OPTPTR"),
        (pl.col("OPTOFD16") + pl.col("OPTSTL16") + pl.col("OPTOPR16") +
         pl.col("OPTOPU16") + pl.col("OPTOSR16") + pl.col("OPTWCP16") +
         pl.col("OPTVA16")).alias("OPTOTZ"),
        # Outpatient physician visits (facility)
        (pl.col("OPVPRV16") + pl.col("OPVTRI16")).alias("OPVPTR"),
        (pl.col("OPVOFD16") + pl.col("OPVSTL16") + pl.col("OPVOPR16") +
         pl.col("OPVOPU16") + pl.col("OPVOSR16") + pl.col("OPVWCP16") +
         pl.col("OPVVA16")).alias("OPVOTZ"),
        # Outpatient physician visits (SBD)
        (pl.col("OPSPRV16") + pl.col("OPSTRI16")).alias("OPSPTR"),
        (pl.col("OPSOFD16") + pl.col("OPSSTL16") + pl.col("OPSOPR16") +
         pl.col("OPSOPU16") + pl.col("OPSOSR16") + pl.col("OPSWCP16") +
         pl.col("OPSVA16")).alias("OPSOTZ"),
    ])

    # Combine facility and SBD for OP physician visits
    FYC = FYC.with_columns([
        (pl.col("OPVSLF16") + pl.col("OPSSLF16")).alias("OPTSLF_p"),
        (pl.col("OPVMCR16") + pl.col("OPSMCR16")).alias("OPTMCR_p"),
        (pl.col("OPVMCD16") + pl.col("OPSMCD16")).alias("OPTMCD_p"),
        (pl.col("OPVPTR") + pl.col("OPSPTR")).alias("OPTPTR_p"),
        (pl.col("OPVOTZ") + pl.col("OPSOTZ")).alias("OPTOTZ_p"),
    ])

    # Define survey design
    dsgn = MEPSSurveyDesign(
        data=FYC, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT16F", nest=True,
    )

    # Total expenditures by event type and SOP
    ob_vars = ["OBVSLF16", "OBVPTR", "OBVMCR16", "OBVMCD16", "OBVOTZ"]
    obd_vars = ["OBDSLF16", "OBDPTR", "OBDMCR16", "OBDMCD16", "OBDOTZ"]
    opt_vars = ["OPTSLF16", "OPTPTR", "OPTMCR16", "OPTMCD16", "OPTOTZ"]
    opv_vars = ["OPTSLF_p", "OPTPTR_p", "OPTMCR_p", "OPTMCD_p", "OPTOTZ_p"]

    all_vars = ob_vars + obd_vars + opt_vars + opv_vars

    print("=== Total expenditures ===")
    totals = survey_total(dsgn, all_vars)
    for est in totals:
        print(f"  {est.variable}: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    print("\n=== Mean expenditure per person ===")
    means = survey_mean(dsgn, all_vars)
    for est in means:
        print(f"  {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")

    # Mean OOP expense per person with OOP expense
    print("\n=== Mean OOP per person with expense ===")
    for var_name, label in [
        ("OBVSLF16", "OB visits"), ("OBDSLF16", "OB phys. visits"),
        ("OPTSLF16", "OP visits"), ("OPTSLF_p", "OP phys. visits"),
    ]:
        sub_dsgn = dsgn.subset(pl.col(var_name) > 0)
        est = survey_mean(sub_dsgn, [var_name])
        print(f"  {label}: {est[0].estimate:,.2f} (SE: {est[0].se:,.2f})")


if __name__ == "__main__":
    main()
