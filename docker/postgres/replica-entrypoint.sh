#!/bin/bash
set -e

if [ -s "$PGDATA/PG_VERSION" ]; then
    echo "[Pulse-Replica] Existing data found - starting PostgreSQL in standby mode..."
    chown -R postgres:postgres "$PGDATA"
    exec sudo -u postgres /usr/lib/postgresql/15/bin/postgres -D "$PGDATA"
fi

PRIMARY_HOST="${POSTGRES_PRIMARY_HOST:?POSTGRES_PRIMARY_HOST is required}"
PRIMARY_PORT="${POSTGRES_PRIMARY_PORT:-5432}"
REPL_USER="${POSTGRES_REPLICATION_USER:-replicator}"
REPL_PASS="${POSTGRES_REPLICATION_PASSWORD:-replicator_password}"

echo "[Pulse-Replica] Fresh volume - waiting for primary at $PRIMARY_HOST:$PRIMARY_PORT ..."

until pg_isready -h "$PRIMARY_HOST" -p "$PRIMARY_PORT" -U "$POSTGRES_USER" -q; do
    echo "[Pulse-Replica] Primary not ready yet, retrying in 3s..."
    sleep 3
done

echo "[Pulse-Replica] Primary is ready - running pg_basebackup..."

mkdir -p "$PGDATA"

PGPASSWORD="$REPL_PASS" pg_basebackup \
    -h "$PRIMARY_HOST" \
    -p "$PRIMARY_PORT" \
    -U "$REPL_USER" \
    -D "$PGDATA" \
    -Fp -Xs -R -P \
    --checkpoint=fast

chown -R postgres:postgres "$PGDATA"
chmod 700 "$PGDATA"

echo "[Pulse-Replica] pg_basebackup complete - starting PostgreSQL in standby mode..."
exec sudo -u postgres /usr/lib/postgresql/15/bin/postgres -D "$PGDATA"
