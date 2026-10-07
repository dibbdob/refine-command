---
description: Turn a GitHub issue into a feature specification a team can build from, asking only what the team alone can answer
argument-hint: <issue-number>
disable-model-invocation: true
---

# Refine

Turn GitHub issue #$ARGUMENTS into a specification that passes the project's Definition of Ready. If no issue number was given, ask for one.

You do the drafting. The team decides what only they can decide, and reviews the rest once. Where this command gives a default, apply it without asking and write it down as an assumption, so the team can overrule it in the review. A session is three rounds of questions, not one per section:

1. **Intent**: the few questions only the team can answer.
2. **Review**: the complete draft, with every assumption listed.
3. **Finish**: one confirmation for everything that leaves the working copy.

## Configuration

Everything specific to the project comes from `.claude/refine.json` at the project root. Read it first.

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
  }
}
```

- `repo` is the GitHub repository that holds the issues, as `owner/name`. Pass it to every `gh` call with `--repo`.
- `paths` are relative to the project root. Set `paths.issueTemplate` to `""` to do without an issue template.
- `paths.behaviourDir` holds what the system does today, generated from the specifications that have been built. See [Current behaviour](#current-behaviour). This command reads it and never writes it.
- `process.mode` is `lean` or `thorough`; see [Thorough mode](#thorough-mode).
- `process.deliveryBudget` is the largest a single feature may be.
- `finalise` controls the finish. Set `finalise.readyLabel` to `""` to leave issue labels alone.

Only `repo` is required. A value that is absent takes the value shown above.

## First run

Do this silently before the session and report it in one line at the start.

1. **No config file, or no `repo` in it.** Run `gh repo view --json nameWithOwner` in the checkout, use the result, and write `.claude/refine.json` with that `repo` and nothing else. Ask only if no repository is found.
2. **A document is missing at its configured path.** Create it from the matching default under [Default documents](#default-documents). Create the issue template only when `repo` is the repository of this checkout and its folder holds no other issue templates.
3. **The issue cannot be read from `repo`.** Show the error and stop.

Never overwrite or reformat a document the project already has. The project's own template and Definition of Ready always win. Files created here are offered for commit at the finish.

## How to work

- **Check what can be checked.** Before asking a question or writing a statement about how something behaves, find out what is true: how a tool behaves, whether a repository setting is available, whether a dependency exists. Use read-only checks, and try things out only in a scratch location. Never change the project or GitHub in order to check. If a check shows that something the issue asks for cannot be met as things stand, that is a question for the Intent round.
- **Hold every answer against what is already agreed.** When an answer contradicts the issue, the narrative, a requirement or a scenario, do not pick one. Show both statements, ask which stands, and bring the other into line.
- **Propose, do not interrogate.** Every question comes with two or three worded options, each written as it would appear in the specification, plus room for the team's own answer.
- **Write down what you assumed.** Every default you applied goes in the specification's Assumptions section, one line each. If the project's template has no such section, add one before the open items.

## Before the Intent round

1. Read the issue, the feature template, the Definition of Ready, the feature index and the project's `CLAUDE.md` if there is one.
2. Look in `paths.featuresDir` for a specification that already exists for this issue: a file whose name starts with the issue number padded to four digits. If there is one, see [Resuming](#resuming).
3. Look at the project itself: what it is built with, how it is tested, how it is laid out. The design and the testing strategy follow what is already there.
4. Run whatever checks the issue calls for.
5. Read what the system does today, and find what this issue would change in it. See [Current behaviour](#current-behaviour).

## Current behaviour

`paths.behaviourDir` describes what the system does today: one file for each area of behaviour, holding the scenarios in force, and a `README.md` that lists the areas. It is generated by a script from the specifications that have been built, so it is never edited by hand and never by this command. The implement command brings a specification into it once its tests pass.

Reading it is how a refinement stays the same size however large the system grows:

- **Read the index, then only the areas this issue touches.** Do not read every earlier specification. Open an earlier specification only when a scenario in force does not settle a question by itself, and find it from the scenario's ID, whose first four digits are its number.
- **Read the decisions that bear on the issue.** List `paths.adrDir` and open the ADRs whose titles relate to it.
- **Earlier specifications without scenario IDs are not in the folder.** If the project has any, read those too, and say in the first-run line that their behaviour is not yet recorded there.

A new issue often changes something already in force. The change is written down in the new specification and nowhere else.

- **Never edit closed work.** A specification whose issue is closed is not edited, and neither are the ADRs it recorded or the issue itself. This holds for every round, including the finish.
- **Find every collision.** Go through the scenarios in force in the areas this issue touches, and the tests that carry their IDs, for anything this issue would change, reverse or make untrue. An example that happens to use what this issue introduces counts, such as a scenario that used a value as its "unknown" case.
- **Ask when it reverses a decision.** If the issue plainly intends the change, record it and move on. If it would reverse an ADR, or something the team chose in an earlier session, and the issue does not say so, that is a contradiction for the Intent round: show both statements and ask which stands.
- **Record it in one section.** The new specification has a section, Changes to current behaviour, with one line for each scenario in force that it replaces or removes: its ID, its title, and what becomes of it (replaced by a named scenario here, or removed). Write "None." when there is nothing. If the project's template has no such section, add it after Out of scope. The script that generates the behaviour folder drops every scenario listed here, so the list has to be complete and has to use the IDs.
- **Carry it through the draft.** A scenario that replaces one in force is written out in full in the new specification under the same title, with a new ID. The implementation plan names each existing test to change or remove, and the testing strategy says so against the scenario. A new ADR that replaces an earlier decision names the one it supersedes in its Context.

### Recording a baseline

A project may have specifications written before scenarios had IDs. Their behaviour is real but is not in the folder, and they cannot be edited. An issue that asks for that behaviour to be recorded is a baseline, and it is refined like any other with these differences:

- **It restates what is in force.** Write out every scenario that holds today, taken from the earlier specifications and checked against the tests, each with an ID and an area. Leave out any that a later specification replaced or removed. This is the one case where scenarios already in force are written again.
- **It changes nothing.** Changes to current behaviour is "None.", and nothing new goes into Out of scope beyond saying that behaviour does not change.
- **Each scenario points at its existing test.** The testing strategy names the existing test that proves each scenario. If a scenario in force has no test, or a test has no scenario, that is a question for the Intent round, not something to settle quietly.
- **Its implementation plan is tagging.** The only step is to add each scenario's ID above its existing test. No test is written, changed or removed, and no code is touched.

### Areas

Every scenario belongs to one area, which decides the file it will appear in.

- **Form.** Lowercase words joined by hyphens, with slashes for folders: `billing/credit-notes`. Write it as a Gherkin tag, `@area:billing/credit-notes`, on the line above `Feature:` when every scenario in the specification shares it, or on a scenario's own tag line when that scenario belongs elsewhere.
- **Choose an existing area where one fits.** An area is a piece of behaviour someone would look up by itself. Putting a scenario in an existing area is a default and goes in the Assumptions.
- **A new area is shown to the team.** It shapes the folder for everyone after, so name it in the review, under Changes to current behaviour. The checker reports it as a warning for that reason.
- **A rule shared by several areas gets one area of its own.** The others rely on it and do not repeat its scenarios.

## Round 1: Intent

Ask only what you cannot settle from the issue, the project, a check, or a default below. That leaves four kinds of question:

- **What only the team knows.** A choice between behaviours where both are reasonable and the scenarios would differ. If the issue is thin, meaning it lacks a narrative (who wants what, and why), a problem, or success criteria, propose the missing parts here.
- **What cannot be done.** Something the issue asks for that a check showed is not possible as things stand.
- **What contradicts.** Two statements in the issue, or the issue and the project, that cannot both hold. That includes an earlier decision the issue would reverse without saying so.
- **What will be costly to change.** A design choice with two or more workable options that differ in what they cost later: how something is produced, where it lives, what it depends on. Look for these before drafting, and ask here, with what each option costs. A decision made after the draft is written means writing the draft twice.

Put them in a single round, most consequential first. Aim for five or fewer. If an answer raises a new question of one of these four kinds, ask it; otherwise move on. If there is nothing to ask, say so and go straight to drafting.

## Draft

Write the complete specification to `paths.featuresDir`, in a file named with the issue number as four digits and a short kebab-case slug, for example `0042-export-to-csv.md`, following the structure of the feature template. Fill every section, using the team's answers first and the defaults below for everything else. If the template has sections not mentioned here, fill them too.

| Section | What goes in it | Default when the issue and the team have not said |
|---|---|---|
| Header | Status, the issue number, and links to any decisions | Status starts as Draft |
| Narrative and problem | From the issue or the Intent round | No default. These are never assumed |
| Functional requirements | One per success criterion, numbered | Derived from the success criteria and nothing more |
| Non-functional requirements | Performance, security, reliability, observability | "None" for each, unless the issue or a check points to one. Never invent a threshold |
| Acceptance criteria | Gherkin scenarios with concrete values, one scenario per test, each with an ID (see [Scenario IDs](#scenario-ids)) and an area (see [Areas](#areas)) | A happy path for every functional requirement, a sad path for every invalid input and every failure the issue names, and an edge case at every boundary |
| Out of scope | What is deliberately not built | Anything not needed for the success criteria, including anything the team was offered in the Intent round and did not choose. Name the nearest things someone might expect to be included |
| Changes to current behaviour | Each scenario in force that this one replaces or removes, by ID, and any new area it creates | Found by reading the behaviour folder, not asked. "None." when there is nothing |
| Design | Interfaces, data, visuals, as far as they apply | The simplest design that satisfies the scenarios, using what the project already uses. No new dependency where an existing one will do |
| External dependencies | Each with whether it is available now | Checked, not asked |
| Implementation plan | Ordered, concrete steps | The first step is to turn each scenario into a failing automated test, where the project has a test setup. No tests are written during refinement. Assume it fits `process.deliveryBudget` when it is a handful of steps in one area. Otherwise propose phases |
| Testing strategy | How each scenario and each non-functional requirement is verified | Automated with the project's existing test setup. A scenario that cannot be automated gets a written manual procedure with the exact commands. If the project has no test setup, every scenario gets one; do not add a test framework unless the issue asks for it. Never plan a test that breaks the default branch or a live system |
| Non-development tasks | Configuration, infrastructure, accounts, documentation | Derived from the design. Owned by the person in the session |
| Assumptions | Every default applied above | |

### Scenario IDs

Every scenario carries an ID, so that a test, a later specification or a script can point at it without quoting its title.

- **Form.** The specification's four-digit number, a hyphen, and a two-digit sequence in the order the scenarios appear: `0042-01`, `0042-02`. Write it as a Gherkin tag on the line above the scenario: `@0042-01`.
- **Stable once Ready.** While the specification is a Draft, renumber freely to keep the sequence in order. Once it is Ready, an ID is never changed and never reused; a scenario added in a later revision takes the next free number, and one that is dropped leaves a gap.
- **Tied to its requirements.** A comment on the line above the tag names the requirements the scenario covers: `# FR-1, FR-3`.
- **Used everywhere the scenario is named.** The testing strategy lists each scenario by its ID and title, with exactly Yes or No in its Automated column. The checker reads that column: a scenario marked No needs a written manual procedure instead of a test. The implementation plan and Changes to current behaviour refer to scenarios by ID, or by title for an earlier scenario that has none.
- **A replacement is a new scenario.** A scenario that replaces an earlier one gets its own ID here; the earlier ID is retired, not carried over.
- **Do not restate what already holds.** A scenario that only repeats one already in force is not written again. The requirement it would have covered cites the existing scenario instead, and the testing strategy says its existing test must pass unmodified.

