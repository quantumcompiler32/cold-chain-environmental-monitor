#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$HOME/.iot_simulation_env"
ZSHRC="$HOME/.zshrc"
START_MARKER="# >>> IoT Simulation shortcuts >>>"
END_MARKER="# <<< IoT Simulation shortcuts <<<"
TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

chmod +x \
  "$PROJECT_ROOT/scripts/iotctl" \
  "$PROJECT_ROOT/scripts/install_iot_shortcuts.sh" \
  "$PROJECT_ROOT/scripts/run_subscriber.command" \
  "$PROJECT_ROOT/scripts/run_simulator.command" \
  "$PROJECT_ROOT/scripts/watch_data.command" \
  "$PROJECT_ROOT/Install IoT Shortcuts.command" \
  "$PROJECT_ROOT/Start IoT Pipeline.command"

escaped_root=${PROJECT_ROOT//\'/\'\\\'\'}
cat > "$ENV_FILE" <<EOF
export IOT_PROJECT_ROOT='$escaped_root'
export PATH="\$IOT_PROJECT_ROOT/scripts:\$PATH"
EOF

# Add a discovered Homebrew PostgreSQL bin directory for direct psql use.
if command -v brew >/dev/null 2>&1; then
  for formula in postgresql@14 postgresql@18 postgresql@17 postgresql@16 postgresql@15 postgresql; do
    if brew list --versions "$formula" >/dev/null 2>&1; then
      pg_bin="$(brew --prefix "$formula")/bin"
      printf 'export PATH=%q:$PATH\n' "$pg_bin" >> "$ENV_FILE"
      break
    fi
  done
fi

touch "$ZSHRC"

awk -v start="$START_MARKER" -v end="$END_MARKER" '
  $0 == start { skip=1; next }
  $0 == end { skip=0; next }
  skip != 1 {
    if ($0 == "# IoT Simulation shortcuts") next
    if ($0 == "source \"$HOME/.iot_simulation_env\"") next
    if ($0 == "source \"$IOT_PROJECT_ROOT/scripts/iot-shortcuts.zsh\"") next
    print
  }
' "$ZSHRC" > "$TMP_FILE"

cat "$TMP_FILE" > "$ZSHRC"
cat >> "$ZSHRC" <<'EOF'

# >>> IoT Simulation shortcuts >>>
if [[ -f "$HOME/.iot_simulation_env" ]]; then
  source "$HOME/.iot_simulation_env"
fi
if [[ -n "${IOT_PROJECT_ROOT:-}" && -f "$IOT_PROJECT_ROOT/scripts/iot-shortcuts.zsh" ]]; then
  source "$IOT_PROJECT_ROOT/scripts/iot-shortcuts.zsh"
fi
# <<< IoT Simulation shortcuts <<<
EOF

printf '\nInstalled IoT shortcuts.\n'
printf 'Project root: %s\n\n' "$PROJECT_ROOT"
printf 'Run exactly:\n'
printf '  source ~/.zshrc\n'
printf '  iot setup\n'
printf '  iot help\n'
printf '  io help\n\n'
printf 'Do not run: source ~/install_iot_shortcuts.sh\n'
printf 'The installer path is: scripts/install_iot_shortcuts.sh\n'
