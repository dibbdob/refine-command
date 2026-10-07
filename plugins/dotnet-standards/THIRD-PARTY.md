# Third-party content

The six folders under `skills/` are copied without change from [Aaronontheweb/dotnet-skills](https://github.com/Aaronontheweb/dotnet-skills), release v1.6.0, commit `784ada78c1821186a57f64108878cc6b0e1d2126`.

| Folder | Name in the skill's own header |
|--------|-------|
| `skills/csharp-coding-standards` | `modern-csharp-coding-standards` |
| `skills/csharp-api-design` | `api-design` |
| `skills/microsoft-extensions-configuration` | `microsoft-extensions-configuration` |
| `skills/microsoft-extensions-dependency-injection` | `dependency-injection-patterns` |
| `skills/package-management` | `package-management` |
| `skills/testcontainers` | `testcontainers-integration-tests` |

They mention other skills of that collection, such as `serialization`, `slopwatch` and `akka-hosting-actor-patterns`. Those are not included here, because no standard refers to them.

To move to a later release, replace each folder with the one from that release, change the release and commit above, and run `python3 scripts/check_references.py`. Read what changed before you do: the standards were written against this release.

## Licence

MIT License

Copyright (c) 2025 Aaron Stannard <https://aaronstannard.com/>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
