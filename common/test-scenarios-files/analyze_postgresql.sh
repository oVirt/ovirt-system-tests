#!/bin/bash -ex

# Analyze postgres logs and generate a reports.
# 1. pgbadger is a static log analyzer that create a static html 'out.html' which will be created under the
# the log directory so if make sure the postgres log dir is an artifact
# 2. pgcluu analyzes more runtime behaviours and produces reports like missing indexes, table sizes, etc

yum install -y https://download.postgresql.org/pub/repos/yum/9.5/redhat/rhel-7-x86_64/pgdg-centos95-9.5-3.noarch.rpm
yum install -y pgbadger pgcluu

cd /var/opt/rh/rh-postgresql95/lib/pgsql/data/pg_log/

# 1. Run PgBadger
# if there is no postgresql.log, find the right one current one
# with the format postgesql-%d.log and link it
pglog=$(su - postgres -c "scl enable rh-postgresql95 -- psql  postgres postgres -t -c 'show log_filename'" | sed 2d)
# trim whitespaces using shell expansion to be independent of other commands
pglog=$(date +${pglog//[[:blank:]]/})

mkdir pgbadger
pgbadger $pglog --outdir pgbadger


# 2. Run PgCluu
su - postgres -c "mkdir -p $PWD/pgcluu/report $PWD/pgcluu/output"
su - postgres -c "scl enable rh-postgresql95 -- pgcluu_collectd -E 1M $PWD/pgcluu/output -U postgres"
su - postgres -c "scl enable rh-postgresql95 -- pgcluu -o $PWD/pgcluu/report $PWD/pgcluu/output"
