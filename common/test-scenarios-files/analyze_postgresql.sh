#!/bin/bash -ex

# Analyze postgres logs and generate a report.
# The tool to use that is pgbadger which is a static log analyzer
# The report is a static html 'out.html' which will be created under the
# the log directory so if make sure the postgres log dir is an artifact

yum install -y https://download.postgresql.org/pub/repos/yum/9.5/redhat/rhel-7-x86_64/pgdg-centos95-9.5-3.noarch.rpm
yum install -y pgbadger

cd /var/opt/rh/rh-postgresql95/lib/pgsql/data/pg_log/

# if there is no postgresql.log, find the right one current one
# with the format postgesql-%d.log and link it
pglog=$(su - postgres -c "scl enable rh-postgresql95 -- psql  postgres postgres -t -c 'show log_filename'" | sed 2d)
# trim whitespaces using shell expansion to be independant of other commands
pglog=$(date +${pglog//[[:blank:]]/})

mkdir pgbadger
pgbadger $pglog --outdir pgbadger
