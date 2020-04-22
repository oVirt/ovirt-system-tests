#!/usr/bin/env bash -ex

DIST=$(uname -r | sed -r  's/^.*\.([^\.]+)\.[^\.]+$/\1/')

yum install -y --nogpgcheck ovirt-engine-appliance

echo "DIST = $DIST"
if [[ "$DIST" =~ "el8" ]]; then
    yum install -y --nogpgcheck ansible gluster-ansible-roles ovirt-hosted-engine-setup ovirt-ansible-hosted-engine-setup ovirt-ansible-repositories ovirt-ansible-engine-setup
else
    yum install -y --nogpgcheck ansible gluster-ansible-roles ovirt-ansible-hosted-engine-setup ovirt-ansible-repositories ovirt-ansible-engine-setup
fi

rm -rf /var/cache/yum/*

## temporary check
echo "Check install package - gluster-ansible"
rpm -qa| grep gluster-ansible

#DISK_DEV=disk/by-id/0QEMU_QEMU_HARDDISK_4
DISK_DEV=sdc

mkfs.xfs -K /dev/${DISK_DEV}
mount /dev/${DISK_DEV} /var/tmp
echo -e '/dev/${DISK_DEV}\t/var/tmp\t\t\txfs\tdefaults\t0 0' >> /etc/fstab


