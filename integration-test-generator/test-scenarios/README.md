# Integration test scenarios

The `test-scenarios` directory contains the language-agnostic scenarios used
to generate SDK integration tests.

## Structure

Scenarios are grouped by API, with one Gherkin feature file per service:

```text
integration-test-generator/
├── scenario-generator/
├── test-generator/
└── test-scenarios/
    ├── README.md
    ├── checkout/
    │   ├── donations.feature
    │   ├── modifications.feature
    │   └── payments.feature
    ├── legal-entity-management/
    │   └── legal-entities.feature
    └── session-authentication/
        └── sessions.feature
```

Add new APIs as top-level directories and new services as `.feature` files
within `test-scenarios`, for example
`checkout/donations.feature`. API and service names use lowercase kebab-case.

## Conventions

- Use `@integration`, API, and service tags so scenarios can be selected
  independently of their file path.
- Describe public API behavior rather than SDK classes, methods, exceptions,
  or test-framework details.
- Put request payloads in JSON doc strings. Their shape must match the API
  request schema.
- Introduce runtime values in `Given` steps and interpolate them in payloads
  with `${name}`. Generators are responsible for mapping these values to the
  target language.
- Keep assertions narrow and stable. Verify only the response fields needed to
  prove the behavior.
- Never include credentials or real resource identifiers. Scenarios run
  against the TEST environment with credentials supplied at runtime.
