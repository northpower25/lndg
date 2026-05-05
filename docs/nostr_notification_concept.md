# Konzept: NOSTR-Benachrichtigungen in LNDg

> **Status:** Konzept / noch nicht implementiert  
> Dieses Dokument beschreibt, wie NOSTR-Benachrichtigungen in LNDg ergänzt werden sollen.  
> Die Telegram-Benachrichtigung ist bereits umgesetzt (siehe `notify.py`, `gui/models.py`).

---

## Ziel

Nutzer von LNDg sollen wichtige Ereignisse (Rebalance abgeschlossen, Channel inaktiv, Auto-Fee-Anpassung) wahlweise auch über das dezentrale **NOSTR**-Protokoll erhalten können – ohne Abhängigkeit von einem zentralisierten Dienst wie Telegram.

---

## Protokoll-Grundlagen

NOSTR (Notes and Other Stuff Transmitted by Relays) ist ein offenes, dezentrales Messaging-Protokoll.

| Begriff | Bedeutung |
|---|---|
| **NIP-01** | Basisprotokoll: Ereignisformat, Signierung, Relay-Kommunikation |
| **Relay** | WebSocket-Server, der Ereignisse speichert und weiterleitet |
| **nsec / privkey** | 32-Byte-Secp256k1-Privatschlüssel (hex oder bech32 `nsec1…`) |
| **npub / pubkey** | Öffentlicher Schlüssel (x-only, hex oder bech32 `npub1…`) |
| **Kind 1** | Öffentliche Text-Notiz – das Format, das für LNDg-Nachrichten genutzt wird |
| **Kind 4** | Verschlüsselte Direktnachricht (NIP-04) – optionale Erweiterung |

---

## Ereignisformat (NIP-01)

Jede Nachricht wird als signiertes JSON-Objekt an alle konfigurierten Relays geschickt:

```json
{
  "id":         "<sha256 der serialisierten Felder>",
  "pubkey":     "<x-only public key (hex)>",
  "created_at": 1700000000,
  "kind":       1,
  "tags":       [],
  "content":    "⚠️ Channel inactive – Peer: Alice (123456789)",
  "sig":        "<Schnorr-Signatur (BIP-340, hex)>"
}
```

Das Event wird per WebSocket als `["EVENT", <event-object>]` an jeden Relay gesendet.

---

## Geplante Implementierung

### 1. Abhängigkeit

```
websocket-client   # WebSocket-Verbindung zu NOSTR-Relays
```

Die Bibliothek muss zu `requirements.txt` hinzugefügt werden.  
Schnorr-Signierung (BIP-340) kann in **reinem Python** implementiert werden – keine weiteren nativen Bibliotheken nötig.

### 2. Datenbankmodell (`gui/models.py`)

Dem bestehenden `NotificationSettings`-Singleton werden folgende Felder hinzugefügt:

```python
nostr_enabled  = models.BooleanField(default=False)
nostr_privkey  = models.CharField(max_length=64, blank=True, default='',
    help_text='32-Byte-Hex-Privatschlüssel für NOSTR-Signierung (NIP-01)')
nostr_relays   = models.TextField(blank=True,
    default='wss://relay.damus.io,wss://nos.lol',
    help_text='Kommagetrennte Liste von NOSTR-Relay-WebSocket-URLs')
```

Dazu eine neue Migration `0042_notificationsettings_nostr.py`.

### 3. Signier- und Publish-Logik (`notify.py`)

```python
# secp256k1-Kurvenparameter (P, N, G)

def _schnorr_sign(msg: bytes, privkey: bytes) -> bytes:
    """BIP-340-Schnorr-Signatur mit zufälligen Aux-Bytes."""
    ...

def _build_nostr_event(privkey_hex: str, content: str, kind: int = 1) -> dict:
    """Erstellt und signiert ein NIP-01-Event."""
    ...

def _publish_nostr_event(event: dict, relays: list, timeout: int = 8) -> dict:
    """Sendet das Event per WebSocket an alle Relays."""
    import websocket
    payload = json.dumps(["EVENT", event])
    for relay in relays:
        ws = websocket.create_connection(relay, timeout=timeout)
        ws.send(payload)
        ws.close()
    ...
```

In `send_notification()` wird der NOSTR-Zweig ergänzt:

```python
if cfg.nostr_enabled and cfg.nostr_privkey:
    relays = [r.strip() for r in cfg.nostr_relays.split(",") if r.strip()]
    event  = _build_nostr_event(cfg.nostr_privkey, message)
    result["nostr"] = _publish_nostr_event(event, relays)
```

