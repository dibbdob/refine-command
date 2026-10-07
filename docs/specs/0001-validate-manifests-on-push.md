# 0001: Validate the plugin manifests on every push to main and every pull request

- **Status:** Ready
- **Issue:** #1
- **Decisions:** [ADR 0001](../decisions/0001-validate-manifests-in-ci.md)

## Narrative

As a maintainer, I want the manifests validated on every push to main and every pull request, so that a broken manifest is caught before anyone tries to install the plugin.

## Problem

- Manifests are only validated when someone remembers to run `claude plugin validate` locally; nothing checks a push.
- A broken manifest would first show up as a failed plugin install on someone else's machine.
- Nothing on GitHub shows whether the current main branch is installable.

## Requirements

### Functional

- FR-1: A push to `main` runs a check that validates the marketplace manifest and the plugin manifest, whichever files the push changed.
- FR-2: A pull request targeting `main` runs the same check when it is opened and on each new commit, whichever files it changes.
- FR-3: The check fails when either manifest has a validation error.
- FR-4: The check fails when either manifest has a validation warning.
- FR-5: The check passes when both manifests are valid with no warnings.
- FR-6: The result shows as a check status on the commit or pull request on GitHub.

### Non-functional

- Performance: the check finishes within 5 minutes.
- Security and privacy: none.
- Availability and reliability: if the check cannot run, that counts as a failure, not a pass.
- Observability: a failure's log names the manifest file and the validation error.

## Acceptance criteria

```gherkin
Feature: Validate the plugin manifests

  Scenario: Push to main with valid manifests
    Given plugin.json and marketplace.json are valid with no warnings
    When a commit is pushed to main
    Then the commit shows a passing "validate" check

  Scenario: Push to main with a manifest error
    Given .claude-plugin/plugin.json contains invalid JSON
    When a commit is pushed to main
    Then the commit shows a failed "validate" check
    And the log names .claude-plugin/plugin.json and "Invalid JSON syntax"

  Scenario: Push to main with a manifest warning
    Given .claude-plugin/marketplace.json has no description
    When a commit is pushed to main
    Then the commit shows a failed "validate" check
    And the log names the missing description

  Scenario: Push to main that touches neither manifest
    Given plugin.json and marketplace.json are valid with no warnings
    When a commit that changes only README.md is pushed to main
    Then the commit shows a passing "validate" check

  Scenario: Pull request with a manifest error
    Given a branch where .claude-plugin/marketplace.json contains invalid JSON
    When a pull request from that branch to main is opened
    Then the pull request shows a failed "validate" check

  Scenario: Fixing a failing pull request
    Given an open pull request with a failed "validate" check
    When a commit that makes both manifests valid is pushed to its branch
    Then the pull request shows a passing "validate" check

  Scenario: Push to a branch with no pull request
    Given a branch named wip with no open pull request
    When a commit with invalid JSON in plugin.json is pushed to wip
    Then no "validate" check runs for that commit
```

## Out of scope

- Preventing a merge into `main` when the check fails. This needs branch protection, which GitHub does not offer for this private repository on the current plan. To revisit if the repository becomes public or the plan changes.
- Any checking of pushes to branches other than `main` that have no pull request.

## Design

A GitHub Actions workflow at `.github/workflows/validate.yml`.

- Triggers: pushes to `main`, and pull requests targeting `main`. No path filter, so every such push and pull request runs it.
- One job named `validate`. It installs the Claude Code CLI from npm and runs `claude plugin validate --strict .` from the repository root. `--strict` makes warnings fail; run against the root, the validator covers both manifests.
- The job has a 5-minute timeout, so an overrun is stopped and reported as a failure.
- No secrets. The validator runs without a signed-in account.

### Architectural decisions

- [ADR 0001](../decisions/0001-validate-manifests-in-ci.md): validate in GitHub Actions, installing the latest CLI on each run.

## External dependencies

| Dependency | Available | Notes |
|------------|-----------|-------|
| GitHub Actions enabled on the repository | Yes | Checked on 2026-10-07 |
| `@anthropic-ai/claude-code` on npm | Yes | 2.1.292 on 2026-10-07 |

## Implementation plan

1. Add `.github/workflows/validate.yml` on a branch.
2. Open a pull request and confirm the `validate` check runs and passes.
3. Write the verification script (see Testing strategy) and run it against the pull-request scenarios.
4. Merge, and confirm the check runs and passes on `main`.

### Phases

None. Agreed as deliverable within one working day.

## Testing strategy

A script using `gh` creates throwaway branches and pull requests, waits for the `validate` check, asserts its result through the GitHub API, and cleans up after itself.

| Scenario | Automated | How it is verified |
|----------|-----------|--------------------|
| Push to main with valid manifests | No | Manual: after the workflow is merged, confirm the merge commit on `main` shows a passing `validate` check |
| Push to main with a manifest error | No | Manual, by inspection: no broken commit is pushed to `main`. Confirm the workflow triggers on pushes to `main` and runs the same job as pull requests, where failure on an error is asserted by the script |
| Push to main with a manifest warning | No | Manual, by inspection: as above, and confirm the job runs the validator with `--strict` |
| Push to main that touches neither manifest | No | Manual: push a commit that changes only `README.md` to `main` and confirm it shows a passing `validate` check |
| Pull request with a manifest error | Yes | Script opens a pull request with invalid JSON in `marketplace.json` and asserts a failed check |
| Fixing a failing pull request | Yes | Script pushes a fixing commit to that pull request and asserts a passing check |
| Push to a branch with no pull request | Yes | Script pushes a broken commit to a branch with no pull request and asserts no check run exists |

## Non-development tasks

| Task | Owner |
|------|-------|
| Mention the check in the README's Developing section | Jan Wilson |
| When the check fails on `main` with no change to the repository, look at whether a new CLI release caused it (see ADR 0001) | Jan Wilson |

## Open items

None.
