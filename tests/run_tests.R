# =============================================================================
# MEPS Test Runner
# Description: Runs all testthat tests and outputs results summary
# Usage: Rscript tests/run_tests.R
# =============================================================================

library(testthat)

# Set repo root environment variable for tests
Sys.setenv(MEPS_REPO_ROOT = normalizePath(file.path(getwd())))

cat("=============================================================\n")
cat("MEPS Repository Test Suite\n")
cat("=============================================================\n")
cat("Repo root:", Sys.getenv("MEPS_REPO_ROOT"), "\n")
cat("R version:", R.version.string, "\n")
cat("testthat version:", as.character(packageVersion("testthat")), "\n")
cat("Test time:", format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z"), "\n")
cat("=============================================================\n\n")

# Run all tests
test_results <- test_dir(
  "tests/testthat",
  reporter = "summary",
  stop_on_failure = FALSE
)

# Print summary
cat("\n=============================================================\n")
cat("Test Summary\n")
cat("=============================================================\n")

# Extract results
results_df <- as.data.frame(test_results)
n_total <- nrow(results_df)
n_passed <- sum(results_df$passed > 0 & results_df$failed == 0 &
                results_df$error == 0 & results_df$skipped == 0)
n_failed <- sum(results_df$failed > 0 | results_df$error > 0)
n_skipped <- sum(results_df$skipped > 0)
n_warning <- sum(results_df$warning > 0)

cat("Total test contexts:", n_total, "\n")
cat("Passed:", n_passed, "\n")
cat("Failed:", n_failed, "\n")
cat("Skipped:", n_skipped, "\n")
cat("Warnings:", n_warning, "\n")
cat("=============================================================\n")

# Save results for report generation
results_file <- file.path("tests", "test_results.csv")
# Convert list columns to character for CSV compatibility
for (col in names(results_df)) {
  if (is.list(results_df[[col]])) {
    results_df[[col]] <- sapply(results_df[[col]], function(x) paste(x, collapse=";"))
  }
}
write.csv(results_df, results_file, row.names = FALSE)
cat("Results saved to:", results_file, "\n")

# Exit with appropriate code
if (n_failed > 0) {
  cat("\nSome tests FAILED!\n")
  quit(status = 1)
} else {
  cat("\nAll tests PASSED!\n")
  quit(status = 0)
}
