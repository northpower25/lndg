# LNDg Next – Copilot Development Instructions

These rules are **mandatory** for every code change in this repository. Check each relevant rule before writing any code. When in doubt, the rules win over convenience.

Full rule details with rationale and code examples: [`ENTWICKLUNGSREGELN.md`](../ENTWICKLUNGSREGELN.md)

---

## Architecture (never violate)

- **R-ARCH-1**: `LightningWriteAdapter` may only be imported and called from `executor.py`. Never from views, templates, recommendation engine, AI/ML modules, or any other file.
- **R-ARCH-2**: UI code must never branch on `settings.backend == "LND"`. Always use `backend.get_capabilities().<capability>` instead.
- **R-ARCH-3**: Views, templates, and API responses use only abstract domain models (`Channel`, `Peer`, `ForwardingEvent`, `FeePolicy`, `SpliceAction`). No LND-specific field names (`chan_id`, `lnd_short_chan_id`) in these layers.
- **R-ARCH-4**: Templates and React components render only. All calculations belong in backend service classes.

## Data Model

- **R-DM-1**: Every Django model has `class Meta: app_label = 'gui'`.
- **R-DM-2**: Defaults belong in the model field, not in view logic.
- **R-DM-3**: Bitcoin amounts are always `BigIntegerField` (sats or msats). Never `FloatField` or `DecimalField` for monetary values.
- **R-DM-4**: Time-series models get `db_index=True` on `timestamp` and a composite index `[chan_id, timestamp]`.
- **R-DM-5**: Every new model with growing data gets a retention rule in `cleaner.py` at the same time as its migration.
- **R-DM-6**: Amount fields are named `amount_sat` or `amount_msat` – never generic `amount`.

## Internationalization

- **R-I18N-1**: Every user-visible string is marked: `{% trans "..." %}` (templates), `_("...")` (Python), `t('key')` (React/i18next). No exceptions.
- **R-I18N-2**: DB field names, API keys, JSON properties stay in English. Only UI labels and help texts are translated.
- **R-I18N-3**: Numeric inputs in the frontend are normalized with `replace(/\D/g, '')` before processing.
- **R-I18N-4**: Amount display uses a central helper function – never hardcode `f"{amount} sats"`.
- **R-I18N-5**: New features ship DE + EN translations together. No merge without both languages.

## GUI

- **R-GUI-1**: Every new UI feature is assigned a mode: `guided` | `advanced` | `expert`. Default for new features: `advanced`.
- **R-GUI-2**: Every write action requires: impact preview, risk label (`low`/`medium`/`high`), and a policy snapshot for rollback.
- **R-GUI-3**: Automated actions default to `dry_run=True`. Users must explicitly switch to live execution.
- **R-GUI-4**: Every metric, number, or recommendation has an expandable "Why?" panel with data source and confidence. No metric widget without `title` + `tooltip`.
- **R-GUI-5**: Touch targets ≥ 44px. No hover-only interactions. Card-default on small screens. No horizontal table scroll without swipe hint.
- **R-GUI-6**: All actions route through API → Audit-Log → UI-Refresh. No direct DOM state mutation.
- **R-GUI-7**: Buttons for unsupported backend capabilities are **disabled + explained via tooltip**, never hidden.

## AI / ML

- **R-AI-1**: No AI/ML module imports `LightningWriteAdapter`. The only allowed flow is: `ML → Recommendation → Policy Engine → Validation → (Human | Approved Automation) → LightningWriteAdapter`.
- **R-AI-2**: New ML features start in shadow mode (log only, no execution). Full automation requires minimum learning period + explicit expert-mode opt-in.
- **R-AI-3**: ML recommendations are only emitted after ≥ 30 days of data and ≥ 50 relevant events. Before that: heuristic recommendations only.
- **R-AI-4**: The `actor` field in `ChangeLog` always identifies who/what triggered an action: `manual`, `policy:<name>`, or `ml:<model>:<version>`.
- **R-AI-5**: Every recommendation includes `confidence` (0.0–1.0) and `confidence_label` (`heuristic` | `rule_based` | `ml_shadow` | `ml_model`). Never a bare recommendation without origin.

