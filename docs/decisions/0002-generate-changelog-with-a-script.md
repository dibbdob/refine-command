# 0002: Generate the changelog with a script in the repository

- **Status:** Accepted
- **Date:** 2026-10-07

## Context

Feature [0002](../specs/0002-add-a-changelog.md) adds a changelog with an entry for every version of the plugin. The version lives in `.claude-plugin/plugin.json`. The repository has no git tags and no GitHub releases, and so far each version has been introduced by exactly one commit.

## Options considered

1. Write entries by hand. No dependency, and entries can say what a user would notice. Relies on remembering to add one.
2. Generate with a small script in the repository that finds each commit that changed the version and uses that commit's message. No dependency and no tags. The script is ours to maintain, and entries read like commit messages.
3. Generate with git-cliff. A standard tool with a config file. Needs a git tag for every version, including six added retroactively, and anyone regenerating the changelog must install the tool.

## Decision

Option 2: a script in the repository, driven by the commits that change the version, without git tags.

## Consequences

- An entry cannot be forgotten once the script is run, but someone still has to run it; nothing does so automatically.
- A version's entry lands in a commit after the one that raises the version, never in the same commit.
- The quality of the changelog is the quality of the commit messages on version changes.
- Changes that do not raise the version do not appear in the changelog.
- To revisit if the repository starts tagging releases, at which point a standard tool becomes the simpler choice.
