#!/usr/bin/env bash

multipath -F

yum install -y --nogpgcheck vdsm  vdsm-gluster ovirt-hosted-engine-setup

rm -rf /var/cache/yum/*
