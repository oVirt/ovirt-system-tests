#!/bin/bash -xe

systemctl enable firewalld
systemctl start firewalld

systemctl enable crond
systemctl start crond

rm -rf /dev/shm/yum /dev/shm/*.rpm
fstrim -va

firewall-cmd --permanent --zone=public --add-interface=eth0
firewall-cmd --reload

# rotate logs quicker, because of the debug logs they tend to flood the root partition if they run > 15 minutes
cat > /etc/cron.d/ovirt-engine << EOF
* * * * * root logrotate /etc/logrotate.d/ovirt-engine
* * * * * root logrotate /etc/logrotate.d/ovirt-engine-dwh
EOF

cat > /etc/ovirt-engine/notifier/notifier.conf.d/20-snmp.conf << EOF
SNMP_MANAGERS=localhost:162
SNMP_OID=1.3.6.1.4.1.2312.13.1.1
FILTER="include:*(snmp:)"
SNMP_VERSION=3
SNMP_ENGINE_ID="80:00:00:00:01:02:05:05"
SNMP_USERNAME=ovirtengine
SNMP_AUTH_PROTOCOL=SHA
SNMP_AUTH_PASSPHRASE=authpass
SNMP_PRIVACY_PROTOCOL=AES128
SNMP_PRIVACY_PASSPHRASE=privpass
SNMP_SECURITY_LEVEL=3
EOF
chown ovirt:ovirt /etc/ovirt-engine/notifier/notifier.conf.d/20-snmp.conf

# Create /var/log/snmptrapd.log with correct SELinux file type
touch /var/log/snmptrapd.log
chcon -t snmpd_log_t /var/log/snmptrapd.log

# Configure snmpd and snmpdtrapd
systemctl stop snmpd
systemctl stop snmptrapd
cat > /etc/snmp/snmptrapd.conf << EOF
disableAuthorization yes
# version 3 traps: allow user ovirtengine to log,execute,net
authUser log,execute,net ovirtengine
# version 3 add a user NoAuthnoPriv who can send noAuthNoPriv
authUser log,execute,net NoAuthNoPriv noauth
# Log incoming traps to /var/log/snmptrapd.log
[snmp] logOption f /var/log/snmptrapd.log
EOF

cat >>  /var/lib/net-snmp/snmpd.conf << EOF
createUser -e 0x8000000001020505 ovirtengine SHA authpass AES privpass
createUser -e 0x8000000001020606 NoAuthNoPriv
EOF

cat >>  /var/lib/net-snmp/snmptrapd.conf << EOF
createUser -e 0x8000000001020505 ovirtengine SHA authpass AES privpass
createUser -e 0x8000000001020606 NoAuthNoPriv
EOF

cat >>  /etc/snmp/snmpd.conf << EOF
rwuser ovirtengine
rwuser NoAuthNoPriv noauth
EOF

cp /usr/share/doc/ovirt-engine/mibs/* /usr/share/snmp/mibs

# We have to set DAYS_TO_SEND_ON_STARTUP to 1 because its default value is 0
# it means that it will not send any old events, a race between the service start and
# the new tag added above will cause that this event will not processed.
echo "DAYS_TO_SEND_ON_STARTUP=1" >  /etc/ovirt-engine/notifier/notifier.conf.d/30-ovirt-engine-notifier.conf
chown ovirt:ovirt /etc/ovirt-engine/notifier/notifier.conf.d/30-ovirt-engine-notifier.conf


systemctl start snmpd
systemctl start snmptrapd
# new user created in net-snmp/snmpd*.conf are available only after services are restarted
# TODO , check if this is a bug
systemctl restart snmpd
systemctl restart snmptrapd
systemctl enable snmpd
systemctl enable snmptrapd

# Allow Grafana to connect PostgreSQL data source to use ovirt_engine_history database
# TODO Replace with proper fix in ovirt-dwh when grafana_can_tcp_connect_postgresql_port is added to grafana-selinux
cat >> /tmp/grafana-postgresql-ds.cil << EOF
(allow grafana_t postgresql_port_t (tcp_socket (name_connect)))
EOF
semodule -i /tmp/grafana-postgresql-ds.cil
