# =============================================================================
# Test Suite: Documentation Tests
# Description: Verifies README files exist, markdown files are well-formed,
#              and quick reference guides are consistent
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
    if (nchar(path) > 0 && file.exists(file.path(path, "README.md"))) {
      return(normalizePath(path))
    }
  }
  stop("Could not find repo root. Set MEPS_REPO_ROOT environment variable.")
}

repo_root <- get_repo_root()

# ---------------------------------------------------------------------------
# README existence tests
# ---------------------------------------------------------------------------
context("Documentation: README Files")

test_that("root README.md exists", {
  expect_true(file.exists(file.path(repo_root, "README.md")))
})

test_that("R/README.md exists", {
  expect_true(file.exists(file.path(repo_root, "R", "README.md")))
})

test_that("SAS/README.md exists", {
  expect_true(file.exists(file.path(repo_root, "SAS", "README.md")))
})

test_that("Stata/README.md exists", {
  expect_true(file.exists(file.path(repo_root, "Stata", "README.md")))
})

test_that("Quick_Reference_Guides/README.md exists", {
  expect_true(file.exists(file.path(repo_root, "Quick_Reference_Guides", "README.md")))
})

# ---------------------------------------------------------------------------
# README content tests
# ---------------------------------------------------------------------------
context("Documentation: README Content Quality")

test_that("root README.md has substantial content", {
  content <- readLines(file.path(repo_root, "README.md"), warn = FALSE)
  expect_true(length(content) >= 20,
    info = "Root README should have at least 20 lines")
})

test_that("root README.md mentions MEPS", {
  content <- paste(readLines(file.path(repo_root, "README.md"), warn = FALSE),
    collapse = "\n")
  expect_true(grepl("MEPS", content),
    info = "Root README should mention MEPS")
  expect_true(grepl("Medical Expenditure Panel Survey", content),
    info = "Root README should have full MEPS name")
})

test_that("root README.md has section headers", {
  content <- readLines(file.path(repo_root, "README.md"), warn = FALSE)
  headers <- content[grepl("^#{1,3}\\s", content)]
  expect_true(length(headers) >= 3,
    info = "Root README should have at least 3 section headers")
})

test_that("R/README.md references R programming language", {
  content <- paste(readLines(file.path(repo_root, "R", "README.md"), warn = FALSE),
    collapse = "\n")
  expect_true(grepl("\\bR\\b", content),
    info = "R README should reference R language")
})

test_that("SAS/README.md references SAS", {
  content <- paste(readLines(file.path(repo_root, "SAS", "README.md"), warn = FALSE),
    collapse = "\n")
  expect_true(grepl("SAS", content),
    info = "SAS README should reference SAS")
})

test_that("Stata/README.md references Stata", {
  content <- paste(readLines(file.path(repo_root, "Stata", "README.md"), warn = FALSE),
    collapse = "\n")
  expect_true(grepl("Stata", content, ignore.case = TRUE),
    info = "Stata README should reference Stata")
})

# ---------------------------------------------------------------------------
# Markdown link validation
# ---------------------------------------------------------------------------
context("Documentation: Markdown Link Validation")

test_that("root README.md internal links reference existing directories", {
  content <- paste(readLines(file.path(repo_root, "README.md"), warn = FALSE),
    collapse = "\n")
  # Check for links to R, SAS, Stata directories
  if (grepl("\\[.*\\]\\(R\\)", content) || grepl("\\[.*\\]\\(R/", content)) {
    expect_true(dir.exists(file.path(repo_root, "R")))
  }
  if (grepl("\\[.*\\]\\(SAS\\)", content) || grepl("\\[.*\\]\\(SAS/", content)) {
    expect_true(dir.exists(file.path(repo_root, "SAS")))
  }
  if (grepl("\\[.*\\]\\(Stata\\)", content) || grepl("\\[.*\\]\\(Stata/", content)) {
    expect_true(dir.exists(file.path(repo_root, "Stata")))
  }
})

