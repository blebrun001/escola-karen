#!/bin/zsh
set -euo pipefail

ROOT="${0:A:h}"
SERVICE="escola-karen-gmail"
LABEL="com.brice.escola-karen.job-watch"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
EMAIL_CONFIG="$ROOT/email_config.local.json"

if [[ ! -f "$EMAIL_CONFIG" ]]; then
  echo "Falta email_config.local.json."
  echo "Copia email_config.example.json, completa l'adreça d'enviament i torna-ho a provar."
  exit 1
fi

SENDER="$(/usr/bin/python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sender"])' "$EMAIL_CONFIG")"

if ! command -v pdftotext >/dev/null 2>&1; then
  echo "pdftotext manque. Installez Poppler avec : brew install poppler"
  exit 1
fi

echo "Crea primer una contrasenya d'aplicació de Google:"
echo "https://myaccount.google.com/apppasswords"
echo
read -s "APP_PASSWORD?Contrasenya d'aplicació de Gmail (16 caràcters): "
echo
APP_PASSWORD="${APP_PASSWORD// /}"
if [[ ${#APP_PASSWORD} -lt 16 ]]; then
  echo "La contrasenya d'aplicació no sembla vàlida."
  exit 1
fi

security add-generic-password \
  -U \
  -s "$SERVICE" \
  -a "$SENDER" \
  -w "$APP_PASSWORD"
unset APP_PASSWORD

mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/logs" "$ROOT/data" "$ROOT/reports"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>$ROOT/job_watch.py</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$ROOT</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>15</integer>
    <key>Minute</key>
    <integer>5</integer>
  </dict>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>StandardOutPath</key>
  <string>$ROOT/logs/launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>$ROOT/logs/launchd.err.log</string>
</dict>
</plist>
PLIST

plutil -lint "$PLIST"
launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo
echo "Instal·lació completada."
echo "L'informe s'enviarà cada dia a les 15.05 h (hora local del Mac)."
echo "Prova manual sense correu: /usr/bin/python3 \"$ROOT/job_watch.py\" --dry-run"