## Security

- **R-SEC-1**: SSH connections use `paramiko.RejectPolicy()`. Never `AutoAddPolicy()`.
- **R-SEC-2**: Credential files (macaroons, passwords, config with secrets) are always created with mode `0o600`.
- **R-SEC-3**: `requirements.txt` is generated from `requirements.in` via `pip-compile` with version bounds. No unpinned dependencies.
- **R-SEC-4**: No external API calls without explicit user opt-in. External calls are async, non-blocking, with graceful degradation.
- **R-SEC-5**: Every new write API endpoint gets rate-limiting + CSRF protection + authentication.
- **R-SEC-6**: Automatic backup before every restore and before every bulk DB operation.

## Backend / Jobs

- **R-JOB-1**: In job files prefer async ORM: `async for obj in qs`, `await qs.aget(...)`, `await Model.objects.abulk_create(...)`.
- **R-JOB-2**: gRPC credentials are loaded once and the connection is reused for the entire job lifecycle. No reconnect per request.
- **R-JOB-3**: Job responsibilities are strictly separated: `collector` → fetch data only · `aggregator` → calculate aggregates only · `analyzer` → compute scores only · `recommender` → create recommendations only · `executor` → execute policies via `PolicyRun` only.
- **R-JOB-4**: All snapshot intervals are configurable with sensible defaults (channel snapshots: 15 min, RPi recommendation: 1h).

## Code Quality

- **R-CODE-1**: `make lint` = `ruff check .`. No PR merge with lint errors. Generated/vendor protobuf outputs in `gui/lnd_deps/*_pb2.py` and `gui/lnd_deps/*_pb2_grpc.py` are intentionally excluded from Ruff because they are toolchain-generated, not hand-maintained code.
- **R-CODE-2**: New Python functions get type annotations. Modified existing functions get type annotations too.
- **R-CODE-3**: New API endpoints go under `/api/v2/`. No breaking changes to existing `/api/v1/` or `/api/` endpoints.
- **R-CODE-4**: Existing views are not deleted. They are marked `[Expert/Legacy]` in navigation.
- **R-CODE-5**: `python manage.py migrate --check` must pass before every commit.
- **R-CODE-6**: After any Umbrel-facing change (`northpower25-lndg/*` or install/version metadata), bump the mirrored release versions in `northpower25-lndg/umbrel-app.yml`, `frontend/package.json` + `frontend/package-lock.json`, and `gui/templates/base.html` so Umbrel detects and downloads the new release.

---

## Pre-coding Checklist

Before writing any code, verify each applicable item:

```
□ R-GUI-1:   Which mode does this feature belong to? (guided / advanced / expert)
□ R-I18N-1:  Are all user-visible strings marked for translation?
□ R-ARCH-2:  Is any code branching on backend type? → Use capability check instead
□ R-ARCH-1:  Is LightningWriteAdapter imported anywhere except executor.py? → FORBIDDEN
□ R-DM-3:    Do any model fields hold Bitcoin amounts? → BigIntegerField only
□ R-GUI-3:   Is this an automated action? → dry_run=True default
□ R-DM-5:    Does the new model produce growing data? → Add cleaner.py rule
□ R-AI-1:    Does any AI/ML module touch LightningWriteAdapter? → FORBIDDEN
□ R-GUI-2:   Is there an impact preview + risk label for every write action?
□ R-AI-5:    Does every recommendation include confidence + confidence_label?
□ R-DM-6:    Are amount fields named amount_sat / amount_msat?
□ R-I18N-5:  Are DE + EN translations provided for every new user-visible text?
```

---

## Phase Continuity Rule (mandatory for all future prompts)

If a prompt requests implementation of any development phase, you must always:
1. Document at the end which items of the requested phase are still open and why.
2. Re-check all previously skipped items from earlier phases and implement those now feasible.
3. Update this file with what was completed, what remains open, and explicit reasons.