Two things are never settled by a default:

- **A decision with lasting consequences.** Where the design has two or more workable options that differ in what they cost later, do not choose. Ask in the Intent round whenever the choice can be seen before drafting. If one only shows up while drafting, draft on the option you would recommend, mark it as undecided, and put the choice at the top of the review; when it is decided, redraft everything that depended on it and show what moved. Once decided, record it as an ADR at `<paths.adrDir>/NNNN-<slug>.md` from `paths.adrTemplate`, using the next free number in that folder, and reference it from the specification.
- **Participants.** Assume one person who covers product, technical and delivery. If the session has more people, ask who covers what and direct each question accordingly.

Before the review, check the draft yourself:

- **Coverage.** Every scenario has an ID in the right form and no ID appears twice. Every functional requirement has a scenario, or cites an existing one. Every scenario and every non-functional requirement has an entry in the testing strategy. Every scenario listed under Changes to current behaviour has a replacement here or is stated as removed, and every existing test it affects is named in the implementation plan. Fix what you can; list what you cannot as an open item.
- **The checker.** Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/backlog_check.py" spec <issue-number>` from the project root. It checks, without judgement, that every scenario has a well-formed and unique ID and an area, every scenario listed as changed is in force, every requirement is cited, every scenario is in the testing strategy, the Changes to current behaviour section exists, links resolve, and a Ready specification has no open items. Fix every line it reports as FAIL and run it again. If it cannot run, say so in the review and do the same checks by reading; never describe them as passed by the checker.
- **Definition of Ready.** Go through `paths.definitionOfReady` item by item. The checklist is whatever that document says. For each item, note whether it is met and what the evidence is.

