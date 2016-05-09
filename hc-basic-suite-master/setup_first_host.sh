#!/usr/bin/env bash
yum install -y --nogpgcheck ovirt-engine-appliance
mkfs.xfs -K -r extsize=1m /dev/vdd
mount /dev/vdd /var/tmp
echo -e '/dev/vdd\t/var/tmp\t\t\txfs\tdefaults\t0 0' >> /etc/fstab


