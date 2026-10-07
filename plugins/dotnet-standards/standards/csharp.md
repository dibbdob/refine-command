# C#

Applies to: `**/*.cs`

Before designing or writing anything this covers, load the `dotnet-standards:csharp-coding-standards` skill. It holds the detail and the examples.

**Check the documentation; do not rely on memory.** Look each of these up with the `microsoft-learn` connector of the dotnet-standards plugin before the design or the code depends on it, and follow what the current documentation says over what you remember:

- every type or member of .NET or a Microsoft library that the change uses and the code around it does not already use
- every fact about how .NET or a Microsoft product behaves that the design rests on, such as a limit, a default, a threshold or an ordering

Record what was looked up. The design, or the first task if there is no design, ends with a line `Documentation checked:` followed by each thing looked up and the page it was found on, or `Documentation checked: nothing new relied on.` if the change uses nothing of either kind.

| No. | Rule | Why |
|-----|------|-----|
| S-CS-1 | A type that carries data is a `record` with `init`-only properties. A mutable class needs a stated reason. | Data that cannot change after it is made cannot be changed by mistake |
| S-CS-2 | A value with a meaning of its own, such as an identifier, an amount or a quantity, is a `readonly record struct`, not a bare `string`, `Guid` or number, and converts to and from the bare type only explicitly. | The compiler then refuses one kind of value where another is meant |
| S-CS-3 | Nullable reference types are enabled and no nullable warning is suppressed or left standing. | A missing value is caught at build time |
| S-CS-4 | Every method that does input or output is `async`, takes a `CancellationToken`, and passes it on. | Work can be stopped when the caller gives up |
| S-CS-5 | Asynchronous code is never blocked on with `.Result`, `.Wait()` or `.GetAwaiter().GetResult()`. | Blocking causes deadlocks and starves the thread pool |
| S-CS-6 | An outcome the business expects, such as a refused order, is returned as a result type that belongs to the operation. Exceptions are for faults. | The caller has to deal with the outcome, and the compiler shows where |
| S-CS-7 | A method takes the least specific collection type it can use and never returns a collection its caller can change. | Callers stay free and internal state stays internal |
| S-CS-8 | Behaviour is shared by composition. Application code has no abstract base class and no inheritance more than one level deep, except where a framework requires it. | Deep hierarchies are hard to change and to test |
| S-CS-9 | One object is turned into another by an explicit method. No library that maps by reflection, such as AutoMapper or Mapster, is used. | A broken mapping fails the build, not production |
