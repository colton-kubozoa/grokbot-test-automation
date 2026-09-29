---
name: commit-github-pr
description: Commit on a feature branch and open a GitHub pull request. Use when the user or the handoff asks to commit or open a PR on a GitHub repo.
---

# Commit GitHub pull request

## Preconditions

- The user, or the handoff for this session, asked to commit or open a pull request.
- The project is on GitHub. `origin` is the repository for this work.
- The tree is buildable when tests exist.
- Findings this session was asked to fix are already fixed.

## Configuration

- **Remote** — `origin` is the GitHub repository for this work
- **PR target branch** — `develop`, or the base branch named on the Issue

## Steps

1. If the current branch is `main`, `master`, or `develop`, create `feature/<name>` or `bugfix/<name>` from the PR target.
2. Run the remote check in `.cursor/rules/git.mdc` and `.cursor/rules/github-scm.mdc`. On failure, stop and say which check failed.
3. Read `git status`, `git diff`, and `git log`. Write the message in the style of `git.mdc`.
4. Stage only the files for this change. Do not stage secrets, `logs/`, or credentials.
5. Commit with a HEREDOC message. Do not pass `--no-verify` unless the user asked.
6. When a pull request was requested, push with `-u origin HEAD` and:

```bash
gh pr create --draft --base <PR-target> --title "..." --body "$(cat <<'EOF'
## Summary
- ...

## Test plan
- [ ] ...
EOF
)"
```

Open it as a draft when verification or documentation is still to come. Omit `--draft` only when the user asked for a finished pull request, or when documentation for this change is already done.

## Do not

- Force-push `develop` or `main`
- Commit secrets
- Merge the pull request
- Use GitLab merge-request commands