This rule applies automatically for all future phase prompts and does not need to be repeated by the user.

---

## Phase 1 + 2 – Remaining Gaps (Open Work)

After every task execution, update this section with what was completed, what is still open,
and — most importantly — **why** something could not yet be completed.

### ✅ Completed (Phase 1 + 2)

| Item | Details |
|------|---------|
| Multi-stage Dockerfile (rootless, `/lndg`) | `Dockerfile` |
| CI pipeline split backend/frontend | `.github/workflows/ci.yml` |
| Backend adapter interfaces + LND + CLN adapters | `gui/backends/` |
| Capability registry singleton | `gui/backends/registry.py` |
| **Registry auto-wiring on startup** | `gui/apps.py` `GuiConfig.ready()` – auto-detects CLN via `CLN-REST-URL`+`CLN-Rune` in LocalSettings, falls back to LND |
| UserMode model + `/api/v2/user/settings/` | `gui/models.py`, `gui/api/v2/views.py` |
| i18n settings infrastructure (DE+EN) | `initialize.py`, `locale/*/LC_MESSAGES/*.po` |
| Cockpit tiles + new navigation | `gui/templates/home.html`, `gui/templates/base.html` |
| Time-series models (ChannelSnapshot, ForwardingAggregate, ChangeLog, BackupLog) + migrations | `gui/models.py`, `gui/migrations/` |
| Cleaner module with all retention functions | `gui/jobs/cleaner.py` |
| Collector module | `gui/jobs/collector.py` |
| Aggregator module | `gui/jobs/aggregator.py` |
| **Collector + Aggregator + Cleaner in jobs.py** | `jobs.py` `_run_phase2_periodic_jobs()` – runs on configurable loop-counter intervals |
| Charts UI + chart API endpoints | `gui/templates/charts.html`, `gui/api/v2/views.py` |
| Backup/Restore UI + API endpoints | `gui/templates/backup_restore.html`, `gui/jobs/backup.py`, `gui/api/v2/views.py` |
| **Cleaner/Maintenance UI** | `gui/templates/cleaner.html`, `gui/views/cleaner_view.py`, URL `/maintenance/`, nav link (advanced/expert) |
| **`/api/v2/cleaner/settings/`** (save retention values) | `gui/api/v2/views.py` |
| **`/api/v2/cleaner/counts/`** (row-count overview) | `gui/api/v2/views.py` |
| **`/api/v2/cleaner/run/` extended** | now supports `dry_run` + all-tables mode alongside single-table backward-compat |
| ChangeLog in fee-update write paths | `gui/views/channels.py` |
| **Phase 3 core models** (`Recommendation`, `Policy`, `PolicyRun`, `SpliceLog`) + migration | `gui/models.py`, `gui/migrations/0005_policy_recommendation_policyrun_splicelog.py` |
| **Recommendation engine (heuristics + rationale schema + persistence)** | `gui/jobs/recommender.py`, `/api/v2/cockpit/` integration |
| **Phase 3 API endpoints** (`/api/v2/recommendations/*/dryrun`, `/api/v2/policies/*/run`, `/api/v2/channels/*/splice/*`) | `gui/api/v2/views.py`, `gui/api/v2/urls.py`, `gui/jobs/executor.py` |
| **Guided Splice Workflow UI + CLN Plugin Panel** | `gui/templates/splice.html`, `gui/templates/cln_plugins.html`, `gui/views/splice_view.py` |
| **Cleaner retention coverage for Phase-3 models** | `gui/jobs/cleaner.py`, `gui/views/cleaner_view.py`, `gui/templates/cleaner.html`, `jobs.py` |
| **ChangeLog for Rebalancer + Autopilot write paths** | `gui/jobs/rebalancer.py` |
| Onboarding wizard (CLN + LND) | `gui/templates/onboarding.html`, `gui/views/onboarding.py` |
| requirements.in with version bounds | `requirements.in` |

