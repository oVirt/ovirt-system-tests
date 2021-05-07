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

# engine 4 resolves its FQDN
NIC=$(ip route | awk '$1=="default" {print $5; exit}')
ADDR=$(/sbin/ip -4 -o addr show dev $NIC | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] "." a[4]}'| awk -F/ '{print $1}')
echo "$ADDR engine" >> /etc/hosts

# if you want to add anything here, please try to preinstall it first
pkgs_to_install=(
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

if  ! rpm -q "${pkgs_to_install[@]}" >/dev/null; then
    dnf module enable -y pki-deps 389-ds postgresql:12
    # only required on CentOS, so check if it exists
    dnf module list javapackages-tools && dnf module enable -y javapackages-tools
    dnf install --nogpgcheck -y "${pkgs_to_install[@]}" || {
        ret=$?
        echo "install failed with status $ret"
        exit $ret
    }
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

if [[ ! -r /etc/NetworkManager/conf.d/10-stable-ipv6-addr.conf ]]; then
    cat << EOF > /etc/NetworkManager/conf.d/10-stable-ipv6-addr.conf
[connection]
ipv6.addr-gen-mode=0
ipv6.dhcp-duid=ll
ipv6.dhcp-iaid=mac
EOF

    systemctl restart NetworkManager
fi
