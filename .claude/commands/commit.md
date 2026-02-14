Analyze all current git changes (both staged and unstaged).

Steps:
1. Run `git status` and `git diff` to understand all changes
2. Run `git log --oneline -5` to see recent commit style
3. Group related changes logically
4. Stage all relevant files (exclude secrets, .env, credentials)
5. Create a commit with a message in Conventional Commits format:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `refactor:` for refactoring
   - `docs:` for documentation
   - `test:` for tests
   - `chore:` for maintenance tasks
   - `style:` for formatting changes
6. The commit message should be concise (max 72 chars for the subject line)
7. Add a body if the change is complex
8. Use English for commit messages

Do NOT push to remote. Only commit locally.
