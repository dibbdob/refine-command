# Configuration

Applies to: `**/*.cs`, `**/appsettings*.json`

Before designing or writing anything this covers, load the `microsoft-extensions-configuration` skill of the dotnet-standards plugin. It holds the detail and the examples.

| No. | Rule | Why |
|-----|------|-----|
| S-CFG-1 | Settings are read through a strongly typed options class bound to one named section. Nothing outside start-up reads `IConfiguration` by key. | Each setting has one place, one type and one name |
| S-CFG-2 | Every options class is validated, and registered with `ValidateOnStart()`. | A bad setting stops the service starting, not a request an hour later |
| S-CFG-3 | A rule about one setting is a data annotation. A rule across settings, or one needing another service, is an `IValidateOptions<T>`. | Each kind of rule sits where it can be tested |
| S-CFG-4 | A validator returns `ValidateOptionsResult.Fail` with every failure it found. It does not throw, and no constructor validates settings. | The operator sees all that is wrong in one start |
| S-CFG-5 | A singleton or background service that needs current settings takes `IOptionsMonitor<T>`. Scoped code takes `IOptionsSnapshot<T>` or `IOptions<T>`. | The lifetime of the settings matches the lifetime of the reader |
