Perform a thorough code review of the current changes.

Steps:
1. Run `git diff` to see all unstaged changes, and `git diff --cached` for staged changes
2. If no changes found, review the last commit with `git diff HEAD~1`
3. Analyze the code for:

**Bugs & Logic Errors:**
- Off-by-one errors, null/undefined access, race conditions
- Incorrect control flow, missing edge cases
- Wrong variable usage, copy-paste errors

**Security Issues:**
- SQL injection, XSS, command injection
- Hardcoded secrets or credentials
- Unsafe deserialization, path traversal
- Missing input validation at system boundaries

**Performance:**
- N+1 queries, unnecessary loops
- Missing indexes, large memory allocations
- Blocking operations in async contexts

**Code Quality:**
- Dead code, unused variables/imports
- Overly complex logic that could be simplified
- Missing error handling for external calls
- Inconsistent naming or style

4. Present findings grouped by severity: Critical > Warning > Info
5. For each issue, show the exact file and line, explain the problem, and suggest a fix
6. If the code looks good, say so — don't invent problems
