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
    "closeIssue": true
  }
}
```

A value that is absent takes the value shown above; `paths.featuresDir` defaults to `docs/specs`. Pass `repo` to every `gh` call with `--repo`. If the file or `repo` is missing, say that the project has not been refined yet and stop.

## Before building

Do these checks silently and report only what stops the work.

1. **Find the specification**: the file in `paths.featuresDir` whose name starts with the issue number padded to four digits.
   - None: say so, point to the refine command, and stop.
   - Status is Draft: list its open items, say it has to be Ready first, and stop.
   - Status is Ready: carry on.
2. **Read it all**, with every ADR it links and the project's `CLAUDE.md` if there is one.
3. **Check the issue** in `repo`. If it is closed, say so and ask whether to carry on.
4. **Check the working copy.** If it has uncommitted changes that are not part of this feature, say what they are and ask whether to carry on; they will not be committed.
5. **Check the starting point.** If something the specification depends on is missing, or the code no longer matches what the specification assumes, show the difference and stop.

## Build

Follow the specification's implementation plan in its order.

1. **Tests first.** Turn each scenario into one automated test, named after the scenario, using the test setup and the commands the testing strategy gives. Run the suite and confirm the new tests fail for the reason expected. A test that passes before the code changes is worth one line saying why.
2. **Make them pass** with the design the specification describes: its names, its messages, its layout. Write the least code that satisfies the scenarios, in the style of the code around it.
3. **Do the non-development tasks that are files in the repository**, such as documentation. Leave the rest, such as accounts or infrastructure, and list them for their owner.
4. **Verify.** Run the whole suite, not only the new tests. Carry out any manual procedure the testing strategy gives and record what happened.

If the specification has phases, build the first phase that is not yet built, and say which.

Three things are not done here:

- **Nothing beyond the specification.** Anything in its out-of-scope list stays out. An improvement noticed along the way is mentioned at the end, not built.
- **No bending the tests.** Never weaken, skip or delete a test to get a green run, and never change an existing test unless the specification says to.
- **No editing the specification.** If it turns out to be wrong, contradicts itself or the code, or asks for something that cannot be done, stop. Show the two things that cannot both hold and say that the fix is a revision through the refine command. Leave what has been built in the working copy, uncommitted.

## Finish

If any test fails or any scenario could not be verified, say so with the output, and offer nothing below.

Otherwise report in this order: what was built, the result of the suite as numbers, anything left for someone else, and anything noticed but not built. Then show, as one numbered list, what is about to leave the working copy, and ask for a single yes. A line can be struck by saying so.

1. **Commit**, if `implement.commit` is true: the files changed for this feature and no others. Message from `implement.commitMessage`, with `{issue}` and `{title}` filled in.
2. **Push** of the current branch.
3. **Close the issue** as completed, if `implement.closeIssue` is true and every phase of the specification is now built. If phases remain, leave it open and say which are left.

Then do what was agreed, in that order, and finish by saying what is on the remote and the state of the issue.
