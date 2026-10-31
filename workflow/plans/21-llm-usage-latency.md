# Record LLM usage and latency (#21)

Record validated provider token counts and elapsed gateway time on existing quota rows without storing user text or changing call controls.

- **Tier/context:** High, AI gateway; human `/slice 21`, starting HEAD `3813b7cbe1135f9222151e97b17703dad27da64b`, branch `slice/21-llm-usage-latency`. Builder reads its role and AGENTS.md; no delegation or Git/GitHub writes. Coordinator owns delivery and usage reports (baseline outside the repository).
- **Confirmed scope/budget:** one requirement, PLT-3 with six criteria; at most 400 inserted plus deleted non-test/non-migration source lines; estimated whole slice 650–1,000 lines including specs/tests/docs/log. No new dependency, service, UI, export, production call or independent telemetry/cleanup subsystem. Stop for an expansion or projected overrun.
- **Why:** the gateway currently ignores provider usage and stores only quota timestamps; record bounded numeric evidence while preserving unavailable values and existing privacy, outcome and resource controls.

## Commit checkpoints

1. **Specs and plan:** update `workflow/specs/product/platform.md`, `workflow/specs/ai/llm-gateway.md`, the AI data model in `TECHNICAL-SPEC.md`, the resource control in `SECURITY-SPEC.md`, and this plan. Reuse PRODUCT-SPEC's existing PLT prefix/area registration. Read back edits, inspect diff/size and check builder scope against the coordinator's snapshot. Yield before tests/code; coordinator commits and supplies a fresh snapshot.
2. **Schema and gateway with regression tests:** add nullable metrics to `src/ai/models.py` and a migration; update `src/ai/gateway.py` result dataclasses, allowlisted usage extraction, checked test-provider metadata, reservation record IDs, monotonic timing and atomic persistence with finally release. Reuse `src/ai/fakes.py` unchanged unless necessary. Add criterion-marked cases in `src/ai/tests/test_gateway.py` and `test_transport.py`; show meaningful red failures before implementation, then focused green tests, Ruff, migration checks, scope and source-size checks. Keep behavior and tests together; yield for coordinator commit.
3. **Developer documentation and integrated evidence:** update `docs/DeveloperGuide.md`'s SoC section to link to the accounting contract and explain readings from one scope. No UI journey changes require browser tests or User Guide updates. Run `.venv` full `ruff check . && ruff format --check . && pytest` in Git Bash, Django system/migration checks, readback and scope/size checks; record actual failures separately from passing evidence. Yield for coordinator commit, independent fixed-candidate verifier/security review and authorized branch/draft PR delivery. Repairs become separate checkpoints if needed.

## Verification partitions

- PLT-3.1/3.3: both scope rows receive identical counts/timing; earlier rows stay null; deterministic monotonic elapsed excludes writes/release; simultaneous users keep distinct record IDs. Count one scope only.
- PLT-3.2: each count independently missing/null/zero/positive/maximum; just outside range, bool, string, fractional number, list/object; absent/non-object usage and unknown/nested data. Preserve inconsistent but valid provider totals without derivation. Test both wire parser and fake result validation.
- PLT-3.3/3.4: success, provider refusal, truncation/invalid envelope, invalid JSON, transport error, timeout, fake exception and not-configured after reservation; no rows/network for live-off, oversized input or refused reservation. Keep existing quota/deadline/cleanup tests passing.
- PLT-3.5: atomic metrics failure leaves both rows unavailable, propagates DatabaseError, attempts release and never repeats provider work; existing reservation/release storage failure behavior and escaped exceptions remain covered.
- PLT-3.6: adversarial unknown usage text cannot persist, return as metadata or reach logs; stale user metrics survive inactivity and disappear with existing scope cleanup at the window boundary. Use synthetic data and no live calls.

## Decisions, open issues and next step

- Minimal design: keep the existing two per-scope rows, add four nullable numeric columns, and reuse result types with optional validated usage. No outcomes/history schema or telemetry subsystem. Expected source diff about 150–250 lines, migration about 30–50, tests about 350–500, specs/plan/docs/log about 120–180; monitor total against the confirmed estimate.
- Existing ambiguity raised to coordinator: the technical AI-gateway introduction says limits are proposals pending confirmation while the gateway contract says they are implemented. Preserve that approval/status wording for now; this slice neither infers approval nor changes quota limits.
- Checkpoint 1 only: no tests or runtime edits yet. Next step is coordinator review/commit and assignment of checkpoint 2 with a fresh scope snapshot. Real-provider availability and smoke/evaluation remain outside this slice.
