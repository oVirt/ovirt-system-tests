#!/bin/sh

# A script to add debug configuration to postgres logs.
# Usually usefull in combination with pgbadger for analysis.

# Software collection pg 9.5 locations.
pg_datadir=/var/opt/rh/rh-postgresql95/lib/pgsql/data
pg_service=rh-postgresql95-postgresql.service

# If you are using default package installation, unmark this
#pg_datadir=/var/lib/pgsql/data
#pg_service=postgresql.service

sed -i 's/#include_dir/include_dir/' ${pg_datadir}/postgresql.conf

mkdir ${pg_datadir}/conf.d

cat > ${pg_datadir}/conf.d/debug.conf << EOF
log_min_duration_statement = 0
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on
log_temp_files = 0
log_autovacuum_min_duration = 0
log_error_verbosity = default
lc_messages='C'
EOF

systemctl restart ${pg_service}
