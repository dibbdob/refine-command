# dotnet-standards

C# and .NET engineering standards for a project whose features are specified and built by an agent, with either the [backlog](https://github.com/dibbdob/refine-command) plugin or OpenSpec through the [openspec-issues](https://github.com/dibbdob/openspec-issues) plugin.

Both supply a process and no opinion on any stack. This plugin supplies the opinion for one stack, in the form both read: one file for each topic in `docs/standards`.

## What it holds

| Part | What it is |
|------|------------|
| `standards/` | One file for each topic: what it applies to and its numbered rules |
| `skills/` | One skill for each topic, with the detail and worked examples behind the rules |
| `.mcp.json` | The Microsoft Learn connector, for looking up the language, the framework and Microsoft libraries in the official documentation |
| `commands/setup.md` | `/dotnet-standards:setup`, which adds the standards to a project |

| Topic | Rules | Skill |
|-------|-------|-------|
| C# | S-CS-1 to 9 | `csharp-coding-standards` |
| Public API | S-API-1 to 6 | `csharp-api-design` |
| Configuration | S-CFG-1 to 5 | `microsoft-extensions-configuration` |
| Dependency injection | S-DI-1 to 6 | `microsoft-extensions-dependency-injection` |
| Packages | S-PKG-1 to 5 | `package-management` |
| Integration tests | S-TEST-1 to 5 | `testcontainers` |

## How it joins the backlog plugin

With OpenSpec the same files are read through the project context that `/issue:setup` adds: the standards covering the files a change touches are read, the skills they name are loaded, and the design ends with the rules it relied on. OpenSpec has nowhere to register the checks, so setup lists the ones that pass for the project's CI.

With backlog:

1. `/dotnet-standards:setup` copies the topics that fit into the project's `docs/standards`, with each topic's paths narrowed to the solution, says which rules contradict what the project does on purpose, and offers the build, format and vulnerability checks that pass today for `implement.verify`.
2. `/backlog:refine` lists the topics that cover the code an issue touches, reads them, designs to them and cites the rules it relied on, such as `Standards applied: S-CS-4, S-DI-1.`
3. Each topic tells the reader to load its skill first, so the detail is read only when that topic applies. Four of them also send questions the rules and skill leave open to the Microsoft Learn connector, so they are answered from the documentation and not from memory.
4. `/backlog:implement` runs the checks and names every topic that covers a changed file.

Once copied, the standards belong to the project. The team edits them, and setup never overwrites one.

## Everything shipped is referenced

A skill or a connector is shipped only if a standard sends the reader to it, and no standard names one that is absent. A skill is named as Claude Code offers it, by its folder. This is checked:

```bash
python3 scripts/check_references.py
```

```bash
python3 -m unittest discover -s tests
```
