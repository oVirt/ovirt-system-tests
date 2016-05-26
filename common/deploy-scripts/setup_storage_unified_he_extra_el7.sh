#!/bin/bash -xe
set -xe
HE_DEV="vde"


setup_device() {
    local device=$1
    local mountpath=$2
    local exportpath=$3
    mkdir -p "${mountpath}"
    echo noop > "/sys/block/${device}/queue/scheduler"
    mkfs.xfs -K -r extsize=1m "/dev/${device}"
    echo "/dev/${device} ${mountpath} xfs defaults 0 0" >> /etc/fstab
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
}

main