### 4. Konfigurationsoberfläche (`notification_settings.html`)

Im bestehenden „Notification Settings"-Panel auf der Home-Seite werden ergänzt:

- **NOSTR On/Off** – Dropdown (`nostr_enabled`)
- **NOSTR Private Key** – Passwortfeld (`nostr_privkey`), `autocomplete="off"`, Wert wird **nie** im DOM gerendert; Checkbox zum Löschen des gespeicherten Schlüssels
- **NOSTR Relays** – Textfeld (`nostr_relays`), kommagetrennte `wss://`-URLs
- Anzeige des abgeleiteten öffentlichen Schlüssels (erste 16 Zeichen) via `GET /api/nostr_pubkey/`

### 5. Neue API-Endpunkte (`gui/views.py` + `gui/urls.py`)

| URL | Methode | Zweck |
|---|---|---|
| `/api/nostr_pubkey/` | GET | Gibt den x-only Public Key zurück, der aus dem gespeicherten Privatschlüssel abgeleitet wird |

Der `notification_settings`-View (POST) wird um die Verarbeitung von `nostr_enabled`, `nostr_privkey` und `nostr_relays` erweitert.

### 6. View-Logik (Sicherheit)

- `nostr_privkey` wird nur überschrieben, wenn das Feld **nicht leer** ist (kein versehentliches Löschen).
- Der Wert wird als 64-stelliger Hex-String validiert (`int(raw, 16)` + `len == 64`).
- Eine Checkbox `nostr_privkey_clear=1` ermöglicht das explizite Löschen.
- Der Privatschlüssel wird in API-Antworten **nicht** zurückgegeben.
- Stack-Traces werden in API-Fehlerantworten **nicht** exponiert (nur serverseitig geloggt).

---

## Sicherheitshinweise

| Aspekt | Maßnahme |
|---|---|
| Privatschlüssel im Browser | `type="password"`, `autocomplete="off"`, kein `value`-Attribut |
| Privatschlüssel in API | Wird nie an den Client zurückgesendet |
| Relay-URLs | Werden nur als `wss://`-Verbindungen verwendet; keine Validierung des Inhalts der Relay-Antworten nötig |
| Fehler in der Signierung | Ausnahmen werden gefangen und geloggt; kein Absturz des Hauptprozesses |
| `websocket-client` nicht installiert | Graceful degradation mit Warnung im Log; Telegram funktioniert weiterhin |

---

## Teststrategie

1. **Unit-Test Schnorr-Signierung:** Privat- und Pubkey erzeugen, Event bauen, Signatur gegen die BIP-340-Testvektoren prüfen.
2. **Integration mit lokalem Relay:** `nostr-rs-relay` oder `strfry` lokal starten, Event senden, empfangen und Signatur verifizieren.
3. **UI-Test:** Einstellungen speichern, Test-Benachrichtigung auslösen, Relay-Ergebnis im Banner prüfen.
4. **Fehlerfall:** Ungültiger Privatschlüssel → Fehlermeldung; nicht erreichbarer Relay → per-Relay-`False` im Ergebnis, kein Absturz.

---

## Abgrenzung zur Telegram-Implementierung

| | Telegram | NOSTR (geplant) |
|---|---|---|
| Transport | HTTPS (Bot-API) | WebSocket (`wss://`) |
| Authentifizierung | Bot-Token | Schnorr-Signatur (privkey) |
| Dezentralisierung | Nein | Ja |
| Empfänger | Ein Chat / Kanal | Öffentlich oder via Direktnachricht (Kind 4) |
| Abhängigkeit | `requests` (bereits vorhanden) | `websocket-client` (neu) |
| Implementierungsaufwand | Gering | Mittel (Schnorr, WS) |

---

## Offene Fragen / Erweiterungsideen

- **Kind 4 (NIP-04) – verschlüsselte Direktnachricht:** Nachrichten könnten verschlüsselt an einen bestimmten Empfänger-Pubkey gesendet werden, sodass sie nicht öffentlich sichtbar sind.
- **NIP-19 bech32-Encoding:** `nsec1…` / `npub1…` als benutzfreundlichere Eingabeformate unterstützen (benötigt die `bech32`-Bibliothek, die bereits in `requirements.txt` steht).
- **Relay-Authentifizierung (NIP-42):** Für Relays, die eine Authentifizierung erfordern.
- **Empfänger-Pubkey:** Alternativ zum eigenen Pubkey könnte man Nachrichten auch an einen fremden Pubkey schicken (nützlich für Monitoring-Dienste).
