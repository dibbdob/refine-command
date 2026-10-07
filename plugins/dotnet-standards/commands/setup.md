---
description: Add the C# and .NET standards to this project so that refine and implement follow them
disable-model-invocation: true
---

# Set up the .NET standards

Add this plugin's standards to the project, fitted to where its code sits. The backlog plugin's refine and implement commands read them from then on. Once added, the files are the project's own: the team edits them, and this command never overwrites one.

## What is on offer

`${CLAUDE_PLUGIN_ROOT}/standards/` holds one file for each topic. Each says what it applies to, names the skill of this plugin that holds its detail, and lists its rules.

| File | Topic | Add it when |
|------|-------|-------------|
| `csharp.md` | C# | Always |
| `dependency-injection.md` | Dependency injection | The solution uses `Microsoft.Extensions.DependencyInjection` |
| `configuration.md` | Configuration | The solution reads settings through `Microsoft.Extensions.Configuration` |
| `packages.md` | Packages | Always |
| `api.md` | Public API | The solution publishes a package, or another system reads what it writes |
| `integration-tests.md` | Integration tests | A test needs a database, a cache or a queue |

## Steps

1. **Find the standards folder.** Read `.claude/refine.json` at the project root. The folder is `paths.standardsDir`, or `docs/standards` if that is absent. If there is no `.claude/refine.json`, say that the backlog plugin has not been set up here, that the standards will be added but nothing will read them until it is, and carry on.
2. **Look at the solution.** Find the solution and project files, which projects are tests, whether versions are held in `Directory.Packages.props`, and which of the conditions in the table hold. Read; do not build.
3. **Work out what each topic applies to.** The files arrive with general patterns such as `**/*.cs`. Narrow each to this solution: source folders for the code topics, test projects for integration tests, and only the projects that are published for the public API. A pattern is written in backticks on the `Applies to:` line; `**` crosses folders and `*` does not.
4. **Show the plan and ask once.** One numbered list: each topic to be added with the patterns it will apply to, each topic left out and why, each already present and so left alone, and the checks from the next section. A line can be struck by saying so.
5. **Add what was agreed.** Copy each file from `${CLAUDE_PLUGIN_ROOT}/standards/` into the standards folder and change only its `Applies to:` line. Change no rule and no rule number. Where the project's packages are not managed centrally, say that S-PKG-2 and S-PKG-3 do not yet hold, and leave them for the team to adopt or strike.
6. **Report** the files added and the rules now in force, by number. Change nothing else and commit nothing; the user commits when ready.

## Checks

The implement command runs the commands in `implement.verify` of `.claude/refine.json`. Offer these, each only if it passes on the project as it stands, and add those agreed without disturbing what is already there:

```json
{ "run": "dotnet build --no-incremental -warnaserror", "when": ["**/*.cs", "**/*.csproj"] }
{ "run": "dotnet format --verify-no-changes", "when": ["**/*.cs"] }
{ "run": "dotnet list package --vulnerable --include-transitive", "when": ["**/*.csproj", "Directory.Packages.props"] }
```

A check that fails today is not added. Say what it found and leave it to the team, because adding it would stop every feature until it is fixed.