---

### ❌ Not Completable in Phase 1 + 2 Scope — Why

These items were identified as Phase 1+2 goals but **cannot** be completed without either
a Phase 3+ effort, inherent technical/operational constraints, or unacceptable regression risk.

#### 1. Full migration of legacy LND direct calls to Backend Adapter
**Status:** ❌ Cannot be done in Phase 1/2 scope.
**Why:** `jobs.py`, `gui/views/channels.py`, `gui/views/peers.py`, `gui/views/routing.py`, `gui/views/payments.py`, `gui/views/settings.py`, and others contain ~300+ direct gRPC (`lnd_connect()`/`LightningStub`) calls. Migrating all of these to go through the Backend Adapter would require:
- Extending the adapter interface with ~30+ additional methods,
- Rewriting every affected view and job function,
- Running full regression tests against a live LND node.
This is **Phase 3+ migration work** and carries high regression risk. The legacy paths are not broken; they just bypass the adapter layer. **Rule R-ARCH-2/R-ARCH-3 compliance for the existing code will be achieved incrementally in Phase 3.**

#### 2. CLN end-to-end integration (live data, all views)
**Status:** ❌ Adapter exists; full wiring to views deferred to Phase 3.
**Why:** The `ClnBackend` adapter is implemented for `get_forwarding_events`, `update_fee_policy`, and `get_capabilities`. However, because all existing views still call LND gRPC directly (see item 1), a CLN node cannot currently replace LND as the primary data source for the full UI. Full CLN support requires completing Phase 3 (view-by-view migration to read-adapter). The onboarding wizard and capability flags already work correctly for CLN.

#### 3. CLN HTLC-stream hooks
**Status:** ❌ Phase 3+ / requires CLN WebSocket/notification infrastructure.
**Why:** CLN's HTLC streaming requires either CLN's `htlc_accepted` hook (Python plugin) or the `notifications` WebSocket channel (CLN ≥ 24.08). Neither mechanism is in place in the current architecture. This is scoped for Phase 3 when CLN becomes a fully supported backend.

#### 4. Pinned `requirements.txt` via `pip-compile`
**Status:** ⚠️ Partially complete (`requirements.in` has version bounds).
**Why:** `pip-compile` must be run in the target Python environment to produce a deterministic lock file. Running it inside the Copilot sandbox produces a lock that may differ from production (Python version, platform markers). The correct process is: **maintainers run `pip-compile requirements.in -o requirements.txt` locally and commit the result**. The `requirements.in` already provides upper-bound constraints as required by R-SEC-3. The unpinned `requirements.txt` is a known gap; CI should enforce `pip-compile --check` to catch drift.

#### 5. Full i18n coverage of legacy templates
**Status:** ⚠️ All **new** Phase 1+2 templates/views are fully i18n'd (DE+EN). Legacy templates are not.
**Why:** Existing templates (`home.html`, `channels.html`, `peers.html`, `advanced.html`, `payments.html`, etc.) contain 400+ strings that predate i18n and are not wrapped in `{% trans %}`. Marking all of them correctly without introducing regressions requires a dedicated pass per template. This is **Phase 1 housekeeping debt** to be resolved incrementally. New code follows R-I18N-1/R-I18N-5 strictly.

#### 6. ChangeLog for all write operations (rebalancer, autopilot, etc.)
**Status:** ⚠️ Partially complete in Phase 3.
**Why:** Rebalancer attempts and autopilot enable/disable paths are now logged in `gui/jobs/rebalancer.py`. Remaining gaps are additional write paths (peer/channel open/close and other legacy actions) that still bypass `ChangeLog` and require incremental hardening to avoid regressions.

#### 7. Database restore via the `/api/v2/backup/restore/` API
**Status:** ⚠️ The restore API currently accepts settings-file restores only; full DB restore is intentionally locked.
**Why:** Restoring the SQLite database while Django is running can corrupt it or silently lose in-flight writes. A safe DB restore requires stopping the application, replacing the file, and restarting — which cannot be done via an HTTP endpoint without a supervisor/container orchestration layer. The endpoint returns HTTP 400 for `type=database` restore requests by design (see `gui/api/v2/views.py`). This is an **operational/security constraint**, not a missing feature.

