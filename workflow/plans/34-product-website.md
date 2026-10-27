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
- Checkpoint 1 committed as `545bee93a44cf8dc09529d325a99f807e0f059ee`. Await coordinator's checkpoint-2 commit and new snapshot before the documentation checkpoint. No hosted release or security-review completion is claimed.

## Checkpoint 2 evidence

Builder trigger: coordinator assignment after checkpoint 1, using the clean `relay-34-builder-implementation.json` scope snapshot; session metadata reports `gpt-6.1-sol`, effort `medium`. Inputs: PLT-2, site/release architecture, CI security controls, existing CI/configuration and source landing page. No delegation or Git/GitHub mutations.

- Red: `pytest src/relay_tests/test_site.py -q` initially could not collect because the checker module did not exist. With its API scaffold returning no errors, the meaningful red run was **19 failed, 2 passed**: absent link/asset/exclusion checks, missing CLI failure and missing workflow jobs. The two valid-artifact cases passed; no manufactured setup failures were used as feature evidence.
- Green: `pytest src/relay_tests/test_site.py src/relay_tests/test_ci.py -q` → **24 passed**; `ruff check .` → passed; `ruff format --check src/check_site.py src/relay_tests/test_site.py` → passed; `python src/manage.py check --settings=relay.settings.test` → no issues. Import ordering and one long test decorator required formatting repairs before green.
- Tests use synthetic artifacts for valid/invalid pages, assets, repository base paths, same-origin links, relative/encoded URLs, excluded guides and CLI status. Workflow tests inspect event/gate/permission/action structure only; they do not execute Actions conditions or deployment. Official pinned Jekyll action inputs and entrypoint were inspected: source/destination are supported and no baseurl override is applied.
- Size: checker **139** new non-test `src/` lines (within 400); regression tests **152** new lines; workflow **42 additions, 1 deletion**; PLT-2.6 classification correction **1 addition, 1 deletion**, authorized by coordinator. No requirement was added by that correction: hosted verification can be automated after operator setup and is pending, rather than inherently manual.
- `git diff --check` and snapshot-based builder scope check passed. Full pytest and integrated formatting verification are deferred to the final documentation candidate by coordinator instruction; no local database or real Jekyll build was attempted. Hosted workflow parsing, real Jekyll build, checked artifact upload and eventual authorized publication remain separate pending evidence.

Next: coordinator commits the coherent workflow/checker/tests checkpoint, then supplies a fresh snapshot for the builder's Developer Guide update while owning the landing page/configuration/README edits. Hosted read-only CI must validate the actual site before freezing independent review.
