"""L2: Link MEPS with NHIS data.

Link MEPS household component data with NHIS (National Health Interview Survey)
data using fixed-width ASCII parsing for the NHIS person-level file.

Input files:
 - C:/MEPS/h60.ssp (2001 FYC)
 - Fixed-width NHIS person-level file

Ported from: SAS/older_exercises_1996_to_2006/Linking_examples/L2/L2.sas
"""


from meps.io.readers import read_fixed_width, read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean


def main(data_dir: str = "C:/MEPS") -> None:
    fyc01 = read_meps(year=2001, file_type="FYC", data_dir=data_dir)

    # Define NHIS column positions (from L2.sas lines 82-88)
    nhis_col_spec = [
        ("HHC_SEQ", 1, 5),
        ("FMX", 6, 7),
        ("FPX", 8, 9),
        ("DUPERSID", 10, 19),
        ("REGION", 20, 20),
        ("STRAT_P", 21, 23),
        ("PSU_P", 24, 24),
    ]

    # Attempt to read NHIS file (may not exist in all environments)
    nhis_path = f"{data_dir}/nhis_personsx.dat"
    try:
        nhis = read_fixed_width(nhis_path, nhis_col_spec)
    except FileNotFoundError:
        print(f"NHIS file not found at {nhis_path}. Skipping NHIS linkage.")
        print("This exercise requires the NHIS person-level ASCII file.")
        return

    # Merge MEPS FYC with NHIS
    fyc_sub = fyc01.select([
        "DUPERSID", "VARSTR", "VARPSU", "PERWT01F",
        "TOTEXP01", "RTHLTH53",
    ])

    merged = fyc_sub.join(nhis, on="DUPERSID", how="inner")
    print(f"Matched records: {merged.height}")

    dsgn = MEPSSurveyDesign(
        data=merged, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT01F", nest=True,
    )

    print("\n=== Linked MEPS-NHIS Estimates ===")
    for est in survey_mean(dsgn, ["TOTEXP01"]):
        print(f"  Mean expenditure: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
