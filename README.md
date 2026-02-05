# Roblox Windows Update Tracker Discord Bot

Ein Discord-Bot, der automatisch Roblox Windows Client Updates überwacht und Benachrichtigungen in einen Discord-Channel sendet.

## Features

✅ Überwacht Roblox Windows Client Updates via [https://status.roblox.com](https://status.roblox.com)  
✅ Sendet schöne Embed-Nachrichten mit Version-Informationen  
✅ `/rbxupdate` Command zum Setzen des Tracking-Channels  
✅ Test-Nachricht bei Command-Ausführung  
✅ Persistente Speicherung der Daten  
✅ Läuft auf Render kostenlos  

## Installation

### 1. Discord Bot erstellen

1. Gehe zu [Discord Developer Portal](https://discord.com/developers/applications)
2. Klicke auf "New Application"
3. Gib einen Namen ein (z.B. "Roblox Update Tracker")
4. Gehe zu "Bot" Tab und klicke "Add Bot"
5. Kopiere den TOKEN (unter dem Bot-Namen)
6. Aktiviere folgende Intents:
   - Message Content Intent
   - Server Members Intent (optional)
7. Gehe zu OAuth2 → URL Generator
8. Wähle folgende Scopes: `bot`
9. Wähle folgende Permissions:
   - Send Messages
   - Embed Links
   - Read Messages/View Channels
10. Kopiere die generierte URL und öffne sie, um den Bot zu deinem Server einzuladen

### 2. Lokale Installation

```bash
# Repository klonen
git clone https://github.com/DEIN_USERNAME/zenk-roblox-tracker
cd zenk-roblox-tracker

# Virtual Environment erstellen (optional, aber empfohlen)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Dependencies installieren
pip install -r requirements.txt
```

### 3. Environment Variablen setzen

Editiere die `.env` Datei:

```env
DISCORD_TOKEN=dein_bot_token_hier
CLIENT_ID=deine_client_id_hier
```

- **DISCORD_TOKEN**: Der Bot-Token aus dem Discord Developer Portal
- **CLIENT_ID**: Die Application ID aus dem Discord Developer Portal (unter General Information)

### 4. Lokal testen

```bash
python main.py
```

Der Bot sollte connecten und "has connected to Discord!" in der Konsole anzeigen.

## Verwendung

1. Gehe zu einem beliebigen Channel in deinem Discord-Server
2. Schreibe: `/rbxupdate`
3. Der Bot wird:
   - Die aktuelle Roblox Version abrufen
   - Eine Test-Nachricht mit der aktuellen Version senden
   - Diesen Channel für zukünftige Update-Benachrichtigungen setzen

Die Bot schaut dann alle 5 Minuten nach Updates und sendet automatisch eine Nachricht wenn eine neue Version vorhanden ist.

## Deployment auf Render

### Schritt 1: Repository auf GitHub pushen

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/repo-name
git push -u origin main
```

### Schritt 2: Render Project erstellen

1. Gehe auf [render.com](https://render.com)
2. Registriere dich / Melde dich an
3. Klicke "New +" → "Web Service"
4. Verbinde dein GitHub-Repository
5. Wähle das Repository
6. Fülle folgendes aus:
   - **Name**: `roblox-update-tracker`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Plan**: `Free` (kostenlos)

### Schritt 3: Environment Variablen auf Render setzen

1. In Render → dein Web Service
2. Gehe zu "Environment"
3. Füge folgende Variablen hinzu:
   - `DISCORD_TOKEN`: Dein Bot-Token
   - `CLIENT_ID`: Deine Application ID

4. Klicke "Deploy" → der Bot startet automatisch

## Struktur

```
.
├── main.py              # Hauptbot-Code
├── requirements.txt     # Python-Dependencies
├── .env                 # Umgebungsvariablen (nicht in Git)
├── .gitignore          # Git ignore Datei
├── tracking_data.json  # Gespeicherte Tracking-Daten (auto-generiert)
└── README.md           # Diese Datei
```

## Troubleshooting

**Bot connectet nicht:**
- Stelle sicher, dass das Token in `.env` korrekt ist
- Token darf nicht in Git gepusht werden!

**Bot antwortet nicht auf /rbxupdate:**
- Überprüfe, dass der Bot in deinem Server die Permission "Send Messages" hat
- Stelle sicher, dass `Message Content Intent` aktiviert ist

**Updates werden nicht erkannt:**
- Überprüfe die Console-Logs
- Die API wird alle 5 Minuten gecheckt

## API-Referenz

Der Bot nutzt die offizielle Roblox Status API:
- **Endpoint**: `https://status.roblox.com/api/v2/components.json`
- **Update-Intervall**: 5 Minuten
- **Version-Format**: `version-XXXXXXXXXXXXXXX` (hex)

## Lizenz

MIT

## Support

Falls du Probleme hast:
1. Überprüfe die Console-Logs
2. Stelle sicher, dass alle Requirements installiert sind
3. Überprüfe die Bot-Permissions auf dem Discord-Server

---

Made with ❤️ for Roblox players
