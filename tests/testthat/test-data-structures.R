# =============================================================================
# Test Suite: Data Structure Tests
# Description: Tests expected column names in reference files, data types,
#              data consistency across related files, and crosswalk key matching
# =============================================================================

library(testthat)

# Helper: get repo root
get_repo_root <- function() {
  candidates <- c(
    Sys.getenv("MEPS_REPO_ROOT"),
    file.path(getwd(), "..", ".."),
    file.path(getwd())
  )
  for (path in candidates) {
    if (nchar(path) > 0 && file.exists(file.path(path, "Quick_Reference_Guides"))) {
      return(normalizePath(path))
    }
  }
  stop("Could not find repo root. Set MEPS_REPO_ROOT environment variable.")
}

repo_root <- get_repo_root()
qrg_dir <- file.path(repo_root, "Quick_Reference_Guides")

# ---------------------------------------------------------------------------
# Column name structure tests
# ---------------------------------------------------------------------------
context("Data Structures: Column Names and Types")

test_that("meps_file_names.csv has correct number of columns", {
  df <- read.csv(file.path(qrg_dir, "meps_file_names.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  # Based on observed structure: Year, Panels, PIT, FYC, Conditions,
  # PMED Events, Events, Jobs, PRPL, CLNK, RXLK, Multum, PSAQ, MOS, FS
  expect_true(ncol(df) >= 10,
    info = "meps_file_names.csv should have at least 10 columns")
})

test_that("meps_file_names.csv contains key file type columns", {
  df <- read.csv(file.path(qrg_dir, "meps_file_names.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  key_cols <- c("FYC", "Conditions", "Events", "CLNK")
  for (col in key_cols) {
    expect_true(col %in% names(df),
      info = paste("Missing key file type column:", col))
  }
})

test_that("meps_ccsr_conditions.csv columns have correct data types", {
  df <- read.csv(file.path(qrg_dir, "meps_ccsr_conditions.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  # CCSR Code should be character
  expect_true(is.character(df[["CCSR Code"]]),
    info = "CCSR Code should be character type")
  # CCSR Description should be character
  expect_true(is.character(df[["CCSR Description"]]),
    info = "CCSR Description should be character type")
})

test_that("meps_ccs_conditions.csv CCS Code values are valid codes or ranges", {
  df <- read.csv(file.path(qrg_dir, "meps_ccs_conditions.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  codes <- df[["CCS Code"]]
  # CCS codes can be numeric or ranges like "65-75"
  valid_pattern <- grepl("^\\d+(-\\d+)?$", codes)
  expect_true(all(valid_pattern),
    info = "CCS Code should be numeric or a valid range (e.g., 65-75)")
})

test_that("meps_longitudinal_file_names.csv has correct data types", {
  df <- read.csv(file.path(qrg_dir, "meps_longitudinal_file_names.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  # Filter out footnote/note rows (non-numeric Panel values)
  data_rows <- df[!is.na(suppressWarnings(as.numeric(df$Panel))), ]
  expect_true(nrow(data_rows) > 0, info = "Should have data rows with numeric Panel")
  expect_true(all(!is.na(suppressWarnings(as.numeric(data_rows$Panel)))),
    info = "Panel data rows should be coercible to numeric")
  expect_true(is.character(df$Years),
    info = "Years should be character (e.g., '1996-1997')")
  expect_true(is.character(df$File_Name),
    info = "File_Name should be character")
})

# ---------------------------------------------------------------------------
# Data consistency across related files
# ---------------------------------------------------------------------------
context("Data Structures: Cross-file Consistency")

test_that("CCSR and CCS files have matching column structure patterns", {
  ccsr <- read.csv(file.path(qrg_dir, "meps_ccsr_conditions.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  ccs <- read.csv(file.path(qrg_dir, "meps_ccs_conditions.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  # Both should have collapsed condition category and body system
  expect_true("MEPS collapsed condition category" %in% names(ccsr))
  expect_true("MEPS collapsed condition category" %in% names(ccs))
  expect_true("Category Body System" %in% names(ccsr))
  expect_true("Category Body System" %in% names(ccs))
})

test_that("CCSR and CCS collapsed condition categories have overlapping values", {
  ccsr <- read.csv(file.path(qrg_dir, "meps_ccsr_conditions.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  ccs <- read.csv(file.path(qrg_dir, "meps_ccs_conditions.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  ccsr_cats <- unique(ccsr[["MEPS collapsed condition category"]])
  ccs_cats <- unique(ccs[["MEPS collapsed condition category"]])
  overlap <- intersect(ccsr_cats, ccs_cats)
  # There should be significant overlap in collapsed categories
  expect_true(length(overlap) >= 10,
    info = "CCSR and CCS should share at least 10 collapsed condition categories")
})

test_that("CCSR Category Body System values follow naming convention", {
  ccsr <- read.csv(file.path(qrg_dir, "meps_ccsr_conditions.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  body_systems <- unique(ccsr[["Category Body System"]])
  # Body systems should contain a colon separator (e.g., "BLD: Diseases of...")
  has_format <- grepl(":", body_systems)
  expect_true(all(has_format),
    info = "Category Body System should follow 'CODE: Description' format")
})

test_that("CCS Category Body System values follow naming convention", {
  ccs <- read.csv(file.path(qrg_dir, "meps_ccs_conditions.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  body_systems <- unique(ccs[["Category Body System"]])
  has_format <- grepl(":", body_systems)
  expect_true(all(has_format),
    info = "Category Body System should follow 'CODE: Description' format")
})

test_that("CCSR body system prefixes match CCSR code prefixes", {
  ccsr <- read.csv(file.path(qrg_dir, "meps_ccsr_conditions.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  # Extract 3-letter prefix from CCSR Code
  code_prefixes <- unique(substr(ccsr[["CCSR Code"]], 1, 3))
  # Extract body system prefixes (before the colon)
  body_prefixes <- unique(gsub(":.*", "", ccsr[["Category Body System"]]))
  # Most code prefixes should appear in body system prefixes
  # (some may differ due to cross-body-system categories)
  overlap <- intersect(code_prefixes, body_prefixes)
  expect_true(length(overlap) >= 5,
    info = "CCSR code prefixes should largely match body system prefixes")
})

# ---------------------------------------------------------------------------
# File names crosswalk consistency
# ---------------------------------------------------------------------------
context("Data Structures: File Names Crosswalk")

test_that("file_names.csv and longitudinal files have mostly distinct file names", {
  fn <- read.csv(file.path(qrg_dir, "meps_file_names.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  long_fn <- read.csv(file.path(qrg_dir, "meps_longitudinal_file_names.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  # Filter to valid data rows
  fyc_names <- fn$FYC[!is.na(fn$Year) & !is.na(fn$FYC) & trimws(fn$FYC) != "" & fn$FYC != "-"]
  long_data <- long_fn[!is.na(suppressWarnings(as.numeric(long_fn$Panel))), ]
  long_names <- long_data$File_Name[!is.na(long_data$File_Name) & trimws(long_data$File_Name) != ""]
  overlap <- intersect(fyc_names, long_names)
  # Allow minimal overlap (some files may serve dual purposes)
  expect_true(length(overlap) <= 2,
    info = "FYC and longitudinal file names should have minimal overlap")
})

test_that("meps_file_names.csv CLNK column has values for recent years", {
  df <- read.csv(file.path(qrg_dir, "meps_file_names.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  # CLNK files should be available for years 2016+
  recent <- df[df$Year >= 2016, ]
  if (nrow(recent) > 0 && "CLNK" %in% names(recent)) {
    clnk_vals <- recent$CLNK
    has_values <- !is.na(clnk_vals) & trimws(clnk_vals) != "" & clnk_vals != "-"
    expect_true(any(has_values),
      info = "CLNK should have values for recent years (2016+)")
  }
})

test_that("meps_file_names.csv Conditions column has values for data years", {
  df <- read.csv(file.path(qrg_dir, "meps_file_names.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  # Filter to actual data rows (non-NA Year)
  data_rows <- df[!is.na(df$Year), ]
  cond_vals <- data_rows$Conditions
  has_values <- !is.na(cond_vals) & trimws(cond_vals) != "" & cond_vals != "-"
  expect_true(sum(has_values) >= nrow(data_rows) * 0.8,
    info = "At least 80% of data years should have Conditions file names")
})

# ---------------------------------------------------------------------------
# Data range and value validation
# ---------------------------------------------------------------------------
context("Data Structures: Value Range Validation")

test_that("meps_file_names.csv years are in reasonable range", {
  df <- read.csv(file.path(qrg_dir, "meps_file_names.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  # Filter to valid data rows (non-NA Year)
  valid_years <- df$Year[!is.na(df$Year)]
  expect_true(length(valid_years) > 0, info = "Should have valid years")
  expect_true(min(valid_years) >= 1996, info = "Earliest year should be 1996")
  expect_true(max(valid_years) <= as.integer(format(Sys.Date(), "%Y")),
    info = "Latest year should not exceed current year")
})

test_that("meps_longitudinal_file_names.csv panels are sequential", {
  df <- read.csv(file.path(qrg_dir, "meps_longitudinal_file_names.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  # Filter to valid data rows (numeric Panel values)
  valid_panels <- suppressWarnings(as.numeric(df$Panel))
  valid_panels <- sort(unique(valid_panels[!is.na(valid_panels)]))
  expect_equal(min(valid_panels), 1, info = "Panels should start at 1")
  expect_true(max(valid_panels) >= 10, info = "Should have at least 10 panels of data")
})

test_that("meps_ccs_conditions.csv CCS codes are in valid range", {
  df <- read.csv(file.path(qrg_dir, "meps_ccs_conditions.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  codes <- df[["CCS Code"]]
  # Handle range codes (e.g., "65-75") by extracting the first number
  first_nums <- suppressWarnings(as.numeric(gsub("-.*", "", codes)))
  valid_nums <- first_nums[!is.na(first_nums)]
  expect_true(length(valid_nums) > 0, info = "Should have valid CCS codes")
  expect_true(all(valid_nums >= 1), info = "CCS codes should be >= 1")
  expect_true(all(valid_nums <= 700), info = "CCS codes should be <= 700")
})

test_that("CCSR codes cover major body systems", {
  df <- read.csv(file.path(qrg_dir, "meps_ccsr_conditions.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  code_prefixes <- unique(substr(df[["CCSR Code"]], 1, 3))
  # Major body systems that should be present
  expected_prefixes <- c("CIR", "RSP", "DIG", "MUS", "NVS", "END", "GEN", "SKN", "MBD")
  for (prefix in expected_prefixes) {
    expect_true(prefix %in% code_prefixes,
      info = paste("Missing major body system prefix:", prefix))
  }
})
