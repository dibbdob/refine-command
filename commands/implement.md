---
description: Build the feature a Ready specification describes, test-first, and close its GitHub issue
argument-hint: <issue-number>
disable-model-invocation: true
---

# Implement

Build what the specification for GitHub issue #$ARGUMENTS describes. If no issue number was given, ask for one.

The specification is the authority. It was agreed in refinement, so this command asks nothing about what to build. It builds, verifies, and then asks once before anything leaves the working copy.

## Configuration

Read `.claude/refine.json` at the project root. This command uses `repo` and `paths.featuresDir` as the refine command does, and its own section:

```json
{
  "implement": {
    "commit": true,
    "commitMessage": "#{issue} Implement: {title}",
    "closeIssue": true,
    "testPaths": []
  }
}
```

A value that is absent takes the value shown above; `paths.featuresDir` defaults to `docs/specs`. Pass `repo` to every `gh` call with `--repo`. If the file or `repo` is missing, say that the project has not been refined yet and stop.

`implement.testPaths` is a list of glob patterns naming the project's test files, for the checker below. Leave it empty to use the common conventions (`tests/`, `test_*`, `*.test.*`, `*_test.*`, `spec/`).

## The checker

`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/backlog_check.py"`, run from the project root, makes the checks that need no judgement. It prints one line for each FAIL and each WARN and ends with a count. A FAIL stops the work at the point described below. A WARN is shown to the user word for word in the finish report. If the checker cannot run, say so in the report and do not describe its checks as passed.

## Before building

Do these checks silently and report only what stops the work.

1. **Find the specification**: the file in `paths.featuresDir` whose name starts with the issue number padded to four digits.
   - None: say so, point to the refine command, and stop.
   - Status is Draft: list its open items, say it has to be Ready first, and stop.
   - Status is Ready: run the checker with `spec <issue-number>`. If it fails, show its output, say the specification needs revising through the refine command, and stop. A specification written before scenarios had IDs fails here for that reason.
2. **Read it all**, with every ADR it links and the project's `CLAUDE.md` if there is one.
3. **Check the issue** in `repo`. If it is closed, say so and ask whether to carry on.
4. **Check the working copy.** If it has uncommitted changes that are not part of this feature, say what they are and ask whether to carry on; they will not be committed.
5. **Check the starting point.** If something the specification depends on is missing, or the code no longer matches what the specification assumes, show the difference and stop.

## Build

Follow the specification's implementation plan in its order.

1. **Tests first.** Turn each scenario into one automated test, named after the scenario, using the test setup and the commands the testing strategy gives. Where a scenario has an ID, the test carries it, written exactly as in the specification, in the test's name or in a comment on the line above it, so that a text search for the ID finds the test. Then run the suite through the checker, with `red <issue-number> -- <the test command>`, before writing any code. It confirms every scenario has its test and that the suite fails, and records that run. If it fails because the suite already passes, the new tests prove nothing as written: find out why before going on. Confirm the new tests fail for the reason expected. A test that passes before the code changes is worth one line saying why.
2. **Make them pass** with the design the specification describes: its names, its messages, its layout. Write the least code that satisfies the scenarios, in the style of the code around it.
3. **Do the non-development tasks that are files in the repository**, such as documentation. Leave the rest, such as accounts or infrastructure, and list them for their owner.
4. **Verify.** Run the whole suite, not only the new tests, through the checker, with `green <issue-number> -- <the test command>`. It fails if the suite fails or if no failing run was recorded first, and it warns about any test that was edited after it was seen to fail. Carry out any manual procedure the testing strategy gives and record what happened. Then run the checker with `tests <issue-number>`. It fails if a scenario of this specification has no test carrying its ID, if a test carries an ID no specification defines, or if the test for any other scenario was changed or removed without the specification listing it under Changes to earlier specifications.

If the specification has phases, build the first phase that is not yet built, and say which.

Three things are not done here:

- **Nothing beyond the specification.** Anything in its out-of-scope list stays out. An improvement noticed along the way is mentioned at the end, not built.
- **No bending the tests.** Never weaken, skip or delete a test to get a green run, and never change an existing test unless the specification says to.
- **No editing the specification.** If it turns out to be wrong, contradicts itself or the code, or asks for something that cannot be done, stop. Show the two things that cannot both hold and say that the fix is a revision through the refine command. Leave what has been built in the working copy, uncommitted.

## Finish

If any test fails, any scenario could not be verified, or the checker reports a FAIL, say so with the output, and offer nothing below. A checker failure is fixed in the code or the tests, never by editing the specification to match.

Before the list, run the checker with `closed`. If it fails, something belonging to a closed issue has been edited: show what it found and offer nothing below.

Otherwise report in this order: what was built, the result of the suite as numbers, anything left for someone else, and anything noticed but not built. Then show, as one numbered list, what is about to leave the working copy, and ask for a single yes. A line can be struck by saying so.

1. **Commit**, if `implement.commit` is true: the files changed for this feature and no others. Message from `implement.commitMessage`, with `{issue}` and `{title}` filled in.
2. **Push** of the current branch.
3. **Close the issue** as completed, if `implement.closeIssue` is true and every phase of the specification is now built. If phases remain, leave it open and say which are left.

Then do what was agreed, in that order. Afterwards run the checker with `state`, which compares every issue with its specification and the feature index, and report any FAIL it prints as something that now needs putting right. Finish by saying what is on the remote and the state of the issue.
