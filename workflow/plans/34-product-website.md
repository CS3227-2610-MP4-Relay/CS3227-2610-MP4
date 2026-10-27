# Slice 34: Publish the product website (#34)

Goal: prepare the existing Cayman product site for checked GitHub Pages publication under [PLT-2](../specs/product/platform.md#plt-2-validate-and-publish-the-product-website).

Why: the existing landing page is stale and static-site publication has no checked delivery path.

Tier: High (CI/deployment boundary). Branch: `feat/34-product-website`, stacked on PR #69 at starting commit `1d9ceccdeab70768d32a2cd2c02040fac7510d73`; the coordinator resolves the PR base to #69's branch. Budget: one requirement, six criteria, at most 400 changed non-test `src/` lines; expected checker about 120–180 lines. Existing Django behaviour is preserved. No new runtime packages/services, custom domain, application hosting, credential management or recovery subsystem.

## Checkpoints

1. **Specs and plan** (`spec:`): `workflow/specs/product/platform.md`, relevant website/release sections of `workflow/specs/TECHNICAL-SPEC.md`, CI/Pages controls in `workflow/specs/SECURITY-SPEC.md`, and this plan. Check readback, links, `git diff --check`, builder scope. Yield before implementation; coordinator commits and supplies a fresh scope snapshot.
2. **Workflow and artifact validation** (`ci:`): `.github/workflows/ci.yml`, a narrowly bounded standard-library checker under `src/` and its tests. Add site build/check/upload and same-run gated deployment according to the technical spec. Focused red-first tests marked PLT-2 IDs cover a valid base-path artifact, missing entry/page/asset, broken base-path links, guide leakage, and workflow event/dependency/permission boundaries; each invalid fixture otherwise remains valid. Exercise failed/skipped prerequisites and PR denial through workflow structure assertions; hosted execution remains separate evidence. Validate syntax and action identities, focused tests, then full verification with `.venv`: `ruff check . && ruff format --check . && pytest` and the existing Django system check. A real Jekyll artifact must be checked through hosted read-only CI if the local environment lacks the existing build runtime; do not install tooling without authorization.
3. **Site and setup documentation** (`docs:`): coordinator owns `docs/index.md`, `docs/_config.yml` and any needed README update (outside builder scope); builder owns `docs/DeveloperGuide.md`. Update the landing page to PLT-2.1 and link to the source guides and rendered Reflections. Document validation, source/base path and operator prerequisites by linking their spec homes. Do not edit `docs/Reflections.md`. Check source and actual rendered links, read back changed sections, run focused tests and full verification on the integrated candidate.
4. **Session summary** (`log:`): coordinator records checks, usage, review findings and actual hosted state in `logs/` using the log skill; independent verifier/security review and stacked draft-PR delivery belong to the coordinator. Record each commit checkpoint before the next begins; repairs use separate focused commits and renewed checks.

## Decisions and evidence boundaries

- Reuse the existing theme and CI workflow; no `configure-pages`, manual trigger or PR publication. Official Pages actions are SHA-pinned after identity verification. See the [site architecture](../specs/TECHNICAL-SPEC.md#product-website) and [CI controls](../specs/SECURITY-SPEC.md#ci-and-dependencies).
- Build validation, actual main-run deployment and anonymous hosted verification are separate results. A green PR cannot satisfy PLT-2.6 or prove environment restrictions.
- Human authorization covers stacked branch/draft-PR delivery. Hosted Pages enablement, environment settings, merge and publication remain pending human action; no role agent changes Git/GitHub state.

## Open issues and next step

- Coordinator reports Pages API currently returns 404 and `github-pages` exists without protection rules; these are observations supplied for planning, not independently verified by the builder. Operator prerequisites remain open under [Release verification](../specs/TECHNICAL-SPEC.md#release-verification).
- Await coordinator's checkpoint-1 review/commit and new snapshot before implementing checkpoint 2. Record red-test evidence and actual diff sizes at that checkpoint. No hosted release or security-review completion is claimed.
