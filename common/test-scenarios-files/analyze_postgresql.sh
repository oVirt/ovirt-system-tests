#!/bin/bash -ex

# Analyze postgres logs and generate a reports.
# 1. pgbadger is a static log analyzer that create a static html 'out.html' which will be created under the
# the log directory so if make sure the postgres log dir is an artifact
# 2. pgcluu analyzes more runtime behaviours and produces reports like missing indexes, table sizes, etc

get_engine_pg_scl() {
    local engine_pg_scl_conf=(/etc/ovirt-engine/engine.conf.d/*scl-postgres*.conf)
    local res=
    if [[ -e $engine_pg_scl_conf ]]; then
        . "${engine_pg_scl_conf}"
        res="${sclenv}"
    fi
    echo "${res}"
}
pg_datadir=/var/lib/pgsql/data
pg_service=postgresql.service
pgdg=
scl_enable=
engine_pg_scl=$(get_engine_pg_scl)
if [[ -n $engine_pg_scl ]]; then
    pg_datadir=/var/opt/rh/${engine_pg_scl}/lib/pgsql/data
    pg_service=${engine_pg_scl}-postgresql.service
    scl_enable="scl enable ${engine_pg_scl} -- "
    case "${engine_pg_scl}" in
        rh-postgresql10)
            pgdg=https://download.postgresql.org/pub/repos/yum/10/redhat/rhel-7-x86_64/pgdg-redhat10-10-2.noarch.rpm
            ;;
        rh-postgresql95)
            pgdg=https://download.postgresql.org/pub/repos/yum/9.5/redhat/rhel-7-x86_64/pgdg-centos95-9.5-3.noarch.rpm
            ;;
        *)
            echo "unknown engine pg scl version ${engine_pg_scl}, please update $0"
            exit 1;
            ;;
    esac
else
    pgver=$(rpm -q postgresql)
    case "${pgver}" in
        postgresql-10.6*el8*)
            pgdg=https://download.postgresql.org/pub/repos/yum/10/redhat/rhel-8-x86_64/pgdg-redhat-repo-latest.noarch.rpm
            ;;
        postgresql-12*el8*)
            pgdg=https://download.postgresql.org/pub/repos/yum/12/redhat/rhel-8-x86_64/pgdg-redhat-repo-latest.noarch.rpm
            ;;
        *)
            echo "unknown engine pg version ${pgver}, please update $0"
            exit 1;
            ;;
    esac
fi
[[ -n $pgdg ]] && yum install -y "${pgdg}"
yum install -y pgbadger pgcluu

# Get log directory
pglogdir=$(su - postgres -c "${scl_enable}psql  postgres postgres -t -c 'show log_directory'" | sed 2d)
pglogdir=${pglogdir//[[:blank:]]/}
cd "${pg_datadir}/${pglogdir}/"

# 1. Run PgBadger
# if there is no postgresql.log, find the right one current one
# with the format postgesql-%d.log and link it
pglog=$(su - postgres -c "${scl_enable}psql  postgres postgres -t -c 'show log_filename'" | sed 2d)
# trim whitespaces using shell expansion to be independent of other commands
pglog=$(date +${pglog//[[:blank:]]/})

mkdir pgbadger
pgbadger -f stderr $pglog --outdir pgbadger


# 2. Run PgCluu
su - postgres -c "mkdir -p $PWD/pgcluu/report $PWD/pgcluu/output"
su - postgres -c "${scl_enable}pgcluu_collectd -E 1M $PWD/pgcluu/output -U postgres"
su - postgres -c "${scl_enable}pgcluu -o $PWD/pgcluu/report $PWD/pgcluu/output"

# vim: expandtab tabstop=4 shiftwidth=4