## Round 2: Review

Show the team the draft in this order, shortest first:

1. **Decisions for you.** Each undecided design choice, with its options and what each costs.
2. **Changes to current behaviour.** The scenarios in force that this one replaces or removes, and any new area, if there are any.
3. **Assumptions.** The full list. This is the part to read.
4. **Scenarios.** The acceptance criteria in full.
5. **Definition of Ready.** The table of items, with any that are not met and any that only the team can vouch for.
6. Where the full specification is, for anyone who wants the rest.

Ask what they want changed. Apply the changes, recheck coverage and the Definition of Ready, and show what moved. Repeat until the team agrees. An assumption the team overrules is replaced by their answer and leaves the Assumptions section; one they accept stays there as a record that it was a default.

Set the status to **Ready** when every Definition of Ready item is met, and otherwise leave it **Draft** with the open items listed in the specification. After setting it to Ready, run the checker again; if it fails, the specification is not Ready.

## Round 3: Finish

Add or update the feature's entry in `paths.featureIndex`. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/backlog_check.py" closed` and, if it fails, stop and show what it found: something belonging to a closed issue has been edited and has to be put back first. Then show the team, as one numbered list, everything that is about to leave the working copy, with the exact text of anything that will be written to GitHub. Present it as what will happen and ask for a single yes. The team can strike a line by saying so; a line is never skipped just because nobody mentioned it.

