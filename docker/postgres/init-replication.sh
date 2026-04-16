#!/bin/bash
set -e

echo "[Pulse] Configuring primary for streaming replication..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$ BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'replicator') THEN
            CREATE USER replicator REPLICATION LOGIN ENCRYPTED PASSWORD 'replicator_password';
        END IF;
    END \$\$;
EOSQL

printf '
host    replication     replicator      all             md5
' >> "$PGDATA/pg_hba.conf"

cat >> "$PGDATA/postgresql.conf" <<-EOF

wal_level = replica
max_wal_senders = 5
wal_keep_size = 128MB
hot_standby = on
EOF

echo "[Pulse] Primary replication configured"
