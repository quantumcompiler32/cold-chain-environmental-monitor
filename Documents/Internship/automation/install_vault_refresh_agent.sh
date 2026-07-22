#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_SOURCE="$SCRIPT_DIR/com.moksh.bytesmart-vault-refresh.plist"
AGENT_DIR="/Users/mokshjoshi/Library/LaunchAgents"
PLIST_TARGET="$AGENT_DIR/com.moksh.bytesmart-vault-refresh.plist"

mkdir -p "$AGENT_DIR"
cp "$PLIST_SOURCE" "$PLIST_TARGET"
launchctl bootout "gui/$(id -u)" "$PLIST_TARGET" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_TARGET"
launchctl enable "gui/$(id -u)/com.moksh.bytesmart-vault-refresh"
echo "Installed and loaded $PLIST_TARGET"
