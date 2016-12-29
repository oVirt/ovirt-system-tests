#!/bin/bash -xe
set -xe
HE_DEV="disk/by-id/scsi-0QEMU_QEMU_HARDDISK_4"


setup_device() {
    local device=$1
    local mountpath=$2
    local exportpath=$3
    mkdir -p "${mountpath}"
    mkfs.xfs -K "/dev/${device}"
    echo "/dev/${device} ${mountpath} xfs defaults,discard 0 0" >> /etc/fstab
    mount "/dev/${device}" "${mountpath}"
    mkdir -p "${exportpath}"
    chmod a+rwx "${exportpath}"
    echo "${exportpath} *(rw,sync,no_root_squash,no_all_squash)" >> /etc/exports
    exportfs -a
}


setup_he() {
    setup_device "${HE_DEV}" /exports/nfs_he /exports/nfs_he
}

main() {
    setup_he
    rm -rf /dev/shm/*.rpm
}

main
