#!/bin/bash -xe

yum install -y pm-utils
#workaround for https://bugzilla.redhat.com/show_bug.cgi?id=1258868
# It delays tuned initialization, as dbus is rejecting 'partial' files
# that were just installed via RPM. Workaround: restart dbus.
# Cuts 2 minutes from host installation
yum update -y tuned
systemctl restart dbus
systemctl restart systemd-logind
systemctl stop postfix
systemctl disable postfix