---

### 🔜 Recommended Next Steps (post-Phase-3 follow-up)

1. Complete legacy write-path migration to `executor.py` + adapter flow (`gui/views/channels.py`, peers/channels open/close, remaining legacy APIs).
2. Expand `ChangeLog` coverage to all remaining write actions beyond rebalancer/autopilot.
3. Wire real CLN splice status/confirmation tracking (`splice_update` / `splice_signed`) and block-height progress.
4. Add full DE/EN translation entries for newly introduced Phase-3 strings in locale catalogs.
5. Run `pip-compile requirements.in -o requirements.txt` in maintainer target environment and enforce `pip-compile --check` in CI.

---

## Phase 3 – Remaining Gaps (Open Work)

- **End-to-end CLN splice execution lifecycle** is only partially implemented: preview and API flow exist, but confirmation progression and backend-specific finalize steps still need robust production handling.
- **Simulation layer coverage** is partial: recommendation dry-run and policy execution now run through `executor.py` with snapshots/audit logging, but no full historical “Was wäre passiert” learning widget yet.
- **Legacy view migration to adapter-based writes** remains incomplete; phase-3 additions follow the executor path, but older write endpoints still require incremental migration.

---

## Phase 4 – Remaining Gaps (Open Work)

### ✅ Completed in this iteration (Phase 4 continuation)

| Item | Details |
|------|---------|
| Policy executor with validation/cooldown/hard caps | `gui/jobs/executor.py` now executes policies with validation and backend delegation |
| PolicyRun + ChangeLog flow in policy API | `/api/v2/policies/{id}/run` now uses executor and writes `actor=policy:<name>` |
| Auto-Fee policy templates as DB defaults | Migration `gui/migrations/0006_phase4_policy_ml_records.py` creates Conservative/Balanced/Revenue-Seeking templates (`dry_run=True`) |
| Phase-4 ML shadow storage models | `RebalanceMLRecord` and `AutoFeeMLRecord` models + migration |
| Retention for Phase-4 ML models | `gui/jobs/cleaner.py`, `cleaner_view.py`, `cleaner.html`, `/api/v2/cleaner/*`, `jobs.py` |
| Periodic policy-engine execution | `jobs.py` runs due active policies on configurable `POLICY-Interval` |

### ❌ Still open / not yet fully implementable in this iteration

1. **Full Auto-Fee Templates UI (4-B)**
   - **Status:** ⚠️ Partial.
   - **Why:** Default template policies now exist in DB, but a dedicated guided/expert template selection UI with parameter expansion is not yet implemented; current UI remains legacy-oriented.

2. **CLN Rebalance plugin execution path (4-C)**
   - **Status:** ⚠️ Partial.
   - **Why:** Capability detection exists, but no production-grade policy execution adapter path for CLN rebalance plugin calls has been wired in executor yet.

3. **ML Shadow recommendation jobs (4-E / 4-F)**
   - **Status:** ⚠️ Data model complete, job logic pending.
   - **Why:** Storage models and retention are implemented, but `ml_predictor.py` and Auto-Fee/Rebalance shadow recommendation generation still need dedicated feature engineering and scheduling.

4. **Rebalance budget queue + dynamic target quotas (4-G)**
   - **Status:** ❌ Not implemented.
   - **Why:** Requires deeper integration with legacy rebalancer flows and additional scoring logic; high coupling with existing `rebalancer.py` behavior warrants an incremental follow-up change.

5. **Audit timeline UI + rollback endpoints (4-H)**
   - **Status:** ❌ Not implemented.
   - **Why:** Policy audit entries are now written, but timeline rendering and safe rollback execution (including automatic backup orchestration) need dedicated API + UI work and strict expert-mode gating.
