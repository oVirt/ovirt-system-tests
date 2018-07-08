#!/bin/bash -xe
set -ex

HUGEPAGES=3

yum update -y iptables

# Reserving port 54322 for ovirt-imageio-daemon service
# ToDo: this workaround can be removed once either of
# the following bugs are resolved:
# https://bugzilla.redhat.com/show_bug.cgi?id=1528971
# https://bugzilla.redhat.com/show_bug.cgi?id=1528972
sysctl -w net.ipv4.ip_local_reserved_ports=54322

for node in /sys/devices/system/node/node*; do
    echo $HUGEPAGES > $node/hugepages/hugepages-2048kB/nr_hugepages;
done

# Configure libvirtd log
mkdir -p /etc/libvirt
echo 'log_outputs="2:file:/var/log/libvirt.log"' >> /etc/libvirt/libvirtd.conf
