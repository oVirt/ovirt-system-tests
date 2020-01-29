set -xe

DIST=$(uname -r |awk -F\. '{print $(NF-1)}')
FC_REGEX="^fc[0-9]+$"

# if needed, install and configure firewalld
function install_firewalld() {
    if [[ "$DIST" == "el7" ]]; then
        if  ! rpm -q firewalld > /dev/null; then
            {
                yum install -y firewalld && \
                {
                systemctl enable firewalld
                systemctl start firewalld
                firewall-cmd --permanent --zone=public --add-interface=eth0
                systemctl restart firewalld;
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
NIC=$(ip route | awk '$1=="default" {print $5; exit}')
ADDR=$(/sbin/ip -4 -o addr show dev $NIC | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] "." a[4]}'| awk -F/ '{print $1}')
echo "$ADDR engine" >> /etc/hosts

pkgs_to_install=(
    "ntp"
    "net-snmp"
    "ovirt-engine"
    "ovirt-log-collector"
    "ovirt-engine-extension-aaa-ldap*"
    "otopi-debug-plugins"
    "cronie"
)

install_firewalld

if [[ "$DIST" == "el7" ]]; then
    install_cmd="yum install --nogpgcheck -y"
elif [[ "$DIST" =~ $FC_REGEX ]]; then
    install_cmd="dnf install -y"
else
    echo "Unknown distro $DIST"
    exit 1
fi

$install_cmd "${pkgs_to_install[@]}" || {
    ret=$?
    echo "install failed with status $ret"
    exit $ret
}

systemctl enable crond
systemctl start crond

rm -rf /var/cache/yum/* /var/cache/dnf/*
fstrim -va
echo "restrict 192.168.0.0 mask 255.255.0.0 nomodify notrap nopeer" >> /etc/ntp.conf
systemctl enable ntpd
systemctl start ntpd
firewall-cmd --add-service=ntp --permanent
firewall-cmd --reload

# Enable debug logs on the engine
sed -i \
    -e '/.*logger category="org.ovirt"/{ n; s/INFO/DEBUG/ }' \
    -e '/.*logger category="org.ovirt.engine.core.bll"/{ n; s/INFO/DEBUG/ }' \
    -e '/.*<root-logger>/{ n; s/INFO/DEBUG/ }' \
    /usr/share/ovirt-engine/services/ovirt-engine/ovirt-engine.xml.in

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

# Reserving port 54323 for ovirt-imageio-proxy service
sysctl -w net.ipv4.ip_local_reserved_ports=54323
