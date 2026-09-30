---
name: generate-github-actions
description: Create or update GitHub Actions for a Python project. Use when the CI system is github-actions or the user or handoff asks for a GitHub pipeline.
---

# Generate GitHub Actions

## Preconditions

- This session owns the pipeline. Do not use it to implement a feature or to write project docs.

## Steps

1. Read `.cursor/rules/github-actions.mdc`. If the app is containerized, also read `.cursor/rules/docker.mdc`.
2. Add or update `.github/workflows/` so lint (`ruff`) and test (`pytest`, Python 3.12) run. Add an image build only when the app is containerized.
3. Keep secrets out of YAML. Use GitHub secrets and variables.
4. Do not add `.gitlab-ci.yml`.
5. Do not add a deploy job unless the Issue names an environment.
6. On an empty repo, a job that has nothing to run yet exits 0, reports that it had nothing to run, and is not a required check. When the files it needs exist, the job runs them and a real failure stays red.

## Do not

- Edit application source or `README.md`.
- Add a Dockerfile unless the app is containerized.
