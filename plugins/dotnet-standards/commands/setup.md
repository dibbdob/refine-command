---
description: Add the C# and .NET standards to this project, for the commands that specify and build features to follow
disable-model-invocation: true
---

# Set up the .NET standards

Add this plugin's standards to the project, fitted to where its code sits. Whatever specifies and builds features here reads them from then on: the backlog plugin's refine and implement commands, or OpenSpec set up with the openspec-issues plugin. Once added, the files are the project's own: the team edits them, and this command never overwrites one.

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

1. **Find the standards folder and what will read it.**
   - If `.claude/refine.json` exists, the backlog plugin is set up. The folder is its `paths.standardsDir`, or `docs/standards` if that is absent.
   - Otherwise the folder is `docs/standards`. If `openspec/config.yaml` mentions `docs/standards`, OpenSpec is set up to read it.
   - If neither holds, say that the standards will be added but nothing here is set up to read them yet, name the two ways to do that (`/backlog:refine`, or `/issue:setup` from the openspec-issues plugin), and carry on.
2. **Look at the solution.** Find the solution and project files, which projects are tests, whether versions are held in `Directory.Packages.props`, and which of the conditions in the table hold. Read; do not build.
3. **Work out what each topic applies to.** The files arrive with general patterns such as `**/*.cs`. Narrow each to this solution: source folders for the code topics, test projects for integration tests, and only the projects that are published for the public API. A pattern is written in backticks on the `Applies to:` line; `**` crosses folders and `*` does not.
4. **Show the plan and ask once.** One numbered list: each topic to be added with the patterns it will apply to, each topic left out and why, each already present and so left alone, and the checks from the next section. A line can be struck by saying so.
5. **Add what was agreed.** Copy each file from `${CLAUDE_PLUGIN_ROOT}/standards/` into the standards folder and change only its `Applies to:` line. Change no rule and no rule number. Where the project's packages are not managed centrally, say that S-PKG-2 and S-PKG-3 do not yet hold. Where a rule contradicts something the project does on purpose, say which rule and what it contradicts. Leave all of these for the team to adopt, reword or strike; the files are theirs to edit.
6. **Report** the files added and the rules now in force, by number. Change nothing else and commit nothing; the user commits when ready.

## Checks

Three commands check what a tool can check. Run each on the project as it stands and offer only those that pass:

| Check | Command | Fails when |
|-------|---------|------------|
| Build | `dotnet build --no-incremental -warnaserror "-warnnotaserror:NU1901,NU1902,NU1903,NU1904"` | The compiler or an analyser warns about anything. Known-vulnerability warnings are left to the third check |
| Format | `dotnet format --verify-no-changes` | Any file is not formatted as the project's settings say |
| Vulnerabilities | `dotnet restore --force -p:NuGetAudit=true -p:NuGetAuditMode=all "-warnaserror:NU1901,NU1902,NU1903,NU1904"` | Any package, direct or transitive, has a known vulnerability |

Do not use `dotnet list package --vulnerable` as a check. It reports vulnerabilities but exits successfully whatever it finds, so it can never fail.

A check that fails today is not added. Say what it found and leave it to the team, because adding it would stop every feature until it is fixed.

Where the checks go depends on what is set up:

- **backlog**: its implement command runs the commands in `implement.verify` of `.claude/refine.json`. Add those agreed, without disturbing what is already there, the build and vulnerability checks with `"when": ["**/*.cs", "**/*.csproj", "Directory.Packages.props"]` and the format check with `"when": ["**/*.cs"]`.
- **OpenSpec**: it has nowhere to register a check. List the passing commands in the report and say that the place to run them is the project's CI.
