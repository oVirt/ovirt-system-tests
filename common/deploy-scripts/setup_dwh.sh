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

# We are using an OST image that includes the engine. We do not setup
# the engine, but install engine-setup code - thus might run it, with
# unintended side effects. Let's remove it.
# Current context: https://bugzilla.redhat.com/2126778
dnf remove -y --noautoremove ovirt-engine