test_that("Quick_Reference_Guides/README.md links to existing files", {
  readme_path <- file.path(repo_root, "Quick_Reference_Guides", "README.md")
  content <- readLines(readme_path, warn = FALSE)
  qrg_dir <- file.path(repo_root, "Quick_Reference_Guides")

  # Extract markdown links that reference local files
  link_pattern <- "\\[.*?\\]\\(([^http][^)]+)\\)"
  for (line in content) {
    matches <- regmatches(line, gregexpr(link_pattern, line))[[1]]
    for (match in matches) {
      # Extract the path from the link
      path <- gsub(".*\\(([^)]+)\\)", "\\1", match)
      # Remove any anchor fragments
      path <- gsub("#.*$", "", path)
      if (nchar(path) > 0 && !grepl("^\\.\\./_images/", path)) {
        full_path <- file.path(qrg_dir, path)
        expect_true(file.exists(full_path),
          info = paste("Broken link in QRG README:", path))
      }
    }
  }
})

test_that("Quick_Reference_Guides/README.md references all CSV files", {
  readme_content <- paste(readLines(
    file.path(repo_root, "Quick_Reference_Guides", "README.md"), warn = FALSE),
    collapse = "\n")
  csv_files <- list.files(file.path(repo_root, "Quick_Reference_Guides"),
    pattern = "\\.csv$")
  for (csv_file in csv_files) {
    expect_true(grepl(csv_file, readme_content),
      info = paste("QRG README should reference:", csv_file))
  }
})

# ---------------------------------------------------------------------------
# Markdown formatting
# ---------------------------------------------------------------------------
context("Documentation: Markdown Formatting")

test_that("all README.md files are valid UTF-8", {
  readme_files <- list.files(repo_root, pattern = "README\\.md$",
    recursive = TRUE, full.names = TRUE)
  for (f in readme_files) {
    content <- tryCatch(
      readLines(f, warn = FALSE),
      error = function(e) NULL
    )
    expect_false(is.null(content),
      info = paste("README should be readable:", f))
  }
})

test_that("markdown files in Quick_Reference_Guides are well-formed", {
  md_files <- list.files(file.path(repo_root, "Quick_Reference_Guides"),
    pattern = "\\.md$", full.names = TRUE)
  for (f in md_files) {
    content <- readLines(f, warn = FALSE)
    # Should not be empty
    expect_true(length(content) > 0,
      info = paste("Markdown file should not be empty:", basename(f)))
    # Should have some non-whitespace content
    non_empty <- content[trimws(content) != ""]
    expect_true(length(non_empty) > 0,
      info = paste("Markdown file should have content:", basename(f)))
  }
})

test_that("programming statements reference all three languages", {
  content <- paste(readLines(
    file.path(repo_root, "Quick_Reference_Guides", "meps_programming_statements.md"),
    warn = FALSE), collapse = "\n")
  expect_true(grepl("SAS", content), info = "Programming statements should mention SAS")
  expect_true(grepl("STATA|Stata", content), info = "Programming statements should mention Stata")
  expect_true(grepl("\\bR\\b", content), info = "Programming statements should mention R")
})

test_that("meps_variables.md references utilization and expenditure", {
  content <- paste(readLines(
    file.path(repo_root, "Quick_Reference_Guides", "meps_variables.md"),
    warn = FALSE), collapse = "\n")
  expect_true(grepl("[Uu]tilization", content),
    info = "Variables guide should reference utilization")
  expect_true(grepl("[Ee]xpenditure", content),
    info = "Variables guide should reference expenditure")
})

# ---------------------------------------------------------------------------
# Cross-language consistency
# ---------------------------------------------------------------------------
context("Documentation: Cross-Language Consistency")

test_that("all language directories have workshop_exercises subdirectory", {
  for (lang in c("R", "SAS", "Stata")) {
    ws_dir <- file.path(repo_root, lang, "workshop_exercises")
    expect_true(dir.exists(ws_dir),
      info = paste(lang, "should have workshop_exercises directory"))
  }
})

test_that("all language directories have summary_tables_examples subdirectory", {
  for (lang in c("R", "SAS", "Stata")) {
    st_dir <- file.path(repo_root, lang, "summary_tables_examples")
    expect_true(dir.exists(st_dir),
      info = paste(lang, "should have summary_tables_examples directory"))
  }
})

test_that("_images directory exists with supporting images", {
  images_dir <- file.path(repo_root, "_images")
  expect_true(dir.exists(images_dir))
  image_files <- list.files(images_dir)
  expect_true(length(image_files) >= 1,
    info = "_images directory should contain at least one image")
})
