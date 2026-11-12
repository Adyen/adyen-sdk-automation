## Context

The engine comes from the buildSrc classpath; CI copies `<project>/gradle.properties` into buildSrc,
so the Go pin is what CI generates with. Raw output depends on `make fmt` (goimports) to compile.
`tests/compat` (increment 1) freezes wire behavior such as W1 and nullable absent/null/value states.

## Goals / Non-Goals

**Goals:** a v7 engine that generates compiling, behavior-compatible Go from 3.1 specs; templates
kept close to Adyen's current client shape.

**Non-Goals:** regenerating production services (increment 5); pointer-to-map rewrite; enum
performance work; webhook handler generation (increment 6).

## Decisions

- **7.11.0 first.** It already runs for other projects, so engine bugs are known. A newer 7.x is
  considered only if 7.11.0 fails the gate. Alternative rejected: latest 7.x straight away (two
  moving parts at once).
- **Port, do not replace, templates.** Diff upstream `go` templates 6.5.0 → 7.11.0 and apply only
  changes needed for 3.1, unions, and nullable handling. Alternative rejected: adopt upstream
  templates wholesale (changes client API and naming).
- **Fixture-first.** Small purpose-built specs isolate each construct; the real IEX-3881 models
  (Management, Balance Platform) prove the end-to-end case.
- **Enum prefixing only on collision**, so existing exported constant names stay stable.
  Open: whether the collision check can live in the template or needs a generator option
  (`enumClassPrefix` prefixes all enums, which is a breaking change).
- **Decoding strictness matches v21.** If v7 rejects unknown fields or enum values that v21 accepts,
  restore the v21 behavior; the HTTP contract fixtures assert it.

## Risks / Trade-offs

- [v7 changes default handling (W1)] → JSON fixtures fail; decide per case, record in the ledger.
- [Templates and generator drift apart] → keep template and generator revisions in the same PR pair.
- [goimports version differences] → pin goimports v0.41.0 in the fixture task, as CI does.

## Open Questions

- Does generated code need a minimum Go version above 1.23?
