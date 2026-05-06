# LNDg Next – Umfassendes Refactoring-Konzept

> **Version:** 1.2 · **Status:** Konzept / Entwurf  
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
17. [Multi-Backend & Multi-Asset Architektur (CLN- & Zukunftsfähigkeit)](#17-multi-backend--multi-asset-architektur-cln---zukunftsfähigkeit)

---

## 1. Leitbild & Ziele (Product North Star)

### Zielgruppe

Neue Routing-Node-Betreiber, die:

1. **Verstehen** wollen, was passiert
2. **Lernen** wollen, warum etwas funktioniert
3. Später **automatisieren** – aber sicher

Sekundäre Zielgruppe: erfahrene Betreiber, die maximale Kontrolle bei geringem kognitiven Aufwand wünschen.

### Strategische Vision

> **LNDg Next soll heute LND perfekt bedienen, aber so refactored werden, dass morgen weder CLN noch Multi-Asset-Lightning eine Neuentwicklung erzwingen.**

LNDg entwickelt sich von einem „LND-Tool" zu einem **Lightning Node Intelligence Layer** – einer implementierungsneutralen Plattform, die jedes Lightning-Backend versteht, erklärt und optimiert.

### Produktziele (messbar / implementierbar)

| Ziel | Messkriterium | Mechanismus im Produkt |
|---|---|---|
| **Time-to-First-Understanding** | Einsteiger kann Inbound/Outbound, Fees, Rebalancing, Peer-Wahl erklären | Onboarding-Wizard + Glossar-Tooltips |
| **Time-to-First-Improvement** | UI zeigt klare „Nächste beste Aktion" mit Simulation | Recommendation Engine + Dry-Run |
| **Safety First** | Automationen standardmäßig Dry-Run, rate-limitiert, mit Rollback | Policy-Engine + Audit-Log |
| **Wachstumspfad** | Feature-Freischaltung durch Modus-Aufstieg | Progressive Disclosure (Guided → Advanced → Expert) |

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

Diese Struktur ersetzt die „gewachsene" Seitenliste (Advanced/Stats/Performance verteilt über viele URLs), **ohne** existierende Views zu entfernen: Alle alten Views bleiben als **„Legacy / Expert"** erreichbar (über dediziertes Menü oder direkten URL-Aufruf).

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
| **B – Resize / Splice** | Kapazität vergrößern oder verkleinern |
| **C – Close / Deprioritize** | Stagnation, Risiko, Opportunitätskosten |
| **D – Rebalance** | Gezielt + kostensensitiv |
| **E – Fee Strategy** | Manuell, semi-auto oder auto |

### 5.2 Heuristiken (Phase 1 – sofort nutzbar)

Alle Signale basieren auf bereits vorhandenen LNDg-Daten:

| Signal | Datenquelle (aktuell) | Empfehlung |
|---|---|---|
| Stagnation: wenig/keine Outbound-Flüsse über Zeitfenster | `Forwards`, `Channels.total_sent` | Fee senken oder Peer kritisch prüfen |
| Einseitige Balance: Inbound ≫ Outbound | `Channels.local_balance` / `remote_balance` | Rebalance oder Fee-Signaling |
| Hohe failed HTLC-Rate | `FailedHTLCs` | Routing-Richtung deaktivieren, Peer prüfen |
| Peer-Konzentration: viele Channels zu ähnlichen Peers | `Channels.remote_pubkey` | Diversifikation empfehlen |
| Ungenutzte Kapazität + geringe Flüsse | `Channels.capacity`, `Forwards` | Reduce/Close erwägen |
| Hoher stabiler Outbound-Flow + Liquidität knapp | `Forwards`, `local_balance` | Kapazitätserweiterung erwägen |

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

> **Hinweis:** Die Backend-Schicht wird so strukturiert, dass LND als erste Implementierung eines abstrakten `LightningBackend`-Adapters gilt. Die vollständige Adapter-Architektur inkl. CLN-Vorbereitung ist in [Abschnitt 17](#17-multi-backend--multi-asset-architektur-cln---zukunftsfähigkeit) beschrieben.

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

**Wichtig:** Keine Views werden entfernt. Sie werden als „Expert / Legacy" gekennzeichnet.

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
- [ ] **UserMode-Model:** Modus-Einstellung persistieren
- [ ] **Build-Optimierung:** Multi-Stage Dockerfile, CI-Caching, Makefile
- [ ] **Adapter-Grundstruktur:** Abstraktes `LightningBackend`-Interface anlegen; LND-Logik in `LndBackend` kapseln (keine UI/Business-Logik ändert sich – nur Strukturierung; siehe Abschnitt 17)
- [ ] **Domänenmodell-Basis:** Abstrakte Modelle `Channel`, `Peer`, `ForwardingEvent`, `FeePolicy` einführen (BTC-only, aber asset-agnostisch modelliert)

### Phase 2: Daten & Visualisierung

- [ ] **Zeitreihen-Models:** `ChannelSnapshot`, `ForwardingAggregate`, `ChangeLog`
- [ ] **Collector/Aggregator-Jobs:** Regelmäßige Snapshots
- [ ] **Neue Charts:** Liquidity Donut, Fee vs. Volume Scatter, Channel Health Heatmap
- [ ] **Backup/Restore-Funktion:** UI + Backend + automatisches Backup
- [ ] **DB-Bereinigung:** Konfigurierbare Aufbewahrungsregeln + UI
- [ ] **Capability-Registry:** Backend registriert seine Fähigkeiten; UI wertet Capabilities aus statt Backend-Typ zu prüfen

### Phase 3: Empfehlungs-Engine

- [ ] **Heuristik-Engine:** Top-3-Aktionen pro Node-Zustand
- [ ] **Recommendation-Model:** Empfehlungen speichern, Status tracken
- [ ] **Dry-Run-Framework:** Jede Empfehlung simulierbar
- [ ] **Explainability-UI:** „Warum?"-Panels für alle Empfehlungen

### Phase 4: Policy-Engine & Automationen

- [ ] **Policy-Engine:** `Policy`, `PolicyRun`-Models, Executor-Job
- [ ] **Auto-Fee-Templates:** Conservative/Balanced/Revenue-Seeking UI
- [ ] **ML-Auto-Fee Shadow-Mode:** Balance-Drain-Velocity-Erkennung, proaktive Gebührenanpassung, erweiterter Parameter-Scope (base_fee, min/max_htlc, inbound_fee)
- [ ] **ML-Rebalancing Shadow-Mode:** Kanalpar-Lernhistorie (`RebalanceMLRecord`), zeitbasierte Features, Erfolgswahrscheinlichkeits-Modell
- [ ] **Rebalance-Budget:** Budget-Konfiguration, Queue mit ML-Priorisierung, Erfolgsmessung
- [ ] **Dynamische Rebalancing-Zielquoten:** Liquiditätsbedarf-Analyse, konfigurierbarer Puffer, Routing-Verhaltens-Adaption
- [ ] **Audit-Log-UI:** Vollständiger Änderungsverlauf mit Rollback
- [ ] **Policy-Domänenentkopplung:** Policy-Definitionen auf Domänenebene; Executor-Adapter übersetzt Policy → konkrete LND-Aktion (CLN-Vorbereitung)

### Phase 5: Externe Integrationen & Erweiterte Features

- [ ] **mempool.space-Integration:** Fee-Ampel bei Open/Close-Empfehlungen
- [ ] **Amboss-Integration:** Optionale Peer-Kontextdaten
- [ ] **Onboarding-Wizard:** Vollständiger 5-Schritte-Wizard
- [ ] **Missions/Glossar:** Learning Center

### Phase 6: ML Shadow Mode & SPA-Konsolidierung

- [ ] **ML-Infrastruktur:** Feature-Engineering, Modell-Training-Pipeline
- [ ] **Shadow Mode (Rebalancing):** ML-Empfehlungen parallel zu Heuristik, nur loggen → Konfidenz aufbauen
- [ ] **Shadow Mode (Auto-Fee):** ML-gesteuerte Gebührenanpassungen erst vorschlagen, dann schrittweise automatisieren
- [ ] **ML-Vollautomation (opt-in, Expert-Mode):** Rebalancing und Auto-Fee vollständig ML-gesteuert, mit definierten Grenzen und Audit-Log
- [ ] **Eskalations-/Deeskalations-Tuning:** Konfigurierbare Faktoren und Grenzen über UI
- [ ] **SPA als Haupt-Produkt:** Phase 2 des Roll-outs
- [ ] **PWA-Vorbereitung:** Service Worker, Manifest, Offline-Fallback

### Phase 7: CLN-Adapter & Multi-Asset-Vorbereitung

- [ ] **CLN-Adapter:** `ClnBackend` als zweite `LightningBackend`-Implementierung (JSON-RPC / Plugin-API)
- [ ] **Capability-UI vollständig:** Features werden angezeigt/ausgegraut basierend auf Backend-Capabilities, nicht auf Backend-Typ
- [ ] **Multi-Node-Backend-Switcher:** UI-Switcher zwischen mehreren Backend-Instanzen
- [ ] **Asset-Attribut im Datenmodell aktivieren:** `asset_id` / `asset_group` / `denomination` in Flow- und Fee-Modellen sichtbar machen
- [ ] **Unit-flexible UI:** Beträge, Charts, Erklärungen arbeiten mit `denomination`-Platzhaltern statt hardcodierten „sats"
- [ ] **CLN-Onboarding-Erweiterung:** Guided-Mode erkennt CLN-Capabilities und passt Wizard-Inhalte an

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

Die folgenden Punkte müssen vor Beginn der Umsetzung entschieden werden:

### Architektur & Technologie

| # | Frage | Optionen | Implikation |
|---|---|---|---|
| A1 | Welches Frontend-Framework? | React + Vite **vs.** HTMX + Alpine.js **vs.** Vue.js | Beeinflusst Entwicklungsaufwand, benötigte Skills, mobile Tauglichkeit |
| A2 | SPA unter `/app/*` oder komplette URL-Migration? | Parallel `/app/*` **vs.** Migration bestehender URLs | Risiko für bestehende Nutzer, Bookmarks, externe Verlinkungen |
| A3 | WebSocket für Live-Updates? | Django Channels (Redis) **vs.** SSE **vs.** Polling beibehalten | Redis-Abhängigkeit; Komplexität im Deployment |
| A4 | Datenbank: SQLite behalten oder PostgreSQL als Standard? | SQLite (einfach, single-file) **vs.** PostgreSQL (besser für Zeitreihen, Concurrent Writes) | Beeinflusst Backup-Strategie, Performance bei Snapshots |
| A5 | ML-Bibliothek: scikit-learn (leicht, kein Overhead) vs. externe ML-API? | scikit-learn lokal **vs.** External ML API | Privacy (keine Daten extern), Ressourcenverbrauch auf kleinen Nodes (RPi) |
| A6 | ML-Modell-Persistenz: Wie werden trainierte Modelle gespeichert und versioniert? | SQLite-BLOB **vs.** Dateisystem (`.joblib`/`.pkl`) **vs.** MLflow | Reproduzierbarkeit, Rollback bei schlechtem Modell |
| A7 | ML-Training: Online-Learning (inkrementell) vs. periodisches Batch-Retraining? | Online (z. B. stündlich) **vs.** Batch (täglich/wöchentlich) | Ressourcenverbrauch vs. Aktualität der Modelle; Stabilität |

### Produkt & UX

| # | Frage | Optionen | Implikation |
|---|---|---|---|
| P1 | Wie werden Betriebsmodi freigeschaltet? | Manuell durch Nutzer **vs.** automatisch nach X Tagen/Aktionen | Engagement vs. Nutzerkontrolle |
| P2 | Soll der Modus (Guided/Advanced/Expert) passwortgeschützt sein? | Ja (verhindert versehentliches Hochstufen) **vs.** Nein | Sicherheit vs. Reibung |
| P3 | Welche Sprachen zum Launch? | Nur DE+EN **vs.** DE+EN+weitere | Übersetzungsaufwand; Community-Resourcen |
| P4 | Sollen Empfehlungen Community-geteilt werden können? | Ja (opt-in) **vs.** Nein (privat) | Privacy-Implikationen; Mehrwert für Community |
| P5 | Wie detailliert soll der Onboarding-Wizard sein? | Minimal (3 Schritte) **vs.** Vollständig (5+ Schritte) | Abbruchrate vs. Lerneffekt |
| P6 | Ab wann darf ML-Rebalancing vollautomatisch ausführen? | Nur Expert-Mode nach N Tagen Shadow-Mode **vs.** Opt-in ab Advanced | Risiko vs. Nutzbarkeit; Vertrauen ins Modell |
| P7 | Wie soll der Übergang von regelbasiert zu ML-gesteuert kommuniziert werden? | Explizites UI-Toggle (Modus: Regelbasiert / ML) **vs.** gradueller Übergang | Nutzerkontrolle vs. Komplexität; Vertrauen |
| P8 | Welche Kanäle sollen vom ML-Auto-Fee ausgeschlossen werden können? | Einzelne Kanäle (Whitelist/Blacklist) **vs.** nur global | Granularität vs. Konfigurationsaufwand |

### Datenschutz & Sicherheit

| # | Frage | Optionen | Implikation |
|---|---|---|---|
| S1 | Welche Daten werden an externe APIs (Amboss, mempool) gesendet? | Nur Pubkeys **vs.** Channel-IDs **vs.** Nichts ohne explizite Einwilligung | Privacy-Policy notwendig; Default muss sicher sein |
| S2 | Soll es eine anonyme Nutzungsstatistik geben? | Opt-in Telemetrie **vs.** Keine | Verbesserung des Produkts vs. Privacy |
| S3 | Wie werden Backup-Dateien verschlüsselt? | AES-256 + Passwort **vs.** Unverschlüsselt **vs.** GPG | Einfachheit vs. Sicherheit |
| S4 | Rollback: Wie weit zurück? | Letzte 1 Änderung **vs.** Letzten 7 Tage **vs.** Unbegrenzt | Speicherbedarf vs. Flexibilität |

### Betrieb & Deployment

| # | Frage | Optionen | Implikation |
|---|---|---|---|
| B1 | Soll Redis als Pflicht-Dependency eingeführt werden? | Ja (WebSocket, Caching) **vs.** Optional **vs.** Nein | Deployment-Komplexität auf kleinen Nodes |
| B2 | Wie soll der Snapshot-Job skaliert werden? (RPi-Limit) | 15-Min-Intervall **vs.** 1h-Intervall **vs.** konfigurierbar | DB-Wachstum vs. Chart-Granularität |
| B3 | Automatisches Backup: lokal vs. remote? | Nur lokal (Standard) **vs.** Optional SFTP/S3 | Sicherheit vs. Konfigurationsaufwand |
| B4 | Soll es ein offizielles Helm-Chart/Umbrel-Update geben? | Ja (Priorität) **vs.** Community-Beitrag **vs.** Später | Adoptions-Reichweite; Maintenance-Aufwand |
| B5 | Minimale Hardware-Anforderung für ML-Features? | Raspberry Pi 4 (4 GB RAM) **vs.** Nur auf leistungsfähiger Hardware | Kompatibilität vs. Feature-Reichhaltigkeit |
| B6 | ML-Training-Frequenz auf ressourcenschwachen Nodes? | Nächtliches Batch-Training **vs.** Nur manuell auslösbar **vs.** Deaktivierbar | Aktualität der Modelle vs. CPU/RAM-Belastung auf RPi |
| B7 | Mindestdatenmenge für ML-Rebalancing-Modell? | 30 Tage / mind. 50 Rebalance-Events **vs.** 14 Tage / 20 Events | Modellqualität vs. Time-to-Value für neue Nutzer |
| B8 | Wie werden ML-Modelle bei Upgrade auf neue LNDg-Version migriert? | Modelle verwerfen + neu trainieren **vs.** Migrations-Skript | Einfachheit vs. Datenverlust beim Upgrade |

---

## 17. Multi-Backend & Multi-Asset Architektur (CLN- & Zukunftsfähigkeit)

> **Leitgedanke:** LNDg Next soll heute LND perfekt bedienen, aber so refactored werden, dass morgen weder CLN noch Multi-Asset-Lightning eine Neuentwicklung erzwingen.

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

**Konsequenz:** LND wird zu einer _Implementierung_ eines „Lightning-Adapters". CLN kann später ein zweiter Adapter sein – ohne UI-Rewrite.

---

### 17.2 Adapter-Pattern für Node-Backends

#### Empfohlene Struktur

```
LightningBackend (Interface / abstrakte Klasse)
├── LndBackend          ← Implementierung heute
└── ClnBackend          ← Implementierung später (future)
```

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
```

Der Adapter kapselt:
- RPC / gRPC / JSON-RPC Unterschiede
- Naming-Unterschiede (z. B. `chan_id` vs. `short_channel_id`)
- Event-Formate (z. B. HTLC-Events in LND vs. CLN-Plugin-Hooks)
- Capability-Flags (z. B. `supports_splicing`, `supports_multi_asset`)

#### Warum das für CLN entscheidend ist

Core Lightning (CLN):
- ist stark plugin-basiert – viele Features kommen aus Plugins, nicht aus dem Core
- liefert viele Daten anders strukturiert (JSON-RPC statt gRPC)
- erweitert sich häufig außerhalb des Core (Plugins: `clnrest`, `cln-grpc`, `rebalance`, etc.)

> Ohne Adapter-Schicht wäre CLN-Support später ein Refactoring-Albtraum.

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
    can_multi_asset: bool        # Multi-Asset-Kanäle (Taproot Assets)
    can_splice: bool             # Channel-Splice (Resize ohne Close)
    can_inbound_fees: bool       # Inbound-Fee-Parameter unterstützt
    can_keysend: bool            # Spontane Payments (Keysend)
    supports_plugins: bool       # Plugin-Erweiterungs-Mechanismus vorhanden
```

#### UI-Verhalten

| Capability | UI-Reaktion wenn `False` |
|---|---|
| `can_auto_fee` | Button ausgegraut + Tooltip „Nicht vom Backend unterstützt" |
| `can_splice` | Resize-Option ausgeblendet in Advanced, Hinweis in Expert |
| `supports_plugins` | CLN-Plugin-Status anzeigen (z. B. „rebalance-Plugin fehlt") |
| `can_multi_asset` | Asset-Bereich nur in Expert-Mode sichtbar |

**Vorteil für CLN:** CLN-Setups unterscheiden sich stark je nach installierten Plugins. Die UI kann Funktionen anzeigen/ausgrauen und erklären, welches Plugin fehlt – ohne harte LND-Feature-Parity vorauszusetzen.

---

### 17.4 Asset-agnostisches Datenmodell

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

**Warum jetzt?**

- Taproot Assets (ex-TARO) nutzen bestehende Lightning-Kanäle – kein separates Netzwerk
- Stablecoins auf Lightning werden kein „separate Channels"-System sein, sondern Routing auf bestehender Infrastruktur
- Ein späteres „DB-Rewrite" wäre extrem teuer – wenn das Datenmodell heute richtig ist, bleibt das UI morgen stabil

**BTC bleibt Default:** Das `asset`-Attribut ist standardmäßig auf `btc` gesetzt. Multi-Asset erscheint nur in Advanced/Expert-Mode und nur wenn `can_multi_asset` aktiv ist.

---

### 17.5 Implementierungsneutrale Policies

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

### 17.6 UX-Strategie: Bereits jetzt „CLN-fähig" denken

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
   Der Guided-Wizard fragt nicht „Hast du LND?", sondern erkennt automatisch via Capability-Check, welche Features verfügbar sind, und passt die Erklärungen an.

#### Strategischer Effekt

Viele Betreiber nutzen CLN nicht, weil moderne GUIs fehlen und die Lernbarrieren hoch sind.

LNDg Next kann genau hier eine Marktlücke schließen:
- CLN ist technisch stark, aber bisher UI-schwach
- LNDg Next bietet: Lernen + Visualisierung + erklärtes Routing – für beide Welten

---

### 17.7 Refactoring-Checkliste (kompakt)

| Punkt | Beschreibung | Phase |
|---|---|---|
| ✅ Abstraktes Domänenmodell | `Channel`, `Peer`, `ForwardingEvent`, `FeePolicy` etc. backend-neutral | Phase 1 |
| ✅ Backend-Adapter-Schicht | `LightningBackend` Interface + `LndBackend` Implementierung | Phase 1 |
| ✅ Capability-basierte UI | Kein `if backend == "LND"` in Templates/Views | Phase 2 |
| ✅ Asset-agnostisches Datenmodell | `asset_id` / `denomination` in Liquiditäts- und Flow-Modellen | Phase 1–2 |
| ✅ Implementierungsneutrale Policies | Policy-Objekte auf Domänenebene; Executor delegiert an Adapter | Phase 4 |
| ✅ UX ohne implizite LND-Annahmen | Generische Lightning-Begriffe; flexible Units; Capability-Checks | Phase 1+ |
| 🔮 CLN-Adapter | `ClnBackend` Implementierung (JSON-RPC + Plugin-API) | Phase 7 |
| 🔮 Multi-Asset-UI | Asset-Bereich in Advanced/Expert wenn `can_multi_asset` aktiv | Phase 7+ |

**Was dadurch möglich wird:**

- CLN-Support ohne Architekturbruch
- Stablecoins & Taproot Assets ohne DB-Rewrite
- Einsteiger-freundliche GUI für LND und CLN
- LNDg entwickelt sich vom „LND-Tool" zum **Lightning Node Intelligence Layer**

---

## Anhang: Abhängigkeiten bestehender LNDg-Komponenten

### Aktuell vorhandene Jobs (jobs.py)

Die bestehenden Jobs werden in Phase 1 nicht verändert, aber in Phase 2 schrittweise in die neue Service-Architektur überführt:

- Forwarding-Collector → `collector.py`
- Auto-Fee-Logik (`af.py`) → bleibt vorerst eigenständig, wird in Phase 4 in Policy-Engine integriert
- Rebalancer (`rebalancer.py`) → bleibt eigenständig, Policy-Engine wrappt ihn
- HTLC-Stream (`htlc_stream.py`) → wird als Input für `FailedHTLCs` beibehalten

### Bestehende API-Endpunkte

Alle bestehenden `/api/`-Endpunkte bleiben unverändert. Die neuen `/api/v2/`-Endpunkte ergänzen sie. Erst in Phase 3+ werden alte Endpunkte als „deprecated" markiert (mit Übergangsfrist von mindestens 6 Monaten).

---

*Dieses Dokument ist ein lebendes Konzept. Änderungen und Ergänzungen sind erwünscht. Bitte offene Punkte aus Abschnitt 16 vor Beginn der jeweiligen Implementierungsphase klären.*
