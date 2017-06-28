#!/usr/bin/env bash
yum install -y --nogpgcheck ntp vdsm  vdsm-gluster ovirt-hosted-engine-setup screen gluster-nagios-addons xauth
rm -rf /dev/shm/*.rpm /dev/shm/yum
