#!/bin/bash -xe
set -ex

yum -y install ovirt-host
rm -rf /dev/shm/*.rpm /dev/shm/yum

virsh -c qemu:///system?authfile=/etc/ovirt-hosted-engine/virsh_auth.conf domcapabilities kvm > /var/log/virsh_domcapabilities.log || res=$?

