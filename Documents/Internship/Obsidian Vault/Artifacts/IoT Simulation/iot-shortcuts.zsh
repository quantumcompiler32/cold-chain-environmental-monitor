# Loaded from ~/.zshrc after running scripts/install_iot_shortcuts.sh.

if [[ -f "$HOME/.iot_simulation_env" ]]; then
  source "$HOME/.iot_simulation_env"
fi

function _iot_validate_root() {
  if [[ -z "${IOT_PROJECT_ROOT:-}" || ! -d "$IOT_PROJECT_ROOT" ]]; then
    echo "IoT project path is missing or stale."
    echo "Open the current project folder and run:"
    echo "  bash scripts/install_iot_shortcuts.sh"
    echo "  source ~/.zshrc"
    return 1
  fi
}

function iot() {
  _iot_validate_root || return 1
  local command="${1:-help}"

  if [[ "$command" == "activate" ]]; then
    if [[ ! -f "$IOT_PROJECT_ROOT/venv/bin/activate" ]]; then
      echo "Virtual environment missing. Run: iot setup"
      return 1
    fi
    cd "$IOT_PROJECT_ROOT" || return 1
    source "$IOT_PROJECT_ROOT/venv/bin/activate"
    echo "Activated: $IOT_PROJECT_ROOT/venv"
    return 0
  fi

  if [[ "$command" == "deactivate" ]]; then
    if (( $+functions[deactivate] )); then
      deactivate
      echo "Virtual environment deactivated."
    else
      echo "No virtual environment is active in this shell."
    fi
    return 0
  fi

  "$IOT_PROJECT_ROOT/scripts/iotctl" "$@"
}

function io() {
  iot "$@"
}
