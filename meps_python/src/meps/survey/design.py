"""Survey design specification for MEPS complex survey data.

Implements the equivalent of R's svydesign() for MEPS data, storing
cluster (VARPSU), strata (VARSTR), and weight column information.

Critical: The subset() method creates a domain indicator WITHOUT dropping
observations, which is required for correct variance estimation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import polars as pl


@dataclass
class MEPSSurveyDesign:
    """Complex survey design specification for MEPS data.

    Equivalent to R's:
        svydesign(id=~VARPSU, strata=~VARSTR, weights=~PERWTyyF,
                  data=dataset, nest=TRUE)

    Attributes:
        data: The full dataset as a polars DataFrame.
        psu_col: Name of the PSU (cluster) column. Default 'VARPSU'.
        strata_col: Name of the strata column. Default 'VARSTR'.
        weight_col: Name of the weight column (e.g., 'PERWT20F').
        nest: Whether PSUs are nested within strata. Default True for MEPS.
        domain_col: Optional domain indicator column for subpopulation analysis.
    """

    data: pl.DataFrame
    psu_col: str = "VARPSU"
    strata_col: str = "VARSTR"
    weight_col: str = "PERWT20F"
    nest: bool = True
    domain_col: Optional[str] = None
    _lonely_psu_adjust: bool = field(default=True, repr=False)

    def __post_init__(self):
        """Validate that required columns exist in the data."""
        required_cols = [self.psu_col, self.strata_col, self.weight_col]
        missing = [c for c in required_cols if c not in self.data.columns]
        if missing:
            raise ValueError(
                f"Required columns not found in data: {missing}. "
                f"Available columns: {self.data.columns[:20]}..."
            )

    @property
    def n_obs(self) -> int:
        """Total number of observations (rows) in the design."""
        return self.data.height

    @property
    def n_strata(self) -> int:
        """Number of unique strata."""
        return self.data[self.strata_col].n_unique()

    @property
    def n_psu(self) -> int:
        """Number of unique PSUs."""
        return self.data[self.psu_col].n_unique()

    def subset(self, mask: pl.Expr | pl.Series | str) -> MEPSSurveyDesign:
        """Create a subpopulation/domain design WITHOUT dropping observations.

        This is critical for correct variance estimation. Instead of filtering
        rows, we add a domain indicator column. All observations are retained
        in the design so that the full sample structure (strata, PSUs) is
        preserved for variance calculation.

        Equivalent to R's: subset(design, condition)

        WARNING: Do NOT filter the data before creating the survey design.
        This will produce incorrect standard errors. See the "DO NOT RUN"
        warning in R/workshop_exercises/cond_mv_2020.R lines 187-205.

        Args:
            mask: A polars expression, Series, or column name that evaluates
                to a boolean indicating domain membership.

        Returns:
            A new MEPSSurveyDesign with domain_col set.
        """
        domain_name = "_domain_indicator"

        if isinstance(mask, str):
            # Interpret as column name containing boolean values
            new_data = self.data.with_columns(pl.col(mask).cast(pl.Boolean).alias(domain_name))
        elif isinstance(mask, pl.Series):
            if len(mask) != self.data.height:
                raise ValueError(
                    f"Mask length ({len(mask)}) does not match data height ({self.data.height})"
                )
            new_data = self.data.with_columns(mask.alias(domain_name).cast(pl.Boolean))
        elif isinstance(mask, pl.Expr):
            new_data = self.data.with_columns(mask.alias(domain_name).cast(pl.Boolean))
        else:
            raise TypeError(f"mask must be a polars Expr, Series, or column name string, got {type(mask)}")

        # Fill nulls with False for the domain indicator
        new_data = new_data.with_columns(pl.col(domain_name).fill_null(False))

        return MEPSSurveyDesign(
            data=new_data,
            psu_col=self.psu_col,
            strata_col=self.strata_col,
            weight_col=self.weight_col,
            nest=self.nest,
            domain_col=domain_name,
            _lonely_psu_adjust=self._lonely_psu_adjust,
        )

    def update(self, **new_columns: pl.Expr) -> MEPSSurveyDesign:
        """Add or update columns in the design's data.

        Equivalent to R's: update(design, new_col = expr)

        Args:
            **new_columns: Column name to polars expression mappings.

        Returns:
            A new MEPSSurveyDesign with updated data.
        """
        exprs = [expr.alias(name) for name, expr in new_columns.items()]
        new_data = self.data.with_columns(exprs)
        return MEPSSurveyDesign(
            data=new_data,
            psu_col=self.psu_col,
            strata_col=self.strata_col,
            weight_col=self.weight_col,
            nest=self.nest,
            domain_col=self.domain_col,
            _lonely_psu_adjust=self._lonely_psu_adjust,
        )

    def get_domain_data(self) -> pl.DataFrame:
        """Get the data filtered to the domain (if set).

        For estimation functions that need only the domain rows for point
        estimates, while the full data is used for variance estimation.
        """
        if self.domain_col is not None:
            return self.data.filter(pl.col(self.domain_col))
        return self.data

    def get_weight_array(self) -> pl.Series:
        """Get the weight column, zeroing out non-domain observations if domain is set."""
        weights = self.data[self.weight_col]
        if self.domain_col is not None:
            domain = self.data[self.domain_col]
            weights = pl.when(domain).then(weights).otherwise(0.0).alias(self.weight_col)
            if isinstance(weights, pl.Expr):
                weights = self.data.select(weights).to_series()
        return weights

    def __repr__(self) -> str:
        parts = [
            "MEPSSurveyDesign(",
            f"  n_obs={self.n_obs:,}",
            f"  psu={self.psu_col}, strata={self.strata_col}, weight={self.weight_col}",
            f"  nest={self.nest}",
        ]
        if self.domain_col:
            n_domain = self.data.filter(pl.col(self.domain_col)).height
            parts.append(f"  domain: {n_domain:,} of {self.n_obs:,} observations")
        parts.append(")")
        return "\n".join(parts)
