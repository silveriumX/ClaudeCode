Find and run the project's tests, then analyze results.

Steps:
1. Detect the project type and test framework:
   - Look for `package.json` (Jest, Vitest, Mocha), `pytest.ini`/`pyproject.toml` (pytest), `Cargo.toml` (cargo test), `go.mod` (go test), etc.
2. Run the appropriate test command
3. Analyze the results:
   - If all tests pass: report summary (total, passed, time)
   - If tests fail:
     a. Show which tests failed and why
     b. Read the relevant source code and test code
     c. Identify the root cause of each failure
     d. Propose a concrete fix
     e. Ask if the user wants the fix applied

If the argument `$ARGUMENTS` is provided, use it to filter which tests to run (e.g., a specific file or test name pattern).
