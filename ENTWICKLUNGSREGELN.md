# LNDg Next – Entwicklungsregeln

> **Version:** 1.0 · **Status:** Verbindlich  
> **Abgeleitet aus:** [REFACTORING_KONZEPT.md](./REFACTORING_KONZEPT.md)

---

## Präambel & Verwendung

Dieses Dokument beschreibt **bindende Entwicklungsregeln** für LNDg Next. Jeder Prompt an eine KI und jeder menschliche Entwicklungsschritt beginnt mit der Überprüfung der hier genannten Prinzipien. **Bei Widerspruch zwischen Convenience und diesen Regeln gewinnen immer die Regeln.**

### Wie dieses Dokument nutzen

- **KI-gestützte Entwicklung:** Den relevanten Regelblock (z.B. `R-ARCH-1`, `R-I18N-1`) explizit im Prompt referenzieren. Die [KI-Prompt-Checkliste](#9-ki-prompt-checkliste) am Ende verwenden.
- **Manuelle Entwicklung:** Vor jedem PR die Checkliste abhaken.
- **Code Review:** Regelreferenzen als Review-Kommentar verwenden (z.B. „Verletzt R-DM-3 – FloatField für Betrag").

Alle Regel-IDs sind stabil und dienen als gemeinsame Sprache zwischen Menschen und KI-Systemen.

---

## Inhaltsverzeichnis

1. [Architektur-Invarianten](#1-architektur-invarianten-niemals-verletzen)
2. [Datenmodell-Regeln](#2-datenmodell-regeln)
3. [Multilanguage-Regeln](#3-multilanguage-regeln)
4. [GUI-Regeln](#4-gui-regeln)
5. [KI / ML-Regeln](#5-ki--ml-regeln)
6. [Sicherheitsregeln](#6-sicherheitsregeln)
7. [Backend / Jobs-Regeln](#7-backend--jobs-regeln)
8. [Code-Qualitätsregeln](#8-code-qualitätsregeln)
9. [KI-Prompt-Checkliste](#9-ki-prompt-checkliste)
10. [Glossar](#10-glossar)

---

## 1. Architektur-Invarianten (niemals verletzen)

### R-ARCH-1 – Read/Write-Trennung

Der `LightningWriteAdapter` ist der einzige Ort mit Schreibrechten auf den Node. Seine Nutzung ist strukturell eingeschränkt:

| Modul | `LightningReadAdapter` | `LightningWriteAdapter` |
|---|---|---|
| Views / Templates | ✅ erlaubt | ❌ verboten |
| Recommendation Engine | ✅ erlaubt | ❌ verboten |
| KI / ML-Module | ✅ erlaubt | ❌ verboten |
| `executor.py` | ✅ erlaubt | ✅ **einzige Ausnahme** |

Verstöße sind per statischer Analyse (Linter-Import-Check) erzwingbar.

**Datenfluss (Action-Gateway):**
```
KI / Recommendation Engine  ──►  Recommendation-Objekt
                                          │
                                   Policy Engine
                                   (deterministische Regeln)
                                          │
                                   Validation Layer
                                   (Sanity-Checks, Hard Caps, Cooldown)
                                          │
                              Human Confirmation | Approved Automation
                                          │
                                  LightningWriteAdapter  ← nur hier
                                          │
                                    ChangeLog-Eintrag
```

### R-ARCH-2 – Capability-basierte UI

UI-Funktionen fragen niemals nach dem Backend-Typ, sondern nach Capabilities:

```python
# ❌ VERBOTEN – direkte Backend-Kopplung
if settings.backend == "LND":
    show_auto_fee_button()

# ✅ PFLICHT – Capability-basiert
if backend.get_capabilities().can_auto_fee:
    show_auto_fee_button()
```

Definierte Capabilities (aus `BackendCapabilities`): `can_auto_fee`, `can_rebalance`, `can_stream_htlcs`, `can_splice`, `can_inbound_fees`, `can_keysend`, `supports_plugins`, `can_multi_asset`, `ai_safe_actions`.

### R-ARCH-3 – Adapter-Neutralität

In Views, Templates und API-Responses werden ausschließlich abstrakte Domänenmodelle verwendet. LND-spezifische Feldnamen sind verboten:

| ❌ Verboten (LND-spezifisch) | ✅ Pflicht (Domänenmodell) |
|---|---|
| `chan_id` | `channel_id` / `Channel` |
| `lnd_short_chan_id` | `short_channel_id` |
| `_forwarding_event` | `ForwardingEvent` |

Abstrakte Domänenmodelle: `Node`, `Peer`, `Channel`, `ForwardingEvent`, `LiquidityState`, `FeePolicy`, `RebalanceAction`, `SpliceAction`.

### R-ARCH-4 – Keine Business-Logik in Templates

Templates und React-Komponenten **rendern nur**. Berechnungen, Filterungen und Transformationen gehören ins Backend (Service-Klassen) oder in dedizierte Utility-Funktionen – nicht in Jinja2-Templates oder JSX.

---

## 2. Datenmodell-Regeln

### R-DM-1 – Vollständiges `app_label`

Jedes Django-Model enthält in seiner `Meta`-Klasse das explizite `app_label`:

```python
class Meta:
    app_label = 'gui'
```

### R-DM-2 – Explizite Defaults im Model

Defaults gehören ins Model-Objekt, nicht in View-Logik oder Formulare. Unterschiedliche Defaults zwischen Code und Datenbank (wie historisch bei `lowliq_limit`) sind ein bekannter Fehlerursprung und werden strukturell vermieden.

```python
# ❌ VERBOTEN – Default in der View
value = request.POST.get('limit') or 500  # versteckter Default

# ✅ PFLICHT – Default im Model
limit = models.IntegerField(default=500)
```

### R-DM-3 – Geldbeträge immer als Integer

Bitcoin-Beträge werden niemals als Fließkommazahl gespeichert:

| ❌ Verboten | ✅ Pflicht |
|---|---|
| `FloatField` für sats/msats | `BigIntegerField` |
| `DecimalField` für sats | `BigIntegerField` (sats) / `BigIntegerField` (msats) |

### R-DM-4 – Zeitreihen immer indiziert

Jedes Model mit Zeitreihen-Charakter (wachsende historische Einträge) bekommt:

```python
timestamp = models.DateTimeField(db_index=True)

class Meta:
    app_label = 'gui'
    indexes = [models.Index(fields=['chan_id', 'timestamp'])]
```

### R-DM-5 – Neue Modelle erfordern Migration + Bereinigungsregel

Jedes neue Datenmodell mit wachsenden Einträgen bekommt **gleichzeitig mit seiner Erstellung** eine Aufbewahrungsregel in der `cleaner.py`-Konfiguration. Kein neues Wachstums-Model ohne Bereinigungsregel.

### R-DM-6 – Denomination-Awareness (Vorbereitung Phase 7)

Felder die Bitcoin-Beträge darstellen, werden eindeutig benannt:

```python
# ❌ Mehrdeutig
amount = models.BigIntegerField()

# ✅ Eindeutig – Einheit im Feldnamen
amount_sat = models.BigIntegerField()
amount_msat = models.BigIntegerField()
fee_msat = models.BigIntegerField()
```

Dies ermöglicht spätere Multi-Asset-Erweiterung ohne Schema-Änderungen.

---

## 3. Multilanguage-Regeln

### R-I18N-1 – Kein hardcodierter UI-String

Jeder vom Nutzer sichtbare String wird markiert – keine Ausnahmen:

| Kontext | Markierung |
|---|---|
| Django-Templates | `{% trans "Kanalübersicht" %}` |
| Python (Views, Models) | `_("Fehler beim Laden")` |
| React/Frontend | `t('channels.overview')` via i18next |

Nicht übersetzen: DB-Feldnamen, API-Keys, JSON-Properties, Log-Nachrichten (nur intern).

### R-I18N-2 – Technische IDs und Schlüssel bleiben englisch

| ❌ Verboten | ✅ Pflicht |
|---|---|
| DB-Feld `kanal_id` | DB-Feld `channel_id` |
| API-Key `"gebühr"` | API-Key `"fee_rate"` |
| JSON `{"fehler": ...}` | JSON `{"error": ...}` |

Nur UI-Labels, Hilfetexte, Fehlermeldungen und Onboarding-Texte werden übersetzt.

### R-I18N-3 – Kein lokales Zahlen-Parsing ohne Locale-Bereinigung

Im Frontend müssen numerische Eingaben normalisiert werden, bevor sie verarbeitet werden. In vielen Locales ist das Tausend-Trennzeichen ein Leerzeichen oder Punkt, nicht ein Komma:

```javascript
// ❌ VERBOTEN – bricht bei Locale-abhängigem Format
const value = parseInt(inputString.replace(/,/g, ''));

// ✅ PFLICHT – alle Nicht-Ziffer-Zeichen entfernen
const value = parseInt(inputString.replace(/\D/g, ''));
```

Betrifft alle numerischen Eingabefelder (Beträge, Fees, Limits, ppm-Werte).

### R-I18N-4 – Sats / mBTC / BTC umschaltbar

Betragsdarstellungen nutzen eine zentrale Hilfsfunktion – nie direkt sats als hartkodierten String einbauen:

```python
# ❌ VERBOTEN
return f"{amount} sats"

# ✅ PFLICHT
return format_amount(amount, unit=user_settings.amount_unit)
```

Die Hilfsfunktion unterstützt: `sats`, `mBTC`, `BTC` (umschaltbar pro User-Einstellung).

### R-I18N-5 – Neue Features: zuerst DE + EN

Bei jedem neuen Feature werden DE- und EN-Übersetzungen **gleichzeitig** geliefert. Kein Feature-Merge ohne beide Sprachen. Weitere Sprachen (ES, FR, ZH) können per Community-Contribution nachgereicht werden.

---

## 4. GUI-Regeln

### R-GUI-1 – Progressive Disclosure

Jede neue UI-Funktion wird einem Betriebsmodus zugeordnet:

| Modus | Zielgruppe | Regel |
|---|---|---|
| `guided` | Einsteiger | Nur erklärende, sichere Aktionen. Neuer Code: nie direkt hier starten. |
| `advanced` | Intermediate | **Default für neue Funktionen** |
| `expert` | Erfahrene | Voller Zugriff; immer mit mode-Guard absichern |

```python
# ✅ Mode-Guard für Expert-Funktion
if user_mode.mode not in ('expert',):
    return HttpResponseForbidden()
```

### R-GUI-2 – Jede Aktion braucht: Impact-Vorschau + Risiko-Label + Undo

Kein Formular-Submit ohne:

1. **Impact-Vorschau** – geschätzter Effekt der Aktion (z.B. „Fee-Änderung beeinflusst voraussichtlich X")
2. **Risiko-Label** – visuell codiert: `low` 🟢 / `medium` 🟡 / `high` 🔴
3. **Policy-Snapshot** – automatisch vor jeder Änderung erstellt (ermöglicht Rollback)

### R-GUI-3 – Dry-Run-First

Jede neue automatisierte Aktion hat `dry_run=True` als Default. Der Nutzer muss explizit auf „Live ausführen" umschalten:

```python
# ✅ Policy-Default
policy = Policy(dry_run=True, ...)  # niemals dry_run=False als Default
```

### R-GUI-4 – Erklärbarkeit-Pflicht

Jede Zahl, Metrik oder Empfehlung hat ein aufklappbares „Warum?"-Panel:

```
┌─────────────────────────────────────────────┐
│ 💡 Empfehlung: Fee für [Peer] senken        │
│ Warum: Kein Outbound-Flow seit 14 Tagen     │
│ Datenquelle: intern (LNDg-Daten, 30d)       │
│ Konfidenz: Heuristik (kein ML aktiv)        │
│ Risiko: Niedrig 🟢                          │
└─────────────────────────────────────────────┘
```

Kein Metric-Widget ohne `title` + `tooltip`-Kontext. Kein Chart ohne Legende und Zeitfenster-Angabe.

### R-GUI-5 – Mobile-First-Pflicht

| Anforderung | Mindeststandard |
|---|---|
| Touch-Targets | ≥ 44px (Höhe und Breite) |
| Interaktionen | Keine Hover-only; immer Touch-Alternative |
| Standardansicht | Karten-Default statt Tabellen-Default |
| Tabellen auf Mobile | Swipe-Hinweis + responsive Spalten, kein blindes horizontales Scrollen |

### R-GUI-6 – Aktions-Routing immer über API + Audit-Log

Keine direkte State-Mutation im DOM:

```
❌ DOM-Mutation direkt
✅ Aktion → POST /api/v2/... → Audit-Log → UI-Refresh
```

Jede schreibende Aktion erzeugt einen `ChangeLog`-Eintrag.

### R-GUI-7 – Capability-Guard für alle Write-Aktionen

Nicht unterstützte Capabilities werden **ausgegraut + erklärt**, nicht versteckt:

```html
<!-- ❌ VERBOTEN – einfach verstecken -->
{% if can_splice %}<button>Splice In</button>{% endif %}

<!-- ✅ PFLICHT – ausgegraut mit Erklärung -->
<button disabled title="Backend unterstützt Splicing nicht (CLN v24.02+ benötigt)">
  Splice In
</button>
```

---

## 5. KI / ML-Regeln

### R-AI-1 – KI schreibt nie direkt

Der vollständige Aktionspfad für KI/ML-Aktionen:

```
KI/ML  →  Recommendation-Objekt  →  Policy Engine
       →  Validation Layer        →  Human Confirmation
       →  LightningWriteAdapter   →  ChangeLog
```

Kein KI-Modul (`recommender.py`, `ml_predictor.py`, `analyzer.py`) importiert `LightningWriteAdapter`. Dies ist per Linter-Regel erzwingbar.

### R-AI-2 – Shadow-Mode-First

Jede neue ML-Funktion durchläuft diese Phasen in dieser Reihenfolge:

1. **Shadow Mode** – ML berechnet Empfehlungen, loggt sie, führt nichts aus
2. **Advisory Mode** – ML zeigt Vorschläge im UI, Nutzer entscheidet
3. **Policy Bound** – ML kann innerhalb explizit genehmigter Policies automatisch handeln (nur Expert-Mode + explizites Opt-in)

Vollautomation (Stufe 3) erst nach: konfigurierter Mindestlernzeit (Shadow-Phase) + explizitem Nutzer-Opt-in im Expert-Modus + ausreichender Datenbasis (R-AI-3).

### R-AI-3 – Mindestdatenmenge vor ML-Empfehlungen

ML-Empfehlungen werden erst ausgegeben wenn:

- ≥ 30 Tage historische Daten für den Kanal
- ≥ 50 relevante Events (Rebalance-Events, Forwarding-Events – je nach Modelltyp)

Bis dahin: ausschließlich heuristische Empfehlungen (`confidence_label = "heuristic"`). Fortschritt wird pro Kanal angezeigt: „Noch X Tage bis ML-Features für diesen Kanal verfügbar".

### R-AI-4 – Jede KI-Aktion im Audit-Log

Das `actor`-Feld im `ChangeLog` muss immer Auskunft geben, wer/was eine Aktion ausgelöst hat:

| Auslöser | `actor`-Wert |
|---|---|
| Manuell durch Nutzer | `manual` |
| Automatische Policy | `policy:<policy_name>` |
| ML-Modul | `ml:<model_name>:<version>` |

### R-AI-5 – Konfidenz immer mitliefern

Jede Empfehlung enthält zwingend:

```json
{
  "confidence": 0.72,
  "confidence_label": "heuristic",
  "reasons": [
    {"rank": 1, "signal": "no_outbound_flow", "value": "14 Tage", "weight": 0.45}
  ],
  "data_source": "internal",
  "data_window_days": 30
}
```

Erlaubte `confidence_label`-Werte: `heuristic` | `rule_based` | `ml_shadow` | `ml_model`.

Niemals eine nackte Empfehlung ohne Herkunft und Begründung.

---

## 6. Sicherheitsregeln

### R-SEC-1 – SSH: RejectPolicy statt AutoAddPolicy

SSH-Verbindungen (z.B. für Channel-DB-Size-Features) akzeptieren keine unbekannten Hosts automatisch:

```python
# ❌ VERBOTEN – MITM-Risiko
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# ✅ PFLICHT
client.set_missing_host_key_policy(paramiko.RejectPolicy())
# Hosts müssen vorab in ~/.ssh/known_hosts eingetragen sein
```

### R-SEC-2 – Sensitive Dateien: mode=0o600

Admin-Passwörter, Macaroon-Dateien und Konfigurationsdateien mit Credentials werden immer mit restriktiven Berechtigungen erstellt:

```python
# ✅ PFLICHT
with open(filepath, 'w', opener=lambda p, f: os.open(p, f, 0o600)) as f:
    f.write(sensitive_content)
```

Keine World-Readable-Defaults (`0o644` oder weiter) für Credential-Dateien.

### R-SEC-3 – Dependency-Pinning

- `requirements.txt` wird aus `requirements.in` via `pip-compile` generiert
- Versions-Bounds verwenden (z.B. `Django>=4.2,<5.0`) – kein unpinntes `Django` ohne Version
- Keine unpinnten Dependencies in `requirements.txt`
- `package-lock.json` wird committed; in CI `npm ci` statt `npm install`

### R-SEC-4 – Externe API-Calls: Privacy by Default

- **Default:** Keine externen Anfragen (mempool.space, Amboss, etc.) ohne explizites Nutzer-Opt-in
- Externe Calls sind: asynchron, nicht blockierend, mit Timeout, mit graceful degradation
- Kein Senden von Node-Daten (Pubkey, Channel-IDs) ohne explizite Einwilligung

```python
# ✅ PFLICHT – Opt-in prüfen
if not settings.mempool_integration_enabled:
    return None  # graceful degradation, UI funktioniert ohne externe Daten
```

### R-SEC-5 – Rate-Limiting auf alle Write-Endpunkte

Jeder neue schreibende API-Endpunkt (`POST`, `PUT`, `DELETE`) bekommt:
- Rate-Limiting (Anfragen pro Zeitfenster konfigurierbar)
- CSRF-Schutz (Django-Standard, nicht deaktivieren)
- Authentifizierung (keine anonymen Write-Operationen)

---

## Phase-Tracking Update (Stand: 2026-05-08)

### ✅ Neu umgesetzt in Phase 6 (dieser Stand)

| Item | Details |
|---|---|
| **6-A: ML-Infrastruktur** | `gui/jobs/ml_trainer.py`: Feature-Engineering aus `ChannelSnapshot`/`RebalanceMLRecord`/`AutoFeeMLRecord`, scikit-learn RandomForestClassifier, Rolling-Window-Features (24h/7d), Modell-Persistenz als `.joblib` unter `models/`, tägliches Batch-Retraining (konfigurierbar, deaktivierbar via `ML-TrainingEnabled=false`) |
| **6-A API** | `POST /api/v2/ml/rebalance/train` (manuelles Retraining), `GET /api/v2/ml/status` (Konfidenz, Datenmenge, letztes Training, data_gate_ok) |
| **6-A deps** | `scikit-learn>=1.4,<2` und `joblib>=1.3,<2` in `requirements.in` und `requirements.txt` |
| **6-B: ML Shadow Recommendations** | `generate_ml_shadow_recommendations()` in `recommender.py`: shadow_rebalance_predict-Integration, `confidence_label='ml_shadow'`, Mindestdatenprüfung R-AI-3 (≥30 Tage, ≥50 Events), nur aktiv wenn `ai_mode` in `shadow`/`policy_bound` |
| **6-C: Auto-Fee ML Suggestions** | `get_autofee_suggestions()` und `get_autofee_history()` in `ml_trainer.py`; Eskalations-/Deeskalations-Faktoren, API `GET /api/v2/ml/autofee/suggestions`, `GET /api/v2/ml/autofee/history` |
| **6-D: ML Vollautomation** | `UserMode.AI_MODE_POLICY_BOUND = 'policy_bound'` + Migration `0009_phase6_usermode_policy_bound.py`; `ai_policy_bound_confirm` Feld (default `True`); `execute_ml_action()` in `executor.py` mit Expert-Mode-Gate, Human-Confirmation-Layer, ChangeLog-Actor `ml:<model>:<version>` (R-AI-4) |
| **6-E: Eskalations-Tuning API** | `GET/PUT /api/v2/ml/escalation/config/` – konfigurierbare Faktoren (`ML-EscalationCooldown`, `ML-EscalationMaxLevels`, `ML-EscalationFeeRateUp/Down`, `ML-TrainingEnabled`, `ML-TrainingIntervalHours`) via `LocalSettings` |
| **6-F SSE** | `GET /api/v2/events/` SSE-Endpunkt in `gui/api/v2/views.py`: heartbeat (15s), `rebalance_status` (neue PolicyRun-Zeilen), `htlc_summary` (30s) |
| **6-F PWA** | `gui/static/manifest.json` (Web App Manifest), `gui/static/service-worker.js` (cache-first für static, network-first für Navigation, network-only für API, offline-fallback); `<link rel="manifest">` + Service-Worker-Registrierung in `base.html` |
| **Phase 4-E/4-F Re-Check** | ML-Shadow-Joblogik jetzt umgesetzt: `generate_ml_shadow_recommendations()` + periodischer Aufruf in `jobs.py` |
| **Phase 4-G Re-Check** | Rebalance-Budget-Queue bleibt offen (hoher Rebalancer-Umbau, separates Paket) |

### ✅ Neu umgesetzt in Phase 5 (vorheriger Stand)

| Item | Details |
|---|---|
| mempool.space Integration (opt-in) | `gui/jobs/external_integrations.py` mit asynchronem Fetch, TTL-Cache, 429-Backoff; Einbindung in Empfehlungen und Splice-Preview |
| Fee-Ampel + Wait-Window-Hinweis | On-chain-Kontext (`🟢/🟡/🔴`) für Open/Close/Splice-Empfehlungen in `gui/jobs/recommender.py` + Anzeige in `gui/templates/home.html` |
| Low-fee Notifier | Periodischer opt-in Benachrichtigungs-Flow in `jobs.py` (`MEMPOOL-NotifyInterval`) |
| Amboss Integration (opt-in) | Optionaler API-Key + explizites Opt-in in `NotificationSettings`; Peer-Kontext nur für bereits verbundene Peers in `gui/views/peers.py` |
| Peer-Kontextdarstellung | Amboss-Rank/Kapazität/Kanäle in `gui/templates/peers.html` inkl. Hinweis auf Nutzungsbedingungen |
| Onboarding-Wizard (5 Schritte) | Neuer 5-Step-Flow inkl. Sprachschritt, LND/CLN-Profilinhalte, Persistenz von `onboarding_step`/`onboarding_completed` in `gui/templates/onboarding.html` |
| Missions & Glossar | Neues Learning-Center unter `/learning/` (`gui/views/learning.py`, `gui/templates/learning_center.html`) |
| i18n DE+EN für neue UI-Texte | Erweiterung `locale/de/LC_MESSAGES/django.po` und `locale/en/LC_MESSAGES/django.po` |

### 🔁 Re-Check offene Punkte aus Phase 1–5

Nach erneuter Prüfung in Phase 6:

1. **Vollständige Migration aller Legacy-LND-Direct-Calls auf Adapter/Executor-Fluss**
   - **Warum offen:** Hohe Querschnittsänderung über viele Legacy-Views/Jobs mit signifikantem Regression-Risiko.
2. **Komplette CLN-End-to-End-Abdeckung über alle Legacy-Ansichten**
   - **Warum offen:** Hängt direkt von Punkt 1 (Legacy-Migration) ab.
3. **Vollständige Auto-Fee-Template-UI (Phase 4-B)**
   - **Warum offen:** Eigenes UI-Refactoring-Paket weiterhin nötig; Eskalations-Tuning-API ist jetzt umgesetzt.
4. **Rebalance-Budget-Queue + dynamische Zielquoten (Phase 4-G)**
   - **Warum offen:** Erfordert tiefe Integration mit Legacy-Rebalancer-Flows; separates Entwicklungspaket.
5. **Audit-Timeline + Rollback-Endpunkte (Phase 4-H)**
   - **Warum offen:** Erfordert gesonderte API/UI-Arbeit inklusive sicherer Backup-Orchestrierung vor Rollback.
6. **ML-Shadow-Joblogik (Phase 4-E/4-F)** ✅ **In Phase 6 umgesetzt** – `generate_ml_shadow_recommendations()` + periodische Ausführung in `jobs.py`.

### ❌ Weiterhin offen in Phase 6

1. **6-B UI-Toggle pro Kanal für ML-Nutzung**
   - **Warum offen:** Benötigt eigenen Channel-Detail-UI-Durchlauf; Backend-Logik (shadow-mode-Flag pro Channel) noch nicht im Datenmodell.
2. **6-C Dynamische Zielanpassung aus Netzwerk-Umfeld**
   - **Warum offen:** Erfordert externe Netzwerkdaten (z.B. Gossip-basierte Peer-Analyse); zu komplex für einen einzelnen Phase-6-Sprint.
3. **6-D UI-Bestätigungsdialog für policy_bound-Aktionen**
   - **Warum offen:** Backend-Gate (`ai_policy_bound_confirm`) ist implementiert; Frontend-Bestätigungsdialog fehlt noch.
4. **6-E Eskalationsstufe im Channel-Detail anzeigen**
   - **Warum offen:** API-Endpunkt vorhanden; UI-Einbettung in Channel-Detailseite fehlt.
5. **6-F SPA-Phase-2-Rollout (Startseite → SPA)**
   - **Warum offen:** Die bestehende Django-Template-Architektur ist noch primär; vollständige SPA-Migration (React/HTMX) erfordert separates Frontend-Refactoring-Paket mit hohem Umfang.
6. **Pinned `requirements.txt` via `pip-compile`**
   - **Warum offen:** `requirements.in` hat Versionsgrenzen (inkl. scikit-learn, joblib); `pip-compile` muss in der Ziel-Python-Umgebung ausgeführt werden.
7. **Vollständige i18n-Abdeckung der Legacy-Templates**
   - **Warum offen:** Neue Phase-6-Texte haben keine eigenständigen `.po`-Einträge (API-only, kein neues Template-HTML); Legacy-Template-i18n bleibt technische Schuld.

### ❌ Weiterhin offen in Phase 5

1. **Amboss-Daten in allen möglichen Peer-Detailoberflächen**
   - **Warum offen:** Aktuell in der zentralen Peers-Liste integriert; tiefergehende Detailansichten folgen separat.
2. **Mempool-Integration in sämtlichen Legacy-Open/Close-Formularen**
   - **Warum offen:** Ampel/Hinweise sind in Empfehlungspfad + Splice-Preview umgesetzt; Legacy-Formseiten benötigen eigenen UI-Durchlauf.

### R-SEC-6 – Backup vor Restore und vor Bulk-Operationen

Automatisches Mini-Backup wird ausgelöst vor:
- Jedem Restore-Vorgang
- Jeder DB-Bereinigung (`cleaner.py`)
- Jeder Bulk-Aktion auf kritischen Tabellen

---

## 7. Backend / Jobs-Regeln

### R-JOB-1 – Async ORM bevorzugen

In Job-Dateien (`collector.py`, `aggregator.py`, `executor.py`, etc.) werden Async-ORM-Methoden bevorzugt um Event-Loop-Blockaden zu vermeiden:

```python
# ❌ Blockierend
channels = list(Channel.objects.filter(is_active=True))

# ✅ Async – mehrere Objekte
channels = [c async for c in Channel.objects.filter(is_active=True)]
# oder mit abulk_create
await Channel.objects.abulk_create(snapshots)
# oder einzelnes Objekt
channel = await Channel.objects.aget(id=channel_id)
```

### R-JOB-2 – gRPC-Verbindung cachen

gRPC-Credentials (TLS-Zertifikat + Macaroon) werden **einmalig** beim Start des Collector-Jobs geladen und gecacht – nicht pro Anfrage neu gelesen. Die gRPC-Connection wird über den gesamten Job-Lifecycle wiederverwendet. Bei Verbindungsabbruch: automatisches Reconnect mit exponentialem Backoff.

### R-JOB-3 – Job-Verantwortlichkeiten einhalten

Klare Trennung der Job-Verantwortlichkeiten – kein Job überschreitet seine Zuständigkeit:

| Job | Darf | Darf nicht |
|---|---|---|
| `collector.py` | Node-Daten lesen, speichern | Analysieren, Entscheidungen treffen |
| `aggregator.py` | Aggregate berechnen | Node-API aufrufen, Policies ausführen |
| `analyzer.py` | Scores berechnen | Node-API aufrufen, direkt schreiben |
| `recommender.py` | Recommendations erstellen | `LightningWriteAdapter` importieren |
| `executor.py` | Policies ausführen (via `PolicyRun`) | Direkte Node-Befehle ohne `PolicyRun` |

### R-JOB-4 – Collector-Intervalle ressourcenabhängig

Alle Snapshot-Intervalle sind konfigurierbar mit dokumentierten Empfehlungen:

| Intervall | Default | RPi-Empfehlung |
|---|---|---|
| Channel-Snapshots | 15 Min | 1h |
| Forwarding-Events | 5 Min | 15 Min |
| Aggregates | 1h | 1h |
| ML-Training | nächtlich (03:00) | manuell auslösbar / deaktivierbar |

---

## 8. Code-Qualitätsregeln

### R-CODE-1 – Linter: ruff

```bash
make lint   # = ruff check .
make fmt    # = ruff format .
```

Kein PR-Merge mit Lint-Fehlern. `ruff` ist der einzige Python-Linter (kein flake8, pylint parallel).
Generierte bzw. vendored Protobuf-Ausgaben unter `gui/lnd_deps/*_pb2.py` und `gui/lnd_deps/*_pb2_grpc.py` sind bewusst vom Ruff-Lauf ausgenommen, weil sie toolchain-abhängig erzeugt werden und nicht manuell gepflegter Anwendungscode sind.

### R-CODE-2 – Typ-Annotationen für neue Funktionen

Neue Python-Funktionen erhalten Typ-Annotationen. Bestehende Funktionen die modifiziert werden, ebenfalls:

```python
# ❌ Keine Annotationen
def get_channel_score(chan_id, window):
    ...

# ✅ Mit Annotationen
def get_channel_score(chan_id: str, window: int) -> float:
    ...
```

### R-CODE-3 – API-Versionierung

Neue API-Endpunkte werden unter `/api/v2/` implementiert. Bestehende `/api/v1/`- bzw. `/api/`-Endpunkte erhalten **keine Breaking Changes** – sie bleiben kompatibel für bestehende Nutzer und externe Integrationen.

### R-CODE-4 – Keine bestehenden Views entfernen

Bestehende Views werden **nicht gelöscht**. Sie werden als `[Expert/Legacy]` in der Navigation markiert und weiterhin unter ihren bestehenden URLs erreichbar gehalten. Kein Breaking Change für bestehende Nutzer, Bookmarks oder externe Verlinkungen.

### R-CODE-5 – Migration-Check vor jedem Commit

```bash
python manage.py migrate --check
```

Muss grün sein. Kein Commit mit nicht angewendeten Migrationen oder fehlenden Migrations-Dateien für neue Models.

---

## 9. KI-Prompt-Checkliste

Bei jedem KI-Prompt zur Code-Generierung diese Prüfpunkte als Kontext mitgeben. Nicht zutreffende Punkte mit `n/a` markieren.

```
ENTWICKLUNGSREGEL-CHECKLISTE (LNDg Next)
=========================================

□ R-GUI-1:  Welchem Betriebsmodus gehört das Feature?
            → guided | advanced | expert
            → Default für neue Features: advanced

□ R-I18N-1: Sind alle UI-Strings für Übersetzung markiert?
            → {% trans %} / _("") / t('key')

□ R-ARCH-2: Wird auf Backend-Typ geprüft?
            → NEIN → Capability prüfen statt Backend-Typ

□ R-ARCH-1: Wird LightningWriteAdapter importiert?
            → NUR aus executor.py erlaubt

□ R-DM-3:   Enthält das Model Bitcoin-Beträge?
            → BigIntegerField (sats/msats), niemals FloatField

□ R-GUI-3:  Ist es eine automatisierte Aktion?
            → dry_run=True als Default

□ R-DM-5:   Erzeugt das Model wachsende Daten?
            → Bereinigungsregel in cleaner.py erforderlich

□ R-AI-1:   Greift KI/ML auf Write-Adapter zu?
            → VERBOTEN – nur Recommendation-Objekte erzeugen

□ R-GUI-2:  Gibt es Impact-Vorschau + Risiko-Label?
            → Pflicht bei jeder schreibenden Aktion

□ R-AI-5:   Enthält die Empfehlung confidence + confidence_label?
            → Pflicht – niemals nackte Empfehlung

□ R-DM-6:   Sind Betragsfelder eindeutig benannt?
            → amount_sat / amount_msat, nicht generisch "amount"

□ R-I18N-5: Sind DE + EN Übersetzungen vorhanden?
            → Beide Sprachen vor dem Merge
```

---

## 10. Glossar

Verbindliche Begriffsdefinitionen für dieses Projekt. Gelten gleichermaßen in Prompts, Code, Kommentaren und Dokumentation.

| Begriff | Definition |
|---|---|
| **Splice / Splice In / Splice Out** | Anpassung der Kapazität eines bestehenden Lightning-Channels ohne Schließen und Wiedereröffnen. Splice In = Kapazität erhöhen (On-Chain-Mittel einzahlen). Splice Out = Kapazität reduzieren und Mittel On-Chain auszahlen. CLN-nativ ab v24.02; LND in Entwicklung. |
| **LightningReadAdapter** | Schreibgeschützte Abstraktionsschicht für Node-Daten (Channels, Peers, Forwards). Darf von allen Modulen importiert werden. |
| **LightningWriteAdapter** | Schreibzugriff auf den Node (Fee-Policies, Splice, etc.). Darf **ausschließlich** aus `executor.py` aufgerufen werden. |
| **BackendCapabilities** | Dataclass, die die Fähigkeiten eines konkreten Node-Backends beschreibt (`can_splice`, `can_auto_fee`, etc.). UI entscheidet anhand von Capabilities, nie anhand des Backend-Namens. |
| **Policy** | Konfigurierte Automatisierungsregel bestehend aus: Trigger + Aktion + Limits + Cooldown. Immer mit `dry_run=True` als Default. |
| **PolicyRun** | Protokoll einer einzelnen Policy-Ausführung mit Auslöser, Zeitstempel, ausgeführten Aktionen und Ergebnis. `executor.py` handelt nur auf Basis eines validierten `PolicyRun`. |
| **Shadow Mode** | Betriebsmodus von ML-Funktionen: Empfehlungen werden berechnet und geloggt, aber **nicht ausgeführt**. Dient dem Vertrauensaufbau und der Modellvalidierung. |
| **dry_run** | Flag auf Policy, Recommendation oder Aktion. Wenn `True`: Simulation ohne echte Ausführung. Ergebnis wird in `dry_run_result` gespeichert. Default immer `True`. |
| **guided / advanced / expert** | Betriebsmodi des Nutzers. `guided` = erklärender Einsteigermodus (nur sichere Aktionen). `advanced` = Default für neue Features. `expert` = voller Zugriff inkl. Policy-Engine, ML-Automation, A/B-Experimente. |
| **rationale** | JSON-Objekt im `Recommendation`-Model das die Begründung einer Empfehlung strukturiert enthält: `reasons[]`, `confidence`, `confidence_label`, `data_source`, `data_window_days`. |
| **ChangeLog** | Audit-Trail aller Änderungen. Jeder Eintrag enthält: Zeitstempel, `change_type`, `target_chan_id`, `actor` (manual / policy / ml), `old_value`, `new_value`, `rationale`. Wird niemals automatisch gelöscht. |
| **ForwardingAggregate** | Voraggregierte Forwarding-Daten für schnelle Chart-Abfragen (1d/7d/30d-Fenster). Wird nie auto-bereinigt (klein, wertvoll). |
| **ChannelSnapshot** | Zeitreihen-Eintrag des Kanal-Zustands (Balance, Fee-Rate, Aktivität) zu einem bestimmten Zeitpunkt. Wird alle 15 Min (konfig.) gespeichert und nach konfigurierbarer Aufbewahrungsdauer bereinigt. |
| **confidence_label** | Herkunfts-Klassifizierung einer Empfehlung: `heuristic` (regelbasierte Heuristik ohne ML), `rule_based` (explizite Regel), `ml_shadow` (ML im Shadow-Mode), `ml_model` (aktives ML-Modell). |
| **Recommendation** | Django-Model das eine generierte Handlungsempfehlung der Recommendation Engine speichert. Enthält `rec_type`, `rationale`, `confidence`, `risk_level`, `status`, `dry_run_result`. |
| **Progressive Disclosure** | UX-Prinzip: Komplexität wird schrittweise freigeschaltet je nach Betriebsmodus (guided → advanced → expert). Schützt Einsteiger vor Überforderung. |
| **ai_safe_actions** | Liste in `BackendCapabilities` die definiert, welche `LightningWriteAdapter`-Aktionen für `policy_bound`-KI freigegeben sind (z.B. `['update_fee_policy']` – nie `splice_in`/`splice_out` ohne explizites Opt-in). |
