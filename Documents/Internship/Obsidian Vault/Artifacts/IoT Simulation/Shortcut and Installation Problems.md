# Shortcut and Installation Problems

[[00 - IoT Simulation Environment Setup|← IoT Home]]

## `zsh: command not found: io`

The updated installer defines both `iot` and `io`.

Run from the project root:

```bash
bash scripts/install_iot_shortcuts.sh
source ~/.zshrc
io help
```

## `zsh: command not found: iot`

```bash
cd "/full/path/to/IoT_Simulation_Obsidian_Final_Updated"
bash scripts/install_iot_shortcuts.sh
source ~/.zshrc
iot help
```

## Incorrect command: `source ~/install_iot_shortcuts.sh`

That path means the script is directly in your home folder, which it is not.

Use:

```bash
bash scripts/install_iot_shortcuts.sh
source ~/.zshrc
```

## Project folder was moved

The stored shortcut path points to the location where the installer was last run. After moving or renaming the folder, rerun:

```bash
cd "/new/path/to/project"
bash scripts/install_iot_shortcuts.sh
source ~/.zshrc
```

## Verify the stored path

```bash
iot where
```

## Test both shortcut names

```bash
type iot
type io
iot help
io help
```

---

Related: [[Simple Command System]]
