#!/bin/bash -xe

sed \
    -i /etc/sysconfig/network-scripts/ifcfg-eth0 \
    -e '/.*HWADDR.*/d'
echo -e "\nDEVICE=eth0" >> /etc/sysconfig/network-scripts/ifcfg-eth0

yum install -y deltarpm pm-utils
#workaround for https://bugzilla.redhat.com/show_bug.cgi?id=1258868
# It delays tuned initialization, as dbus is rejecting 'partial' files
# that were just installed via RPM. Workaround: restart dbus.
# Cuts 2 minutes from host installation
yum update -y tuned
systemctl restart dbus
systemctl restart systemd-logind
