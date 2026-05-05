# LNDg – Ideensammlung für zukünftige Features

Dieses Dokument sammelt Feature-Ideen und Erweiterungsvorschläge für LNDg, die noch nicht implementiert wurden.
Jeder Eintrag enthält eine kurze Beschreibung, den Mehrwert, technische Hinweise sowie bekannte Risiken und offene Fragen.

---

## Ideen-Vorlage

```
### [Titel der Idee]
**Priorität:** hoch / mittel / niedrig
**Aufwand:** gering / mittel / groß

**Beschreibung:**
...

**Mehrwert:**
...

**Technische Hinweise:**
...

**Risiken / Offene Fragen:**
...
```

---

## Ideen

### 1. Automatisierte Gewinnausschüttung auf eine Lightning-Adresse

**Priorität:** mittel  
**Aufwand:** mittel

**Beschreibung:**  
Zu einem konfigurierbaren Stichtag (z. B. alle 30 Tage, erster Montag im Monat, bestimmte Monatstage wie 01.01., 02.01., 03.01. …) prüft LNDg automatisch, ob die letzten 30 **und** 90 Tage im Gewinn waren. Wenn beide Bedingungen erfüllt sind, wird der Nettogewinn der letzten 30 Tage an eine konfigurierbare Lightning-Adresse gesendet.

**Mehrwert:**  
- Automatisches „Abschöpfen" akkumulierter Routing-Gewinne ohne manuellen Eingriff.  
- Schützt Betreiber davor, Gewinne im Node zu belassen und so Klumpenrisiko zu erhöhen.  
- Unterstützt regelbasiertes Liquiditätsmanagement (kein Ausschütten bei negativen Perioden).

**Konfigurierbare Parameter (über `LocalSettings`):**

| Schlüssel | Beispielwert | Bedeutung |
|---|---|---|
| `AP-Enabled` | `1` | Funktion aktiviert (0 = aus) |
| `AP-LnAddress` | `user@wallet.de` | Ziel-Lightning-Adresse (LNURL-pay) |
| `AP-Schedule` | `interval:30` / `weekday:0` / `monthday:1` | Ausschüttungszeitplan |
| `AP-MinProfit30d` | `1000` | Mindest-Nettogewinn letzte 30 Tage (Sats) |
| `AP-MinProfit90d` | `1` | Mindest-Nettogewinn letzte 90 Tage (Sats; 0 = ignorieren) |
| `AP-MaxFeePpm` | `100` | Max. Routing-Gebühr für die Ausschüttungszahlung (ppm) |
| `AP-LastPayout` | `2025-04-01T12:00:00` | Timestamp der letzten erfolgreichen Ausschüttung |
| `AP-DryRun` | `1` | Simulationsmodus (kein echtes Senden) |

**Technische Hinweise:**  
- Gewinnberechnung bereits vorhanden (30d/90d in `gui/views.py` income-View):  
  `profit = routing_revenue − rebalancing_fees − onchain_fees − closing_costs`  
- Hintergrundjob in `jobs.py` läuft alle 20 Sekunden und kann Scheduling-Logik tragen.  
- Lightning-Adressen (z. B. `user@domain.com`) müssen über **LNURL-pay** aufgelöst werden:  
  1. `GET https://domain.com/.well-known/lnurlp/user` → Callback-URL  
  2. `GET <callback>?amount=<msats>` → BOLT11-Invoice  
  3. `SendPaymentSync(invoice)` via LND-gRPC  
- `requests`-Paket ist bereits in `requirements.txt` vorhanden.  
- Idempotenz-Guard: `AP-LastPayout` **vor** dem Senden schreiben, um Doppelzahlungen bei Neustart zu vermeiden.

**Scheduling-Logik (Pseudocode):**
```python
if schedule == "interval:N":
    due = (now - last_payout) >= timedelta(days=N)
elif schedule == "weekday:D":
    due = (now.weekday() == D) and (now.date() != last_payout.date())
elif schedule == "monthday:D":
    due = (now.day == D) and not same_month(now, last_payout)
```

**Risiken / Offene Fragen:**

| Risiko | Schwere | Mitigation |
|---|---|---|
| Doppel-Zahlung bei Neustart | 🔴 hoch | `AP-LastPayout` vor dem Senden setzen |
| Stiller Zahlungsfehler (`payment_error != ""`) | 🔴 hoch | Ergebnis explizit prüfen; `AP-LastPayout` nur bei Erfolg schreiben |
| Falsche Gewinnberechnung (schwebende Rebalances) | 🟡 mittel | Nie >80 % des berechneten Gewinns ausschütten |
| Kompromittierter LNURL-Server liefert fremde Invoice | 🟡 mittel | Empfänger-Pubkey in der Invoice verifizieren |
| Unzureichende Outbound-Liquidität | 🟡 mittel | Vor dem Senden `ChannelBalance` prüfen |
| Falsch eingegebene Lightning-Adresse | 🟡 mittel | Eingabevalidierung + Bestätigungsschritt im UI |
| Steuerliche Relevanz der Transaktion | 🟢 niedrig | Payout-History im UI dokumentieren (Datum, Betrag, Status) |
| Privacy (regelmäßige Zahlungen an dieselbe Adresse) | 🟢 niedrig | Hinweis in der Doku; optional rotierende Adressen |
| LNURL-HTTP schlägt auf Tor-only-Instanzen fehl | 🟢 niedrig | Fallback: direkte Pubkey-Zahlung via Keysend |

**Empfohlene Umsetzungsreihenfolge:**  
1. `resolve_lightning_address(lnaddr) → bolt11` Hilfsfunktion  
2. `profit_payout(stub)` in `jobs.py` mit DryRun-Unterstützung  
3. Settings-UI für alle `AP-*`-Schlüssel  
4. Payout-History-Tabelle im UI  
5. Warnbanner wenn Liquidität für nächste Ausschüttung nicht ausreicht

---

<!-- Weitere Ideen hier einfügen -->
