# Integration tests

Applies to: `tests/**/*.cs`

Covers tests of anything that leaves the process: a database, a cache, a queue. Before designing or writing anything this covers, load the `testcontainers-integration-tests` skill of the dotnet-standards plugin. It holds the detail and the examples. Its examples use xUnit; follow the test framework the project already uses.

| No. | Rule | Why |
|-----|------|-----|
| S-TEST-1 | Behaviour that belongs to a dependency, such as a query, a constraint, a transaction or a lock, is tested against the real thing in a container, never a mock or an in-memory substitute. | A mock proves the code calls the mock |
| S-TEST-2 | A container's port is assigned at random and the test waits until the service answers before it starts. | Tests run side by side and do not start early |
| S-TEST-3 | Every test starts from known data: a fresh container, or a reset of the data between tests. | No test depends on the one before it |
| S-TEST-4 | A container is shared within a test class or collection where that is safe, and always disposed. | Speed without leftovers |
| S-TEST-5 | Database migrations are run against the real database engine as part of the suite. | A migration that fails is found before release |
