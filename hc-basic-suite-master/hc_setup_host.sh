#!/usr/bin/env bash
yum install -y --nogpgcheck ntp vdsm  vdsm-gluster ovirt-hosted-engine-setup screen gluster-nagios-addons xauth
rm -rf /var/cache/yum/* /var/cache/dnf/*
