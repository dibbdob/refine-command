# refine

A Claude Code command that turns a GitHub issue into a feature specification a team can build from. You give it an issue number; it drafts the specification, asks you only what it cannot work out, and checks the result against your Definition of Ready.

```
/refine 42
```

It works in a new project with nothing set up, and in an existing project that already has its own templates.

## Quick start

You need [Claude Code](https://claude.com/claude-code) and the [GitHub CLI](https://cli.github.com), signed in.

1. From the root of your project, copy the command in:

   ```bash
   mkdir -p .claude/commands && gh api repos/dibbdob/refine-command/contents/commands/refine.md -H "Accept: application/vnd.github.raw" > .claude/commands/refine.md
   ```

2. Start Claude Code in the project and run `/refine` with an issue number.
3. Answer a handful of questions, read the list of assumptions it made, and say yes to the finish.

There is no configuration to write. On the first run the command finds your repository and creates the templates it needs. Everything below is reference.

## What it does

The command drafts the whole specification itself and keeps its questions to three rounds:

1. **Intent.** The few things only you can answer: a choice between behaviours, a design choice that would be costly to change later, something the issue asks for that turns out not to be possible, or a contradiction. Usually five questions or fewer.
2. **Review.** The complete draft. Every default the command applied is listed under Assumptions, so you can overrule any of them. Design choices with lasting consequences are never assumed; they are asked in the Intent round and recorded as ADRs.
3. **Finish.** One list of what is about to happen (commit, push, updated issue description, label) and a single yes. Strike any line you do not want.

Along the way it checks what it can before asking (how a tool behaves, whether a repository setting is available) and points out when an answer contradicts something already agreed.

The result is `docs/specs/NNNN-<slug>.md`, marked Ready or Draft, containing:

- narrative and problem
- functional and non-functional requirements
- acceptance criteria in Gherkin: happy paths, sad paths, edge cases
- what is out of scope
- design, with an ADR for each lasting decision
- external dependencies
- implementation plan, split into phases if it is too big
- testing strategy for every scenario
- non-development tasks, each with an owner
- the assumptions it made

Two situations are handled on the way in:

- **A thin issue.** If the issue has no clear narrative, problem or success criteria, the command proposes them in the Intent round. At the finish the issue's description is rewritten with what was agreed, so the issue and the specification say the same thing.
- **An unfinished specification.** If a Draft already exists for the issue, running the command again asks only about its open items. Running it on a Ready specification asks whether you want to revise it.

### Thorough mode

The default, lean mode, suits one person or a small team. When several people are in the session, or nothing should be assumed, set `"mode": "thorough"` in the configuration. The command then proposes each default for you to choose instead of applying it, and agrees the specification section by section.

## Requirements

- [Claude Code](https://claude.com/claude-code)
- The [GitHub CLI](https://cli.github.com), signed in (`gh auth status`)
- A GitHub repository with the issue you want to refine

## Install

There are two ways to get the command. Pick one.

| | Copy the command | Install the plugin |
|---|---|---|
| Lives in | the project's `.claude/commands/` | your Claude Code install |
| Available in | that project, for everyone who clones it | every project on your machine |
| Invoked as | `/refine 42` | `/backlog:refine 42` |
| Updates | copy the file again | `claude plugin update` |
| Can be edited per project | yes | no |

### Option 1: copy the command into a project

Run this from the root of the project:

```bash
mkdir -p .claude/commands && gh api repos/dibbdob/refine-command/contents/commands/refine.md -H "Accept: application/vnd.github.raw" > .claude/commands/refine.md
```

Commit `.claude/commands/refine.md` so the rest of the team gets it. Start a new Claude Code session and run `/refine <issue-number>`.

The command is a single file with no other dependencies, so copying it by hand from [commands/refine.md](commands/refine.md) works just as well.

### Option 2: install as a plugin

Add this repository as a marketplace:

```bash
claude plugin marketplace add dibbdob/refine-command
```

Install the plugin from it:

```bash
claude plugin install backlog@refine-command
```

Start a new Claude Code session and run `/backlog:refine <issue-number>`. Plugin commands carry the plugin's name as a prefix, which keeps this one from colliding with a `/refine` a project already has.

To have a project suggest the plugin to everyone who opens it, add this to the project's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "refine-command": {
      "source": { "source": "github", "repo": "dibbdob/refine-command" }
    }
  },
  "enabledPlugins": {
    "backlog@refine-command": true
  }
}
```

## First run

The first time you run the command in a project, it sets itself up without asking and tells you what it did:

1. **Repository.** It takes the checkout's GitHub remote and saves it to `.claude/refine.json`. It asks only if it finds none.
2. **Documents.** It creates any of the five documents below that the project does not have, from built-in defaults.

| Document | Default path |
|---|---|
| Feature template | `docs/specs/TEMPLATE.md` |
| Feature index | `docs/specs/README.md` |
| Definition of Ready | `docs/specs/READY.md` |
| ADR template | `docs/decisions/TEMPLATE.md` |
| Issue template | `.github/ISSUE_TEMPLATE/feature.md` |

The issue template gives new issues a narrative, problem and success criteria, which is what a session starts from; the more complete the issue, the fewer questions the command asks. GitHub only picks it up once it is on the repository's default branch. It is skipped if the project already has issue templates, and setting `paths.issueTemplate` to `""` turns it off.

Nothing is committed during setup. At the finish, the command offers to commit these files along with the specification.

### Existing projects

If the project already has a feature template, a Definition of Ready or an ADR template, point the configuration at them before the first run. The command uses your documents as they are and never overwrites or reformats them. Your Definition of Ready is the checklist; the built-in one is only a starting point for projects that have none.

## Configuration

`.claude/refine.json`, at the project root. The command writes this file itself on the first run, with only `repo` in it, and most projects never need to edit it. Everything else falls back to the value shown.

```json
{
  "repo": "owner/name",
  "paths": {
    "featuresDir": "docs/specs",
    "featureTemplate": "docs/specs/TEMPLATE.md",
    "featureIndex": "docs/specs/README.md",
    "definitionOfReady": "docs/specs/READY.md",
    "adrDir": "docs/decisions",
    "adrTemplate": "docs/decisions/TEMPLATE.md",
    "issueTemplate": ".github/ISSUE_TEMPLATE/feature.md"
  },
  "process": {
    "mode": "lean",
    "deliveryBudget": "one working day"
  },
  "finalise": {
    "commit": true,
    "commitMessage": "#{issue} Specify: {title}",
    "updateIssue": true,
    "readyLabel": "ready"
  }
}
```

| Key | Meaning |
|---|---|
| `repo` | GitHub repository that holds the issues, as `owner/name`. Used for every `gh` call, so the git remotes of the checkout do not matter. |
| `paths.*` | Where the documents live and where new ones are written, relative to the project root. |
| `process.mode` | `lean` (default) or `thorough`. See [Thorough mode](#thorough-mode). |
| `process.deliveryBudget` | The largest a single feature may be. Anything bigger is split into phases. |
| `finalise.commit` | Commit the specification at the end of the session. |
| `finalise.commitMessage` | Commit message. `{issue}` and `{title}` are filled in. |
| `finalise.updateIssue` | Rewrite the issue's description as a summary of what was agreed: narrative, problem, success criteria, a link to the specification with its status, and the decisions with links to their ADRs. Requirements and scenarios stay in the specification. |
| `finalise.readyLabel` | Label added to the issue when the specification is Ready, and removed if it goes back to Draft. Created in the repository on first use, with your agreement. Set to `""` to turn labelling off. |

Even with these switched on, nothing leaves your working copy without a yes. At the finish the command shows one list of what it is about to commit, push, write to the issue and label, with the exact text, and you can strike any line.

## What is fixed

The command is deliberately opinionated. These are not configurable:

- One feature specification per GitHub issue, numbered by the issue.
- The command drafts; you review. In lean mode it applies its defaults and lists them, instead of asking.
- Narrative, problem and lasting design decisions are never assumed.
- Acceptance criteria are written in Gherkin, with concrete values, one scenario per test.
- Non-functional requirements are "none" unless something points to one. No invented thresholds.
- The simplest design that satisfies the scenarios, using what the project already uses.
- Tests are automated with the project's existing setup wherever possible. Refinement writes no tests; turning each scenario into a failing test is the first step of the implementation plan.
- A feature is not Ready until every item of the Definition of Ready is met.
- Features are kept small; a feature over the delivery budget is split into phases.

If one of these does not suit a project, use Option 1 and edit the project's copy.

## Updating and removing

**Copied command:** run the install line again to update, or delete `.claude/commands/refine.md` to remove it.

**Plugin:** update with

```bash
claude plugin update backlog@refine-command
```

and remove with

```bash
claude plugin uninstall backlog@refine-command
```

## Developing

To try a local checkout of this repository without installing it:

```bash
claude --plugin-dir /path/to/refine-command
```

To check the manifests:

```bash
claude plugin validate /path/to/refine-command
```

The layout:

```
.claude-plugin/plugin.json        plugin manifest
.claude-plugin/marketplace.json   marketplace manifest, lists this one plugin
commands/refine.md                the command, including the default documents
```

## Licence

[MIT](LICENSE)
