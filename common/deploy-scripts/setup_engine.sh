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
SNMP_MANAGERS="localhost:162"
SNMP_COMMUNITY=public
SNMP_OID=1.3.6.1.4.1.2312.13.1.1
FILTER="include:*(snmp:) \${FILTER}"
EOF
chown ovirt:ovirt /etc/ovirt-engine/notifier/notifier.conf.d/20-snmp.conf

echo "[snmp] logOption f /var/log/snmptrapd.log" >> /etc/snmp/snmptrapd.conf
echo "disableAuthorization yes" >> /etc/snmp/snmptrapd.conf

cp /usr/share/doc/ovirt-engine/mibs/* /usr/share/snmp/mibs

systemctl start snmptrapd
systemctl enable snmptrapd

# Fapolicyd with debug output
if [ "$(systemctl is-active fapolicyd)" = "active" ]; then
  mkdir -p /etc/systemd/system/fapolicyd.service.d
  cat > /etc/systemd/system/fapolicyd.service.d/10-debug-deny.conf << EOF
[Service]
Type=simple
Restart=no
ExecStart=
ExecStart=/usr/sbin/fapolicyd --debug-deny
EOF
  restorecon -vR /etc/systemd/system/fapolicyd.service.d
  systemctl daemon-reload
  systemctl restart fapolicyd
fi

# Install imageio for Python 3.8 from pip until we have proper RPM package
dnf install -y python38-devel gcc
pip3.8 install ovirt-imageio

