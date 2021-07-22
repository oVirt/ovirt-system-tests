#!/bin/bash -xe

LOCALTMP=$(mktemp --dry-run /dev/shm/XXXXXX)
cat > /root/ovirt-log-collector.conf << EOF
[LogCollector]
user=admin@internal
passwd=123
engine=engine:443
local-tmp=$LOCALTMP
output=/dev/shm
EOF

# add "engine" to /etc/hosts. This should be eliminated in favor of FQDN everywhere.
# relies on eth0 being the management network.
ADDR=$(/sbin/ip -o addr show dev eth0 scope global | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] "." a[4]}'| awk -F/ '{print $1; exit}')
echo "$ADDR engine" >> /etc/hosts

# if you want to add anything here, please try to preinstall it first
required_pkgs=(
    "net-snmp"
    "ovirt-engine"
    "ovirt-log-collector"
    "ovirt-engine-extension-aaa-ldap-setup"
    "otopi-debug-plugins"
    "cronie"
    "nfs-utils"
    "rpcbind"
    "lvm2"
    "targetcli"
    "sg3_utils"
    "iscsi-initiator-utils"
    "policycoreutils-python-utils"
)

systemctl enable firewalld
systemctl start firewalld

if  ! rpm -q "${required_pkgs[@]}" >/dev/null; then
    echo "one of the required packages is missing: ${required_pkgs[@]}"
    exit 10
fi

systemctl enable crond
systemctl start crond

rm -rf /dev/shm/yum /dev/shm/*.rpm
fstrim -va

systemctl enable chronyd
systemctl start chronyd
firewall-cmd --permanent --zone=public --add-interface=eth0
firewall-cmd --permanent --zone=public --add-service=ntp
firewall-cmd --reload

# rotate logs quicker, because of the debug logs they tend to flood the root partition if they run > 15 minutes
cat > /etc/cron.d/ovirt-engine << EOF
* * * * * root logrotate /etc/logrotate.d/ovirt-engine
* * * * * root logrotate /etc/logrotate.d/ovirt-engine-dwh
EOF

cat > /etc/ovirt-engine/notifier/notifier.conf.d/20-snmp.conf << EOF
SNMP_MANAGERS="localhost:162"
SNMP_COMMUNITY=public
SNMP_OID=1.3.6.1.4.1.2312.13.1.1
FILTER="include:*(snmp:) \${FILTER}"
EOF

echo "[snmp] logOption f /var/log/snmptrapd.log" >> /etc/snmp/snmptrapd.conf
echo "disableAuthorization yes" >> /etc/snmp/snmptrapd.conf

cp /usr/share/doc/ovirt-engine/mibs/* /usr/share/snmp/mibs

systemctl start snmptrapd
systemctl enable snmptrapd

