# Packages

Applies to: `**/*.csproj`, `Directory.Packages.props`, `Directory.Build.props`, `NuGet.config`

Before designing or writing anything this covers, load the `dotnet-standards:package-management` skill. It holds the detail and the examples.

**Check the documentation; do not rely on memory.** Look each of these up with the `microsoft-learn` connector of the dotnet-standards plugin before the design or the code depends on it, and follow what the current documentation says over what you remember:

- every type or member of .NET or a Microsoft library that the change uses and the code around it does not already use
- every fact about how .NET or a Microsoft product behaves that the design rests on, such as a limit, a default, a threshold or an ordering

Record what was looked up. The design, or the first task if there is no design, ends with a line `Documentation checked:` followed by each thing looked up and the page it was found on, or `Documentation checked: nothing new relied on.` if the change uses nothing of either kind.

| No. | Rule | Why |
|-----|------|-----|
| S-PKG-1 | A package is added or removed with the `dotnet` command line, never by editing a project file by hand. | The tool checks that the package exists and resolves its dependencies |
| S-PKG-2 | Versions are held centrally in `Directory.Packages.props`. No project file carries a version. | One version of each package across the solution |
| S-PKG-3 | Packages released together share one version variable. | They cannot drift apart |
| S-PKG-4 | A `VersionOverride` carries a comment saying why and when it can go. | An exception that explains itself can be removed |
| S-PKG-5 | No package with a known vulnerability is added, and none is left once reported by `dotnet list package --vulnerable`. | |
