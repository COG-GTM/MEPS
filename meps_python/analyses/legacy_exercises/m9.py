"""M9: Parent-child linkage demonstration, 2001.

Links children to their parents using MEPS family structure variables.

Input file: C:/MEPS/h60.ssp (2001 Full-year consolidated)

Ported from: SAS/older_exercises_1996_to_2006/Misc_examples/M9/M9.sas
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean


def main(data_dir: str = "C:/MEPS") -> None:
    fyc01 = read_meps(year=2001, file_type="FYC", data_dir=data_dir)

    # Children under 18
    children = fyc01.filter(pl.col("AGELAST") < 18)

    # Parent identifier columns (MOM/DAD DUID+PID)
    mom_cols = [c for c in fyc01.columns if "MOM" in c and "PID" in c]
    dad_cols = [c for c in fyc01.columns if "DAD" in c and "PID" in c]

    print(f"Children under 18: {children.height}")
    print(f"Mom ID columns: {mom_cols}")
    print(f"Dad ID columns: {dad_cols}")

    # Create parent-child links
    if mom_cols:
        mom_col = mom_cols[0]
        has_mom = children.filter(pl.col(mom_col).is_not_null() & (pl.col(mom_col) != ""))
        print(f"Children with mother identified: {has_mom.height}")

    if dad_cols:
        dad_col = dad_cols[0]
        has_dad = children.filter(pl.col(dad_col).is_not_null() & (pl.col(dad_col) != ""))
        print(f"Children with father identified: {has_dad.height}")

    # Survey estimates for children
    dsgn = MEPSSurveyDesign(
        data=fyc01, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT01F", nest=True,
    )
    child_dsgn = dsgn.subset(pl.col("AGELAST") < 18)

    print("\n=== Children's Healthcare Expenditures ===")
    for est in survey_mean(child_dsgn, ["TOTEXP01"]):
        print(f"  Mean: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
