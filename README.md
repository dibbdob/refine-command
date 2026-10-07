# backlog

A Claude Code plugin that takes a GitHub issue from a rough idea to working, tested code. It has two commands:

```
/backlog:refine 42
```

turns the issue into a feature specification a team can build from. It drafts the specification, asks you only what it cannot work out, and checks the result against your Definition of Ready.

```
/backlog:implement 42
```

builds what a Ready specification describes, test-first, and closes the issue.

It works in a new project with nothing set up, and in an existing project that already has its own templates.

## Quick start

You need [Claude Code](https://claude.com/claude-code) and the [GitHub CLI](https://cli.github.com), signed in.

1. Install the plugin:

   ```bash
   claude plugin marketplace add dibbdob/refine-command
   ```

   ```bash
   claude plugin install backlog@refine-command
   ```

2. Start a new Claude Code session in your project and run `/backlog:refine` with an issue number.
3. Answer a handful of questions, read the list of assumptions it made, and say yes to the finish.
4. Run `/backlog:implement` with the same number and say yes when the tests pass.

There is no configuration to write. On the first run the command finds your repository and creates the templates it needs. Everything below is reference.

## From issue to done

Starting from an issue on GitHub that nobody has refined:

1. **Refine it.** Run `/backlog:refine <issue-number>`.
   - **Intent:** it asks only what it cannot work out, usually zero to five questions. Pick an option for each.
   - **Review:** it shows the assumptions, the scenarios and the Definition of Ready table. Accept them, or say what to change.
   - **Finish:** it lists the commit, the push, the issue update and the label. Say yes.

   The issue now carries the agreed summary and a link to a Ready specification in `docs/specs`.

2. **Implement it.** Run `/backlog:implement <issue-number>`.

   It asks nothing up front. It writes a failing test for each scenario, makes them pass, runs the whole suite and reports the numbers. Then it lists the commit, the push and closing the issue. Say yes.

   The code is on your branch with every test passing, and the issue is closed.

Three things can interrupt that:

- **A thin issue.** If it has no clear narrative, problem or success criteria, refine proposes them in the Intent round.
- **A failing test.** Implement reports the failure and offers neither the commit nor the close.
- **A wrong specification.** If implement finds that the specification contradicts itself or the code, it stops. Run `/backlog:refine` on the same number to revise it.

## What refine does

The command drafts the whole specification itself and keeps its questions to three rounds:

1. **Intent.** The few things only you can answer: a choice between behaviours, a design choice that would be costly to change later, something the issue asks for that turns out not to be possible, or a contradiction. Usually five questions or fewer.
2. **Review.** The complete draft. Every default the command applied is listed under Assumptions, so you can overrule any of them. Design choices with lasting consequences are never assumed; they are asked in the Intent round and recorded as ADRs.
3. **Finish.** One list of what is about to happen (commit, push, updated issue description, label) and a single yes. Strike any line you do not want.

Along the way it checks what it can before asking (how a tool behaves, whether a repository setting is available) and points out when an answer contradicts something already agreed.

The result is `docs/specs/NNNN-<slug>.md`, marked Ready or Draft, containing:

- narrative and problem
- functional and non-functional requirements
- acceptance criteria in Gherkin: happy paths, sad paths, edge cases, each scenario with a stable ID such as `0042-03` that its test also carries
- what is out of scope
- what it changes in current behaviour
- design, with an ADR for each lasting decision
- external dependencies
- implementation plan, split into phases if it is too big
- testing strategy for every scenario
- non-development tasks, each with an owner
- the assumptions it made

Three situations are handled on the way in:

- **A thin issue.** If the issue has no clear narrative, problem or success criteria, the command proposes them in the Intent round. At the finish the issue's description is rewritten with what was agreed, so the issue and the specification say the same thing.
- **An issue that changes earlier work.** The command reads the behaviour folder for the areas the issue touches, and lists what the new issue changes there: scenarios it replaces or removes, and the tests that have to change. If the issue would reverse an earlier decision without saying so, it asks which stands. The earlier specifications themselves are left untouched.
- **An unfinished specification.** If a Draft already exists for the issue, running the command again asks only about its open items. Running it on a Ready specification asks whether you want to revise it, as long as its issue is still open; once the issue is closed, a change starts with a new issue.

### Thorough mode

The default, lean mode, suits one person or a small team. When several people are in the session, or nothing should be assumed, set `"mode": "thorough"` in the configuration. The command then proposes each default for you to choose instead of applying it, and agrees the specification section by section.

## What implement does

`/backlog:implement <issue-number>` builds the feature from its specification. It asks nothing about what to build, because that was agreed in refinement.

1. It finds the specification for the issue and stops if there is none or it is still a Draft.
2. It turns each scenario into a failing test, then writes the code that makes them pass, following the specification's design and implementation plan.
3. It runs the whole test suite and reports the result.
4. It shows one list of what is about to happen (commit, push, close the issue) and asks for a single yes. If a test fails, it reports the failure and offers nothing.

It builds nothing beyond the specification, never changes a test to get a green run, and never edits the specification. If the specification turns out to be wrong or impossible, it stops and sends you back to `/backlog:refine`.

## Current behaviour

The numbered specifications are a history: each says what one issue changed and why, and is never edited once its issue is closed. On their own they do not say what the system does now; for that you would have to read them all in order.

So the plugin keeps a second set of documents that does:

```
docs/
  specs/         history: one specification per issue
  decisions/     ADRs
  behaviour/     the present: what the system does today
    README.md    the areas, how many scenarios each holds, which specification last changed it
    vat/
      line-vat.md
      invoice-totals.md
```

- **One file for each area of behaviour**, holding the scenarios in force. Each scenario names its area with a tag in its specification, such as `@area:vat/line-vat`.
- **Generated, never written.** A script builds the folder from the specifications that have been built: all their scenarios, less any that a later specification lists as replaced or removed. Nobody edits it, and a check fails if anyone has.
- **Updated by implement, when the tests pass.** A specification that is Ready but not built describes what will be true, so it is not there yet.
- **Read by refine.** It reads the index and only the areas an issue touches, so a refinement costs the same in a system of forty specifications as in one of four.

A project whose earlier specifications were written before scenarios had IDs will find the folder empty at first. Those specifications cannot be edited to add them. To bring that behaviour in, raise an issue to record the baseline: its specification restates the scenarios in force with IDs and areas, changes nothing, and its implementation is tagging the existing tests.

## What is checked by script

Some promises of the process are too important to rest on careful reading, so a script checks them and the commands stop when it fails. It is `scripts/backlog_check.py` in this plugin, and it can be run by hand or in CI from the project root.

| Command | Run by | Fails when |
|---|---|---|
| `spec <issue>` | refine, before the review and again when setting Ready; implement, before building | a scenario has no ID, an ID is malformed or used twice, a requirement is cited by no scenario, a scenario is missing from the testing strategy, a scenario has no area, a scenario listed as changed is not in force, a link does not resolve, or a Ready specification has open items. Warns when a specification creates a new area |
| `tests <issue>` | implement, after the suite passes | a scenario has no test carrying its ID, a test carries an ID no specification defines, or the test for any other scenario was changed or removed without the specification listing it |
| `closed` | both, before anything is committed | a specification or ADR belonging to a closed issue was edited after the issue closed |
| `red <issue> -- <test command>` | implement, after writing the tests and before any code | a scenario has no test yet, or the suite already passes |
| `green <issue> -- <test command>` | implement, after the code | the suite fails, or no failing run was recorded first. Warns when a test was edited after it was seen to fail |
| `behaviour` | implement, before building | a file in the behaviour folder differs from what the specifications generate, or was not generated at all |
| `behaviour --add <issue>` | implement, after the suite and the other checks pass | never; it regenerates the folder with that specification included |
| `state` | both, after the finish | a specification's status disagrees with its issue's label, its issue's text or the feature index; or an issue is closed while its specification is a Draft, is missing from the behaviour folder, or has a scenario with no test |

The second row is the guard against bending a test to get a green run. `red` and `green` are the evidence that the tests came first; the record of the failing run is kept inside `.git`, not in your project's files. Test code written before scenarios had IDs cannot be tied to a specification, so a change to it is reported as a warning for a person to look at, not as a failure.

A scenario the testing strategy marks as not automated is not expected to have a test. The checker lists it as a warning, so that its written procedure is carried out by hand and the result reported. A project with no test setup at all still works: every scenario is manual, and `red` and `green` have nothing to run.

What no script checks: whether the right questions were asked, whether an assumption is sensible, and whether a test really asserts what its scenario says.

## Requirements

- [Claude Code](https://claude.com/claude-code)
- The [GitHub CLI](https://cli.github.com), signed in (`gh auth status`)
- Python 3, for the checker. It uses only the standard library, whatever language your project is in
- A GitHub repository with the issue you want to refine

## Install

The command is installed as a Claude Code plugin called `backlog`. It is then available in every project on your machine as `/backlog:refine`; the prefix is the plugin's name, and keeps the command from colliding with a `/refine` a project already has.

Add this repository as a marketplace:

```bash
claude plugin marketplace add dibbdob/refine-command
```

Install the plugin from it:

```bash
claude plugin install backlog@refine-command
```

Start a new Claude Code session and run `/backlog:refine <issue-number>`.

Do not also copy `commands/refine.md` into a project's `.claude/commands/`. That gives the project a second command, `/refine`, which does the same thing from a file that never updates.

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
    "issueTemplate": ".github/ISSUE_TEMPLATE/feature.md",
    "behaviourDir": "docs/behaviour"
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
  },
  "implement": {
    "commit": true,
    "commitMessage": "#{issue} Implement: {title}",
    "closeIssue": true,
    "testPaths": []
  }
}
```

| Key | Meaning |
|---|---|
| `repo` | GitHub repository that holds the issues, as `owner/name`. Used for every `gh` call, so the git remotes of the checkout do not matter. |
| `paths.*` | Where the documents live and where new ones are written, relative to the project root. |
| `paths.behaviourDir` | Where the description of current behaviour is generated. See [Current behaviour](#current-behaviour). |
| `process.mode` | `lean` (default) or `thorough`. See [Thorough mode](#thorough-mode). |
| `process.deliveryBudget` | The largest a single feature may be. Anything bigger is split into phases. |
| `finalise.commit` | Commit the specification at the end of the session. |
| `finalise.commitMessage` | Commit message. `{issue}` and `{title}` are filled in. |
| `finalise.updateIssue` | Rewrite the issue's description as a summary of what was agreed: narrative, problem, success criteria, a link to the specification with its status, and the decisions with links to their ADRs. Requirements and scenarios stay in the specification. |
| `finalise.readyLabel` | Label added to the issue when the specification is Ready, and removed if it goes back to Draft. Created in the repository on first use, with your agreement. Set to `""` to turn labelling off. |
| `implement.commit` | Commit the feature when `/backlog:implement` has built and verified it. |
| `implement.commitMessage` | Commit message. `{issue}` and `{title}` are filled in. |
| `implement.closeIssue` | Close the issue as completed once every phase of the specification is built. |
| `implement.testPaths` | Glob patterns naming the project's test files, for the checker. Empty means the common conventions: `tests/`, `test_*`, `*.test.*`, `*_test.*`, `spec/`. |

Even with these switched on, nothing leaves your working copy without a yes. At the finish the command shows one list of what it is about to commit, push, write to the issue and label, with the exact text, and you can strike any line.

## What is fixed

The command is deliberately opinionated. These are not configurable:

- One feature specification per GitHub issue, numbered by the issue.
- Closed work is a record. A specification whose issue is closed is never edited, and neither are its ADRs or the issue. A later issue that changes it says so in its own specification, under Changes to current behaviour.
- The command drafts; you review. In lean mode it applies its defaults and lists them, instead of asking.
- Narrative, problem and lasting design decisions are never assumed.
- Acceptance criteria are written in Gherkin, with concrete values, one scenario per test.
- Non-functional requirements are "none" unless something points to one. No invented thresholds.
- The simplest design that satisfies the scenarios, using what the project already uses.
- Tests are automated with the project's existing setup wherever possible. Refinement writes no tests; turning each scenario into a failing test is the first step of the implementation plan.
- A feature is not Ready until every item of the Definition of Ready is met.
- Features are kept small; a feature over the delivery budget is split into phases.

If one of these does not suit you, fork this repository, edit the files in `commands/`, and install the plugin from your fork.

## Updating and removing

Update with

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

A workflow in this repository, `.github/workflows/version.yml`, fails any push or pull request that changes a command or script without raising the version in `.claude-plugin/plugin.json`. An installed plugin only updates when its version changes.

To check the manifests:

```bash
claude plugin validate /path/to/refine-command
```

The layout:

```
.claude-plugin/plugin.json        plugin manifest
.claude-plugin/marketplace.json   marketplace manifest, lists this one plugin
commands/refine.md                the refine command, including the default documents
commands/implement.md             the implement command
scripts/backlog_check.py          the checks that need no judgement
```

## Licence

[MIT](LICENSE)