1. **Commit**, if `finalise.commit` is true: the specification, any ADRs, the feature index, and any first-run files not yet committed. Message from `finalise.commitMessage`, with `{issue}` and `{title}` filled in.
2. **Push** of the current branch, so that links to the specification resolve.
3. **Issue**, if `finalise.updateIssue` is true: rewrite the issue's description as a summary of what was agreed, in the form below.
4. **Label**, if `finalise.readyLabel` is not empty: added when Ready, removed when a Ready specification has gone back to Draft, and created in `repo` if it does not exist.

The issue description is a summary, not a copy of the specification:

```markdown
## Narrative

## Problem

## Success criteria

## Specification

[<path to the specification>](<link to it at the pushed commit>)

Status: **Ready** or **Draft**, with the open items if Draft

## Changes to earlier work

- NNNN: what this changes in that specification, in one line

## Decisions

- [ADR NNNN](<link>): the decision in one line
```

Keep any other sections the issue already had, such as known limits, and update them if the session settled them. Requirements, scenarios, design and test procedures stay in the specification only, so there is one place to change them. Leave out the Decisions section when there are no ADRs, and the Changes to earlier work section when there are none. Only this issue is written to; an earlier issue is never edited, open or closed.

If the team strikes a line, tell them what that leaves behind before going on: without the push, the issue's link will not resolve; without the issue update, the issue and the specification say different things and nothing on GitHub shows the specification exists. Then do what was agreed, in the order above. Afterwards run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/backlog_check.py" state`, which compares every issue with its specification and the feature index, and report any FAIL it prints as something that now needs putting right. Finish by saying where the specification is, its status, and anything still open.

## Resuming

A specification that already exists for the issue is continued, never duplicated.

