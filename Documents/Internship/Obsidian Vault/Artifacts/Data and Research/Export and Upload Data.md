# Export and Upload Data

[[00 - IoT Simulation Environment Setup|← IoT Home]]

## Export the PostgreSQL table

```bash
iot save
```

Equivalent long command:

```bash
iot export
```

The command writes a timestamped CSV under `exports/` and prints its full path.

## Preview the newest export

```bash
iot latest
```

## Open the export folder

```bash
iot exports
```

## Export and prepare for Google Colab

```bash
iot upload
```

The command:

1. Exports a fresh CSV.
2. Reveals that file in Finder.
3. Opens Google Colab in the browser.
4. Prints the exact file to upload.

Browser upload remains a manual action because Google requires interaction with the file picker.

## Upload steps in Colab

1. Open the Files panel on the left.
2. Select **Upload to session storage**.
3. Choose the CSV revealed by `iot upload`.
4. Run the notebook cells.

A ready notebook is included:

```text
notebooks/IoT_Telemetry_Analysis.ipynb
```

---

Related: [[Google Colab Guide]] · [[Analysis Examples]]
