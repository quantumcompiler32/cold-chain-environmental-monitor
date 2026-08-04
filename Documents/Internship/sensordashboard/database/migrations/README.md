# Database migrations

The clean local/demo schema is `../bootstrap/001_core.sql`. Put additive or
data-preserving upgrades for an already-populated database here; do not add
experimental `CREATE TABLE`/`ALTER TABLE` sequences to the clean bootstrap.

Apply `004_add_run_id_correlation.sql` to an existing installation before
starting a bridge built from the current code. Readiness checks require the
`run_id` columns so a partially upgraded database fails clearly instead of
returning an unexplained API error.
