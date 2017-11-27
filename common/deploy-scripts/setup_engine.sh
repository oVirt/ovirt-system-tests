set -xe

# if needed, install and configure firewalld
EL7="release 7\.[0-9]"
function install_firewalld() {
    if grep "$EL7" /etc/redhat-release > /dev/null; then
        if  ! rpm -q firewalld > /dev/null; then
            {
                yum install -y firewalld && \
                {
                systemctl enable firewalld
                systemctl start firewalld
                firewall-cmd --permanent --zone=public --add-interface=eth0
                systemctl restart firewalld;
                systemctl restart NetworkManager
                }
            }
        else
            systemctl enable firewalld
            systemctl start firewalld
        fi
    fi
}

cat > /root/iso-uploader.conf << EOF
[ISOUploader]
user=admin@internal
passwd=123
engine=localhost:443
EOF

cat > /root/ovirt-log-collector.conf << EOF
[LogCollector]
user=admin@internal
passwd=123
engine=engine:443
local-tmp=/dev/shm/log
output=/dev/shm
EOF

# engine 4 resolves its FQDN
ADDR=$(/sbin/ip -4 -o addr show dev eth0 | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] "." a[4]}'| awk -F/ '{print $1}')
echo "$ADDR engine" >> /etc/hosts

install_firewalld
yum install --nogpgcheck -y --downloaddir=/dev/shm ntp net-snmp ovirt-engine ovirt-log-collector ovirt-engine-extension-aaa-ldap* otopi-debug-plugins
RET_CODE=$?
if [ ${RET_CODE} -ne 0 ]; then
    echo "yum install failed with status ${RET_CODE}."
    exit ${RET_CODE}
fi
rm -rf /dev/shm/yum /dev/shm/*.rpm

if grep "$EL7" /etc/redhat-release > /dev/null; then
    fstrim -va

    #Configure ntpd only on EL7 - will be used in 4.0, 4.1, Master suites.
    echo "restrict 192.168.0.0 mask 255.255.0.0 nomodify notrap nopeer" >> /etc/ntp.conf
    systemctl enable ntpd
    systemctl start ntpd
    firewall-cmd --add-service=ntp --permanent
    firewall-cmd --reload
fi

# Enable debug logs on the engine
sed -i \
    -e '/.*logger category="org.ovirt"/{ n; s/INFO/DEBUG/ }' \
    -e '/.*<root-logger>/{ n; s/INFO/DEBUG/ }' \
    /usr/share/ovirt-engine/services/ovirt-engine/ovirt-engine.xml.in

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
