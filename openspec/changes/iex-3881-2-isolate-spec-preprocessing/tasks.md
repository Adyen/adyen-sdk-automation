## 1. Preprocessing in memory

- [x] 1.1 Add `SpecProcessor.Options` (downgrade, General-tag replacement, webhook-root marking) and `process(content, options)`
- [x] 1.2 Keep `process(content)` defaulting to the legacy downgrade behavior

## 2. Staging

- [x] 2.1 Make `:specs` clone only
- [x] 2.2 Register `prepareSpec<Service>` per applicable service writing `build/specs/<filename>`; point `inputSpec` at it
- [x] 2.3 Remove `ungroup<Service>` and `addWebhookExtension<Service>`
- [x] 2.4 Add `sdkAutomation.preserveOpenApiVersion` (default false) and set it in `go/build.gradle.kts`

## 3. Tests

- [x] 3.1 SpecProcessor: version preserved with 3.1 null unions intact, `x-methodName`, tag rename, webhook roots
- [x] 3.2 Conventions: staged `inputSpec` path and dependency, non-Go 3.0.0, Go 3.1.0, removeTags, webhook-only marking, source unchanged

## 4. Gate

- [x] 4.1 `./gradlew :buildSrc:test` and `python3.12 -m unittest discover -s .github/scripts` pass
- [x] 4.2 Staged specs for java, php, node, python, ruby, dotnet are byte-identical to the old pipeline output (188/188)
- [x] 4.3 Go staged specs keep `openapi: 3.1.0` and are otherwise identical to the old output (29/29)
- [x] 4.4 `git -C schema status` is clean after staging all 217 project/service pairs
- [ ] 4.5 Review and push the automation branch
