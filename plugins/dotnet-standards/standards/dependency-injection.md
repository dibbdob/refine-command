# Dependency injection

Applies to: `**/*.cs`

Before designing or writing anything this covers, load the `dependency-injection-patterns` skill of the dotnet-standards plugin. It holds the detail and the examples.

| No. | Rule | Why |
|-----|------|-----|
| S-DI-1 | Services are registered in `IServiceCollection` extension methods, one for each feature, named `Add{Feature}Services` and returning the collection. `Program.cs` only calls them. | Start-up stays readable and tests reuse the same registrations |
| S-DI-2 | The extension method sits in the same folder as the services it registers. | A registration is found beside what it registers |
| S-DI-3 | A service is a singleton only if it holds no state for a request and is safe on many threads. Anything that uses a database context is scoped. | The lifetime follows the state |
| S-DI-4 | A singleton never takes a scoped service in its constructor. | The scoped service would otherwise live, and be shared, for ever |
| S-DI-5 | Background work creates its own scope for each unit of work and resolves scoped services from it. | There is no request to supply one |
| S-DI-6 | Tests build their services with the production extension methods and replace only what they must. | The test runs what production runs |
