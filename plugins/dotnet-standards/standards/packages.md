# Packages

Applies to: `**/*.csproj`, `Directory.Packages.props`, `Directory.Build.props`, `NuGet.config`

Before designing or writing anything this covers, load the `package-management` skill of the dotnet-standards plugin. It holds the detail and the examples.

| No. | Rule | Why |
|-----|------|-----|
| S-PKG-1 | A package is added or removed with the `dotnet` command line, never by editing a project file by hand. | The tool checks that the package exists and resolves its dependencies |
| S-PKG-2 | Versions are held centrally in `Directory.Packages.props`. No project file carries a version. | One version of each package across the solution |
| S-PKG-3 | Packages released together share one version variable. | They cannot drift apart |
| S-PKG-4 | A `VersionOverride` carries a comment saying why and when it can go. | An exception that explains itself can be removed |
| S-PKG-5 | No package with a known vulnerability is added, and none is left once reported by `dotnet list package --vulnerable`. | |
