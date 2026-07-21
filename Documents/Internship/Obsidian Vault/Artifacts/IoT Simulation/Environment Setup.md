# Environment Setup

[[00 - IoT Simulation Environment Setup|← IoT Home]]

## Supported primary environment

The shortcut system in this folder is designed for macOS with `zsh` and Homebrew. The Python source code itself is cross-platform.

## Recommended setup

From the project root:

```bash
bash scripts/install_iot_shortcuts.sh
source ~/.zshrc
iot setup
```

`iot setup` performs these actions:

1. Confirms Homebrew is available.
2. Installs Mosquitto if missing.
3. Installs an available PostgreSQL formula if missing.
4. Ensures Python 3 is available.
5. Creates `venv/`.
6. Installs `requirements.txt`.
7. Creates `.env` with your macOS username as the PostgreSQL user.
8. Starts MQTT and PostgreSQL.
9. Creates the `iot_platform` database and schema.
10. Runs health checks.

## Manual Homebrew commands

```bash
brew update
brew install mosquitto
brew install postgresql@14
```

If `postgresql@14` is unavailable, use:

```bash
brew install postgresql
```

The included command system detects whichever supported PostgreSQL formula is installed.

## Manual Python environment

```bash
cd "/full/path/to/IoT_Simulation_Obsidian_Final_Updated"
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

> [!tip]
> `iot subscriber`, `iot simulator`, and `iot analyze` call `venv/bin/python` directly. They do not depend on whether your current Terminal prompt shows `(venv)`.

## Windows reference

Install Mosquitto and PostgreSQL from an Administrator PowerShell window:

```powershell
winget install Eclipse.Mosquitto
winget install PostgreSQL.PostgreSQL
```

Create and activate Python environment:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The `iot` shortcut shell functions are macOS-specific. Windows users can run the source scripts directly.

---

Next: [[Mosquitto Setup]] · [[PostgreSQL Setup]] · [[Python Environment]]
