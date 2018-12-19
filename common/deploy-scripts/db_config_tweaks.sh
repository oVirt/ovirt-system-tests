#!/bin/bash -ex

# A script to add debug configuration to postgres logs.
# Usually usefull in combination with pgbadger for analysis.

# Set locations. If engine uses SCL, use that, otherwise use default.

get_engine_pg_scl() {
    local engine_pg_scl_conf=(/etc/ovirt-engine/engine.conf.d/*scl-postgres*.conf)
    local res=
    if [[ -e $engine_pg_scl_conf ]]; then
        # This will only work if there is exactly one file matching above
        # glob pattern. Ignore other cases for now - they should not
        # happen normally.
        . "${engine_pg_scl_conf}"
        res="${sclenv}"
    fi
    echo "${res}"
}
pg_datadir=/var/lib/pgsql/data
pg_service=postgresql.service
engine_pg_scl=$(get_engine_pg_scl)
if [[ -n $engine_pg_scl ]]; then
    pg_datadir=/var/opt/rh/${engine_pg_scl}/lib/pgsql/data
    pg_service=${engine_pg_scl}-postgresql.service
fi

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

# TODO If in the future we want to tweak a config item that demands a restart
# to take effect we must wait in the script till engine renews the
# connection:
#
#```bash
# test 200 == $(curl -k https://ovirt/services/health  -o /dev/null -s -w %{http_code})
#```
systemctl reload ${pg_service}

# vim: expandtab tabstop=4 shiftwidth=4
