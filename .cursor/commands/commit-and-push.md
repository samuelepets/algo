# commit-and-push

Create one or more well-scoped commits from the current changes and push them,
optimizing for **traceability**: any future reader should understand *what*
changed and *why* from the git history alone, without re-reading the chat.

All commit messages MUST be written in **English** (see `AGENTS.md` → Author
preferences).

## Steps

1. **Inspect state.** Run in parallel:
   - `git status` (untracked + modified files)
   - `git diff` and `git diff --staged` (actual content changes)
   - `git log --oneline -10` (match the repo's existing message style)
   - `git log -1 --format='%an %ae'` (confirm authorship for amend safety)

2. **Decide scope.** Group related changes into logical, atomic commits. If the
   working tree mixes unrelated concerns, make multiple commits rather than one
   catch-all. Never bundle a refactor with a behavior change silently.

3. **Exclude what should not be committed:**
   - The `data/` corpus is version-controlled; committing changes to it is fine,
     but never commit *generated* artifacts (backtest outputs, caches) — those
     belong in `.gitignore`.
   - Never commit secrets (`.env`, credentials, tokens, keys). Warn the user if
     they explicitly ask to commit such files.
   - Be deliberate about editor/local files (e.g. `.vscode/`); only include them
     if the user intends to share them.
   - Prefer `git add <explicit paths>` over `git add -A` / `git add .`.

4. **Write the message.** Use this structure, derived from the conversation
   context and the diff:
   - **Subject** (≤ ~72 chars, imperative mood): start with `add`, `update`,
     `fix`, `refactor`, `docs`, `test`, `chore`, etc. Use `add` only for genuinely
     new capabilities, `update` for enhancements, `fix` for bug fixes.
   - **Blank line**, then a **body** that explains:
     - *Why* the change was made (the problem, goal, or rationale from the
       conversation) — this is the most important part for traceability.
     - *What* changed at a high level, and any notable trade-offs or decisions.
     - Links/refs (issue numbers, related commits) when relevant.
   - Always pass the message via a HEREDOC to preserve formatting:

```bash
git commit -m "$(cat <<'EOF'
update data loader to parse EET timestamps

The bars CSVs use ';' separators and EET timestamps, which pandas
misparsed by default. Set explicit sep and date_format so downstream
backtests align bars correctly across instruments.
EOF
)"
```

5. **Verify the commit** with `git status` and `git log -1`.

6. **Push.** Push the current branch to its upstream (default `main`):
   `git push origin HEAD`. Pushing to a protected branch (`main`) may require
   explicit user approval — proceed only after the commit succeeds, and never
   force-push unless the user explicitly asks.

## Guardrails

- Only commit when there are actual changes; never create empty commits.
- Do not update git config, skip hooks, or rewrite published history.
- If a pre-commit hook modifies files, create a follow-up commit (avoid `--amend`
  on already-pushed or non-authored commits).
- If the commit or push fails, report the exact error and the recommended fix
  instead of retrying blindly.
