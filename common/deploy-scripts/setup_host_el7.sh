#!/bin/bash -xe

yum update -y iptables

# Reserving port 54322 for ovirt-imageio-daemon service
# ToDo: this workaround can be removed once either of
# the following bugs are resolved:
# https://bugzilla.redhat.com/show_bug.cgi?id=1528971
# https://bugzilla.redhat.com/show_bug.cgi?id=1528972
sysctl -w net.ipv4.ip_local_reserved_ports=54322