- **Draft:** read it, tell the team its open items, and ask only about those in the Intent round. Keep everything already agreed. Reopen something only if the team asks or the issue has since changed in a way that contradicts it.
- **Ready, issue still open:** say so and ask whether to leave it or revise it. A revision sets the status back to Draft until the Definition of Ready is met again.
- **Issue closed:** the specification is a record and is not revised. Say so, say that a change to it starts with a new issue, and stop.

## Thorough mode

Use `"mode": "thorough"` when several people are in the session, or when the feature is contentious enough that nothing should be assumed. Everything above still applies, with these differences:

- No default is applied silently. Each one becomes a proposal the team chooses or replaces, so the Assumptions section stays empty.
- The specification is agreed section by section, in the order of the table, instead of in one review. Sections may share a round when none depends on an answer not yet given. Acceptance criteria and the Definition of Ready check always get a round of their own.
- Start by asking who is in the session and which points of view they cover.
- On a first run, confirm the repository and ask before creating each document.

## Default documents

These are used only on a first run, to create documents the project does not have. Copy each one exactly as written.

### Feature template

Written to `paths.featureTemplate`.

````markdown
# NNNN: Feature title

- **Status:** Draft
- **Issue:** #N
- **Decisions:** none

## Narrative

As a <role>, I want <capability>, so that <benefit>.

## Problem

What is wrong or missing today, and for whom.

## Requirements

### Functional

- FR-1:

### Non-functional

- Performance:
- Security and privacy:
- Availability and reliability:
- Observability:

## Acceptance criteria

```gherkin
@area:<area>
Feature: <feature title>

  # FR-1
  @NNNN-01
  Scenario: <happy path>
    Given <starting state>
    When <action>
    Then <observable result>
```

## Out of scope

-

## Changes to current behaviour

None.

## Design

### Architectural decisions

-

## External dependencies

| Dependency | Available | Notes |
|------------|-----------|-------|

## Implementation plan

1.

### Phases

None.

## Testing strategy

| Scenario | Automated | How it is verified |
|----------|-----------|--------------------|

## Non-development tasks

| Task | Owner |
|------|-------|

## Assumptions

Defaults that were applied without being discussed. Overrule any of them.

-

## Open items

None.
````

### Definition of Ready

Written to `paths.definitionOfReady`.

````markdown
# Definition of Ready

A specification is Ready when someone who was not in the session could build the feature from it without having to ask a question. Every box below must be ticked; until then the specification is a Draft.

## Why it is worth building

- [ ] It names who benefits and what they will be able to do that they cannot do today
- [ ] Each success criterion is something an outsider could observe

## What will be built

- [ ] Each success criterion is covered by a requirement, and each requirement by a scenario
- [ ] Scenarios use concrete values, and at least one shows the feature refusing or failing where it can
- [ ] The nearest things deliberately left out are listed as out of scope

## How it will be built

- [ ] Choices that would be costly to reverse have been made by the team and recorded as decisions
- [ ] The team has read every assumption and accepted or overruled it
- [ ] Each scenario has a stated way of being verified

## Whether it can start

- [ ] Nothing it needs is missing: other work, access, data or content
- [ ] It fits the delivery budget, or is split into phases that each do
- [ ] Work outside the code has a named owner
- [ ] There are no open items
````

### Issue template

Written to `paths.issueTemplate`. If `finalise.readyLabel` is empty, leave the `labels` line as it is; the template never applies the ready label.

````markdown
---
name: Feature
about: Propose a feature for refinement
title: ""
labels: ""
---

## Narrative

As a <role>, I want <capability>, so that <benefit>.

## Problem

What is wrong or missing today, and for whom.

## Success criteria

How we will know this worked, in terms the business would recognise.

-

## Known limits

Anything already known that narrows the solution, and anything still undecided.

-
````

### Feature index

Written to `paths.featureIndex`.

````markdown
# Features

| No.  | Feature | Status | Issue |
|------|---------|--------|-------|
````

### ADR template

Written to `paths.adrTemplate`.

````markdown
# NNNN: Decision title

- **Status:** Proposed
- **Date:**

## Context

What forces the decision, and what constrains it.

## Options considered

1.

## Decision

What was chosen, and why.

## Consequences

What becomes easier, what becomes harder, and what has to be revisited later.
````
