#!/bin/zsh
cd "$(dirname "$0")"
bash scripts/install_iot_shortcuts.sh
source "$HOME/.zshrc"
printf '\nTesting shortcuts...\n'
iot help
printf '\nInstallation finished. Press Return to close.\n'
read
