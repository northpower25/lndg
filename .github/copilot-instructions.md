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
