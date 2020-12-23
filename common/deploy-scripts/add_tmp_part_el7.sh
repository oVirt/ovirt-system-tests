#!/bin/bash
TMP_DEV="/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_2"

mkfs.xfs -K ${TMP_DEV}
mount -t xfs ${TMP_DEV} /var/tmp
chmod 1777 /var/tmp
echo -e "${TMP_DEV} /var/tmp xfs defaults 0 0" >> /etc/fstab
