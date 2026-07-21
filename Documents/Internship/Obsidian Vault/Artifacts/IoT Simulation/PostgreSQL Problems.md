# PostgreSQL Problems

[[00 - IoT Simulation Environment Setup|← IoT Home]]

## `psql: command not found`

Use the shortcut, which discovers the Homebrew PostgreSQL binary:

```bash
iot postgres
```

Or reinstall/repair:

```bash
iot fix
```

## Connection refused on port 5432

```bash
iot on
iot status
```

## Database does not exist

```bash
iot db-init
```

## Table does not exist

```bash
iot db-init
iot schema
```

## Role does not exist

The project normally uses your macOS username. Check:

```bash
whoami
cat .env
```

The `.env` file should contain:

```text
IOT_DB_USER=your_macos_username
```

After editing `.env`:

```bash
iot restart
iot db-init
```

## Password authentication failure

For a standard Homebrew local installation, a password is usually left blank. Remove an incorrect password from `.env`, or set the correct one:

```text
IOT_DB_PASSWORD=
```

## Inspect PostgreSQL status

```bash
iot postgres-status
```

---

Related: [[PostgreSQL Setup]] · [[Database Operations]]
