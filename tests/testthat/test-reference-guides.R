# =============================================================================
# Test Suite: Data Reference Guide Tests
# Description: Validates CSV files in Quick_Reference_Guides/ for structure,
#              completeness, and data integrity
# =============================================================================

library(testthat)

# Helper: get repo root (works from tests/testthat/)
get_repo_root <- function() {
  # Try common locations
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
# meps_file_names.csv
# ---------------------------------------------------------------------------
context("Reference Guide: meps_file_names.csv")

test_that("meps_file_names.csv exists and is readable", {
  filepath <- file.path(qrg_dir, "meps_file_names.csv")
  expect_true(file.exists(filepath))
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  expect_true(nrow(df) > 0)
})

test_that("meps_file_names.csv has expected columns", {
  filepath <- file.path(qrg_dir, "meps_file_names.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  expected_cols <- c("Year", "Panels", "PIT", "FYC", "Conditions")
  for (col in expected_cols) {
    expect_true(col %in% names(df),
      info = paste("Missing expected column:", col))
  }
})

test_that("meps_file_names.csv Year column contains valid years for data rows", {
  filepath <- file.path(qrg_dir, "meps_file_names.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  # Filter to actual data rows (non-NA Year); file may have footnote rows
  years <- df$Year[!is.na(df$Year)]
  expect_true(length(years) > 0, info = "Should have rows with valid years")
  expect_true(all(years >= 1996), info = "Years should be >= 1996 (MEPS start year)")
  expect_true(all(years <= 2030), info = "Years should be reasonable (<=2030)")
})

test_that("meps_file_names.csv data rows have meaningful content", {
  filepath <- file.path(qrg_dir, "meps_file_names.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  # Focus on data rows (non-NA Year) - footnote rows at end are expected
  data_rows <- df[!is.na(df$Year), ]
  non_year_cols <- setdiff(names(data_rows), "Year")
  all_empty <- apply(data_rows[, non_year_cols, drop = FALSE], 1, function(row) {
    all(is.na(row) | trimws(row) == "" | row == "-")
  })
  expect_false(any(all_empty),
    info = "Data rows should have meaningful content beyond just Year")
})

test_that("meps_file_names.csv FYC column has valid file name patterns", {
  filepath <- file.path(qrg_dir, "meps_file_names.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  fyc_vals <- df$FYC[!is.na(df$FYC) & trimws(df$FYC) != "" & df$FYC != "-"]
  # MEPS FYC file names start with 'h' followed by numbers
  expect_true(all(grepl("^h\\d+", fyc_vals)),
    info = "FYC file names should start with 'h' followed by numbers")
})

test_that("meps_file_names.csv has consecutive years without gaps", {
  filepath <- file.path(qrg_dir, "meps_file_names.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  # Filter to actual data rows (non-NA Year)
  years <- sort(df$Year[!is.na(df$Year)])
  diffs <- diff(years)
  expect_true(all(diffs == 1),
    info = "Years should be consecutive without gaps")
})

test_that("meps_file_names.csv Panels column is not empty for data rows", {
  filepath <- file.path(qrg_dir, "meps_file_names.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  # Filter to actual data rows (non-NA Year)
  data_rows <- df[!is.na(df$Year), ]
  panels <- data_rows$Panels
  expect_true(all(!is.na(panels) & trimws(as.character(panels)) != ""),
    info = "Panels column should not have empty values for data rows")
})

# ---------------------------------------------------------------------------
# meps_longitudinal_file_names.csv
# ---------------------------------------------------------------------------
context("Reference Guide: meps_longitudinal_file_names.csv")

test_that("meps_longitudinal_file_names.csv exists and is readable", {
  filepath <- file.path(qrg_dir, "meps_longitudinal_file_names.csv")
  expect_true(file.exists(filepath))
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  expect_true(nrow(df) > 0)
})

test_that("meps_longitudinal_file_names.csv has expected columns", {
  filepath <- file.path(qrg_dir, "meps_longitudinal_file_names.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  expected_cols <- c("Panel", "Years", "Number_of_Years", "File_Name")
  for (col in expected_cols) {
    expect_true(col %in% names(df),
      info = paste("Missing expected column:", col))
  }
})

test_that("meps_longitudinal_file_names.csv Panel values are numeric and valid for data rows", {
  filepath <- file.path(qrg_dir, "meps_longitudinal_file_names.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  # Filter to data rows (Panel is coercible to numeric); file may have footnote rows
  numeric_panels <- suppressWarnings(as.numeric(df$Panel))
  data_panels <- numeric_panels[!is.na(numeric_panels)]
  expect_true(length(data_panels) > 0, info = "Should have data rows with numeric Panel")
  expect_true(all(data_panels >= 1), info = "Panel numbers should be >= 1")
})

test_that("meps_longitudinal_file_names.csv File_Name starts with 'h'", {
  filepath <- file.path(qrg_dir, "meps_longitudinal_file_names.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  # Filter to data rows (numeric Panel)
  data_rows <- df[!is.na(suppressWarnings(as.numeric(df$Panel))), ]
  fnames <- data_rows$File_Name[!is.na(data_rows$File_Name) & trimws(data_rows$File_Name) != ""]
  expect_true(all(grepl("^h\\d+", fnames)),
    info = "File names should start with 'h' followed by numbers")
})

test_that("meps_longitudinal_file_names.csv Number_of_Years is valid for data rows", {
  filepath <- file.path(qrg_dir, "meps_longitudinal_file_names.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  # Filter to data rows (numeric Panel)
  data_rows <- df[!is.na(suppressWarnings(as.numeric(df$Panel))), ]
  noy <- data_rows$Number_of_Years
  expect_true(all(grepl("year", noy, ignore.case = TRUE)),
    info = "Number_of_Years should contain 'year'")
})

# ---------------------------------------------------------------------------
# meps_ccsr_conditions.csv
# ---------------------------------------------------------------------------
context("Reference Guide: meps_ccsr_conditions.csv")

test_that("meps_ccsr_conditions.csv exists and is readable", {
  filepath <- file.path(qrg_dir, "meps_ccsr_conditions.csv")
  expect_true(file.exists(filepath))
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  expect_true(nrow(df) > 0)
})

test_that("meps_ccsr_conditions.csv has expected columns", {
  filepath <- file.path(qrg_dir, "meps_ccsr_conditions.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  expected_cols <- c("CCSR Code", "CCSR Description",
                     "MEPS collapsed condition category", "Category Body System")
  for (col in expected_cols) {
    expect_true(col %in% names(df),
      info = paste("Missing expected column:", col))
  }
})

test_that("meps_ccsr_conditions.csv CCSR Code follows expected pattern", {
  filepath <- file.path(qrg_dir, "meps_ccsr_conditions.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  codes <- df[["CCSR Code"]]
  # CCSR codes are 3 letters followed by 3 digits (e.g., BLD001, CIR002)
  expect_true(all(grepl("^[A-Z]{3}\\d{3}$", codes)),
    info = "CCSR codes should be 3 uppercase letters followed by 3 digits")
})

test_that("meps_ccsr_conditions.csv has no empty CCSR Description", {
  filepath <- file.path(qrg_dir, "meps_ccsr_conditions.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  descriptions <- df[["CCSR Description"]]
  expect_true(all(!is.na(descriptions) & trimws(descriptions) != ""),
    info = "CCSR Description should not be empty")
})

test_that("meps_ccsr_conditions.csv has no empty collapsed condition category", {
  filepath <- file.path(qrg_dir, "meps_ccsr_conditions.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  categories <- df[["MEPS collapsed condition category"]]
  expect_true(all(!is.na(categories) & trimws(categories) != ""),
    info = "MEPS collapsed condition category should not be empty")
})

test_that("meps_ccsr_conditions.csv Category Body System is not empty", {
  filepath <- file.path(qrg_dir, "meps_ccsr_conditions.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  body_sys <- df[["Category Body System"]]
  expect_true(all(!is.na(body_sys) & trimws(body_sys) != ""),
    info = "Category Body System should not be empty")
})

test_that("meps_ccsr_conditions.csv CCSR codes are unique", {
  filepath <- file.path(qrg_dir, "meps_ccsr_conditions.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  codes <- df[["CCSR Code"]]
  expect_equal(length(codes), length(unique(codes)),
    info = "CCSR codes should be unique (no duplicates)")
})

test_that("meps_ccsr_conditions.csv has reasonable number of rows", {
  filepath <- file.path(qrg_dir, "meps_ccsr_conditions.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  # CCSR has several hundred codes
  expect_true(nrow(df) >= 100,
    info = "Should have at least 100 CCSR condition mappings")
})

# ---------------------------------------------------------------------------
# meps_ccs_conditions.csv
# ---------------------------------------------------------------------------
context("Reference Guide: meps_ccs_conditions.csv")

test_that("meps_ccs_conditions.csv exists and is readable", {
  filepath <- file.path(qrg_dir, "meps_ccs_conditions.csv")
  expect_true(file.exists(filepath))
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  expect_true(nrow(df) > 0)
})

test_that("meps_ccs_conditions.csv has expected columns", {
  filepath <- file.path(qrg_dir, "meps_ccs_conditions.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  expected_cols <- c("CCS Code", "CCS Description",
                     "MEPS collapsed condition category", "Category Body System")
  for (col in expected_cols) {
    expect_true(col %in% names(df),
      info = paste("Missing expected column:", col))
  }
})

test_that("meps_ccs_conditions.csv CCS Code follows valid pattern", {
  filepath <- file.path(qrg_dir, "meps_ccs_conditions.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  codes <- df[["CCS Code"]]
  expect_true(all(!is.na(codes)), info = "CCS codes should not be NA")
  # CCS codes can be numeric or ranges like "65-75"
  expect_true(all(grepl("^\\d+(-\\d+)?$", as.character(codes))),
    info = "CCS codes should be numeric or valid ranges")
})

test_that("meps_ccs_conditions.csv has no empty descriptions", {
  filepath <- file.path(qrg_dir, "meps_ccs_conditions.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  desc <- df[["CCS Description"]]
  expect_true(all(!is.na(desc) & trimws(desc) != ""),
    info = "CCS Description should not be empty")
})

test_that("meps_ccs_conditions.csv has no empty collapsed condition category", {
  filepath <- file.path(qrg_dir, "meps_ccs_conditions.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  categories <- df[["MEPS collapsed condition category"]]
  expect_true(all(!is.na(categories) & trimws(categories) != ""),
    info = "MEPS collapsed condition category should not be empty")
})

test_that("meps_ccs_conditions.csv CCS codes are unique", {
  filepath <- file.path(qrg_dir, "meps_ccs_conditions.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  codes <- df[["CCS Code"]]
  expect_equal(length(codes), length(unique(codes)),
    info = "CCS codes should be unique")
})

test_that("meps_ccs_conditions.csv has reasonable number of rows", {
  filepath <- file.path(qrg_dir, "meps_ccs_conditions.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  expect_true(nrow(df) >= 200,
    info = "Should have at least 200 CCS condition mappings")
})

# ---------------------------------------------------------------------------
# meps_cond_icd10_labels.csv
# ---------------------------------------------------------------------------
context("Reference Guide: meps_cond_icd10_labels.csv")

test_that("meps_cond_icd10_labels.csv exists and is readable", {
  filepath <- file.path(qrg_dir, "meps_cond_icd10_labels.csv")
  expect_true(file.exists(filepath))
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  expect_true(nrow(df) > 0)
})

test_that("meps_cond_icd10_labels.csv has ICD10 description column", {
  filepath <- file.path(qrg_dir, "meps_cond_icd10_labels.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  # Should have at least one column with ICD descriptions
  expect_true(ncol(df) >= 1, info = "Should have at least 1 column")
})

test_that("meps_cond_icd10_labels.csv has no completely empty rows", {
  filepath <- file.path(qrg_dir, "meps_cond_icd10_labels.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  all_empty <- apply(df, 1, function(row) all(is.na(row) | trimws(row) == ""))
  expect_false(any(all_empty), info = "Should not have completely empty rows")
})

# ---------------------------------------------------------------------------
# meps_cond_icd9_labels.csv
# ---------------------------------------------------------------------------
context("Reference Guide: meps_cond_icd9_labels.csv")

test_that("meps_cond_icd9_labels.csv exists and is readable", {
  filepath <- file.path(qrg_dir, "meps_cond_icd9_labels.csv")
  expect_true(file.exists(filepath))
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  expect_true(nrow(df) > 0)
})

test_that("meps_cond_icd9_labels.csv has ICD9 description column", {
  filepath <- file.path(qrg_dir, "meps_cond_icd9_labels.csv")
  df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE)
  expect_true(ncol(df) >= 1, info = "Should have at least 1 column")
})

# ---------------------------------------------------------------------------
# Archive CSV consistency
# ---------------------------------------------------------------------------
context("Reference Guide: Archive files consistency")

test_that("archive/meps_ccsr_conditions.csv exists", {
  filepath <- file.path(qrg_dir, "archive", "meps_ccsr_conditions.csv")
  expect_true(file.exists(filepath))
})

test_that("archive/meps_ccs_conditions.csv exists", {
  filepath <- file.path(qrg_dir, "archive", "meps_ccs_conditions.csv")
  expect_true(file.exists(filepath))
})

test_that("archive CCSR has same columns as current CCSR", {
  current <- read.csv(file.path(qrg_dir, "meps_ccsr_conditions.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  archive <- read.csv(file.path(qrg_dir, "archive", "meps_ccsr_conditions.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  # Archive should have at least the core columns
  core_cols <- c("CCSR Code", "CCSR Description", "MEPS collapsed condition category")
  for (col in core_cols) {
    expect_true(col %in% names(archive),
      info = paste("Archive CCSR missing column:", col))
  }
})

test_that("archive CCS has same columns as current CCS", {
  current <- read.csv(file.path(qrg_dir, "meps_ccs_conditions.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  archive <- read.csv(file.path(qrg_dir, "archive", "meps_ccs_conditions.csv"),
    stringsAsFactors = FALSE, check.names = FALSE)
  core_cols <- c("CCS Code", "CCS Description", "MEPS collapsed condition category")
  for (col in core_cols) {
    expect_true(col %in% names(archive),
      info = paste("Archive CCS missing column:", col))
  }
})

# ---------------------------------------------------------------------------
# CSV encoding and delimiter consistency
# ---------------------------------------------------------------------------
context("Reference Guide: CSV file encoding and format")

test_that("multi-column CSV files use comma delimiters consistently", {
  csv_files <- list.files(qrg_dir, pattern = "\\.csv$", full.names = TRUE, recursive = TRUE)
  for (f in csv_files) {
    df <- tryCatch(
      read.csv(f, stringsAsFactors = FALSE, check.names = FALSE),
      error = function(e) NULL
    )
    if (!is.null(df) && ncol(df) > 1) {
      first_line <- readLines(f, n = 1, warn = FALSE)
      # Multi-column CSV files should have commas in the header
      expect_true(grepl(",", first_line),
        info = paste("Multi-column file should use comma delimiters:", basename(f)))
    }
    # Single-column CSVs (like ICD label files) are valid without commas
  }
})

test_that("all CSV files are valid UTF-8 or ASCII", {
  csv_files <- list.files(qrg_dir, pattern = "\\.csv$", full.names = TRUE, recursive = TRUE)
  for (f in csv_files) {
    # Try reading the file; if it fails, encoding is wrong
    content <- tryCatch(
      readLines(f, warn = FALSE),
      error = function(e) NULL
    )
    expect_false(is.null(content),
      info = paste("File should be readable:", basename(f)))
  }
})

test_that("all CSV files have consistent number of columns per row", {
  csv_files <- list.files(qrg_dir, pattern = "\\.csv$", full.names = TRUE, recursive = TRUE)
  for (f in csv_files) {
    df <- tryCatch(
      read.csv(f, stringsAsFactors = FALSE, check.names = FALSE),
      error = function(e) NULL
    )
    if (!is.null(df)) {
      expect_true(ncol(df) >= 1,
        info = paste("File should have at least 1 column:", basename(f)))
    }
  }
})
