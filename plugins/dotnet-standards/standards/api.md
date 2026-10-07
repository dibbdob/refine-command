# Public API

Applies to: `**/*.cs`

Covers types and members that code outside the solution can call, and anything written to a wire or a store that another version will read. Before designing or writing anything this covers, load the `dotnet-standards:csharp-api-design` skill. It holds the detail and the examples.

| No. | Rule | Why |
|-----|------|-----|
| S-API-1 | A public member is never removed or renamed, and its signature and behaviour never change, outside a major version. New behaviour is added beside the old. | Callers built against the old version keep working |
| S-API-2 | A public member that is to go is first marked `[Obsolete]` with a message naming its replacement, and stays for at least one minor version. | Callers get a warning and time to move |
| S-API-3 | A type is `internal` unless something outside the solution has to use it, and a class is `sealed` unless it was designed to be inherited. | What was never public never has to be kept |
| S-API-4 | The public surface is recorded by an API approval test, and a change to the approved file is reviewed as a change to the API. | A breaking change cannot go in unnoticed |
| S-API-5 | A new version reads everything the previous version wrote. A new wire or stored format is read for one release before anything writes it. | Old and new versions run side by side during a rollout |
| S-API-6 | Nothing serialised depends on a type name or on polymorphic type discovery. | Renaming a class must not break stored data |
