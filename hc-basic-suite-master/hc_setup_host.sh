#!/usr/bin/env bash

DIST=$(uname -r | sed -r  's/^.*\.([^\.]+)\.[^\.]+$/\1/')

if [[ "$DIST" =~ "el8" ]]; then
    yum install -y --nogpgcheck vdsm  vdsm-gluster ovirt-hosted-engine-setup
else
    yum install -y --nogpgcheck ntp vdsm  vdsm-gluster ovirt-hosted-engine-setup screen gluster-nagios-addons xauth
fi

rm -rf /var/cache/yum/*
