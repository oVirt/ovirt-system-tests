#!/usr/bin/env bash
yum install -y --nogpgcheck ovirt-engine-appliance
rm -rf /dev/shm/*.rpm /dev/shm/yum

#DISK_DEV=disk/by-id/0QEMU_QEMU_HARDDISK_4
DISK_DEV=sdc

mkfs.xfs -K /dev/${DISK_DEV}
mount /dev/${DISK_DEV} /var/tmp
echo -e '/dev/${DISK_DEV}\t/var/tmp\t\t\txfs\tdefaults\t0 0' >> /etc/fstab


