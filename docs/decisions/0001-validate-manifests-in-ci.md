# 0001: Validate manifests in GitHub Actions with the latest CLI

- **Status:** Accepted
- **Date:** 2026-10-07

## Context

The plugin and marketplace manifests are only validated when someone runs `claude plugin validate` locally. Feature [0001](../specs/0001-validate-manifests-on-push.md) adds a check on pushes to `main` and on pull requests. The check needs the Claude Code CLI, which is released often, and each release can change what the validator accepts or warns about. The check treats warnings as failures.

## Options considered

1. Install the latest CLI on each run. No upkeep, and new validation rules apply immediately. The check on `main` can start failing with no change to the repository when a new CLI release adds a warning.
2. Install a pinned CLI version. Results only change when the repository changes. Someone has to bump the pin, or the check validates against stale rules.

## Decision

Option 1: the check runs in GitHub Actions and installs the latest CLI on each run.

## Consequences

- The manifests are always validated against the rules current users of the plugin will meet.
- A failing check on `main` does not always mean the last commit broke something; a new CLI release is the other possible cause.
- No pin to maintain.
- To revisit if failures caused by CLI releases become frequent.
