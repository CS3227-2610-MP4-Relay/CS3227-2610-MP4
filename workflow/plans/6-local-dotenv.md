# Local dotenv configuration follow-up (#6)

Load existing local configuration from optional repository-root `.env` without exposing the developer's file or changing test/production configuration.

- **Trigger/tier:** human requested reading the existing SoC key from `.env`; High configuration/credential boundary. Starting HEAD `e7305d8edbde7b53dbd8f5ca6edc9783c7ce2711`; continue authorized branch/draft PR #94 delivery as a distinct follow-up to the completed adapter slice. Preserve the completed adapter plan.
- **Scope/budget:** standard-library local-settings loader, isolated synthetic tests/probes and setup docs only; no dependency, service, credential, production dotenv loading or gateway behaviour change. One requirement, PLT-1 (criteria 1.4/1.5); expected at most 120 runtime changed lines and roughly 200–350 total follow-up lines. README and `.env.example` are outside builder scope; do not edit them. Stop if scope/dependency/budget expansion becomes necessary.
- **Why:** local settings currently ignore the user's existing file. The [configuration contract](../specs/TECHNICAL-SPEC.md#configuration) owns supported syntax, names, precedence, safe failures and environment isolation.

## Commit checkpoints

1. **Specs/plan only:** update technical configuration and narrow PLT-1.4/1.5 wording, write this plan, read back, check diff/scope against `%TEMP%/relay-dotenv-spec.json`, then yield for coordinator commit and fresh snapshot. No actual dotenv reads or startup probes.
2. **One coherent implementation/test/setup unit:** first isolate existing `settings_probe.py`, `database_destination_probe.py` and `wsgi_probe.py` before any local auto-loading. Patch a Python path constant to synthetic temporary locations before importing local settings, preserving isolated `-I` WSGI startup without `PYTHONPATH`; add no runtime path toggle. Add tests under existing configuration coverage and demonstrate focused missing-behaviour failures. Implement a small loader under `src/relay/settings/` and invoke it only from `local.py`; update Developer Guide setup and SoC instructions, linking to the contract. Run focused checks and full High-tier verification with fixed test settings and synthetic probe inputs only. Yield for coordinator commit, final-head CI, independent verifier/security review and session log. Never run default-local manage.py checks against the real root file.

## Verification partitions

- Missing file; blank/comments; whitespace; optional export; quoted/unquoted literal values including `#`, `$` and backslashes; empty file values; duplicate names; process overrides including empty values; fixed path independent of cwd.
- Allowed local/SoC names versus ignored settings-module, production, interpreter/process-option and arbitrary names; malformed allowed assignments and quote forms; UTF-8/read failures with fixed errors and no synthetic value/exception-detail leakage. Existing secret/debug/loopback validations remain enforced for file-derived values.
- Test/production settings never invoke the loader. All subprocess paths use synthetic files, including invalid/missing-secret cases, database-destination probes and direct-file WSGI startup. Confirm existing provider/test-network isolation and no gateway behaviour changes.

## Handoff and next step

- No agent may open or print the real `.env`; no new dependencies or external configuration changes are authorized. Test data and probe output must remain synthetic. Provider smoke/evaluation is separate and remains pending.
- Usage baseline `%TEMP%/relay-dotenv-usage-baseline.json` was captured after initial inspection; coordinator-owned reporting must retain that coverage limitation, not treat missing usage as zero.
- **Next:** coordinator reviews/commits checkpoint 1, then assigns checkpoint 2 with a fresh scope snapshot and isolated test setup.
