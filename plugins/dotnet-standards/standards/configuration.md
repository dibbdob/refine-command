# Configuration

Applies to: `**/*.cs`, `**/appsettings*.json`

Before designing or writing anything this covers, load the `dotnet-standards:microsoft-extensions-configuration` skill. It holds the detail and the examples.

**Check the documentation; do not rely on memory.** Look each of these up with the `microsoft-learn` connector of the dotnet-standards plugin before the design or the code depends on it, and follow what the current documentation says over what you remember:

- every type or member of .NET or a Microsoft library that the change uses and the code around it does not already use
- every fact about how .NET or a Microsoft product behaves that the design rests on, such as a limit, a default, a threshold or an ordering

Record what was looked up. The design, or the first task if there is no design, ends with a line `Documentation checked:` followed by each thing looked up and the page it was found on, or `Documentation checked: nothing new relied on.` if the change uses nothing of either kind.

| No. | Rule | Why |
|-----|------|-----|
| S-CFG-1 | Settings are read through a strongly typed options class bound to one named section. Nothing outside start-up reads `IConfiguration` by key. | Each setting has one place, one type and one name |
| S-CFG-2 | Every options class is validated, and registered with `ValidateOnStart()`. | A bad setting stops the service starting, not a request an hour later |
| S-CFG-3 | A rule about one setting is a data annotation. A rule across settings, or one needing another service, is an `IValidateOptions<T>`. | Each kind of rule sits where it can be tested |
| S-CFG-4 | A validator returns `ValidateOptionsResult.Fail` with every failure it found. It does not throw, and no constructor validates settings. | The operator sees all that is wrong in one start |
| S-CFG-5 | A singleton or background service that needs current settings takes `IOptionsMonitor<T>`. Scoped code takes `IOptionsSnapshot<T>` or `IOptions<T>`. | The lifetime of the settings matches the lifetime of the reader |
