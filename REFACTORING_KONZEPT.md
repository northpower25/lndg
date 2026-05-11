# LNDg Next – Umfassendes Refactoring-Konzept

> **Version:** 1.5 · **Status:** Konzept / Aktiv (Grundentscheidungen getroffen, Phase 1 kann beginnen)  
> **Sprache dieses Dokuments:** Deutsch (Multilanguage-Fähigkeit ist Teil des Konzepts)

---

## Inhaltsverzeichnis

1. [Leitbild & Ziele (Product North Star)](#1-leitbild--ziele-product-north-star)
2. [UX-Grundprinzipien](#2-ux-grundprinzipien)
3. [Informationsarchitektur & Navigation](#3-informationsarchitektur--navigation)
4. [Guided Routing: Der Lernpfad im Produkt](#4-guided-routing-der-lernpfad-im-produkt)
5. [Empfehlungs-Engine](#5-empfehlungs-engine)
6. [Automationen: Auto-Fee & Rebalancing](#6-automationen-auto-fee--rebalancing)
7. [Externe Datenquellen](#7-externe-datenquellen)
8. [Grafische & zeitgemäße Darstellung](#8-grafische--zeitgemässe-darstellung)
9. [Backend-Konzept](#9-backend-konzept)
10. [Multilanguage-Fähigkeit](#10-multilanguage-fähigkeit)
11. [Backup / Restore & Datenbank-Bereinigung](#11-backup--restore--datenbank-bereinigung)
12. [Build-Prozess-Optimierung](#12-build-prozess-optimierung)
13. [UI/UX-Hybrid-Strategie](#13-uiux-hybrid-strategie)
14. [Implementierungsfahrplan](#14-implementierungsfahrplan)
15. [Zusätzliche Ideen & Erweiterungsvorschläge](#15-zusätzliche-ideen--erweiterungsvorschläge)
16. [Offene Fragen & Entscheidungsbedarfe](#16-offene-fragen--entscheidungsbedarfe)
17. [Multi-Backend-Architektur: LND & CLN (inkl. Channel-Splice)](#17-multi-backend-architektur-lnd--cln-inkl-channel-splice)
18. [KI & Agentic KI – Advisory, Safety und graduierte Autonomie](#18-ki--agentic-ki--advisory-safety-und-graduierte-autonomie)
19. [ToDo-Liste / Implementierungs-Tracking](#19-todo-liste--implementierungs-tracking)

---

## 1. Leitbild & Ziele (Product North Star)

### Zielgruppe

Neue Routing-Node-Betreiber, die:

1. **Verstehen** wollen, was passiert
2. **Lernen** wollen, warum etwas funktioniert
3. Später **automatisieren** – aber sicher

Sekundäre Zielgruppe: erfahrene Betreiber, die maximale Kontrolle bei geringem kognitiven Aufwand wünschen.

### Strategische Vision

> **LNDg Next ist von Anfang an für LND und CLN gebaut – gleichzeitig, nicht nacheinander.**

LNDg entwickelt sich von einem „LND-Tool" zu einem **Lightning Node Intelligence Layer** – der ersten modernen GUI, die beide führenden Lightning-Implementierungen (LND + CLN) vollständig unterstützt, erklärt und optimiert.

**Kernwertversprechen:**

- **LND-Nutzer:** Beste-in-Klasse Routing-Optimierung mit ML-gestützter Automation
- **CLN-Nutzer:** Erste vollwertige, erklärende GUI für Core Lightning – inkl. nativer **Channel-Splice**-Unterstützung
- **Für alle:** Channel-Größen dynamisch anpassen ohne Close/Reopen – das ist das Alleinstellungsmerkmal der Routing-Node-Verwaltung

### Produktziele (messbar / implementierbar)

| Ziel | Messkriterium | Mechanismus im Produkt |
|---|---|---|
| **Time-to-First-Understanding** | Einsteiger kann Inbound/Outbound, Fees, Rebalancing, Peer-Wahl erklären | Onboarding-Wizard + Glossar-Tooltips |
| **Time-to-First-Improvement** | UI zeigt klare „Nächste beste Aktion" mit Simulation | Recommendation Engine + Dry-Run |
| **Safety First** | Automationen standardmäßig Dry-Run, rate-limitiert, mit Rollback | Policy-Engine + Audit-Log |
| **Wachstumspfad** | Feature-Freischaltung durch Modus-Aufstieg | Progressive Disclosure (Guided → Advanced → Expert) |
| **CLN-First-GUI** | CLN-Nutzer können Node vollständig über LNDg verwalten | Backend-Adapter + Capability-UI + CLN-Onboarding |
| **Splice-Workflows** | Routing-Nodes können Channel-Kapazität ohne Close/Reopen anpassen | Guided Splice-In/Out Workflow (CLN nativ, LND wenn verfügbar) |

---

## 2. UX-Grundprinzipien

### 2.1 Progressive Disclosure durch Betriebsmodi

| Modus | Zielgruppe | Merkmale |
|---|---|---|
| **Guided** (Beginner) | Einsteiger, < 3 Monate Erfahrung | Erklärt, empfiehlt, lässt nur sichere Änderungen zu. Keine Rohwerte ohne Kontext. |
| **Advanced** | Betreiber mit Grundkenntnissen | Mehr Metriken, Bulk-Aktionen, weiterhin Schutzplanken |
| **Expert** | Erfahrene Betreiber | Voller Zugriff inkl. Auto-Fee/Rebalance-Regeln & Policy-Engine, A/B-Experimente |

**Wichtig:** Die gleichen Daten – aber unterschiedliche Darstellung und Interaktionsrechte. Der Modus ist jederzeit umschaltbar und wird im Profil gespeichert. Beim ersten Start ist immer **Guided** aktiv.

### 2.2 Aufgabenorientierung statt Tabellenorientierung

Nutzer sieht immer in dieser Reihenfolge:

```
1. Was ist der aktuelle Zustand?
2. Warum ist er so?
3. Was sollte ich tun?
4. Was ist bereits passiert? (Audit-Trail)
```

Tabellen sind nicht verboten – sie sind in Advanced/Expert weiterhin verfügbar – aber nicht der Default-Einstieg für Einsteiger.

### 2.3 Jede Aktion braucht: Impact-Vorschau + Risiko

Kein Einstellungs-Commit ohne:

- **Impact-Vorschau** (z. B. „Fee-Änderung wird voraussichtlich X beeinflussen")
- **Risiko-Label** (niedrig / mittel / hoch) mit visueller Kennzeichnung
- **Undo/Restore** (Policy-Snapshot wird automatisch vor jeder Änderung erstellt)

### 2.4 Erklärbarkeit als Designprinzip

Jede Zahl, jede Empfehlung, jede Automatisierungs-Aktion hat einen „Warum?"-Kontext. Dieser ist im Guided-Modus immer sichtbar, in Advanced per Tooltip, in Expert ausblendbar.

---

## 3. Informationsarchitektur & Navigation

### 3.1 Neue Hauptnavigation (5 Kernbereiche)

```
┌──────────────────────────────────────────────────────┐
│  🏠 Cockpit  │  ⚡ Channels  │  🤝 Peers  │  🤖 Automationen  │  📚 Lernen & Verlauf  │
└──────────────────────────────────────────────────────┘
```

Diese Struktur ersetzt die „gewachsene" Seitenliste (Advanced/Stats/Performance verteilt über viele URLs). Alte Views werden nicht parallel weitergeführt, sondern domänenbasiert in die neue Struktur überführt oder entfernt.

### 3.2 Cockpit (Einsteiger-Dashboard)

Kacheln + Story-Panels statt Tabellen:

| Kachel | Datenquelle (aktuelles LNDg) | Darstellung |
|---|---|---|
| Routing-Aktivität (7d/30d) | `Forwards`-Tabelle | Sparkline + Trend |
| Liquiditätsbalance | `Channels.local_balance` / `remote_balance` | Donut-Chart |
| Fee-Positionierung | `Channels.local_fee_rate` | Relative Positionierung vs. Peer-Durchschnitt |
| Probleme | `FailedHTLCs`, `local_disabled` | Warnhinweis-Banner (wenn vorhanden) |
| Nächste beste Aktion | Recommendation Engine | Top-3 Aktionen mit Priorität |

### 3.3 Channels-Bereich (Karten-/Listenhybrid)

**Default (Guided):** Channel-Karten mit:

- **Rolle** (UI-Label): „Routing", „Inbound-Magnet", „Balanced", „Parking"
- **Zustand**: „zu wenig Outbound", „zu wenig Inbound", „stagnierend", „gesund"
- **1-Klick**: „Empfohlene Aktion ansehen"

**Advanced/Expert:** Umschaltbar zur Tabellenansicht mit:

- Spalten-Presets: „Beginner", „Fees", „Flows", „Risk", „ROI"
- Inline-Tooltips (Glossar)
- Bulk-Aktionen (mehrere Channels gleichzeitig bearbeiten)
- **Kanal-Gruppen / Tags:** Channels können zu benannten Gruppen zusammengefasst werden (z. B. „Premium Peers", „Inbound-Anker"). Gruppen erben globale Policy-Defaults und können gruppenspezifische Overrides erhalten. Kanalgruppen sind die Grundlage für Bulk-Aktionen und granulare Policy-Zuweisung (siehe Abschnitt 6.1). Ein Channel kann mehreren Gruppen angehören, sofern keine Konflikte in gemeinsamen Einstellungen entstehen.
- **Channel-Aktionen** (kontextsensitiv, abhängig von Backend-Capabilities):
  - **Splice In** – Kapazität erhöhen ohne Close (CLN nativ; LND wenn Capability aktiv)
  - **Splice Out** – Kapazität reduzieren und On-Chain auszahlen
  - **Rebalance** – Liquidität verschieben
  - **Close** – Kanal kooperativ schließen (mit Kostenampel)

### 3.4 Peers-Bereich

- Peer-Karten mit Verbindungsqualität, Ping-Zeit, Channel-Übersicht
- „Peer entdecken"-Flow (gefiltert nach eigener Topologie, nicht generisch)
- Integration externer Peer-Daten (Amboss) als optionale Ergänzung

### 3.5 Automationen-Bereich

- Policy Studio: Templates + Dry-Run + Schedule + Limits
- Auto-Fee Strategien (Conservative / Balanced / Revenue-Seeking)
- Rebalance-Plan (Queue + Erfolgsmessung)
- Ausführungsprotokoll (Audit-Log)

### 3.6 Lernen & Verlauf

- **Glossar**: Kontext-Tooltips + „Mehr erfahren"-Links
- **Missions**: Kurze Lernaufgaben (z. B. „Balance herstellen", „Fee-Strategie verstehen")
- **Änderungsverlauf**: Jede Fee-Änderung/Rebalance als Timeline (wer/was/warum/Ergebnis)
- **Dokumentation**: Inline-Hilfe, keine externe Wiki-Abhängigkeit für Grundlagen

---

## 4. Guided Routing: Der Lernpfad im Produkt

### 4.1 Onboarding-Wizard (15–20 Min, modular)

```
Schritt 1: Node-Profil wählen
  → „Routing Revenue" | „Payment Node" | „Balanced"

Schritt 2: Aktuelle Channels verstehen
  → UI zeigt: „So sieht deine In/Out-Verteilung aus"

Schritt 3: Was sind Fees?
  → Fee-Grundlagen (Base + ppm) im UI erklärt

Schritt 4: Was ist Rebalancing?
  → „Du verschiebst Liquidität, um Routing-Chancen zu erhöhen"

Schritt 5: Erste sichere Optimierung
  → Vorschlag mit Dry-Run / Simulation + „Warum"
```

Jeder Schritt ist **überspringbar** und **wiederholbar**. Fortschritt wird gespeichert. Onboarding kann jederzeit über „Lernen & Verlauf" erneut durchlaufen werden.

### 4.2 Kontextlernen (Micro-Learning)

- Jede Metrik hat ein „Warum relevant?"-Panel (aufklappbar)
- Jede Empfehlung hat ein „Welche Daten sprechen dafür?"-Modul (Explainability)
- Glossar-Begriffe werden im Text automatisch als Tooltip-Links hervorgehoben

---

## 5. Empfehlungs-Engine

### 5.1 Empfehlungstypen

| Typ | Beschreibung |
|---|---|
| **A – Open New Channel** | Neuer Peer oder Kapazitätserweiterung zu bestehendem Peer |
| **B – Splice In** | Kapazität eines bestehenden Channels erhöhen (kein Close nötig; CLN nativ, LND capability-abhängig) |
| **C – Splice Out** | Kapazität reduzieren und Überschuss On-Chain auszahlen (kein Close nötig) |
| **D – Close / Deprioritize** | Stagnation, Risiko, Opportunitätskosten – wenn Splice nicht sinnvoll oder verfügbar |
| **E – Rebalance** | Gezielt + kostensensitiv |
| **F – Fee Strategy** | Manuell, semi-auto oder auto |

### 5.2 Heuristiken (Phase 1 – sofort nutzbar)

Alle Signale basieren auf bereits vorhandenen LNDg-Daten:

| Signal | Datenquelle (aktuell) | Empfehlung |
|---|---|---|
| Stagnation: wenig/keine Outbound-Flüsse über Zeitfenster | `Forwards`, `Channels.total_sent` | Fee senken oder Peer kritisch prüfen |
| Einseitige Balance: Inbound ≫ Outbound | `Channels.local_balance` / `remote_balance` | Rebalance oder Fee-Signaling |
| Hohe failed HTLC-Rate | `FailedHTLCs` | Routing-Richtung deaktivieren, Peer prüfen |
| Peer-Konzentration: viele Channels zu ähnlichen Peers | `Channels.remote_pubkey` | Diversifikation empfehlen |
| Ungenutzte Kapazität + geringe Flüsse | `Channels.capacity`, `Forwards` | Reduce/Close erwägen |
| Hoher stabiler Outbound-Flow + Liquidität knapp | `Forwards`, `local_balance` | Kapazitätserweiterung erwägen: **Splice In** (wenn verfügbar) oder neuer Channel |
| Channel permanent einseitig (Inbound chronisch ≫ Outbound) | `Channels.local_balance`, `ChannelSnapshot`-Trend | **Splice Out** + Outbound in neuem Channel oder Rebalance; Close als letztes Mittel |

**UI-Ausgabe pro Empfehlung:**

```
┌─────────────────────────────────────────────┐
│ 💡 Empfehlung: Fee für [Peer] senken        │
│ Warum: Kein Outbound-Flow seit 14 Tagen     │
│ Risiko: Niedrig                             │
│ Erwarteter Effekt: Mehr Routing-Anfragen    │
│ Alternativen: [Rebalance] [Schließen]       │
│ [Simulation starten]  [Anwenden]            │
└─────────────────────────────────────────────┘
```

**Formalisiertes Rationale-Schema**

Jede Empfehlung verwendet ein standardisiertes JSON-Schema im `rationale`-Feld des `Recommendation`-Models (siehe Abschnitt 9.1). Das Schema gilt gleichermaßen für heuristische und spätere ML-Empfehlungen und ist die Grundlage für alle „Warum?"-Panels in der UI:

```json
{
  "reasons": [
    {"rank": 1, "signal": "no_outbound_flow", "value": "14 Tage",         "weight": 0.45},
    {"rank": 2, "signal": "balance_ratio",    "value": "78 % Inbound",    "weight": 0.35},
    {"rank": 3, "signal": "fee_vs_peers",     "value": "+39 % über Median","weight": 0.20}
  ],
  "data_source": "internal",
  "data_window_days": 30,
  "confidence": 0.72,
  "confidence_label": "heuristic",
  "alternatives": ["rebalance", "close"],
  "simulation_available": true
}
```

`confidence_label`-Typen: `heuristic` | `rule_based` | `ml_shadow` | `ml_model`. Das Schema ist in Phase 1 (nur Heuristik) sofort einsetzbar – ML-Modelle müssen nicht aktiv sein. Die KI-Sicherheitsarchitektur für das `Recommendation`-Model ist in Abschnitt 18 beschrieben.

### 5.3 ML-Komponente (Phase 2–3)

**Wichtig:** ML darf anfangs **nur beraten** ("shadow mode"), nicht automatisch ausführen.

**Datenbasis (intern):**
- Forwarding-Historie, Fee-Änderungen, Rebalance-Events
- Channel-Balance-Zeitreihen (`ChannelSnapshot` – neues Modell)
- Erfolg/Failure-Signale (HTLC-Fehlerstream via `FailedHTLCs`)

**Features (Beispiele):**
- Rolling windows: 1d/7d/30d (Volumen, Ertrag, Fail-Rate)
- Balance-Drift-Rate (wie schnell „kippt" ein Channel)
- Peer-Stabilität (Uptime-Proxy über `Peers.connected`-History)
- Fee-Elastizität: „Wie reagiert Flow auf Fee-Änderung?"

**Modelle:**
- **Start:** Gradient Boosting / Random Forest (tabellarische Daten, interpretierbar)
- **Output:** Policy-Vorschläge + Konfidenz-Score
- **Explainability:** SHAP-ähnliche Feature-Beiträge (UI: „Hauptgründe")

**Zusätzliche ML-Features für Rebalancing & Auto-Fee:**
- Kanal-Paar-Erfolgsrate: Welches (Ausgangs-/Zielkanal)-Paar gelingt wann mit welchem Betrag und welcher Gebühr?
- Zeitreihen-Features: Stunde, Wochentag, Tages-Segment (Nacht/Tag/Peak) als Eingangsgrößen
- Balance-Drain-Velocity: Wie schnell entleert sich ein Kanal → proaktive Fee-Anpassung statt reaktiver
- Inbound-Fee-Elastizität: Wie reagiert eingehender Flow auf Änderungen von Base-Fee und Inbound-Fee?
- HTLC-Größen-Verteilung: Welche min/max-HTLC-Konfiguration maximiert die Routing-Erfolgsrate?

**Guardrails:**
- Mindestdatenmenge (z. B. 30 Tage) bevor ML Empfehlungen ausgibt
- Konfidenz-Schwelle: unterhalb → nur „Beobachten"-Modus
- A/B-Experimente ausschließlich in Expert-Mode (Feature Flag)
- Shadow-Mode-Protokoll: ML-Empfehlungen werden geloggt und mit echtem Ausgang verglichen

---

## 6. Automationen: Auto-Fee & Rebalancing

### 6.1 Policy-Engine (statt „Checkbox = live")

Im bestehenden LNDg gibt es `af.py` (Auto-Fee) und `rebalancer.py`. „Next" führt eine strukturierte **Policy-Engine** ein:

**Policy-Bausteine:**

```
Trigger     → Balance-Schwelle, Flow-Trend, Zeit-basiert
Aktion      → Fee-Adjust, Rebalance-Attempt, Notify, Webhook
Limits      → max. Änderungen / Zeitraum, max. ppm-Delta
Cooldown    → verhindert Churn/Gossip (Mindestwartezeit zwischen Anpassungen)
```

**Sicherheitsmechaniken:**

- **Default:** Dry-Run + Preview (kein echtes Ausführen)
- „Apply" erfordert: Advanced/Expert-Modus + Impact-Preview bestätigt
- Jede Policy schreibt in Audit-Log mit: Zeitstempel, Auslöser, alter Wert, neuer Wert, Ergebnis
- **Policy-Snapshot:** Vor jeder Änderung wird der aktuelle Zustand gespeichert (ermöglicht Rollback)
- **Default-Konsistenz:** Alle Policy-Parameter-Defaults werden ausschließlich im Datenmodell (Policy-Objekt) definiert. Unterschiedliche Defaults zwischen Code und Datenbank (wie bei `lowliq_limit` im bestehenden System) werden durch explizite Default-Policy-Objekte strukturell vermieden.

### 6.2 Auto-Fee: „Wähle eine Strategie" statt 20 Parameter

**UI-Templates (Beginner-freundlich):**

| Template | Beschreibung | Anpassungsfrequenz | ppm-Delta-Cap |
|---|---|---|---|
| **Conservative** | Seltene Anpassungen, kleine Schritte | max. alle 7 Tage | ±10 % |
| **Balanced** | Moderat, reagiert auf Flow-Trends | alle 2–3 Tage | ±20 % |
| **Revenue-Seeking** | Aggressiver, aber mit Caps | täglich möglich | ±40 % |

Expert-Detailpanel: zeigt alle Parameter erst bei explizitem Aufklappen. Entspricht weitgehend dem existierenden `af.py`-Verhalten, aber konfigurierbar über UI statt Datenbank-Keys.

### 6.2a ML-gesteuertes Auto-Fee-Management (Phase 4–5)

Das bisherige regelbasierte Auto-Fee-System wird durch einen **dynamischen, ML-gestützten Mechanismus** ergänzt, der proaktiver und ganzheitlicher agiert:

**Proaktive statt reaktiver Gebührenanpassung:**

Das System wartet nicht, bis ein Kanal bereits vollständig entleert ist, bevor es die Gebühren erhöht. Stattdessen:
- Erkennt der ML-Algorithmus anhand der **Balance-Drain-Velocity** einen bevorstehenden Engpass (z. B. „Kanal wird bei aktuellem Trend in ~4 h unter 20 % Outbound fallen")
- Löst eine schrittweise Gebührenerhöhung aus, bevor der kritische Schwellenwert erreicht wird
- Passt die Anpassungsgeschwindigkeit der Drain-Rate an (schnelle Entleerung → schnellere Reaktion)

**Erweiterter Fee-Parameter-Scope:**

Alle relevanten Fee-Parameter werden in die dynamische Anpassung einbezogen:

| Parameter | Bisherig | Neu (ML-gesteuert) |
|---|---|---|
| `fee_rate` (ppm) | ✅ Bereits dynamisch | ✅ Weiterhin primär |
| `base_fee` | ❌ Statisch | ✅ Dynamisch (Einfluss auf kleine HTLC-Routing-Attraktivität) |
| `min_htlc` | ❌ Statisch | ✅ Dynamisch (Filterung unrentabler Kleinstpayments) |
| `max_htlc` | ❌ Statisch | ✅ Dynamisch (Schutz vor Übernutzung knapper Liquidität) |
| `inbound_fee` | ❌ Nicht berücksichtigt | ✅ Neu: ML-gesteuerte Inbound-Fee-Anpassung |

**ML-Lernmechanismus für Auto-Fee:**

```
Feature-Inputs:
  - Aktuelle Balance (local/remote), Balance-Trend (1h/4h/24h)
  - Historische Routing-Volumen nach Tageszeit/Wochentag
  - Failed-HTLC-Typen (fee_insufficient / temporary_channel_failure / ...)
  - Peer-Fee-Positionierung (relativ zum Netzwerk-Median)
  - Vergangene Fee-Änderungen + resultierender Flow-Effekt (Fee-Elastizität)

Modell-Output:
  - Empfohlener neuer Wert pro Parameter (ppm, base_fee, min/max_htlc, inbound_fee)
  - Konfidenz-Score + Begründung
  - Eskalationsstufe (kein Eingriff / leichte Anpassung / starke Anpassung)

Eskalations-/Deeskalationsprinzip:
  - Schrittweise Anpassung in konfigurierbaren Grenzen (min/max pro Parameter)
  - Bei positivem Routing-Signal: Deeskalation (Fee zurück senken)
  - Bei anhaltendem Drain trotz Erhöhung: weitere Eskalation
  - Cooldown: Mindestwartezeit zwischen zwei Anpassungen desselben Parameters
```

**Dynamische Zielanpassung basierend auf Routing-Verhalten:**

Das System beobachtet kontinuierlich das Routing-Verhalten und passt die Zielparameter an:
- Steigt das Routing-Volumen über einen Kanal, werden die Fee-Ziele nach oben angepasst
- Sinkt das Volumen trotz niedrigerer Fees, wird dies als Signal für strukturelle Probleme gewertet (nicht nur Fee-Problem)
- Änderungen im Netzwerk-Umfeld (Peer ändert Fees) werden erkannt und fließen in die Anpassung ein

**Konfigurierbare Grenzen (je Kanal oder global):**

```
fee_rate:    min: 1 ppm    max: 5000 ppm   step: konfigurierbar
base_fee:    min: 0 msat   max: 10000 msat step: konfigurierbar
min_htlc:    min: 1 msat   max: 100000 msat
max_htlc:    min: 100k sat max: 100% capacity
inbound_fee: min: -500 ppm max: +500 ppm   (Netzwerk-Grenzen beachten)
```

**UI-Transparenz:**
- Jede ML-getriggerte Änderung erscheint im Audit-Log mit Begründung
- „Warum?"-Panel: „Fee wurde erhöht, da Balance in 3 h unter Schwellenwert fallen würde (Konfidenz: 78 %)"
- Shadow-Mode: ML-Empfehlungen werden zuerst nur angezeigt, bis der Nutzer dem System vertraut

### 6.3 Rebalancing: „Budgetiert & zielgerichtet"

Rebalancing soll nicht „immer" laufen, sondern:

- **Budget** pro Tag/Woche (in sats oder ppm-Kosten)
- **Zielzustände** (z. B. Outbound-Quote ≥ 40 %)
- **Priorisierung:** Channels mit hohem erwartetem Nutzen (Heuristik/ML)
- **Balance-Berechnung:** Beim Start eines Rebalance-Versuchs wird die aktuelle Local Balance **ohne** unsettled HTLC-Saldo berechnet. Bei parallelen Rebalance-Versuchen auf demselben Kanal (MPP) sorgt dies dafür, dass kein Versuch einen Outbound-Target unterschreitet, der durch noch offene HTLCs bereits belastet ist.

**UI:** Rebalance-Plan (Queue) + Erfolgsmessung:

```
„Hat der Rebalance das Routing verbessert?"
  → Vergleich: Outbound-Flüsse 7 Tage vorher vs. 7 Tage nachher
```

### 6.3a ML-Modus für Rebalancing (Phase 4–5)

Das Rebalancing wird um einen **lernenden ML-Modus** ergänzt, der statische Regeln durch datengetriebene Erkenntnisse ersetzt:

**Lernziel des ML-Modells:**

LNDg lernt für jedes Kanalpar (Quell-/Zielkanal), zu welchen Zeitpunkten, mit welchen Beträgen und zu welchen Gebühren ein Rebalancing erfolgreich durchführbar ist und danach tatsächlich zu mehr Routing-Revenue führt.

```
ML lernt: (Quellkanal, Zielkanal, Tageszeit, Wochentag, Betrag, max_fee_ppm)
             → P(Erfolg) + E(Routing-Revenue-Verbesserung in 24h/48h/7d)
```

**Feature-Set für Rebalancing-ML:**

| Feature-Gruppe | Beispiel-Features |
|---|---|
| **Kanal-Zustand** | local_balance, remote_balance, capacity, Balance-Trend |
| **Historische Rebalance-Daten** | Erfolgsrate pro Kanalpar, durchschnittliche Kosten, Zeitdauer |
| **Zeitliche Features** | Stunde des Tages, Wochentag, Wochenende/Werktag |
| **Routing-Kontext** | Outbound-Flow letzter 24h/7d, Failed-HTLC-Rate, Peer-Stabilität |
| **Netzwerk-Kontext** | Peer-Fee-Änderungen, Channel-Aktivität des Peers |
| **Ergebnismessung** | Routing-Revenue Δ 24h/48h/7d nach Rebalance |

**Eskalations- und Deeskalationsprinzip:**

Das System passt Betrag und Gebühren schrittweise innerhalb konfigurierbarer Grenzen an:

```
Eskalation (wenn vorheriger Versuch erfolglos):
  Betrag:   aktueller_betrag × eskalationsfaktor (z. B. 0.75 → Betrag reduzieren)
  max_fee:  max_fee × eskalationsfaktor_fee (z. B. erhöhen um 10 %)
  → Maximal: definiertes Limit (z. B. max 500 ppm Rebalancing-Kosten)

Deeskalation (wenn Routing nach Rebalance gut läuft):
  Nächster Versuch: niedrigere Gebühr zuerst probieren
  → Bewährte Parameter werden bevorzugt wiederverwendet

Abbruch:
  Nach N erfolglosen Versuchen: Kanal temporär aus Queue entfernen
  → Nächster Versuch nach konfigurierter Wartezeit
```

**Dynamische Zielquoten (In-/Outbound):**

Die prozentualen Rebalancing-Ziele werden nicht mehr statisch gesetzt, sondern dynamisch anhand der tatsächlichen Liquiditätsbedürfnisse angepasst:

- **Liquiditätsbedarf-Analyse:** Channels mit hohem aktivem Outbound-Flow benötigen höhere Outbound-Quoten als inaktive Channels
- **Konfigurierbarer Puffer:** Zielquote = Mindestquote + dynamischer Puffer (z. B. 30 % Mindest-Outbound + 10–20 % Puffer je nach Flow-Stärke)
- **Routing-Verhaltens-Adaption:** Ändert sich das Routing-Muster (z. B. ein Peer wird inaktiv), werden die Zielquoten für betroffene Channels automatisch angepasst
- **Manuelle Override:** Nutzer kann für einzelne Channels fixe Zielquoten setzen (überschreibt ML-Empfehlung)

```
Dynamische Zielquote (Beispiel):
  Channel X hat durchschnittlich 80k sats/Tag Outbound-Flow
  → Ziel-Outbound: max(30%, min_outbound + flow_faktor × 15%) = z. B. 45%
  Channel Y hat 0 sats/Tag Outbound-Flow seit 7 Tagen
  → Ziel-Outbound: 30% (Minimum, kein Puffer nötig)
  
  Bei Routing-Änderung (Channel X Flow sinkt auf 10k sats/Tag):
  → Ziel-Outbound wird schrittweise auf 32% reduziert (Cooldown: 48h)
```

**Priorisierung der Rebalance-Queue:**

ML-Score bestimmt die Priorität der Rebalancing-Aufgaben:

```
Prioritätsscore = w1 × P(Erfolg) 
                + w2 × E(Routing-Revenue-Verbesserung)
                - w3 × geschätzte_Rebalancing-Kosten
                + w4 × Dringlichkeit (Balance kritisch?)

Queue-Reihenfolge: absteigend nach Prioritätsscore
```

**UI-Darstellung des ML-Rebalancing-Modus:**

- **ML-Modus-Toggle** im Rebalancing-Bereich (Guided/Advanced/Expert-abhängig)
- **Lern-Fortschritt-Anzeige:** „Das Modell hat X Kanalpaare analysiert, Y Muster gelernt"
- **Erklärbarkeit:** Pro Queue-Eintrag: „Warum jetzt? Warum dieser Betrag?" mit Top-3-Gründen
- **Erfolgs-Tracking:** Timeline der Rebalance-Events mit tatsächlichem vs. erwartetem Ergebnis
- **Shadow-Mode (Phase 4):** ML schlägt vor, Nutzer entscheidet; erst in Phase 5 volle Automation möglich

---

## 7. Externe Datenquellen

### 7.1 mempool.space (On-chain Kosten & Timing)

**Nutzen:** On-chain-Aktionen (Open/Close/Splice) sind fee-sensitiv.

**Integration:**
- Endpunkt: `GET /api/v1/fees/recommended`
- Cache: TTL 5–10 Min + Rate-Limit-Guard (429-Handling mit exponential backoff)
- Datenschutz: keine Channel- oder Node-Daten werden gesendet

**UI-Einsatz:**
- Bei jeder Open/Close-Empfehlung: Kostenampel (🟢 günstig / 🟡 ok / 🔴 teuer)
- „Wartefenster"-Vorschlag (ohne Zwang, nie blockierend)

### 7.2 Amboss Space (Peer-Daten & Netzwerk-Kontext)

**API:** GraphQL unter `https://api.amboss.space/graphql`

**Integration:**
- Optionaler API-Key (User-Settings)
- Abfrage **nur** für Peers, die bereits vorhanden oder aktiv evaluiert werden (Privacy/Overfetch vermeiden)
- Hinweis auf nicht-kommerzielle Nutzungsbedingungen im UI

**UI-Einsatz:**
- Peer-Cards: Netzwerk-Einordnung (Peer-Größe, Channel-Kriterien)
- Warnhinweise: Disabled-Channel-Kontext
- „Peer Discovery": Vorschläge gefiltert nach bestehender Topologie

### 7.3 Lightning Terminal / litd (optional, lokal)

- Nur aktiv, wenn litd lokal installiert ist (Auto-Detection)
- LiT-Autofee als alternative Strategy-Source anbindbar
- LNDg bleibt primär eigenständig; LiT ist „Enhancement"

### 7.4 CheeseRobot (Explorer-Kontext, sekundär)

- Optionale zweite Quelle für Netzwerk-Überblick (wenn JSON-Endpunkte verfügbar)
- Amboss ist strukturierter und hat Vorrang

### 7.5 Allgemeine Integrationsregeln

```
- Alle externen Calls: asynchron, nicht blockierend
- Fehler → graceful degradation (UI funktioniert ohne externe Daten)
- Kein Senden sensibler Node-Daten ohne explizite Nutzereinwilligung
- Cache-Layer: Redis oder Django's Cache-Framework (DB-Fallback)
- Rate-Limit-Handling: eigene Queue per Datenquelle
```

---

## 8. Grafische & zeitgemässe Darstellung

### 8.1 Neue Visual-Komponenten

| Komponente | Beschreibung | Datenquelle |
|---|---|---|
| **Liquidity Donut** | Inbound vs. Outbound pro Channel + Node-Gesamt | `Channels.local/remote_balance` |
| **Flow Sankey** | Peer-zu-Peer-Flüsse aggregiert | `Forwards` |
| **Channel Health Heatmap** | Zeit vs. Channel (Balance/Volume) | `ChannelSnapshot` (neu) |
| **Fee vs. Volume Scatter** | Zeigt Fee-Elastizität | `Forwards`, `FeeLog` |
| **Before/After Diff-View** | Nach Policy-Änderung (7d-Vergleich) | `ChangeLog` (neu) |
| **Rebalance Timeline** | Rebalance-Events vs. Routing-Erfolg | `Rebalancer`, `Forwards` |
| **Node Topology Graph** | Eigene Peers visualisiert als Netzwerk | `Channels`, `Peers` |

### 8.2 Explainability-UI

Jede Empfehlung hat ein aufklappbares „Warum"-Panel:

```
Hauptgründe (Top 3):
  1. Kein Outbound-Flow seit 14 Tagen (-70 % vs. 30d-Durchschnitt)
  2. Inbound > Outbound Balance: 78 % Inbound
  3. Fee-Rate: 250 ppm vs. Peer-Durchschnitt 180 ppm

Datenquelle: intern (LNDg-Daten, 30d)
Konfidenz: Heuristik (noch kein ML-Modell aktiv)
```

### 8.3 Mobile-First-Designregeln

- Kein Hover ohne Touch-Alternative
- Karten statt Tabellen (Default)
- Drawer / Bottom Sheets statt Modals
- Touch-Targets ≥ 44px
- Charts skalieren → Sparklines → Summaries auf kleinen Screens
- Keine horizontalen Scroll-Tabellen auf Mobile ohne Swipe-Hinweis

---

## 9. Backend-Konzept

> **Hinweis:** Die Backend-Schicht wird so strukturiert, dass LND und CLN beide als gleichrangige Implementierungen des abstrakten `LightningBackend`-Adapters gebaut werden. Die vollständige Adapter-Architektur inkl. CLN, Channel-Splice und Capability-System ist in [Abschnitt 17](#17-multi-backend-architektur-lnd--cln-inkl-channel-splice) beschrieben. Die KI-Sicherheitsarchitektur (Read/Write-Trennung, Action-Gateways) ist in [Abschnitt 18](#18-ki--agentic-ki--advisory-safety-und-graduierte-autonomie) beschrieben.

### 9.0 ReadAdapter / WriteAdapter – Strukturelle Sicherheitstrennung

Der `LightningBackend`-Adapter (Abschnitt 17.2) wird in zwei getrennte Interface-Klassen aufgeteilt. Diese Trennung ist ein Architektur-Constraint, der KI-Schreibzugriff strukturell unmöglich macht – nicht nur durch Konvention:

```python
class LightningReadAdapter:
    """Schreibgeschützte Schicht. Darf von Analyse, Empfehlungs-Engine und KI direkt genutzt werden."""
    def get_node_info(self) -> Node: ...
    def list_channels(self) -> list[Channel]: ...
    def list_peers(self) -> list[Peer]: ...
    def get_forwarding_events(self, start, end) -> list[ForwardingEvent]: ...
    def get_liquidity_state(self, channel_id) -> LiquidityState: ...
    def get_capabilities(self) -> BackendCapabilities: ...

class LightningWriteAdapter:
    """Schreibzugriff. Nur über den Validation Layer erreichbar – niemals direkt aus Views,
    Recommendation Engine oder KI-Modulen."""
    def update_fee_policy(self, channel_id, policy: FeePolicy) -> bool: ...
    def splice_in(self, channel_id: str, amount_sat: int, fee_rate: int) -> SpliceAction: ...
    def splice_out(self, channel_id: str, amount_sat: int, destination: str, fee_rate: int) -> SpliceAction: ...
    def get_splice_status(self, splice_id: str) -> SpliceAction: ...
```

**Datenfluss (Action-Gateway):**

```
KI / Recommendation Engine  ──►  Recommendation-Objekt (kein direkter API-Call)
                                          │
                                   Policy Engine
                                   (deterministische Regeln, konfigurierbarer Scope)
                                          │
                                   Validation Layer
                                   (Sanity-Checks, Hard Caps, Cooldown-Guard)
                                          │
                              Human Confirmation (UI) | Approved Automation (Policy-gebunden)
                                          │
                                  LightningWriteAdapter
                                  (einziger Ort mit Schreibrechten)
                                          │
                                    ChangeLog-Eintrag
```

`LightningReadAdapter` ist für alle Module zugänglich. `LightningWriteAdapter` wird ausschließlich vom `executor.py`-Job aufgerufen, der seinerseits nur über einen validierten `PolicyRun` aktiviert wird. Details zur KI-Sicherheitsarchitektur: Abschnitt 18.

### 9.1 Datenmodell-Erweiterungen (neue Models)

```python
# Neue Models (ergänzend zu bestehenden)

class ChannelSnapshot(models.Model):
    """Zeitreihe für Charts, Trend-Analyse und ML-Features."""
    timestamp = models.DateTimeField(db_index=True)
    chan_id = models.CharField(max_length=20, db_index=True)
    local_balance = models.BigIntegerField()
    remote_balance = models.BigIntegerField()
    capacity = models.BigIntegerField()
    local_fee_rate = models.IntegerField()
    local_base_fee = models.IntegerField()
    local_disabled = models.BooleanField()
    is_active = models.BooleanField()

    class Meta:
        app_label = 'gui'
        indexes = [models.Index(fields=['chan_id', 'timestamp'])]

class ForwardingAggregate(models.Model):
    """Voraggregierte Forwarding-Daten für schnelle Abfragen."""
    window = models.CharField(max_length=5)  # '1d', '7d', '30d'
    chan_id = models.CharField(max_length=20, db_index=True)
    window_start = models.DateTimeField()
    in_msat = models.BigIntegerField(default=0)
    out_msat = models.BigIntegerField(default=0)
    fees_msat = models.BigIntegerField(default=0)
    forward_count = models.IntegerField(default=0)
    fail_count = models.IntegerField(default=0)

    class Meta:
        app_label = 'gui'
        unique_together = (('window', 'chan_id', 'window_start'),)

class Recommendation(models.Model):
    """Erzeugte Empfehlungen der Recommendation Engine."""
    TYPES = [('open', 'Open Channel'), ('resize', 'Resize'), ('close', 'Close'),
             ('rebalance', 'Rebalance'), ('fee', 'Fee Strategy')]
    STATUS = [('pending', 'Pending'), ('applied', 'Applied'), ('dismissed', 'Dismissed'), ('expired', 'Expired')]
    created_at = models.DateTimeField(auto_now_add=True)
    rec_type = models.CharField(max_length=20, choices=TYPES)
    target_chan_id = models.CharField(max_length=20, null=True, blank=True)
    target_pubkey = models.CharField(max_length=66, null=True, blank=True)
    rationale = models.JSONField()          # { "reasons": [...], "data": {...} }
    confidence = models.FloatField()        # 0.0–1.0
    risk_level = models.CharField(max_length=10)  # low/medium/high
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    dry_run_result = models.JSONField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'gui'

class Policy(models.Model):
    """Automation-Policies (Auto-Fee, Rebalance-Regeln)."""
    name = models.CharField(max_length=100)
    policy_type = models.CharField(max_length=20)  # 'auto_fee', 'rebalance', 'notify'
    definition = models.JSONField()   # Trigger + Aktion + Limits + Cooldown
    is_active = models.BooleanField(default=False)
    dry_run = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_run = models.DateTimeField(null=True)
    mode_required = models.CharField(max_length=10, default='advanced')  # guided/advanced/expert

    class Meta:
        app_label = 'gui'

class PolicyRun(models.Model):
    """Protokoll jeder Policy-Ausführung."""
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE)
    executed_at = models.DateTimeField(auto_now_add=True)
    was_dry_run = models.BooleanField()
    trigger_data = models.JSONField()
    actions_taken = models.JSONField()
    outcome = models.JSONField(null=True)

    class Meta:
        app_label = 'gui'

class ChangeLog(models.Model):
    """Audit-Trail aller Änderungen."""
    timestamp = models.DateTimeField(auto_now_add=True)
    change_type = models.CharField(max_length=30)  # fee_update, rebalance, policy_apply, ...
    target_chan_id = models.CharField(max_length=20, null=True)
    actor = models.CharField(max_length=20)  # manual / policy_name / auto
    old_value = models.JSONField(null=True)
    new_value = models.JSONField(null=True)
    rationale = models.TextField(blank=True)
    policy_run = models.ForeignKey(PolicyRun, null=True, on_delete=models.SET_NULL)

    class Meta:
        app_label = 'gui'
        indexes = [models.Index(fields=['timestamp']), models.Index(fields=['target_chan_id'])]

class RebalanceMLRecord(models.Model):
    """Lernhistorie für ML-Rebalancing: Kanalpar + Kontext + Ergebnis."""
    timestamp = models.DateTimeField(db_index=True)
    source_chan_id = models.CharField(max_length=20, db_index=True)
    target_chan_id = models.CharField(max_length=20, db_index=True)
    amount_sat = models.BigIntegerField()
    fee_ppm = models.IntegerField()
    hour_of_day = models.IntegerField()    # 0–23
    day_of_week = models.IntegerField()    # 0–6
    success = models.BooleanField()
    routing_revenue_delta_24h = models.BigIntegerField(null=True)  # Δ nach 24h
    routing_revenue_delta_7d = models.BigIntegerField(null=True)   # Δ nach 7d
    ml_predicted_success_prob = models.FloatField(null=True)
    ml_confidence = models.FloatField(null=True)

    class Meta:
        app_label = 'gui'
        indexes = [models.Index(fields=['source_chan_id', 'target_chan_id', 'timestamp'])]

class AutoFeeMLRecord(models.Model):
    """Lernhistorie für ML-Auto-Fee: Parameteränderung + Ergebnis."""
    timestamp = models.DateTimeField(db_index=True)
    chan_id = models.CharField(max_length=20, db_index=True)
    param_name = models.CharField(max_length=20)  # fee_rate, base_fee, min_htlc, max_htlc, inbound_fee
    old_value = models.BigIntegerField()
    new_value = models.BigIntegerField()
    trigger_reason = models.CharField(max_length=50)  # drain_velocity / low_flow / high_flow / ...
    ml_confidence = models.FloatField(null=True)
    routing_volume_delta_24h = models.BigIntegerField(null=True)
    routing_revenue_delta_24h = models.BigIntegerField(null=True)
    escalation_level = models.IntegerField(default=0)  # 0=neutral, >0=eskaliert, <0=deeskaliert

    class Meta:
        app_label = 'gui'
        indexes = [models.Index(fields=['chan_id', 'timestamp'])]


    """Nutzer-Betriebsmodus und Onboarding-Fortschritt."""
    mode = models.CharField(max_length=10, default='guided')  # guided/advanced/expert
    onboarding_step = models.IntegerField(default=0)
    onboarding_completed = models.BooleanField(default=False)
    language = models.CharField(max_length=10, default='de')
    updated_at = models.DateTimeField(auto_now=True)

    # KI-Feature-Flags (alle Default: off / conservative)
    # Aktivierung erfordert explizite Nutzeraktion im Expert-Modus (siehe Abschnitt 18.4)
    ai_mode = models.CharField(max_length=20, default='off')
    # Werte: 'off' | 'advisory' | 'shadow' | 'policy_bound'
    ai_explain_always = models.BooleanField(default=True)
    ai_min_data_days = models.IntegerField(default=30)
    ai_max_auto_actions_day = models.IntegerField(default=0)  # 0 = manuell only
    ai_cooldown_minutes = models.IntegerField(default=60)
    ai_shadow_log_enabled = models.BooleanField(default=True)

    class Meta:
        app_label = 'gui'
```

### 9.2 Service-Architektur (Jobs)

Das bestehende `jobs.py` wird in klare Verantwortlichkeiten aufgeteilt:

```
jobs/
├── collector.py      # Holt LND-Daten → ChannelSnapshot, Peers, Forwards
├── aggregator.py     # Berechnet ForwardingAggregates aus Rohdaten
├── analyzer.py       # Berechnet Channel-Scores, Peer-Scores
├── recommender.py    # Erzeugt Recommendations (Heuristik + optional ML)
├── executor.py       # Führt Policies aus (nur wenn erlaubt + nicht dry_run)
├── ml_trainer.py     # Trainiert/aktualisiert ML-Modelle (Rebalancing + Auto-Fee)
├── ml_predictor.py   # Erzeugt ML-Vorschläge (Rebalancing-Queue, Fee-Anpassungen)
├── notifier.py       # UI-Notifications / Webhooks
└── cleaner.py        # DB-Bereinigung (siehe Abschnitt 11)
```

**Collector-Intervalle:**
- Channel-Snapshots: alle 15 Min (konfigurierbar)
- Forwarding: alle 5 Min
- Aggregates: stündlich (Batch)
- Empfehlungen: alle 30 Min (konfigurierbar)
- ML-Training: täglich (nächtlich, konfigurierbar; bei Ressourcenmangel: manuell auslösbar)
- ML-Predictions (Rebalancing-Queue-Update): alle 30 Min oder nach Rebalance-Event

**gRPC-Verbindungsmanagement:**
gRPC-Credentials (TLS-Zertifikat + Macaroon) werden einmalig beim Start des Collector-Jobs geladen und gecacht – nicht pro Anfrage neu gelesen. Die gRPC-Connection wird über den gesamten Job-Lifecycle wiederverwendet (kein Connection-Overhead pro Snapshot). Bei Verbindungsabbruch erfolgt automatisches Reconnect mit Backoff. Async ORM-Methoden (`aget`, `afilter`, `abulk_create`) werden im gesamten Job-Stack bevorzugt, um Event-Loop-Blockaden zu vermeiden.

### 9.3 API-Layer v2

Neue versionierte REST-Endpunkte (parallel zu bestehender API):

```
GET  /api/v2/overview                    # Cockpit-Daten
GET  /api/v2/channels?mode=guided        # Channel-Liste mit Labels
GET  /api/v2/channels/{id}/history       # Zeitreihe für einen Channel
GET  /api/v2/recommendations             # Aktuelle Empfehlungen
POST /api/v2/recommendations/{id}/apply  # Empfehlung anwenden
POST /api/v2/recommendations/{id}/dryrun # Dry-Run simulieren
GET  /api/v2/policies                    # Policy-Liste
POST /api/v2/policies                    # Neue Policy anlegen
PUT  /api/v2/policies/{id}               # Policy aktualisieren
POST /api/v2/policies/{id}/run           # Policy manuell ausführen
GET  /api/v2/changelog                   # Audit-Trail
GET  /api/v2/changelog/{id}/rollback     # Rollback-Vorschau
POST /api/v2/changelog/{id}/rollback     # Rollback ausführen
GET  /api/v2/ml/rebalance/suggestions    # ML-Rebalancing-Vorschläge (Queue)
GET  /api/v2/ml/rebalance/history        # Lernhistorie Kanalpar-Erfolg
POST /api/v2/ml/rebalance/train          # Manuelles Modell-Retraining auslösen
GET  /api/v2/ml/autofee/suggestions      # ML-Auto-Fee-Vorschläge
GET  /api/v2/ml/autofee/history          # Lernhistorie Fee-Anpassungen + Ergebnis
GET  /api/v2/ml/status                   # Modell-Status (Konfidenz, Datenmenge, letztes Training)

# Channel-Management (Splice, wenn Backend-Capability vorhanden)
GET  /api/v2/channels/{id}/splice/preview   # Vorschau: Kosten + Effekt eines Splice
POST /api/v2/channels/{id}/splice/in        # Splice-In ausführen (Kapazität erhöhen)
POST /api/v2/channels/{id}/splice/out       # Splice-Out ausführen (Kapazität reduzieren + Auszahlung)
GET  /api/v2/channels/{id}/splice/status    # Status eines laufenden Splice-Vorgangs
```

**Optional:** WebSocket/SSE für Live-Updates (statt Auto-Refresh-Polling). Empfohlen für Rebalance-Status und HTLC-Stream.

### 9.4 Sicherheits- und Rechtekonzept

**Rollen:**

| Rolle | Kann | Kann nicht |
|---|---|---|
| `viewer` | Alle Daten lesen, Empfehlungen sehen | Änderungen vornehmen |
| `operator` | Manuelle Aktionen, Dry-Run | Policy-Engine konfigurieren |
| `expert` | Alles, inkl. Policy-Engine, A/B-Experimente | – |

**Mechaniken:**

- Macaroon-Scopes: Read-only vs. Write (bei LND-Integration)
- Jede Write-Aktion benötigt: Audit-Log + Policy-Snapshot + Undo-Option
- Rate-Limiting auf alle schreibenden API-Endpunkte
- CSRF-Schutz für alle Formulare (bereits via Django vorhanden, beibehalten)
- **SSH-Verbindungen** (z. B. für Channel-DB-Size-Feature): `RejectPolicy` statt `AutoAddPolicy`; Hosts müssen in `~/.ssh/known_hosts` eingetragen sein – kein automatisches Akzeptieren unbekannter Hosts (MITM-Schutz)
- **Sensitive Dateien** (z. B. Admin-Passwort): werden mit `mode=0o600` erstellt; keine World-Readable-Defaults
- **Dependency-Pinning:** `requirements.txt` verwendet explizite Mindestversionen mit oberer Grenze (z. B. `Django>=4.2,<5.0`) um Sicherheitslücken durch veraltete oder brechende Versionen zu vermeiden (`pip-compile` aus `requirements.in`)
- **KI-Zugriffsrechte:** KI-Module (`recommender.py`, `ml_predictor.py`) dürfen ausschließlich `LightningReadAdapter` und Django ORM Leseoperationen nutzen. Kein direkter Import von `LightningWriteAdapter` in KI-Modulen. Validierung per statischer Analyse (Linter-Regel) erzwingbar. Details: Abschnitt 18.

---

## 10. Multilanguage-Fähigkeit

### 10.1 Strategie

LNDg Next soll vollständig internationalisierbar sein. Als primäre Sprachen sind **Deutsch** und **Englisch** vorgesehen; weitere Sprachen werden durch Community-Beiträge ergänzt.

### 10.2 Backend (Django i18n)

Django hat ein ausgereiftes Internationalisierungs-Framework, das genutzt wird:

```python
# settings.py
LANGUAGE_CODE = 'de'  # Default
USE_I18N = True
USE_L10N = True
LANGUAGES = [
    ('de', 'Deutsch'),
    ('en', 'English'),
    ('es', 'Español'),
    ('fr', 'Français'),
    ('zh-hans', '中文'),
    # Weitere nach Bedarf
]
LOCALE_PATHS = [BASE_DIR / 'locale']
```

**Alle Strings** in Templates und Views werden mit `{% trans "..." %}` bzw. `_("...")` markiert.

Übersetzungsdateien (`.po`/`.mo`) liegen unter `locale/<lang>/LC_MESSAGES/django.po`.

### 10.3 Frontend (SPA)

Für die React/SPA-Schicht wird **i18next** (oder `react-i18next`) verwendet:

```
frontend/
└── locales/
    ├── de/translation.json
    ├── en/translation.json
    └── ...
```

Sprachauswahl wird im `UserMode`-Model gespeichert und über `/api/v2/user/settings` gelesen.

### 10.4 Sprache-Switch im UI

- Prominenter Sprach-Switcher im Header (Flag + Kürzel)
- Sprachauswahl sofort aktiv (kein Reload erforderlich im SPA)
- Im Guided-Onboarding: Sprachauswahl als erster Schritt

### 10.5 Übersetzungs-Workflow

- Neue Strings: `makemessages -l de -l en` → `.po`-Datei aktualisieren
- Kompilierung: `compilemessages` → `.mo` generieren
- CI-Check: fehlende Übersetzungen erzeugen Warning (kein Blocken)
- Empfehlung: Weblate oder Crowdin als Community-Übersetzungsplattform

### 10.6 Datumsformate & Zahlenformate

- Datumsformat richtet sich nach gewählter Sprache (Django `USE_L10N`)
- Satoshi-Beträge: einheitlich als sats mit optionaler mBTC/BTC-Umschaltung
- Zahlenformate (Trennzeichen) passen sich der Locale an
- **Locale-sicheres Zahlen-Parsing im Frontend:** JS-Hilfsfunktionen (`intcomma`, `toInt`) dürfen nicht blind auf Komma als Tausend-Trenner angewiesen sein – in vielen Locales ist der Trenner ein Leerzeichen oder Punkt. Korrekte Implementierung: beim Zurückrechnen alle Nicht-Ziffern-Zeichen entfernen (`replace(/\D/g, '')`) statt nur Kommas. Betrifft alle numerischen Eingabefelder (Beträge, Fees, Limits).

---

## 11. Backup / Restore & Datenbank-Bereinigung

### 11.1 Backup-Funktion

**Scope:** Backup umfasst:
1. **Settings-Backup**: Alle `LocalSettings` + `Policy`-Objekte (JSON/YAML-Export)
2. **Vollständiges DB-Backup**: Gesamter Datenbankdump (SQLite: `.db`-Datei; PostgreSQL: `pg_dump`)
3. **LND-Macaroon-Backup**: Optional, falls Macaroon-Pfade in Settings hinterlegt sind

**UI-Flow:**

```
[Backup erstellen]
  → Typ wählen: „Nur Settings" | „Vollständige DB" | „Beides"
  → Optional: Passwortschutz (AES-256)
  → Download als .tar.gz
  → Eintrag in BackupLog (wann/was/Größe/Hash)
```

**Automatisches Backup:**
- Konfigurierbar: täglich/wöchentlich (Cron-ähnlich via `jobs.py`)
- Aufbewahrung: letzte N Backups (konfigurierbar, Default: 7)
- Speicherort: lokal (Standardpfad), optional SFTP/S3 (Expert-Mode)

**Neues Model:**

```python
class BackupLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    backup_type = models.CharField(max_length=20)  # settings / full / both
    file_path = models.CharField(max_length=500)
    file_size_bytes = models.BigIntegerField()
    checksum_sha256 = models.CharField(max_length=64)
    is_encrypted = models.BooleanField(default=False)
    status = models.CharField(max_length=20)  # success / failed / partial
    notes = models.TextField(blank=True)

    class Meta:
        app_label = 'gui'
```

### 11.2 Restore-Funktion

**UI-Flow:**

```
[Backup wiederherstellen]
  → Datei hochladen oder lokale Datei auswählen
  → Integritätsprüfung (Checksum)
  → Vorschau: „Folgende Settings werden überschrieben: ..."
  → Warnung: „DB-Restore überschreibt alle aktuellen Daten"
  → Bestätigung erforderlich (Typ „RESTORE" eintippen)
  → Restore-Log-Eintrag
```

**Sicherheitsmechaniken:**
- Restore erfordert Expert-Modus
- Automatisches Backup **vor** dem Restore
- Keine Restore-Aktion ohne Checksummen-Validierung

### 11.3 Datenbank-Bereinigungsfunktion

Ohne Bereinigung wächst die DB durch `Forwards`, `FailedHTLCs`, `ChannelSnapshot` und `Rebalancer` unbegrenzt.

**Bereinigungsregeln (konfigurierbar):**

| Tabelle | Standard-Aufbewahrung | Empfehlung |
|---|---|---|
| `Forwards` | 365 Tage | 180–365 Tage |
| `FailedHTLCs` | 90 Tage | 30–90 Tage |
| `ChannelSnapshot` | 180 Tage | 90–180 Tage |
| `ForwardingAggregate` | unbegrenzt | nie löschen (klein) |
| `Rebalancer` | 365 Tage | 180 Tage |
| `RebalanceMLRecord` | unbegrenzt | nie auto-löschen (Trainingsdaten) |
| `AutoFeeMLRecord` | unbegrenzt | nie auto-löschen (Trainingsdaten) |
| `Payments` (fehlgeschlagen) | 30 Tage | 14 Tage |
| `PolicyRun` | 90 Tage | 60 Tage |
| `ChangeLog` | unbegrenzt | nie auto-löschen (Audit) |

**UI:**

```
[Datenbank-Bereinigung]
  → Aktuelle DB-Größe anzeigen
  → Tabellen-Übersicht mit Zeilenanzahl und geschätzter Größe
  → Schieberegler für Aufbewahrungsdauer pro Tabelle
  → Vorschau: „X Einträge werden gelöscht, geschätzte Einsparung: Y MB"
  → „Jetzt bereinigen" (manuell) oder „Automatisch täglich um 03:00"
  → Bereinigungsprotokoll
```

**Automatische Bereinigung:**
- Job `cleaner.py` läuft täglich (konfigurierbar)
- Bereinigung erfolgt in Batches (verhindert DB-Lock)
- Vorher: automatisches Mini-Backup der gelöschten Daten als JSON (optional)

**Bestehende Funktion:** `clean_failed_payments` (bereits vorhanden) wird in die neue Bereinigungsfunktion integriert.

---

## 12. Build-Prozess-Optimierung

### 12.1 Aktuelle Probleme

Das bestehende LNDg hat keinen formellen Build-Prozess (Django-Apps benötigen keinen „Build" im klassischen Sinne). Mit der Einführung der SPA-Schicht entsteht ein Frontend-Build. Ohne Optimierung führt jede kleine Änderung zu langen Build-Zeiten.

### 12.2 Frontend-Build-Optimierung

**Vite statt Webpack/CRA:**
- Vite bietet Hot Module Replacement (HMR) ohne vollständige Neukompilierung
- Dev-Server startet in < 1 Sekunde
- Production-Build: Code-Splitting + Tree-Shaking automatisch

```
# Entwicklung
npm run dev          # HMR, sofortige Updates

# Production
npm run build        # Optimierter Bundle, nur geänderte Chunks
```

**Inkrementelle Builds:**
- TypeScript: `tsc --incremental` (nutzt `.tsbuildinfo`)
- ESLint: nur geänderte Dateien (`--cache`)

### 12.3 Docker-Optimierung

```dockerfile
# Multi-Stage Build

# Stage 1: Frontend-Build
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --only=production    # Cached Layer bei unverändertem package.json
COPY frontend/ .
RUN npm run build

# Stage 2: Python-Dependencies (cached bei unverändertem requirements.txt)
FROM python:3.11-slim AS python-deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Final Image (klein, nur Runtime)
FROM python:3.11-slim
COPY --from=python-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=frontend-builder /app/frontend/dist /app/gui/static/spa
COPY . /app
```

**Kern-Prinzip:** Jeder Layer wird nur neu gebaut, wenn sich sein Input ändert. `requirements.txt` und `package.json` ändern sich selten → Python- und npm-Dependencies werden gecacht.

**Rootless Container:** Der finale Container läuft als nicht-privilegierter User (kein `root`). Das reduziert die Angriffsfläche im Deployment erheblich und entspricht Best Practices für Produktions-Container. Arbeitsverzeichnis: `/lndg/` (statt `/app` im bisherigen Setup – Breaking Change beim Upgrade dokumentieren).

### 12.4 CI/CD-Pipeline-Optimierung

```yaml
# GitHub Actions – Optimiertes Caching
- uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}

- uses: actions/cache@v3
  with:
    path: frontend/node_modules
    key: ${{ runner.os }}-node-${{ hashFiles('frontend/package-lock.json') }}
```

**Separate Jobs:**
- `test-backend` und `test-frontend` laufen parallel
- `build-docker` läuft nur bei Merge in `main` (nicht bei jedem PR-Push)

### 12.5 Entwicklungs-Workflow-Optimierung

```bash
# Hot-Reload für Django-Templates (bereits vorhanden: runserver --reload)

# Zusätzlich: DB-Migration-Check
make check   # = python manage.py check --deploy + migrate --check

# Schnelle Linting-Pipeline
make lint    # = ruff check . (statt flake8, deutlich schneller)
make fmt     # = ruff format .
```

**Makefile (neu):**

```makefile
dev:
    python manage.py runserver & cd frontend && npm run dev

test:
    python manage.py test gui --keepdb  # --keepdb: DB nicht jedes Mal neu aufbauen

migrate:
    python manage.py migrate

lint:
    ruff check . && cd frontend && npm run lint

build:
    cd frontend && npm run build
    python manage.py collectstatic --noinput
```

### 12.6 Abhängigkeits-Management

- **Python:** `pip-compile` (aus `requirements.in` → `requirements.txt` mit Hash-Pinning)
- **Node:** `package-lock.json` committen, `npm ci` statt `npm install` in CI
- **Renovate/Dependabot:** Automatische Dependency-Updates mit PR-Vorschlag

### 12.7 🔧 Aufgabe: pip-compile Lock-Datei erstellen (R-SEC-3)

**Was:** `requirements.txt` wird derzeit manuell gepflegt und enthält keine versionsgenauen Hash-Pins. Das verletzt R-SEC-3 und öffnet die Tür für Supply-Chain-Angriffe (unsichere Abhängigkeiten, die beim nächsten `pip install` eingeschleust werden können).

**Warum:** `requirements.in` existiert bereits mit oberen Versionsgrenzen. Es fehlt nur der generierte Lock-File, der die exakten Versionen + Hashes aller transitiven Abhängigkeiten festschreibt.

**Wie:**

```bash
# Einmalig in der Ziel-Python-Umgebung (Python 3.12, Linux) ausführen:
pip install pip-tools
pip-compile requirements.in --generate-hashes --output-file requirements.txt
# Ergebnis prüfen und committen
git add requirements.txt && git commit -m "chore: pin requirements via pip-compile"
```

**CI-Schutz (damit der Lock nie veraltet):**

```yaml
# In .github/workflows/ci.yml hinzufügen:
- name: Check requirements.txt is up to date
  run: pip-compile requirements.in --generate-hashes --dry-run --check
```

**Wichtig:** `pip-compile` muss **lokal vom Maintainer** in der exakten Produktions-Python-Umgebung ausgeführt werden (gleiche Python-Version, gleiche Plattform). Ein Ausführen im Copilot-Sandbox kann zu anderen Hash-Werten führen (andere Python-Micro-Version, Plattform-Marker). Nach jeder Änderung an `requirements.in` muss `pip-compile` neu ausgeführt und das Ergebnis committed werden.

---

## 13. UI/UX-Hybrid-Strategie

### 13.1 Architektur-Leitsatz

```
Django = Wahrheit & Kontrolle
SPA    = Erklärung & Interaktion
```

### 13.2 Zwei UI-Welten

**Welt A: Modernes SPA-UI (neu)**

Für alles, was erklärt, visualisiert, interaktiv ist oder Einsteiger betrifft:
- Cockpit / Übersicht
- Channel-Karten & Gesundheitsstatus
- Empfehlungen (Next Best Action)
- Learn-by-Doing-Flows
- Policy-Preview & Dry-Run-Visualisierung
- Charts & Zeitreihen

→ Läuft unter `/app/*`

**Welt B: Klassisches Django-UI (bestehend)**

Für alles, was technisch, tabellarisch, selten benutzt oder Expert-only ist:
- Alle bestehenden Channel-Tabellen
- Debug-Pages
- Raw Statistics
- Admin- und Maintenance-Views
- Notfall-Fallback-UI

→ Läuft weiterhin unter bestehenden URLs

**Wichtig:** Keine dauerhafte Legacy-Schiene. Technische Altsichten werden in die neue Domänenstruktur migriert und anschließend entfernt.

### 13.3 Technologie-Stack (SPA)

**Empfehlung:**

| Bereich | Technologie | Begründung |
|---|---|---|
| Framework | React 18+ | Große Community, gut mit Django kombinierbar |
| Build-Tool | Vite | Schnell, HMR, gutes Django-Integration-Beispiel |
| State | Zustand + React Query | Leichtgewichtig, Server-State optimal |
| Charts | Recharts oder Nivo | Einfach, React-nativ, responsive |
| UI-Komponenten | Tailwind CSS + Headless UI | Kein Overhead, vollständig anpassbar |
| i18n | react-i18next | Standard, gut dokumentiert |

**Alternative (geringere Änderung):** HTMX + Alpine.js + Tailwind CSS (kein vollständiges SPA, aber deutlich moderner als Django-Templates). Empfohlen als **Phase 1** wenn React-Expertise nicht vorhanden ist.

### 13.4 Progressiver Roll-out

```
Phase 1 – Parallelbetrieb:
  Neues /app/* wird zusätzlich bereitgestellt
  Bestehendes LNDg bleibt unverändert erreichbar
  Gemeinsame Authentifizierung (Django-Session)

Phase 2 – UX-Schwerpunkt verlagern:
  Startseite → SPA (/app/cockpit)
  Navigation Standard → SPA
  Alte Seiten: Expert Mode oder Deep-Link

Phase 3 – Konsolidierung (optional):
  Alte Views werden teilweise migriert oder bewusst archiviert
  Backend ist längst API-first
```

### 13.5 Technische Leitplanken

```
✓ Keine neue Business-Logik in Templates
✓ Kein JS-Business-State im DOM
✓ Jede Aktion → API → Audit-Log
✓ Jede Automatik → Dry-Run-fähig
✓ Jede Empfehlung → erklärbar
✓ Kein Breaking Change für bestehende /api/-Endpunkte
```

---

## 14. Implementierungsfahrplan

### Phase 1: Foundation (kein Big Bang)

- [ ] **UI-Reframe:** Neue Navigation (5-Bereiche), Modus-Switcher, Cockpit-Kacheln (nur Darstellung + Tooltips)
- [ ] **Multilanguage-Basis:** Django i18n aktivieren, alle bestehenden Strings markieren, DE/EN-Übersetzungen
- [ ] **UserMode-Model:** Modus-Einstellung persistieren inkl. AI-Feature-Flags (alle Default: `off`)
- [ ] **Build-Optimierung:** Multi-Stage Dockerfile (rootless, `/lndg/`), CI-Caching, Makefile
- [ ] **LightningBackend-Interface:** Abstraktes Interface aufteilen in `LightningReadAdapter` + `LightningWriteAdapter` (KI-Sicherheitstrennung, Abschnitt 9.0); `SpliceAction`-Domänenobjekt definieren (siehe Abschnitt 17)
- [ ] **LndBackend:** Bestehende LND-Logik in Adapter kapseln (keine UI-Logik ändert sich – nur Strukturierung); gRPC-Credentials einmalig cachen, Connection wiederverwenden
- [ ] **ClnBackend (Skelett):** Verbindung + Authentifizierung via `clnrest` / `cln-grpc`; grundlegende Methoden (`get_node_info`, `list_channels`, `list_peers`) implementieren
- [ ] **Domänenmodell-Basis:** Abstrakte Modelle `Channel`, `Peer`, `ForwardingEvent`, `FeePolicy`, `SpliceAction` einführen
- [ ] **Sicherheits-Baseline:** SSH-Host-Key-Verification (RejectPolicy), Datei-Permissions 0o600, Dependency-Pinning mit Versions-Bounds

### Phase 2: CLN-Integration & Daten

- [ ] **ClnBackend vollständig:** Forwarding-Events, Fee-Update, HTLC-Stream (via `listforwards`, `setchannel`, CLN-Hooks)
- [ ] **CLN-Onboarding-Pfad:** Guided-Wizard erkennt CLN und passt Erklärungen + Begriffe an
- [ ] **Capability-Registry:** Backend registriert seine Fähigkeiten; UI wertet Capabilities aus statt Backend-Typ zu prüfen
- [ ] **Zeitreihen-Models:** `ChannelSnapshot`, `ForwardingAggregate`, `ChangeLog` (backend-neutral)
- [ ] **Collector/Aggregator-Jobs:** Regelmäßige Snapshots für LND und CLN
- [ ] **Neue Charts:** Liquidity Donut, Fee vs. Volume Scatter, Channel Health Heatmap
- [ ] **Backup/Restore-Funktion:** UI + Backend + automatisches Backup
- [ ] **DB-Bereinigung:** Konfigurierbare Aufbewahrungsregeln + UI

### Phase 3: Empfehlungs-Engine & Splice-Workflow

- [ ] **Heuristik-Engine:** Top-3-Aktionen pro Node-Zustand (inkl. Splice-In/Out Empfehlungen)
- [ ] **Recommendation-Model:** Empfehlungen speichern, Status tracken; Rationale-Schema formalisieren und validieren (Abschnitt 5.2)
- [ ] **Simulation Layer:** Jede Policy mit `simulate=True` aufrufbar; Ergebnis in `dry_run_result` speichern; „Was wäre passiert wenn…"-Widget im Lernen-&-Verlauf-Bereich
- [ ] **Dry-Run-Framework:** Jede Empfehlung simulierbar
- [ ] **Explainability-UI:** „Warum?"-Panels für alle Empfehlungen (basierend auf Rationale-Schema)
- [ ] **Guided Splice-Workflow (CLN):** Schritt-für-Schritt UI für Splice-In und Splice-Out
  - Kostenvorschau (On-Chain-Gebühren via mempool.space)
  - Impact-Simulation (neue Kapazität, neues Balanceverhältnis)
  - Fortschritts-Tracking (Splice dauert Blöcke – UI zeigt Status)
  - Audit-Log-Eintrag
- [ ] **Splice-Workflow (LND):** Gleicher UI-Flow, aber capability-abhängig aktiviert (LND Splice ist in Entwicklung)
- [ ] **CLN Plugin-Status-Panel:** Zeigt welche CLN-Plugins installiert/aktiv sind; erklärt fehlende Capabilities

### Phase 4: Policy-Engine & Automationen

- [ ] **Policy-Engine:** `Policy`, `PolicyRun`-Models, Executor-Job
- [ ] **Auto-Fee-Templates:** Conservative/Balanced/Revenue-Seeking UI
- [ ] **CLN-Policy-Adapter:** `setchannel`-Aufrufe für Fee-Policies; CLN-Rebalancing via `rebalance`-Plugin
- [ ] **ML-Auto-Fee Shadow-Mode:** Balance-Drain-Velocity-Erkennung, proaktive Gebührenanpassung, erweiterter Parameter-Scope (base_fee, min/max_htlc, inbound_fee)
- [ ] **ML-Rebalancing Shadow-Mode:** Kanalpar-Lernhistorie (`RebalanceMLRecord`), zeitbasierte Features, Erfolgswahrscheinlichkeits-Modell
- [ ] **Rebalance-Budget:** Budget-Konfiguration, Queue mit ML-Priorisierung, Erfolgsmessung
- [ ] **Dynamische Rebalancing-Zielquoten:** Liquiditätsbedarf-Analyse, konfigurierbarer Puffer, Routing-Verhaltens-Adaption
- [ ] **Audit-Log-UI:** Vollständiger Änderungsverlauf mit Rollback
- [ ] **Policy-Domänenentkopplung:** Policy-Definitionen auf Domänenebene; Executor-Adapter übersetzt Policy → konkrete LND- oder CLN-Aktion

### Phase 5: Externe Integrationen & Erweiterte Features

- [ ] **mempool.space-Integration:** Fee-Ampel bei Open/Close/Splice-Empfehlungen
- [ ] **Amboss-Integration:** Optionale Peer-Kontextdaten
- [ ] **Onboarding-Wizard:** Vollständiger 5-Schritte-Wizard (LND- und CLN-Variante)
- [ ] **Missions/Glossar:** Learning Center (inkl. CLN-spezifischer Erklärungen)

### Phase 6: ML Shadow Mode & SPA-Konsolidierung

- [ ] **ML-Infrastruktur:** Feature-Engineering, Modell-Training-Pipeline
- [ ] **Shadow Mode (Rebalancing):** ML-Empfehlungen parallel zu Heuristik, nur loggen → Konfidenz aufbauen
- [ ] **Shadow Mode (Auto-Fee):** ML-gesteuerte Gebührenanpassungen erst vorschlagen, dann schrittweise automatisieren
- [ ] **ML-Vollautomation (opt-in, Expert-Mode):** Rebalancing und Auto-Fee vollständig ML-gesteuert, mit definierten Grenzen und Audit-Log
- [ ] **Eskalations-/Deeskalations-Tuning:** Konfigurierbare Faktoren und Grenzen über UI
- [ ] **SPA als Haupt-Produkt:** Phase 2 des Roll-outs
- [ ] **PWA-Vorbereitung:** Service Worker, Manifest, Offline-Fallback

### Phase 7: Multi-Asset-Vorbereitung (Optional – Spätere Roadmap)

> **Hinweis:** Multi-Asset (Taproot Assets, Stablecoins auf Lightning) ist aktuell noch nicht produktionsreif und wird bewusst zurückgestellt. Die Adapter-Architektur aus den vorherigen Phasen ermöglicht nachträgliche Integration ohne Rewrite.

- [ ] **Asset-Attribut im Datenmodell aktivieren:** `asset_id` / `asset_group` / `denomination` in Flow- und Fee-Modellen sichtbar machen
- [ ] **Unit-flexible UI:** Beträge, Charts, Erklärungen arbeiten mit `denomination`-Platzhaltern statt hardcodierten „sats"
- [ ] **Multi-Asset-UI:** Asset-Bereich in Advanced/Expert wenn `can_multi_asset` aktiv
- [ ] **Multi-Node-Backend-Switcher:** UI-Switcher zwischen mehreren Backend-Instanzen

---

## 15. Zusätzliche Ideen & Erweiterungsvorschläge

### 15.1 Node-Health-Score

Ein aggregierter „Node Health Score" (0–100) gibt auf einen Blick Auskunft über den Gesamtzustand des Nodes. Zusammengesetzt aus:

- Liquiditäts-Balance (Inbound/Outbound-Verhältnis)
- Routing-Aktivität (7d-Trend)
- Failed-HTLC-Rate
- Peer-Stabilität (Uptime-Proxy)
- Fee-Positionierung (relativ zum Netzwerk)

Angezeigt prominent im Cockpit mit Trend-Pfeil (besser/schlechter als letzte Woche).

### 15.2 Peer-Vergleichs-Tool

„Wie ist mein Channel zu Peer X im Vergleich zu ähnlichen Channels im Netzwerk?" – Visualisierung:
- Meine Fee vs. Peer-Markt-Median
- Mein Flow vs. ähnliche Channels (anonymisiert)

### 15.3 Notification-System (Multi-Channel)

Erweiterung des bestehenden Benachrichtigungssystems:
- **Telegram-Bot-Integration** (besonders beliebt in LN-Community)
- **E-Mail-Digest** (täglich/wöchentlich)
- **Webhook** (für externe Automatisierungen)
- **In-App-Notifications** (Browser-Benachrichtigungen via PWA)

Notification-Typen:
- Channel inaktiv seit X Tagen
- Rebalance erfolgreich/fehlgeschlagen
- Policy ausgeführt
- On-chain-Gebühren günstig (gutes Zeitfenster für Open/Close)
- Node-Health-Score verschlechtert sich

### 15.4 Steuer-Reporting-Export

Erweiterung der bestehenden `export_accounting`-Funktion:
- **FIFO/LIFO-Berechnung** für Routing-Fees
- **CSV/JSON-Export** kompatibel mit gängigen Krypto-Steuer-Tools (Koinly, CoinTracking, etc.)
- Trennung: Routing-Revenue vs. Rebalancing-Kosten vs. On-chain-Fees
- Periodenbericht (Monat/Quartal/Jahr)

### 15.5 Channel-Template-System

Vordefinierte Channel-Konfigurationen für häufige Use Cases:
- „Standard Routing Channel"
- „Inbound-Kanal (Liquiditätsprovider)"
- „Private Payment Channel"

Templates definieren: Capacity-Range, initiale Fee-Strategie, Auto-Rebalance-Ziele.

### 15.6 Peer-Blacklist / Whitelist mit Begründung

Erweiterung des bestehenden `add_avoid`-Systems:
- Blacklist mit **Begründungs-Tags** (z. B. „instabil", „hohe Failed-Rate", „closed unilateral")
- Whitelist für bevorzugte Peers (höhere Rebalance-Priorität, niedrigere Fee-Strategie)
- Import/Export der Listen (für Community-Austausch)

### 15.7 Routing-Simulator

„Was wäre wenn?"-Simulator für Fee-Strategien:
- Eingabe: neue Fee-Konfiguration
- Ausgabe: geschätzter Effekt auf Routing-Volumen (basierend auf historischen Daten)
- Vergleich: aktuelle Konfiguration vs. Simulation

### 15.8 Multi-Node-Support

Verwaltung mehrerer LND-Nodes in einer LNDg-Instanz:
- Node-Switcher im Header
- Aggregierte Übersicht aller Nodes
- Separate Settings und Policies pro Node
- Besonders relevant für Node-Runner mit mehreren Nodes

### 15.9 LN-Adresse / LNURL-Integration (bereits in IDEAS.md)

Automatisierte Gewinnausschüttung auf Lightning-Adresse (bereits detailliert in `IDEAS.md` beschrieben). Integration in das neue Policy-Engine-System als `profit_payout`-Policy-Typ.

### 15.10 API-Zugangsschlüssel (API Keys)

Für externe Integrationen und Monitoring-Tools:
- Generierung von API-Keys mit definierten Scopes (read-only / read-write)
- Key-Rotation und Revocation
- Audit-Log für API-Key-Nutzung
- Ermöglicht Integration mit externen Dashboards (Grafana, etc.)

### 15.11 Grafana/Prometheus-Integration

Opt-in Metrics-Export für Nutzer, die bereits Grafana/Prometheus betreiben:
- `/metrics`-Endpunkt (Prometheus-Format)
- Vordefinierte Dashboards als Download
- Kein Zwang: LNDg-eigene Charts bleiben primär

### 15.12 Dark Mode

- Vollständiger Dark-Mode-Support (System-Default + manuell überschreibbar)
- Gespeichert in `UserMode`

### 15.13 Guided Channel-Close-Workflow

Schließen eines Channels ist risikobehaftet. Dedizierter Workflow:
1. Analyse: Warum schließen? (Simulation der Opportunitätskosten)
2. Depriorisierungs-Phase: Fees hochsetzen, Routing deaktivieren
3. Warte-Empfehlung: „Kanal hat noch X sats Outbound, warte auf natürlichen Drain"
4. Günstigstes Zeitfenster (mempool.space)
5. Close-Bestätigung mit vollem Impact-Überblick

---

## 16. Offene Fragen & Entscheidungsbedarfe

Die folgenden Punkte wurden entschieden oder sind noch offen. Entschiedene Punkte sind mit ✅ markiert, offene mit 🔲.

### Architektur & Technologie

| # | Frage | Optionen | Implikation | Entscheidung |
|---|---|---|---|---|
| A1 ✅ | Welches Frontend-Framework? | React + Vite **vs.** HTMX + Alpine.js **vs.** Vue.js | Beeinflusst Entwicklungsaufwand, benötigte Skills, mobile Tauglichkeit | **React + Vite** – größtes Ökosystem, beste Community-Unterstützung, zukunftssicher |
| A2 ✅ | SPA unter `/app/*` oder komplette URL-Migration? | Parallel `/app/*` **vs.** Migration bestehender URLs | Risiko für bestehende Nutzer, Bookmarks, externe Verlinkungen | **Komplette URL-Migration** – da noch keine produktiven Nutzer auf dem Projekt arbeiten, kein Migrationsrisiko |
| A3 ✅ | WebSocket für Live-Updates? | Django Channels (Redis) **vs.** SSE **vs.** Polling beibehalten | Redis-Abhängigkeit; Komplexität im Deployment | **SSE (Server-Sent Events)** – kein Redis nötig, ausreichend für einseitige Push-Updates; Polling als Fallback erhalten |
| A4 ✅ | Datenbank: SQLite behalten oder PostgreSQL als Standard? | SQLite (einfach, single-file) **vs.** PostgreSQL (besser für Zeitreihen, Concurrent Writes) | Beeinflusst Backup-Strategie, Performance bei Snapshots | **SQLite Standard, PostgreSQL optional** – SQLite für Standardsetups (inkl. RPi), PostgreSQL als dokumentierte optionale Alternative |
| A5 ✅ | ML-Bibliothek: scikit-learn (leicht, kein Overhead) vs. externe ML-API? | scikit-learn lokal **vs.** External ML API | Privacy (keine Daten extern), Ressourcenverbrauch auf kleinen Nodes (RPi) | **scikit-learn lokal** – Privacy-first, offline-fähig, läuft auf allen Zielplattformen inkl. RPi 4 |
| A6 ✅ | ML-Modell-Persistenz: Wie werden trainierte Modelle gespeichert und versioniert? | SQLite-BLOB **vs.** Dateisystem (`.joblib`/`.pkl`) **vs.** MLflow | Reproduzierbarkeit, Rollback bei schlechtem Modell | **Dateisystem (`.joblib`)** – einfachstes bewährtes Pattern für scikit-learn; Ablage unter `models/rebalance_v{timestamp}.joblib` |
| A7 ✅ | ML-Training: Online-Learning (inkrementell) vs. periodisches Batch-Retraining? | Online (z. B. stündlich) **vs.** Batch (täglich/wöchentlich) | Ressourcenverbrauch vs. Aktualität der Modelle; Stabilität | **Periodisches Batch-Retraining** – stabil und ressourcenschonend; Frequenz konfigurierbar; auf Nodes mit wenig RAM deaktivierbar oder nur manuell auslösbar |

### Produkt & UX

| # | Frage | Optionen | Implikation | Entscheidung |
|---|---|---|---|---|
| P1 ✅ | Wie werden Betriebsmodi freigeschaltet? | Manuell durch Nutzer **vs.** automatisch nach X Tagen/Aktionen | Engagement vs. Nutzerkontrolle | **Manuell durch Nutzer** – technisch affine Zielgruppe erwartet Kontrolle; CTA im UI ("Bereit für mehr?") |
| P2 ✅ | Soll der Modus (Guided/Advanced/Expert) passwortgeschützt sein? | Ja (verhindert versehentliches Hochstufen) **vs.** Nein | Sicherheit vs. Reibung | **Nein** – Confirmation-Dialog mit klarer Warnung beim Hochstufen ausreichend |
| P3 ✅ | Welche Sprachen zum Launch? | Nur DE+EN **vs.** DE+EN+weitere | Übersetzungsaufwand; Community-Resourcen | **Nur DE + EN** – weitere Sprachen via Community-Contributions (i18n-Framework) nachrüstbar |
| P4 🔲 | Sollen Empfehlungen Community-geteilt werden können? | Ja (opt-in) **vs.** Nein (privat) | Privacy-Implikationen; Mehrwert für Community | *Noch offen – zurückgestellt* |
| P5 ✅ | Wie detailliert soll der Onboarding-Wizard sein? | Minimal (3 Schritte) **vs.** Vollständig (5+ Schritte) | Abbruchrate vs. Lerneffekt | **Vollständig (5+ Schritte)** – höherer Lerneffekt; bessere initiale Konfiguration |
| P6 ✅ | Ab wann darf ML-Rebalancing vollautomatisch ausführen? | Nur Expert-Mode nach N Tagen Shadow-Mode **vs.** Opt-in ab Advanced | Risiko vs. Nutzbarkeit; Vertrauen ins Modell | **Nur Expert-Mode nach N Tagen Shadow-Mode** – Pflicht-Lernphase baut Vertrauen auf und validiert das Modell am konkreten Setup |
| P7 ✅ | Wie soll der Übergang von regelbasiert zu ML-gesteuert kommuniziert werden? | Explizites UI-Toggle (Modus: Regelbasiert / ML) **vs.** gradueller Übergang | Nutzerkontrolle vs. Komplexität; Vertrauen | **Explizites UI-Toggle** – klarer "Modus: Regelbasiert / ML"-Toggle mit Status-Indikator (letzter ML-Eingriff, Konfidenzwert); UI-Benachrichtigung sobald genug ML-Daten verfügbar sind; **pro Kanal einzeln aktivier-/deaktivierbar** |
| P8 ✅ | Welche Kanäle sollen vom ML-Auto-Fee ausgeschlossen werden können? | Einzelne Kanäle (Whitelist/Blacklist) **vs.** nur global | Granularität vs. Konfigurationsaufwand | **Einzelne Kanäle (Whitelist/Blacklist)** – gilt ebenso für ML-gesteuertes Rebalancing; **pro Kanal konfigurierbar ob ML-Nutzung ready und aktiv ist**; Toggle direkt in der Kanalübersicht |

### Datenschutz & Sicherheit

| # | Frage | Optionen | Implikation | Entscheidung |
|---|---|---|---|---|
| S1 ✅ | Welche Daten werden an externe APIs (Amboss, mempool) gesendet? | Nur Pubkeys **vs.** Channel-IDs **vs.** Nichts ohne explizite Einwilligung | Privacy-Policy notwendig; Default muss sicher sein | **Nichts ohne explizite Einwilligung** – Default: keine externen Anfragen; bestehende Integrationen als bewusstes Opt-in |
| S2 ✅ | Soll es eine anonyme Nutzungsstatistik geben? | Opt-in Telemetrie **vs.** Keine | Verbesserung des Produkts vs. Privacy | **Opt-in Telemetrie** – klare Anzeige im UI was gesendet wird; Privacy by default |
| S3 ✅ | Wie werden Backup-Dateien verschlüsselt? | AES-256 + Passwort **vs.** Unverschlüsselt **vs.** GPG | Einfachheit vs. Sicherheit | **AES-256 + Passwort** – bester Kompromiss aus Sicherheit und Usability |
| S4 ✅ | Rollback: Wie weit zurück? | Letzte 1 Änderung **vs.** Letzten 7 Tage **vs.** Unbegrenzt | Speicherbedarf vs. Flexibilität | **Letzte 7 Tage** – ausreichend für Fehlerdiagnose; beherrschbarer Speicherbedarf |
| S5 ✅ | Darf KI (`ai_mode=shadow`) Empfehlungen automatisch in Policies überführen? | Nein (immer manuell) **vs.** Ja, nach Konfidenz-Schwelle + Cooldown | Kernfrage der KI-Sicherheitsarchitektur (Abschnitt 18) | **Nein (immer manuell)** – Shadow-Mode ist Beobachtungs-Modus; automatische Überführung würde Sicherheitsversprechen brechen |
| S6 ✅ | Welche ML-Bibliothek für lokale Modelle? | scikit-learn (lokal, privacy-safe) **vs.** externe ML-API (komfortabler, aber Datenweitergabe) | Privacy vs. Wartungsaufwand; externe API erfordert explizite Einwilligung + klare Datenschutzerklärung | **scikit-learn (lokal, privacy-safe)** – identisch mit A5; externe ML-APIs sind für self-hosted Privacy-First-Anwendung keine valide Option |
| S7 ✅ | Ab welchem `ai_mode`-Level darf KI Policy-Ausführung auslösen? | Nur `policy_bound` (nie `shadow`/`advisory`) **vs.** konfigurierbar | Sicherheit vs. Komfort; `policy_bound` ist der frühestmögliche sichere Level (Abschnitt 18.2) | **Nur `policy_bound`** – folgt direkt aus S5 (Shadow-Mode nie ausführend) und Abschnitt 18.2; `advisory` und `shadow` sind per Architekturentscheidung rein beobachtend |

### Betrieb & Deployment

| # | Frage | Optionen | Implikation | Entscheidung |
|---|---|---|---|---|
| B1 ✅ | Soll Redis als Pflicht-Dependency eingeführt werden? | Ja (WebSocket, Caching) **vs.** Optional **vs.** Nein | Deployment-Komplexität auf kleinen Nodes | **Optional** – mit SSE statt WebSocket entfällt der Hauptgrund für Redis; bleibt optionale Caching-Schicht für leistungsfähigere Setups |
| B2 ✅ | Wie soll der Snapshot-Job skaliert werden? (RPi-Limit) | 15-Min-Intervall **vs.** 1h-Intervall **vs.** konfigurierbar | DB-Wachstum vs. Chart-Granularität | **Konfigurierbar (Default: 15 Min)** – 1h als RPi-Empfehlung; automatische Ressourcenerkennung für sinnvollen Default |
| B3 ✅ | Automatisches Backup: lokal vs. remote? | Nur lokal (Standard) **vs.** Optional SFTP/S3 | Sicherheit vs. Konfigurationsaufwand | **Nur lokal (Standard)** – remote optional via SFTP / S3 / Azure / OneDrive; Standardinstallation bleibt einfach |
| B4 ✅ | Soll es ein offizielles Helm-Chart/Umbrel-Update geben? | Ja (Priorität) **vs.** Community-Beitrag **vs.** Später | Adoptions-Reichweite; Maintenance-Aufwand | **Ja (Priorität)** – Umbrel und Start9 sind die meistgenutzten Plattformen; offizielles Package erhöht Adoptionsrate |
| B5 ✅ | Minimale Hardware-Anforderung für ML-Features? | Raspberry Pi 4 (4 GB RAM) **vs.** Nur auf leistungsfähiger Hardware | Kompatibilität vs. Feature-Reichhaltigkeit | **Raspberry Pi 4 (4 GB RAM)** – Referenzplattform der meisten Home-Node-Betreiber; auf schwächerer Hardware automatisch deaktiviert mit klarer Meldung |
| B6 ✅ | ML-Training-Frequenz auf ressourcenschwachen Nodes? | Nächtliches Batch-Training **vs.** Nur manuell auslösbar **vs.** Deaktivierbar | Aktualität der Modelle vs. CPU/RAM-Belastung auf RPi | **Nächtliches Batch-Training, deaktivierbar** – Training z. B. um 03:00 Uhr minimiert Konflikte mit Node-Betrieb; für sehr kleine Nodes (RPi 3, 2 GB RAM) vollständig deaktivierbar |
| B7 ✅ | Mindestdatenmenge für ML-Rebalancing-Modell? | 30 Tage / mind. 50 Rebalance-Events **vs.** 14 Tage / 20 Events | Modellqualität vs. Time-to-Value für neue Nutzer | **30 Tage / mind. 50 Events** – Qualität vor Geschwindigkeit; **pro Kanal mit individuellem Status und de-/aktivierbar**; Fortschrittsanzeige für neue Nutzer ("Noch X Tage bis ML-Features für diesen Kanal verfügbar") |
| B8 ✅ | Wie werden ML-Modelle bei Upgrade auf neue LNDg-Version migriert? | Modelle verwerfen + neu trainieren **vs.** Migrations-Skript | Einfachheit vs. Datenverlust beim Upgrade | **Modelle verwerfen + neu trainieren** – Trainingsdaten bleiben in lokaler DB erhalten; Neu-Training nach Upgrade max. eine Nacht; automatischer Hinweis beim Upgrade |

---

## 17. Multi-Backend-Architektur: LND & CLN (inkl. Channel-Splice)

> **Leitgedanke:** LNDg Next wird von Anfang an für LND und CLN gebaut – beide Backends sind gleichrangige, gleichzeitig implementierte Ziele des Refactorings. Channel Splicing ist das technische Alleinstellungsmerkmal, das Routing-Nodes erstmals über eine GUI zugänglich gemacht wird.

---

### 17.1 Trennung von „Lightning-Logik" und „Implementierungs-Details"

#### Was heute vermieden werden muss

Direkte Kopplung von UI/Business-Logik an:

- LND-spezifische RPC-Felder (z. B. `chan_id`, `_forwarding_event`, `lnd_short_chan_id`)
- LND-spezifische Begrifflichkeiten in Templates und Kommentaren
- Vermischung von Routing-Konzepten und Implementierungsartefakten

#### Abstrakte Lightning-Domänenmodelle

Folgende Modelle beschreiben **was passiert**, nicht wie es technisch geliefert wird:

| Domänenmodell | Beschreibung |
|---|---|
| `Node` | Eigener Lightning-Node (Backend-unabhängig) |
| `Peer` | Verbundener Lightning-Knoten |
| `Channel` | Bidirektionaler Liquiditätskanal |
| `ForwardingEvent` | Weitergeleites HTLC mit In-/Outbound-Channel, Betrag, Fee |
| `LiquidityState` | Snapshot des Kanal-Zustands (lokal/remote/total) |
| `FeePolicy` | Gebührenparameter (base_fee, fee_rate, min/max_htlc, inbound_fee) |
| `RebalanceAction` | Rebalancing-Vorgang mit Quelle, Ziel, Betrag, Kosten |
| `SpliceAction` | Channel-Resize-Vorgang: Typ (in/out), Betrag, On-Chain-Fee, Status (pending/confirmed) |

**Konsequenz:** LND und CLN sind beide _Implementierungen_ eines „Lightning-Adapters". Beide werden im Rahmen dieses Refactorings implementiert – kein zukünftiger Mehraufwand für CLN-Support.

---

### 17.2 Adapter-Pattern für Node-Backends

#### Empfohlene Struktur

```
LightningBackend (Interface / abstrakte Klasse)
├── LndBackend          ← Phase 1: LND gRPC-Adapter
└── ClnBackend          ← Phase 1–2: CLN clnrest/cln-grpc-Adapter (gleichzeitig!)
```

**Beide Backends werden im gleichen Refactoring-Zyklus implementiert** – LND zuerst (da bestehende Logik nur umstrukturiert wird), CLN direkt danach (Phase 2, da neue Verbindungslogik nötig).

#### Was der Adapter kapselt

```python
class LightningBackend:
    """Abstraktes Interface für alle Lightning-Node-Backends."""

    def get_node_info(self) -> Node: ...
    def list_channels(self) -> list[Channel]: ...
    def list_peers(self) -> list[Peer]: ...
    def get_forwarding_events(self, start, end) -> list[ForwardingEvent]: ...
    def get_liquidity_state(self, channel_id) -> LiquidityState: ...
    def update_fee_policy(self, channel_id, policy: FeePolicy) -> bool: ...
    def get_capabilities(self) -> BackendCapabilities: ...

    # Splice-Operationen (nur aktiv wenn can_splice == True)
    def splice_in(self, channel_id: str, amount_sat: int, fee_rate: int) -> SpliceAction: ...
    def splice_out(self, channel_id: str, amount_sat: int, destination: str, fee_rate: int) -> SpliceAction: ...
    def get_splice_status(self, splice_id: str) -> SpliceAction: ...
```

Der Adapter kapselt:
- RPC / gRPC / JSON-RPC Unterschiede
- Naming-Unterschiede (z. B. `chan_id` vs. `short_channel_id`)
- Event-Formate (z. B. HTLC-Events in LND vs. CLN-Plugin-Hooks)
- Capability-Flags (z. B. `can_splice`, `can_inbound_fees`)

#### CLN-spezifische Adapter-Details

**Verbindung:** CLN bietet zwei API-Wege:
- `clnrest` – HTTP REST API (empfohlen für neue Implementierungen, ab CLN v23.08)
- `cln-grpc` – gRPC (ähnlich wie LND, aber andere Schemas)

**Plugin-Abhängigkeiten (ClnBackend muss prüfen):**

| Plugin | Capability | CLN-Befehl |
|---|---|---|
| `clnrest` (Core) | Basisverbindung | – |
| `rebalance` | `can_rebalance` | `rebalance` |
| Core (ab v24.02) | `can_splice` | `splice_init`, `splice_update`, `splice_signed` |
| `feeadjuster` | `can_auto_fee` | – (alternativ: `setchannel`) |

> Ohne Adapter-Schicht wäre der Umgang mit CLN-Plugin-Abhängigkeiten fehleranfällig und schwer wartbar.

---

### 17.3 Capability-basierte UI

#### Refactoring-Regel

UI-Funktionen dürfen **nicht** fragen:

```python
# ❌ FALSCH – direkte Backend-Kopplung
if settings.backend == "LND":
    show_auto_fee_button()
```

sondern müssen fragen:

```python
# ✅ RICHTIG – Capability-basiert
if backend.get_capabilities().can_auto_fee:
    show_auto_fee_button()
```

#### Definierte Capabilities

```python
@dataclass
class BackendCapabilities:
    can_auto_fee: bool           # Fee-Anpassung via API möglich
    can_rebalance: bool          # Kreisförmige Payments für Rebalancing
    can_stream_htlcs: bool       # Live HTLC-Event-Stream verfügbar
    can_splice: bool             # Channel-Splice (Resize ohne Close) – CLN nativ; LND in Entwicklung
    can_inbound_fees: bool       # Inbound-Fee-Parameter unterstützt
    can_keysend: bool            # Spontane Payments (Keysend)
    supports_plugins: bool       # Plugin-Erweiterungs-Mechanismus vorhanden (CLN)
    can_multi_asset: bool        # Multi-Asset-Kanäle (Taproot Assets) – für spätere Phase
    ai_safe_actions: list[str]   # Welche WriteAdapter-Aktionen für policy_bound-KI freigegeben sind
                                 # z. B. ['update_fee_policy'] – nie 'splice_in'/'splice_out' ohne explizites Opt-in
```

#### UI-Verhalten

| Capability | LndBackend | ClnBackend | UI-Reaktion wenn `False` |
|---|---|---|---|
| `can_auto_fee` | ✅ (gRPC) | ✅ (`setchannel`) | Button ausgegraut + Tooltip |
| `can_splice` | ⚠️ (in Entwicklung) | ✅ (ab CLN v24.02) | Button ausgegraut + „Backend unterstützt Splicing nicht" |
| `can_rebalance` | ✅ (circular payment) | ✅ (`rebalance`-Plugin) | Rebalancing-Tab ausgegraut + Plugin-Hinweis |
| `supports_plugins` | ❌ | ✅ | CLN-Plugin-Panel einblenden |
| `can_multi_asset` | ⚠️ (Taproot Assets) | ⚠️ (Experimentell) | Asset-Bereich nur in Expert-Mode (Phase 7) |

**Vorteil für CLN:** CLN-Setups unterscheiden sich stark je nach installierten Plugins. Die UI kann Funktionen anzeigen/ausgrauen und erklären, welches Plugin fehlt – ohne harte LND-Feature-Parity vorauszusetzen.

---

### 17.4 Channel Splicing – Alleinstellungsmerkmal für Routing-Nodes

#### Was ist Channel Splicing?

Channel Splicing ermöglicht es, die Kapazität eines bestehenden Lightning-Channels **ohne Schließen und Wiedereröffnen** zu verändern. Es gibt zwei Operationen:

| Operation | Beschreibung |
|---|---|
| **Splice In** | On-Chain-Mittel in einen bestehenden Channel einzahlen → Kapazität erhöhen |
| **Splice Out** | Kapazität eines Channels reduzieren und Mittel On-Chain auszahlen |

Während des Splice-Vorgangs bleibt der Channel **aktiv und routing-fähig** (er wird nur kurz pausiert während der On-Chain-Bestätigung, nicht geschlossen).

#### Warum ist das für Routing-Nodes entscheidend?

Routing-Nodes sind kein statisches Netzwerk – Routing-Verhalten, Nachfrage und Peers ändern sich kontinuierlich. Heute sind die Optionen bei falscher Channel-Größe:

```
Zu klein → Routing-Chancen werden verpasst
           → Einzige Option: neuen Channel öffnen (On-Chain-Kosten × 2)

Zu groß  → Kapital ineffizient gebunden
           → Einzige Option: schließen + kleiner wiedereröffnen (On-Chain-Kosten × 2)
```

**Mit Splice:**

```
Zu klein → Splice In: Kapazität erhöhen, Channel bleibt offen, ein On-Chain-TX
Zu groß  → Splice Out: Überkapazität auszahlen, Channel bleibt offen, ein On-Chain-TX
```

#### CLN-nativer Splice-Support

Core Lightning unterstützt Splicing nativ ab **CLN v24.02** (`splice_init`, `splice_update`, `splice_signed`). Es ist keine zusätzliche Plugin-Installation nötig – es ist Teil des Core.

**LND:** Splice ist in Entwicklung (Experimental-Flag). LNDg unterstützt es capability-abhängig sobald stabil.

#### Guided Splice-Workflow (UI)

```
Trigger: Empfehlungs-Engine schlägt Splice vor
  → „Dein Channel zu [Peer] hat seit 30 Tagen konstant hohen Outbound-Flow
     und ist regelmäßig ausgeschöpft. Empfehlung: Splice In (+2M sats)"

Schritt 1: Impact-Vorschau
  → Neue Kapazität: 3M sats (aktuell: 1M sats)
  → Geschätzte On-Chain-Kosten: ~1.200 sats (🟢 günstig)
  → Routing-Pausierung: ~6 Blöcke (~60 Minuten)
  → Erwarteter Effekt: +40% Routing-Kapazität

Schritt 2: Betrag & Fee wählen
  → Schieberegler für Betrag (innerhalb konfigurierbarer Grenzen)
  → On-Chain-Fee: Auto (mempool.space) | Manuell
  → Warnung wenn mempool überlastet (🔴 teuer)

Schritt 3: Bestätigung (Impact-Check)
  → Risiko-Label: Niedrig (Kanal bleibt aktiv)
  → Audit-Log-Vorschau
  → „Ausführen" nur in Advanced/Expert-Mode

Schritt 4: Fortschritts-Tracking
  → Live-Status: Warte auf Bestätigung (Block X von 6)
  → Kanal-Status: „Splicing – eingeschränktes Routing"
  → Nach Abschluss: Bestätigungsnotifikation + Eintrag im Änderungsverlauf
```

#### Splice-Out-Workflow (Kapazität reduzieren)

```
Trigger: Empfehlung oder manuell
  → „Kanal zu [Peer] hat seit 60 Tagen kaum Routing-Aktivität.
     Erwäge Splice Out: 500k sats On-Chain zurückziehen statt zu schließen."

Vorschau:
  → Neue Kapazität: 500k sats (aktuell: 1M sats)
  → Auszahlung: 500k sats → [eigene On-Chain-Adresse]
  → Kosten, Dauer, Kanal bleibt offen

Besonderheit:
  → Splice Out ist oft günstiger als Close + Reopen
  → UI erklärt den Kostenvergleich explizit
```

#### Splice im Datenmodell

```python
@dataclass
class SpliceAction:
    channel_id: str
    splice_type: str              # "in" | "out"
    amount_sat: int               # Betrag der Splice-Operation
    on_chain_fee_sat: int         # Tatsächliche On-Chain-Fee
    destination: str | None       # Bei splice_out: Zieladresse
    status: str                   # "pending" | "broadcasting" | "confirming" | "confirmed" | "failed"
    blocks_remaining: int | None  # Schätzung verbleibende Blöcke
    txid: str | None              # On-Chain-Transaktions-ID
    initiated_at: datetime
    confirmed_at: datetime | None
```

```python
# Neues DB-Model für Splice-Historie
class SpliceLog(models.Model):
    channel_id = models.CharField(max_length=20, db_index=True)
    splice_type = models.CharField(max_length=5)   # "in" | "out"
    amount_sat = models.BigIntegerField()
    on_chain_fee_sat = models.BigIntegerField()
    status = models.CharField(max_length=20)
    txid = models.CharField(max_length=64, null=True)
    initiated_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True)
    rationale = models.TextField(blank=True)       # Warum wurde gespliced?
    recommendation_id = models.IntegerField(null=True)  # Verknüpfung zur Empfehlung

    class Meta:
        app_label = 'gui'
        indexes = [models.Index(fields=['channel_id', 'initiated_at'])]
```

---

### 17.5 Asset-agnostisches Datenmodell (Vorbereitung für spätere Phasen)

Auch wenn LNDg Next zunächst ausschließlich BTC-Routing zeigt, sollte jede Liquidität, jede Fee und jeder Flow intern ein Asset-Attribut tragen:

```python
@dataclass
class AssetContext:
    asset_id: str            # "btc" | "usdt.taproot" | ...
    asset_group: str         # "bitcoin" | "stablecoin" | "token"
    denomination: str        # "sat" | "msat" | "usd-cent" | ...
    display_unit: str        # "sats" | "USD" | "Token" (für UI)
    decimals: int            # Dezimalstellen für Darstellung
```

**Betroffene Domänenmodelle:**

```python
class ForwardingEvent:
    asset: AssetContext      # Default: AssetContext("btc", "bitcoin", "msat", "sats", 0)
    in_amount: int
    out_amount: int
    fee_earned: int
    ...

class FeePolicy:
    asset: AssetContext
    fee_rate_ppm: int
    base_fee: int
    ...

class LiquidityState:
    asset: AssetContext
    local_balance: int
    remote_balance: int
    ...
```

**Warum bereits jetzt modellieren (auch wenn Multi-Asset erst Phase 7 ist)?**

- Taproot Assets (ex-TARO) nutzen bestehende Lightning-Kanäle – kein separates Netzwerk
- Stablecoins auf Lightning werden kein „separate Channels"-System sein, sondern Routing auf bestehender Infrastruktur
- Ein späteres „DB-Rewrite" wäre extrem teuer – wenn das Datenmodell heute richtig ist, bleibt das UI morgen stabil
- Das `asset`-Attribut ist standardmäßig auf `btc` gesetzt und kostet keine Mehraufwände in Phase 1–6

**BTC bleibt Default:** Multi-Asset-UI erscheint erst in Phase 7, nur in Advanced/Expert-Mode und nur wenn `can_multi_asset` aktiv ist.

---

### 17.6 Implementierungsneutrale Policies

#### Fehler, den man jetzt vermeiden sollte

```python
# ❌ FALSCH – LND-spezifische Policy-Logik
def run_auto_fee():
    lnd_client.update_channel_policy(
        chan_point=lnd_channel_id,
        fee_rate_ppm=calculated_ppm,
        time_lock_delta=LND_DEFAULT_CLTV
    )
```

#### Richtige Struktur: Domänenebene + Backend-Adapter

```python
# ✅ RICHTIG – implementierungsneutrale Policy
@dataclass
class FeePolicyUpdate:
    """Domänen-Objekt: Was soll passieren (ohne Backend-Details)."""
    channel_id: str           # Abstrakte Channel-ID
    target_fee_rate_ppm: int
    target_base_fee: int
    rationale: str            # Für Audit-Log

# Executor delegiert an den aktiven Backend-Adapter:
def execute_fee_policy(update: FeePolicyUpdate):
    backend = get_active_backend()   # LndBackend oder ClnBackend
    backend.update_fee_policy(update.channel_id, FeePolicy(
        fee_rate_ppm=update.target_fee_rate_ppm,
        base_fee=update.target_base_fee,
    ))
    ChangeLog.create(rationale=update.rationale, ...)
```

**Vorteil:**
- LND verwendet integrierte gRPC-Mechaniken
- CLN verwendet `lightning-cli setchannel` oder Plugin-API
- Die Policy bleibt gleich – nur der Executor ändert sich

---

### 17.7 UX-Strategie: CLN als gleichrangiger Bürger

#### Konkrete UI-Regeln

1. **Keine LND-Begrifflichkeiten in der UI**  
   Statt „LND Channel ID" → „Channel ID"  
   Statt „LND Macaroon" → „Node-Zugangsdaten"  
   Statt „HTLC forwarding event" → „Weiterleitungsereignis"

2. **Keine Screens, die implizit identische Features aller Nodes voraussetzen**  
   Jede Funktion ist mit Capability-Check versehen – in der UI unsichtbar wenn nicht unterstützt.

3. **Beträge und Einheiten flexibel halten**  
   Texte, Charts, Erklärungen arbeiten mit `denomination`-Platzhaltern statt hardcodierten „sats":
   
   ```
   ❌ "Dein Outbound-Guthaben beträgt 500.000 sats"
   ✅ "Dein Outbound-Guthaben beträgt 500.000 {denomination}"
   ```

4. **Onboarding erkennt das Backend**  
   Der Guided-Wizard erkennt automatisch via Capability-Check, welches Backend aktiv ist, und passt Erklärungen, Terminologie und Funktionen an:

   ```
   LND-Nutzer sieht:  „Macaroon-Pfad", „gRPC-Adresse"
   CLN-Nutzer sieht:  „Rune / API-Token", „clnrest-Endpunkt", „Plugin-Status"
   ```

5. **CLN Plugin-Panel im Expert-Mode**  
   Übersicht aller bekannten CLN-Plugins mit Status (installiert / aktiv / fehlend). Für fehlende Plugins: Erklärung + Installationshinweis.

#### Strategischer Effekt

Core Lightning ist technisch führend (native Splice-Unterstützung, flexible Plugin-Architektur), hat aber bisher keine moderne, erklärende GUI. **LNDg Next ist die erste vollwertige GUI für CLN-Routing-Node-Betreiber.**

Dies öffnet einen neuen Nutzerkreis:
- CLN-Betreiber, die bisher auf CLI-Tools angewiesen waren
- Einsteiger, die CLN wählen, aber keine GUI hatten
- Routing-Node-Betreiber, die Splice-Workflows grafisch steuern möchten

---

### 17.8 Refactoring-Checkliste (kompakt)

| Punkt | Beschreibung | Phase |
|---|---|---|
| ✅ Abstraktes Domänenmodell | `Channel`, `Peer`, `ForwardingEvent`, `FeePolicy`, `SpliceAction` backend-neutral | Phase 1 |
| ✅ LndBackend | Bestehende LND-Logik als Adapter-Implementierung | Phase 1 |
| ✅ ClnBackend | CLN-Implementierung via `clnrest`/`cln-grpc` | Phase 1–2 |
| ✅ Capability-basierte UI | Kein `if backend == "LND"` in Templates/Views | Phase 2 |
| ✅ Guided Splice-Workflow | Splice-In/Out mit Kostenvorschau + Fortschritts-Tracking | Phase 3 |
| ✅ CLN Plugin-Panel | Plugin-Status-Übersicht, Capability-Hinweise | Phase 3 |
| ✅ Implementierungsneutrale Policies | Policy-Objekte auf Domänenebene; Executor delegiert an Adapter | Phase 4 |
| ✅ CLN-Policy-Adapter | `setchannel`, `rebalance`-Plugin-Integration | Phase 4 |
| ✅ UX ohne implizite LND-Annahmen | Backend-erkennender Onboarding-Wizard; generische Begriffe | Phase 1+ |
| ✅ KI Advisory Layer | `ReadAdapter`-only; Rationale-Schema; Shadow-Log; AI-Feature-Flags (Default: off) | Phase 1–3 |
| ✅ KI Policy-Bound Automation | `LightningWriteAdapter` nur über Validation Layer; Human-Confirmation; ChangeLog-Pflicht | Phase 4–5 |
| 🔮 KI Agentic (Stufe 3) | Vollautomation mit Hard Caps; nur nach Shadow-Mode-Erfolg; ausschließlich Expert-Mode | Phase 6 |
| 🔮 Multi-Asset-UI | Asset-Bereich in Advanced/Expert wenn `can_multi_asset` aktiv | Phase 7 |
| 🔮 Unit-flexible UI | `denomination`-Platzhalter statt hardcodierten „sats" | Phase 7 |

**Was dadurch möglich wird:**

- **Sofort:** LND-Nutzer erhalten die beste Routing-Optimierungs-GUI
- **Phase 2–3:** CLN-Nutzer erhalten die **erste vollwertige CLI-freie Node-Management-GUI** für Core Lightning
- **Phase 3:** Routing-Nodes können Channel-Kapazitäten via **Splice ohne Close/Reopen** optimieren
- **Phase 7+:** Taproot Assets / Multi-Asset ohne Architekturbruch nachrüstbar
- LNDg entwickelt sich vom „LND-Tool" zum **Lightning Node Intelligence Layer**

---

## Anhang: Abhängigkeiten bestehender LNDg-Komponenten

### Aktuell vorhandene Jobs (jobs.py)

Die bestehenden Jobs werden in Phase 1 nicht verändert, aber in Phase 2 schrittweise in die neue Service-Architektur überführt:

- Forwarding-Collector → `collector.py`
- Auto-Fee-Logik (`af.py`) → wird in die neue Policy-/Executor-Struktur überführt
- Rebalancer (`rebalancer.py`) → wird in die neue Job-/Policy-Struktur überführt
- HTLC-Stream (`htlc_stream.py`) → wird als Collector-Modul in die neue Jobstruktur überführt

**Wichtig für alle Jobs:** Kein Job darf `LightningWriteAdapter` direkt importieren – ausschließlich über den Validation Layer (Abschnitt 9.0). KI-Jobs (`recommender.py`, `ml_predictor.py`) sind rein lesend und haben keinen Zugriff auf `LightningWriteAdapter`.

### Bestehende API-Endpunkte

Alle bestehenden `/api/`-Endpunkte bleiben unverändert. Die neuen `/api/v2/`-Endpunkte ergänzen sie. Erst in Phase 3+ werden alte Endpunkte als „deprecated" markiert (mit Übergangsfrist von mindestens 6 Monaten).

---

*Dieses Dokument ist ein lebendes Konzept. Änderungen und Ergänzungen sind erwünscht. Die Grundentscheidungen aus Abschnitt 16 sind getroffen (nur P4 – Community-Sharing – ist bewusst zurückgestellt). Implementierung kann mit Phase 1 beginnen.*

---

## 18. KI & Agentic KI – Advisory, Safety und graduierte Autonomie

> **Leitprinzip: „AI-Assisted, Policy-Bound, Human-Controlled"**  
> KI ist für LNDg ein hochwertiges Analyse-, Erklär- und Empfehlungssystem. Agentische KI (handelnde Autonomie) auf einem Lightning-Node ist zunächst gefährlich und darf nur sehr begrenzt, streng kontrolliert und schrittweise eingesetzt werden.

---

### 18.1 Warum KI wertvoll – und agentische KI gefährlich ist

**Hoher Wert (sofort):**
- Routing-Muster erkennen, Liquiditäts-Drift analysieren, Peer-Verhalten klassifizieren
- Fee-Elastizität abschätzen, Erfolg/Misserfolg von Maßnahmen evaluieren
- Fachbegriffe erklären, Charts kommentieren, nächste sinnvolle Aktion bewerten

**Reales Risiko bei unkontrollierter Automation:**
- Fee-Explosion / Rebalancing-Churn durch fehlerhafte Aktionskaskaden
- Kapitalverlust durch halluzinierte Parameter oder fehlerhafte Confidence-Scores
- Gossip-Spam durch zu häufige Fee-Anpassungen
- Reputationsschaden im Lightning-Netzwerk

**Konsequenz:** KI wird als erfahrener Analyst behandelt – nicht als autonomer Node-Admin.

---

### 18.2 Drei Autonomiestufen (graduierte Aktivierung)

| Stufe | Bezeichnung | Was KI darf | Was KI nicht darf | LNDg-Phase |
|---|---|---|---|---|
| 🟢 **1** | `advisory` | Analysieren, Erklären, Empfehlen, Simulieren | Fees ändern, Kanäle öffnen/schließen, Rebalance auslösen | Phase 1–3 (Default) |
| 🟡 **2** | `policy_bound` | Empfehlungen innerhalb vordefinierter Policies mit Hard Caps, Cooldowns und vollständigem Audit-Trail | Aktionen ohne Human Confirmation oder Policy-Freigabe | Phase 4–5 (opt-in, Expert) |
| 🔴 **3** | `agentic` | Policy-gebundene Ausführung ohne manuelle Bestätigung pro Aktion | Alles außerhalb definierter Policy-Grenzen; niemals breite Node-Credentials | Phase 6+ (sehr begrenzt, nur Expert) |

**Stufe 1 ist Default und der empfohlene Dauerbetrieb für neue Nutzer.**  
Höhere Stufen werden ausschließlich im Expert-Modus freigeschaltet, erfordern explizite Bestätigung und sind jederzeit einzeln rückschaltbar.

**Beispiel Stufe 2 (policy_bound):**
```
Policy: "Wenn outbound_ratio < 20 % für ≥ 7 Tage
  → Empfehle Fee-Erhöhung um max. 5 %
  → Ausführung nur nach User-Bestätigung (kein Auto-Apply)"
KI = Policy-Interpreter, nicht Entscheider
```

---

### 18.3 Action-Gateway-Architektur (absolut kritisch)

KI darf **niemals direkt:**
- gRPC-Calls auslösen
- `LightningWriteAdapter`-Methoden aufrufen
- Node-Zustand ändern

Der vollständige Datenfluss ist in Abschnitt 9.0 dargestellt. Als Referenz:

```
KI-Modul  →  Recommendation-Objekt
                    │
             Policy Engine (Regelprüfung)
                    │
             Validation Layer (Caps, Cooldown, Sanity-Checks)
                    │
          Human / Approved Automation (Policy-gebunden)
                    │
          LightningWriteAdapter  →  ChangeLog
```

Das verhindert Halluzinations-Damage, Parameter-Fehler und „Guessing instead of verifying".

---

### 18.4 AI-Feature-Flags (im `UserMode`-Model, Abschnitt 9.1)

| Feld | Typ | Default | Beschreibung |
|---|---|---|---|
| `ai_mode` | enum | `off` | `off` \| `advisory` \| `shadow` \| `policy_bound` |
| `ai_explain_always` | bool | `True` | Erklärungstext immer anzeigen (nie ausblendbar in Guided/Advanced) |
| `ai_min_data_days` | int | `30` | Mindestdatenmenge (Tage) bevor KI Empfehlungen ausgibt |
| `ai_max_auto_actions_day` | int | `0` | Max. automatische Aktionen/Tag (0 = manuell only) |
| `ai_cooldown_minutes` | int | `60` | Mindestwartezeit zwischen KI-getriggerten Änderungen |
| `ai_shadow_log_enabled` | bool | `True` | Shadow-Mode-Protokoll: KI-Empfehlungen loggen ohne auszuführen |

**Aktivierungsregeln:**
- `ai_mode != 'off'` → nur im Expert-Modus einstellbar, erfordert explizite Bestätigung
- `ai_mode = 'policy_bound'` → zusätzlich: mindestens eine aktive Policy muss definiert sein
- Jede Änderung an `ai_mode` schreibt einen `ChangeLog`-Eintrag

---

### 18.5 Erklärbarkeit by Design

Jede KI-Empfehlung **muss** anzeigen: Warum? Welche Daten? Welche Alternativen? Wie sicher?

Ohne Erklärbarkeit → keine Ausführung. Das Rationale-Schema (Abschnitt 5.2) ist die technische Grundlage. Im Guided-Modus ist das „Warum?"-Panel immer sichtbar, in Advanced per Tooltip, in Expert ausblendbar.

**Shadow-Mode-Protokoll:**  
Wenn `ai_mode = 'shadow'`, werden KI-Empfehlungen im `ChangeLog` protokolliert und kontinuierlich mit dem tatsächlichen Ergebnis verglichen – ohne ausgeführt zu werden. Das ist die Grundlage, um schrittweise Vertrauen in ein Modell aufzubauen, bevor `policy_bound` aktiviert wird.

---

### 18.6 Simulation Layer

Der `dry_run`-Mechanismus (Abschnitt 6.1) wird als vollwertiger Simulation Layer ausgebaut:

- Jede Policy kann mit `simulate=True` aufgerufen werden
- Ergebnis: Welche Fees/Balances würden sich wie ändern? (basierend auf Vergangenheitsdaten)
- `dry_run_result` wird in `Recommendation` und `PolicyRun` gespeichert
- UI: „Was wäre passiert, wenn..."-Widget im Lernen-&-Verlauf-Bereich
- **Keine KI nötig** – der Simulation Layer ist deterministisch und ab Phase 3 sofort verfügbar

Der Simulation Layer ist auch die sichere Sandstrecke zum Testen von `policy_bound`-Konfigurationen, bevor sie live gehen.

---

### 18.7 ChannelSnapshot & ChangeLog als KI-Datenbasis

KI kann nur so gut sein wie die Datenbasis. Beide Modelle (Abschnitt 9.1) erfüllen gleichzeitig operative und KI-Anforderungen:

| Modell | Operative Funktion | KI-Funktion |
|---|---|---|
| `ChannelSnapshot` | Zeitreihen für Charts | Feature-Engineering für ML-Modelle |
| `ChangeLog` | Audit-Trail aller Änderungen | Event-Sourcing: Trainingsdaten + Rollback-Grundlage |
| `RebalanceMLRecord` | Rebalance-Lernhistorie | Kanalpar-Erfolgsrate, Zeitreihen-Features |
| `AutoFeeMLRecord` | Auto-Fee-Lernhistorie | Fee-Elastizität, Drain-Velocity-Muster |

**KI-Bereitschafts-Maßnahme:** `ChannelSnapshot` und `ChangeLog` werden ab Phase 1 aktiv befüllt – auch wenn KI-Features noch nicht aktiv sind. Ohne historische Daten können ML-Modelle in Phase 4–6 nicht sinnvoll trainiert werden.

---

### 18.8 CLN-spezifische KI-Sicherheitsregeln

CLN ist plugin-basiert – das erhöht die Flexibilität, aber auch die Angriffsfläche:

- KI/Policy darf niemals Plugin-Zustandsänderungen direkt auslösen
- CLN-Plugin-Aktionen laufen ausschließlich über `LightningWriteAdapter` mit denselben Guardrails wie LND
- Im Capability-System (Abschnitt 17.3) wird eine `AI_SAFE`-Markierung für KI-taugliche Operationen eingeführt: nur `AI_SAFE`-markierte Aktionen dürfen in `policy_bound`-Automation einfließen
- CLN-Plugins sind mögliche Ausführungsschicht für deterministische Aktionen – niemals Entscheidungsschicht

---

### 18.9 Was jetzt (noch) nicht umgesetzt wird

Die folgenden Punkte sind bewusst ausgeschlossen bis die Sicherheitsarchitektur (Stufen 1–2) vollständig etabliert und erprobt ist:

| Nicht jetzt | Grund |
|---|---|
| KI mit Schreibrechten auf LND/CLN | Stufe 1–2 zuerst etablieren |
| Externe KI-API ohne Opt-in (OpenAI, Anthropic etc.) | Datenschutz: keine Node-Daten extern ohne explizite Einwilligung |
| Auto-Execution ohne `PolicyRun`-Protokoll | Nachvollziehbarkeit nicht gewährleistet |
| KI-Zugriff auf Macaroon/Cert-Pfade | Credential-Scope strikt trennen |
| `ai_mode = 'policy_bound'` ohne mindestens 30 Tage Datenbasis | Modellqualität zu gering |
| Agentische Stufe 3 ohne explizites Shadow-Mode-Protokoll der Vorphasen | Vertrauen muss progressiv aufgebaut werden |

---

### 18.10 Implementierungsfahrplan KI

| Phase | KI-Task |
|---|---|
| **1** | `ReadAdapter`/`WriteAdapter`-Trennung implementieren; AI-Feature-Flags in `UserMode` (Default: `off`); `ChannelSnapshot` + `ChangeLog` aktiv befüllen |
| **2** | Shadow-Log-Infrastruktur: KI-Empfehlungen mitloggen (noch kein ML-Modell nötig) |
| **3** | Simulation Layer; Rationale-Schema in Recommendation validieren; „Was wäre passiert"-Widget |
| **4** | `ai_mode = 'shadow'` freischalten (Expert): ML-Empfehlungen parallel zu Heuristik loggen; `RebalanceMLRecord` + `AutoFeeMLRecord` befüllen |
| **5** | `ai_mode = 'policy_bound'` freischalten (Expert): Policy-gebundene KI-Automation mit Human-Confirmation-Layer |
| **6** | Vollautomation (sehr begrenzt, opt-in Expert): nur nach nachgewiesenem Shadow-Mode-Erfolg + konfigurierten Hard Caps |

---

*Dieses Dokument ist ein lebendes Konzept. Änderungen und Ergänzungen sind erwünscht. Die Grundentscheidungen aus Abschnitt 16 sind getroffen (nur P4 – Community-Sharing – ist bewusst zurückgestellt). Implementierung kann mit Phase 1 beginnen.*

---

## 19. ToDo-Liste / Implementierungs-Tracking

> **Hinweis:** Jede Aufgabe ist so dimensioniert, dass sie in einer einzigen Copilot-Prompt-Sitzung umsetzbar ist. Abhängigkeiten innerhalb einer Phase sind durch die Reihenfolge impliziert – bei Zweifeln zuerst die früheren Aufgaben abschliessen.
>
> **Stand-Interpretation (05/2026):** Nicht abgehakte Punkte sind entweder noch offen oder nur teilweise umgesetzt. Das betrifft insbesondere die vollständige i18n-Abdeckung in Legacy-Views, die vollständige Capability-/ChangeLog-Migration alter Write-Pfade, verpflichtende Backup-Guards vor Restore/Bulk-Operationen, vollständige Tooltip-Abdeckung in allen neuen Charts sowie den noch offenen Analyzer-/„Was wäre passiert“-Baustein.

---

### Phase 1 – Foundation

#### 1-A: Makefile & CI-Pipeline
- [x] `Makefile` anlegen mit Targets: `dev`, `test`, `lint`, `fmt`, `check`, `build`, `migrate`
- [x] `.github/workflows/ci.yml` anpassen: separater `test-backend`- und `test-frontend`-Job, pip-Cache per `requirements.txt`-Hash, Node-Cache per `package-lock.json`-Hash

#### 1-B: Multi-Stage Dockerfile
- [x] `Dockerfile` als Multi-Stage-Build umschreiben (Stage: `frontend-builder`, `python-deps`, `final`)
- [x] Final-Image als rootless Container konfigurieren (non-root user, Arbeitsverzeichnis `/lndg/`)
- [x] Upgrade-Dokumentation für Breaking Change (`/app` → `/lndg/`) erstellen

#### 1-C: Sicherheits-Baseline
- [x] Alle `paramiko`-Verbindungen auf `RejectPolicy()` umstellen (kein `AutoAddPolicy`)
- [x] Alle Stellen prüfen und anpassen, wo Credential-Dateien erzeugt werden → `mode=0o600`
- [x] `requirements.in` anlegen und `pip-compile` für `requirements.txt` mit Versions-Bounds einrichten

#### 1-D: Abstrakte Lightning-Domänenmodelle
- [x] Python-Dataclasses erstellen: `Node`, `Peer`, `Channel`, `ForwardingEvent`, `LiquidityState`, `FeePolicy`, `SpliceAction`, `RebalanceAction`
- [x] `AssetContext`-Dataclass mit Default `btc` einführen (als Vorbereitung für Phase 7)
- [x] Modul-Struktur unter `gui/domain/` anlegen und alle Domänenklassen dort platzieren

#### 1-E: LightningBackend Interface (Read/Write-Trennung)
- [x] Abstrakte Klasse `LightningReadAdapter` mit allen Lese-Methoden (`get_node_info`, `list_channels`, `list_peers`, `get_forwarding_events`, `get_liquidity_state`, `get_capabilities`) definieren
- [x] Abstrakte Klasse `LightningWriteAdapter` mit allen Schreib-Methoden (`update_fee_policy`, `splice_in`, `splice_out`, `get_splice_status`) definieren
- [x] `BackendCapabilities`-Dataclass mit allen Capability-Flags (`can_auto_fee`, `can_rebalance`, `can_stream_htlcs`, `can_splice`, `can_inbound_fees`, `can_keysend`, `supports_plugins`, `can_multi_asset`, `ai_safe_actions`) definieren

#### 1-F: LndBackend Adapter
- [x] `gui/backends/lnd_backend.py` anlegen, der `LightningReadAdapter` implementiert (bestehende LND-gRPC-Logik kapseln)
- [x] `LightningWriteAdapter` in `LndBackend` implementieren (bestehende Fee-Update-Logik kapseln)
- [x] gRPC-Credentials-Caching: Credentials einmalig laden und Connection über Job-Lifecycle wiederverwenden (kein Reconnect pro Request)
- [x] `LndBackend.get_capabilities()` mit korrekten LND-spezifischen Capability-Flags implementieren

#### 1-G: ClnBackend Skelett
- [x] `gui/backends/cln_backend.py` anlegen mit Verbindungsaufbau via `clnrest` (HTTP REST)
- [x] Authentifizierung via Rune / API-Token implementieren
- [x] Basis-Methoden implementieren: `get_node_info`, `list_channels`, `list_peers`
- [x] `ClnBackend.get_capabilities()` mit CLN-spezifischen Flags implementieren (`can_splice=True` ab v24.02, `supports_plugins=True`)

#### 1-H: UserMode Django Model
- [x] `UserMode`-Model anlegen mit Feldern: `mode` (guided/advanced/expert), `onboarding_step`, `onboarding_completed`, `language`, `updated_at`
- [x] AI-Feature-Flags im Model anlegen: `ai_mode` (default `off`), `ai_explain_always`, `ai_min_data_days`, `ai_max_auto_actions_day`, `ai_cooldown_minutes`, `ai_shadow_log_enabled`
- [x] Migration erstellen und `class Meta: app_label = 'gui'` sicherstellen
- [x] API-Endpunkte `GET/PUT /api/v2/user/settings` anlegen (rate-limiting, CSRF, authentication)

#### 1-I: Django i18n Basis
- [x] `settings.py` für i18n konfigurieren: `USE_I18N=True`, `USE_L10N=True`, `LANGUAGES=[('de', ...), ('en', ...)]`, `LOCALE_PATHS`
- [ ] Alle bestehenden User-facing Strings in Templates mit `{% trans "..." %}` markieren
- [ ] Alle bestehenden User-facing Strings in Python-Dateien mit `_("...")` markieren
- [x] `locale/de/LC_MESSAGES/django.po` und `locale/en/LC_MESSAGES/django.po` initial befüllen und kompilieren

#### 1-J: Neue Hauptnavigation & Modus-Switcher
- [x] Navigation auf 5 Kernbereiche umstellen: Cockpit, Channels, Peers, Automationen, Lernen & Verlauf
- [x] Modus-Switcher (Guided/Advanced/Expert) im Header implementieren, Auswahl in `UserMode` speichern
- [x] Cockpit-Seite mit Basis-Kacheln anlegen (Routing-Aktivität, Liquiditätsbalance, Fee-Positionierung, Probleme, Nächste Aktion) – vorerst nur Darstellung ohne Recommendation Engine

---

### Phase 2 – CLN-Integration & Daten

#### 2-A: Zeitreihen-Models
- [x] `ChannelSnapshot`-Model mit Feldern anlegen: `timestamp` (db_index), `chan_id` (db_index), `local_balance`, `remote_balance`, `capacity`, `local_fee_rate`, `local_base_fee`, `local_disabled`, `is_active` + Composite-Index `[chan_id, timestamp]`
- [x] `ForwardingAggregate`-Model anlegen mit `window`, `chan_id`, `window_start`, `in_msat`, `out_msat`, `fees_msat`, `forward_count`, `fail_count` + `unique_together`
- [x] Migrationen erstellen; Retention-Regeln in `cleaner.py` für beide Models hinzufügen

#### 2-B: ChangeLog Model
- [x] `ChangeLog`-Model anlegen: `timestamp`, `change_type`, `target_chan_id`, `actor` (`manual`/`policy:<name>`/`ml:<model>:<version>`), `old_value`, `new_value`, `rationale`, `policy_run` (FK)
- [x] Migration erstellen; Index auf `timestamp` und `target_chan_id`
- [ ] `ChangeLog`-Eintrag bei jeder bestehenden Fee-Änderung / Rebalance-Aktion automatisch erzeugen

#### 2-C: Collector Job
- [x] `jobs/collector.py` erstellen: liest Channel-Daten von aktivem Backend (LND + CLN) und erstellt `ChannelSnapshot`-Einträge alle 15 Min (konfigurierbar)
- [ ] Async ORM-Methoden verwenden (`abulk_create`, `aget`, `afilter`)
- [x] gRPC-Verbindung über gesamten Job-Lifecycle cachen (kein Reconnect pro Snapshot)

#### 2-D: Aggregator Job
- [x] `jobs/aggregator.py` erstellen: berechnet `ForwardingAggregate` für Fenster `1d`, `7d`, `30d` stündlich aus `Forwards`-Tabelle
- [x] Idempotent implementieren (kein Duplikat bei Mehrfachausführung)

#### 2-E: Capability-Registry & capability-basierte UI
- [x] `BackendCapabilities`-Instanz beim Start des Backends registrieren und als Singleton verfügbar machen
- [ ] Alle bestehenden `if settings.backend == "LND":`-Branches in Templates/Views durch Capability-Checks ersetzen
- [x] API-Endpunkt `GET /api/v2/capabilities` anlegen, der aktuelle Capabilities zurückgibt
- [ ] Buttons für nicht unterstützte Capabilities in UI deaktivieren + Tooltip-Erklärung

#### 2-F: CLN Backend vollständig
- [ ] `ClnBackend` um alle Methoden erweitern: `get_forwarding_events` (via `listforwards`), `update_fee_policy` (via `setchannel`), HTLC-Stream via CLN-Hooks
- [ ] Plugin-Abhängigkeiten prüfen: `rebalance`, `feeadjuster`; fehlende Capabilities korrekt auf `False` setzen
- [ ] Integrations-Tests für CLN-Adapter (Mock-Server)

#### 2-G: CLN-Onboarding-Pfad
- [ ] Onboarding-Wizard erkennt über `get_capabilities()` das aktive Backend
- [ ] CLN-spezifische Erklärungen und Terminologie: „Rune / API-Token" statt „Macaroon", „clnrest-Endpunkt", Plugin-Status
- [ ] LND-Terminologie aus allen Templates entfernen (kein `chan_id`, `lnd_short_chan_id` in UI-Texten)

#### 2-H: Backup/Restore
- [x] `BackupLog`-Model anlegen + Migration + `cleaner.py`-Regel
- [x] Backup-Job in `jobs/` anlegen: Settings-Backup (JSON), vollständiger DB-Dump, optionaler Macaroon-Backup
- [ ] Automatisches Backup vor jedem Restore und vor jeder Bulk-DB-Operation
- [x] UI-Flow für Backup (Typ wählen, Passwortschutz, Download) und Restore (Upload, Checksum, Vorschau, Bestätigung)

#### 2-I: DB-Bereinigung (cleaner.py)
- [x] `jobs/cleaner.py` anlegen mit konfigurierbaren Retention-Regeln für alle Tabellen (Standard-Aufbewahrungszeiten aus Abschnitt 11.3)
- [x] Bestehende `clean_failed_payments`-Funktion in `cleaner.py` integrieren
- [ ] Batch-Löschung (verhindert DB-Lock); automatisches Mini-Backup der gelöschten Daten (optional)
- [x] UI: Tabellen-Übersicht, Schieberegler für Aufbewahrungsdauer, Vorschau der Löschmenge, manueller Trigger

#### 2-J: Neue Chart-Komponenten
- [x] **Liquidity Donut**: Inbound vs. Outbound pro Channel + Node-Gesamt (Daten: `Channels.local/remote_balance`)
- [x] **Channel Health Heatmap**: Zeit vs. Channel (Balance/Volume) basierend auf `ChannelSnapshot`
- [x] **Fee vs. Volume Scatter**: Fee-Elastizität aus `Forwards` + `FeeLog`
- [ ] Alle Komponenten mit `title` + `tooltip` ausstatten (R-GUI-4)

---

### Phase 3 – Empfehlungs-Engine & Splice-Workflow

#### 3-A: Recommendation & Policy Models
- [x] `Recommendation`-Model anlegen: `created_at`, `rec_type`, `target_chan_id`, `target_pubkey`, `rationale` (JSONField), `confidence`, `risk_level`, `status`, `dry_run_result`, `applied_at` + Migration
- [x] `Policy`-Model anlegen: `name`, `policy_type`, `definition` (JSONField), `is_active`, `dry_run` (default `True`), `created_at`, `last_run`, `mode_required` + Migration
- [x] `PolicyRun`-Model anlegen: `policy` (FK), `executed_at`, `was_dry_run`, `trigger_data`, `actions_taken`, `outcome` + Migration + Retention-Regel in `cleaner.py`

#### 3-B: Heuristik-Engine
- [x] `jobs/recommender.py` anlegen (nur lesend, kein `LightningWriteAdapter`-Import)
- [x] Heuristiken implementieren: Stagnation (kein Outbound-Flow), einseitige Balance, hohe Failed-HTLC-Rate, Peer-Konzentration, ungenutzte Kapazität, hoher Outbound-Flow
- [x] Rationale-Schema (JSON) gemäß Abschnitt 5.2 für jede Empfehlung befüllen (`reasons`, `confidence`, `confidence_label='heuristic'`, `alternatives`, `simulation_available`)
- [x] Empfehlungen als `Recommendation`-Objekte in DB speichern; Top-3 pro Cockpit-Aufruf liefern

#### 3-C: Simulation Layer (Dry-Run Framework)
- [x] Jede Policy mit `simulate=True`-Flag aufrufbar machen; Ergebnis in `dry_run_result` speichern
- [ ] `jobs/analyzer.py` anlegen: berechnet Channel-Scores, Peer-Scores auf Basis historischer Daten
- [x] API-Endpunkte: `POST /api/v2/recommendations/{id}/dryrun` und `POST /api/v2/policies/{id}/run` (mit `simulate=True`)
- [ ] „Was wäre passiert wenn…"-Widget im Lernen-&-Verlauf-Bereich

#### 3-D: Explainability-UI
- [ ] „Warum?"-Panel für jede Empfehlung: Top-3 Gründe aus `rationale.reasons`, Datenquelle, Konfidenzlabel
- [ ] Im Guided-Modus immer sichtbar, Advanced als Tooltip, Expert ausblendbar
- [ ] Glossar-Begriffe in Templates automatisch als Tooltip-Links hervorheben

#### 3-E: SpliceLog Model & API
- [x] `SpliceLog`-Model anlegen: `channel_id`, `splice_type`, `amount_sat`, `on_chain_fee_sat`, `status`, `txid`, `initiated_at`, `confirmed_at`, `rationale`, `recommendation_id` + Migration + Index
- [x] API-Endpunkte anlegen: `GET /api/v2/channels/{id}/splice/preview`, `POST /api/v2/channels/{id}/splice/in`, `POST /api/v2/channels/{id}/splice/out`, `GET /api/v2/channels/{id}/splice/status`
- [x] Alle Endpunkte: rate-limiting, CSRF, authentication; nur über `LightningWriteAdapter` via Validation Layer

#### 3-F: Guided Splice-Workflow CLN
- [ ] Schritt-für-Schritt UI für Splice-In: Impact-Vorschau (neue Kapazität, On-Chain-Kosten, Routing-Pausierung, erwarteter Effekt), Betrag-Schieberegler, Bestätigungs-Dialog mit Risiko-Label
- [ ] Fortschritts-Tracking (Blöcke-Anzeige bis Bestätigung, Kanal-Status „Splicing – eingeschränktes Routing")
- [ ] Splice-Out-Workflow analog + Kostenvergleich (Splice Out vs. Close + Reopen)
- [ ] Audit-Log-Eintrag bei jedem Splice-Vorgang; `actor`-Feld gemäß R-AI-4 befüllen

#### 3-G: Splice-Workflow LND & CLN Plugin-Panel
- [x] LND-Splice-Workflow: gleicher UI-Flow wie CLN, aber capability-abhängig aktiviert (`can_splice`); Button deaktiviert + Tooltip wenn nicht verfügbar (R-GUI-7)
- [x] CLN Plugin-Status-Panel (Expert-Mode): Liste aller bekannten CLN-Plugins mit Status (installiert/aktiv/fehlend), Erklärung + Installationshinweis für fehlende Plugins

---

### Phase 4 – Policy-Engine & Automationen

#### 4-A: Policy-Engine & Executor Job
- [x] `jobs/executor.py` anlegen: führt Policies aus – als **einzige Datei** mit `LightningWriteAdapter`-Import
- [x] Validation Layer implementieren: Sanity-Checks, Hard Caps, Cooldown-Guard vor jeder Ausführung
- [x] `PolicyRun`-Eintrag vor jeder Ausführung anlegen; `ChangeLog`-Eintrag nach jeder Ausführung mit `actor=policy:<name>`
- [x] Policy-Snapshot vor jeder Änderung speichern (ermöglicht Rollback)

#### 4-B: Auto-Fee Templates
- [ ] Drei UI-Templates implementieren: Conservative (max. alle 7d, ±10 %), Balanced (alle 2–3d, ±20 %), Revenue-Seeking (täglich, ±40 %)
- [ ] Expert-Detailpanel: alle Parameter erst bei explizitem Aufklappen sichtbar
- [x] Templates als Default-`Policy`-Objekte in DB anlegen (keine Defaults in View-Logik, R-DM-2)
- [x] Default `dry_run=True` für alle neuen Policies (R-GUI-3)

#### 4-C: CLN Policy-Adapter
- [x] `setchannel`-Aufrufe für Fee-Policies in `ClnBackend.update_fee_policy` implementieren
- [ ] CLN-Rebalancing via `rebalance`-Plugin in `ClnBackend` integrieren (capability-abhängig)
- [x] Policy-Objekte sind implementierungsneutral auf Domänenebene; Executor delegiert via Backend-Adapter

#### 4-D: RebalanceMLRecord & AutoFeeMLRecord Models
- [x] `RebalanceMLRecord`-Model anlegen: `timestamp`, `source_chan_id`, `target_chan_id`, `amount_sat`, `fee_ppm`, `hour_of_day`, `day_of_week`, `success`, `routing_revenue_delta_24h`, `routing_revenue_delta_7d`, `ml_predicted_success_prob`, `ml_confidence` + Migration + Composite-Index
- [x] `AutoFeeMLRecord`-Model anlegen: `timestamp`, `chan_id`, `param_name`, `old_value`, `new_value`, `trigger_reason`, `ml_confidence`, `routing_volume_delta_24h`, `routing_revenue_delta_24h`, `escalation_level` + Migration + Index
- [x] Beide Models: `amount_sat`/`routing_revenue_delta_*` als `BigIntegerField` (R-DM-3); keine `FloatField` für Beträge

#### 4-E: ML Shadow Mode – Auto-Fee
- [ ] Balance-Drain-Velocity-Berechnung implementieren (Trend-Analyse aus `ChannelSnapshot`)
- [ ] ML-Shadow-Empfehlungen für Auto-Fee generieren (nur loggen, nicht ausführen, `ai_mode='shadow'`)
- [ ] Erweiterter Parameter-Scope: `base_fee`, `min_htlc`, `max_htlc`, `inbound_fee` in Shadow-Empfehlungen einbeziehen
- [ ] Jede Shadow-Empfehlung in `ChangeLog` mit `actor=ml:autofee_shadow:v1` protokollieren

#### 4-F: ML Shadow Mode – Rebalancing
- [ ] `jobs/ml_predictor.py` anlegen (nur lesend, kein `LightningWriteAdapter`-Import, R-AI-1)
- [ ] Kanalpar-Lernhistorie aus `RebalanceMLRecord` auswerten; zeitbasierte Features (Stunde, Wochentag) einbeziehen
- [ ] Shadow-Empfehlungen für Rebalancing-Queue generieren (parallel zur Heuristik, nur loggen)
- [ ] Lern-Fortschritt-Anzeige in UI: „X Kanalpaare analysiert, Y Muster gelernt"

#### 4-G: Rebalance-Budget & Queue
- [ ] Budget-Konfiguration: max. Sats/Tag oder max. ppm-Kosten pro Zeitraum
- [ ] Rebalance-Queue mit Prioritätsscore (Formel aus Abschnitt 6.3a): `P(Erfolg)`, `E(Revenue-Verbesserung)`, `geschätzte Kosten`, `Dringlichkeit`
- [ ] Dynamische Zielquoten: Liquiditätsbedarf-Analyse, konfigurierbarer Puffer, Routing-Verhaltens-Adaption; manuelle Override pro Kanal
- [ ] Erfolgsmessung: Outbound-Flüsse 7d vorher vs. 7d nachher

#### 4-H: Audit-Log UI & Rollback
- [ ] Vollständiger Änderungsverlauf als Timeline im UI (wer/was/warum/Ergebnis)
- [ ] Rollback-Vorschau: `GET /api/v2/changelog/{id}/rollback`
- [ ] Rollback-Ausführung: `POST /api/v2/changelog/{id}/rollback` (nur Expert-Modus, automatisches Backup vorher)
- [ ] API-Endpunkte `GET /api/v2/changelog` anlegen (rate-limiting, CSRF, authentication)

---

### Phase 5 – Externe Integrationen & Erweiterte Features

#### 5-A: mempool.space Integration
- [x] Async HTTP-Client für `GET https://mempool.space/api/v1/fees/recommended` einrichten (TTL-Cache 5–10 Min, exponential backoff bei 429)
- [x] Kostenampel (🟢/🟡/🔴) bei allen Open/Close/Splice-Empfehlungen anzeigen
- [x] „Wartefenster"-Vorschlag in UI (nie blockierend); keine Channel- oder Node-Daten an externe API senden
- [x] Notifier-Job: Notification wenn mempool günstig (gutes Zeitfenster für On-Chain-Aktionen)

#### 5-B: Amboss Integration
- [x] Optionalen API-Key (User-Settings) für Amboss GraphQL-API einrichten
- [x] Abfrage **nur** für bereits vorhandene oder aktiv evaluierte Peers (kein Overfetch)
- [x] Peer-Cards um Netzwerk-Einordnung erweitern; Hinweis auf nicht-kommerzielle Nutzungsbedingungen im UI
- [x] Kein externer Call ohne explizite Nutzereinwilligung (R-SEC-4)

#### 5-C: Onboarding-Wizard
- [x] 5-Schritte-Wizard implementieren: Node-Profil wählen, Channels verstehen, Fees erklären, Rebalancing erklären, erste sichere Optimierung
- [x] LND-Variante: Macaroon-Pfad, gRPC-Adresse; CLN-Variante: Rune/Token, clnrest-Endpunkt, Plugin-Status
- [x] Fortschritt in `UserMode.onboarding_step` speichern; Wizard jederzeit überspringbar und wiederholbar
- [ ] Sprachauswahl als erster Schritt im Wizard

#### 5-D: Missions & Glossar (Learning Center)
- [ ] Missions-System: Kurze Lernaufgaben (z. B. „Balance herstellen", „Fee-Strategie verstehen")
- [ ] Glossar mit Kontext-Tooltips; „Mehr erfahren"-Links
- [ ] CLN-spezifische Erklärungen für alle Capabilities und Plugin-abhängige Features
- [ ] Alle Strings in Missions/Glossar mit `{% trans "..." %}` markiert; DE + EN Übersetzungen

---

### Phase 6 – ML-Infrastruktur & SPA-Konsolidierung

#### 6-A: ML-Infrastruktur & Feature-Engineering
- [x] `jobs/ml_trainer.py` anlegen: Batch-Retraining täglich (konfigurierbar); auf ressourcenschwachen Nodes deaktivierbar oder nur manuell auslösbar
- [x] Feature-Engineering aus `ChannelSnapshot`, `RebalanceMLRecord`, `AutoFeeMLRecord`: Rolling Windows 1d/7d/30d, Balance-Drift-Rate, Peer-Stabilität, Fee-Elastizität
- [x] Modell-Persistenz als `.joblib`-Datei unter `models/rebalance_v{timestamp}.joblib` (scikit-learn, lokal, privacy-safe)
- [x] API: `POST /api/v2/ml/rebalance/train` (manuelles Retraining); `GET /api/v2/ml/status` (Konfidenz, Datenmenge, letztes Training)

#### 6-B: ML Shadow Mode – Rebalancing Vollbetrieb
- [x] ML-Empfehlungen parallel zur Heuristik in `Recommendation`-Tabelle speichern mit `confidence_label='ml_shadow'`
- [x] Shadow-Mode-Protokoll: Empfehlung vs. tatsächlichem Ergebnis kontinuierlich vergleichen
- [x] Mindestdatenmenge (30 Tage, R-AI-3) und Konfidenz-Schwelle prüfen bevor ML Empfehlungen ausgibt
- [x] UI-Toggle pro Kanal: ML-Nutzung aktivier-/deaktivierbar (R-P8-Entscheidung)

#### 6-C: ML Shadow Mode – Auto-Fee Vollbetrieb
- [ ] ML-gesteuerte Gebührenanpassungsvorschläge für alle Fee-Parameter (fee_rate, base_fee, min/max_htlc, inbound_fee) generieren
- [ ] Eskalations-/Deeskalations-Logik implementieren (konfigurierbare Faktoren und Grenzen)
- [ ] Dynamische Zielanpassung basierend auf Routing-Verhalten; Änderungen im Netzwerk-Umfeld einbeziehen
- [x] UI: `GET /api/v2/ml/autofee/suggestions`, `GET /api/v2/ml/autofee/history`

#### 6-D: ML Vollautomation (opt-in, Expert-Mode)
- [x] `ai_mode='policy_bound'` freischalten (nur Expert-Modus, nur nach ≥ 30 Tagen Shadow-Mode-Daten, R-AI-2/R-AI-3)
- [x] Human-Confirmation-Layer für policy_bound: UI-Bestätigung vor jeder ML-getriggerten Ausführung
- [x] Hard Caps, Cooldown-Guard, vollständiger Audit-Trail für alle automatischen Aktionen
- [x] Jede ML-getriggerte Änderung im ChangeLog mit `actor=ml:<model>:<version>` (R-AI-4)

#### 6-E: Eskalations-/Deeskalations-Tuning UI
- [x] Konfigurierbare Eskalationsfaktoren und Grenzwerte pro Kanal oder global im UI einstellbar
- [x] Cooldown-Konfiguration zwischen Anpassungen desselben Parameters
- [x] Anzeige: letzter ML-Eingriff, aktueller Konfidenzwert, Eskalationsstufe im Channel-Detail

#### 6-F: SPA als Hauptprodukt & PWA
- [x] SPA-Phase-2-Rollout: Startseite → SPA (`/cockpit`); Standard-Navigation → SPA; alte Seiten als Expert-Mode / Deep-Link
- [ ] Service Worker, Web App Manifest, Offline-Fallback (PWA-Grundfunktionen)
- [ ] SSE-Endpunkt für Live-Updates (Rebalance-Status, HTLC-Stream) als Alternative zu Polling

---

### Phase 7 – Multi-Asset-Vorbereitung (Optional)

> **Hinweis:** Diese Phase ist bewusst zurückgestellt bis Multi-Asset auf Lightning produktionsreif ist. Die Adapter-Architektur aus den vorherigen Phasen ermöglicht Integration ohne Rewrite.

#### 7-A: Asset-Attribut im Datenmodell
- [ ] `AssetContext`-Dataclass in allen Domänenmodellen aktivieren (`ForwardingEvent`, `FeePolicy`, `LiquidityState`)
- [ ] DB-Migrationen für Asset-Felder in betroffenen Models (default: `btc`)
- [ ] API-Antworten um `asset`-Kontext erweitern

#### 7-B: Unit-flexible UI
- [ ] Alle hardcodierten „sats"-Strings durch `{denomination}`-Platzhalter ersetzen
- [ ] Zentrale Hilfsfunktion für Betragsdarstellung einführen (R-I18N-4)
- [ ] Charts und Erklärungen auf `denomination`-Platzhalter umstellen

#### 7-C: Multi-Asset-UI
- [ ] Asset-Bereich in Advanced/Expert-Mode anzeigen wenn `can_multi_asset` aktiv
- [ ] Multi-Node-Backend-Switcher im UI-Header implementieren
- [ ] Aggregierte Übersicht aller Nodes (separate Settings und Policies pro Node)

---

> **Tracking-Hinweis:** Abgehakte Aufgaben (`- [x]`) kennzeichnen abgeschlossene Implementierungen. Eine Phase gilt als abgeschlossen, wenn alle Aufgaben dieser Phase abgehakt sind. Neue Erkenntnisse während der Implementierung können zusätzliche Aufgaben in eine Phase einbringen – diese werden direkt in der jeweiligen Phase ergänzt.
