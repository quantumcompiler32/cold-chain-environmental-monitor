#!/bin/zsh
cd "$(dirname "$0")"
if ! type iot >/dev/null 2>&1; then
  bash scripts/install_iot_shortcuts.sh
  source "$HOME/.zshrc"
fi
iot go
printf '\nPipeline launch requested. Press Return to close.\n'
read
