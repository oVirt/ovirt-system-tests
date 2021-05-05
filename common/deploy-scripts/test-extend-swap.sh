#!/bin/sh

# create additional swap
device=$(ls -1 /dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_* |tail -1)
mkswap  "${device}"
echo "${device}_swap swap swap defaults 0 0" >> /etc/fstab
systemctl daemon-reload
swapon -v  "${device}"

