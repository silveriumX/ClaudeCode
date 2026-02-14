Refactor the specified code while preserving its behavior.

Target: $ARGUMENTS (file path or function name). If not specified, look at recent git changes.

Steps:
1. Read and understand the target code thoroughly
2. Identify refactoring opportunities:
   - Reduce duplication (DRY)
   - Simplify complex conditionals
   - Extract long functions into smaller, focused ones
   - Improve naming for clarity
   - Remove dead code and unused imports
   - Apply appropriate design patterns where they simplify the code
   - Improve type safety if applicable
3. Plan the refactoring — list what will change and why
4. Apply the changes
5. Verify behavior is preserved:
   - Run existing tests if available
   - Check that all usages/callers still work
6. Summarize what was changed and why

Rules:
- Do NOT change external behavior or APIs
- Do NOT add new features
- Do NOT over-engineer — keep it simple
- Keep changes minimal and focused
- If tests exist, they must still pass after refactoring
